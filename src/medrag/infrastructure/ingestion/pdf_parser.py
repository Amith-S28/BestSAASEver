"""Layout-aware PDF parser for diagnostic laboratory panels."""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber

from medrag.domain.exceptions import IngestionCorruptedException
from medrag.domain.patient import LabObservation, ObservationFlag
from medrag.infrastructure.ontology.entity_linker import RuleBasedEntityLinker


class PDFLabParser:
    """Tier 1 layout-aware diagnostic PDF lab parser using pdfplumber."""

    def __init__(self) -> None:
        self.entity_linker = RuleBasedEntityLinker()

    @staticmethod
    def _parse_numeric_and_unit(val_str: str) -> Tuple[float, str]:
        """Separate numeric value from unit in strings like '1.8 mg/dL' or '140'."""
        clean = val_str.strip()
        match = re.search(r"^([<>]?\s*\d+\.?\d*)\s*(.*)$", clean)
        if match:
            num_part = match.group(1).replace("<", "").replace(">", "").strip()
            unit_part = match.group(2).strip()
            try:
                return float(num_part), unit_part
            except ValueError:
                return 0.0, unit_part
        return 0.0, ""

    @staticmethod
    def _parse_reference_range(range_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse reference intervals like '0.7 - 1.3' or '70-100'."""
        clean = range_str.strip()
        match = re.search(r"(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)", clean)
        if match:
            try:
                return float(match.group(1)), float(match.group(2))
            except ValueError:
                return None, None
        return None, None

    @staticmethod
    def _determine_flag(val: float, low: Optional[float], high: Optional[float], raw_flag: str) -> ObservationFlag:
        """Derive observation flag from parsed text and reference ranges."""
        rf = raw_flag.upper().strip()
        if rf in ("CH", "CRIT", "CRITICAL", "HH", "CRIT_H"):
            return ObservationFlag.CRITICAL_HIGH
        if rf in ("CL", "CRIT_L", "LL"):
            return ObservationFlag.CRITICAL_LOW
        if rf in ("H", "HIGH", "*"):
            return ObservationFlag.HIGH
        if rf in ("L", "LOW"):
            return ObservationFlag.LOW

        if low is not None and val < low:
            if val < low * 0.7:
                return ObservationFlag.CRITICAL_LOW
            return ObservationFlag.LOW
        if high is not None and val > high:
            if val > high * 1.5:
                return ObservationFlag.CRITICAL_HIGH
            return ObservationFlag.HIGH

        return ObservationFlag.NORMAL

    async def parse_pdf(
        self, file_path: str, report_date: Optional[datetime] = None
    ) -> Tuple[List[LabObservation], float]:
        """Extract tabular lab observations from a PDF file.

        Returns:
            Tuple of (List[LabObservation], parse_confidence_score).
        """
        p = Path(file_path)
        if not p.exists():
            raise IngestionCorruptedException(p.name, "File does not exist")

        observations: List[LabObservation] = []
        observed_at = report_date or datetime.now(timezone.utc)
        total_cells_checked = 0
        valid_rows_parsed = 0

        try:
            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    raise IngestionCorruptedException(p.name, "PDF contains no pages")

                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        # Header identification
                        header = [str(col).lower().strip() if col else "" for col in table[0]]
                        total_cells_checked += len(header)

                        # Determine column mapping
                        test_col = 0
                        val_col = 1
                        ref_col = 2
                        flag_col = 3

                        for c_idx, col_name in enumerate(header):
                            if any(k in col_name for k in ("test", "analyte", "component")):
                                test_col = c_idx
                            elif any(k in col_name for k in ("result", "value")):
                                val_col = c_idx
                            elif any(k in col_name for k in ("reference", "interval", "normal", "range")):
                                ref_col = c_idx
                            elif any(k in col_name for k in ("flag", "status")):
                                flag_col = c_idx

                        # Process rows
                        for row in table[1:]:
                            if not row or len(row) <= test_col or not row[test_col]:
                                continue

                            test_name = str(row[test_col]).strip()
                            if not test_name or test_name.lower().startswith("test"):
                                continue

                            val_raw = str(row[val_col]).strip() if len(row) > val_col and row[val_col] else ""
                            ref_raw = str(row[ref_col]).strip() if len(row) > ref_col and row[ref_col] else ""
                            flag_raw = str(row[flag_col]).strip() if len(row) > flag_col and row[flag_col] else ""

                            num_val, unit = self._parse_numeric_and_unit(val_raw)
                            ref_low, ref_high = self._parse_reference_range(ref_raw)
                            flag = self._determine_flag(num_val, ref_low, ref_high, flag_raw)

                            # Ontology extraction for analyte
                            loinc_results = await self.entity_linker.extract_loinc(test_name)
                            snomed_results = await self.entity_linker.extract_snomed(test_name)

                            loinc_code = loinc_results[0][0] if loinc_results else ""
                            snomed_code = snomed_results[0][0] if snomed_results else ""

                            obs = LabObservation(
                                code_snomed=snomed_code,
                                code_loinc=loinc_code,
                                display_name=test_name,
                                numeric_value=num_val,
                                unit=unit,
                                reference_low=ref_low,
                                reference_high=ref_high,
                                flag=flag,
                                observed_at=observed_at,
                                raw_text=f"{test_name}: {val_raw} (Ref: {ref_raw}) {flag_raw}".strip(),
                            )
                            observations.append(obs)
                            valid_rows_parsed += 1

        except Exception as e:
            if isinstance(e, IngestionCorruptedException):
                raise
            raise IngestionCorruptedException(p.name, f"PDF extraction failure: {e}")

        # Compute parse confidence
        if observations:
            parse_confidence = min(1.0, 0.70 + (valid_rows_parsed * 0.03))
        else:
            parse_confidence = 0.10

        return observations, parse_confidence
