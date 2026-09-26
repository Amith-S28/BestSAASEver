"""Integration tests for layout-aware PDF lab parser."""

from unittest.mock import MagicMock, patch
import pytest

from medrag.domain.exceptions import IngestionCorruptedException
from medrag.domain.patient import ObservationFlag
from medrag.infrastructure.ingestion.pdf_parser import PDFLabParser


@pytest.mark.asyncio
async def test_pdf_lab_parser_extraction_with_table(tmp_path):
    """PDF parser extracts table rows, LOINC codes, reference intervals, and severity flags."""
    dummy_pdf = tmp_path / "sample_lab_report.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content")

    mock_table = [
        ["Test Name", "Result", "Reference Range", "Flag"],
        ["Serum Creatinine", "2.1 mg/dL", "0.7 - 1.3", "H"],
        ["Potassium", "6.4 mmol/L", "3.5 - 5.1", "CRIT"],
        ["eGFR", "28 mL/min", "> 60", "L"],
    ]

    mock_page = MagicMock()
    mock_page.extract_tables.return_value = [mock_table]

    mock_pdf_doc = MagicMock()
    mock_pdf_doc.pages = [mock_page]
    mock_pdf_doc.__enter__.return_value = mock_pdf_doc
    mock_pdf_doc.__exit__.return_value = None

    parser = PDFLabParser()

    with patch("pdfplumber.open", return_value=mock_pdf_doc):
        observations, confidence = await parser.parse_pdf(str(dummy_pdf))

    assert len(observations) == 3
    assert confidence >= 0.70

    # Creatinine check
    creat_obs = observations[0]
    assert creat_obs.display_name == "Serum Creatinine"
    assert creat_obs.code_loinc == "2160-0"
    assert creat_obs.numeric_value == 2.1
    assert creat_obs.unit == "mg/dL"
    assert creat_obs.reference_low == 0.7
    assert creat_obs.reference_high == 1.3
    assert creat_obs.flag == ObservationFlag.HIGH

    # Potassium check (Critical High)
    k_obs = observations[1]
    assert k_obs.display_name == "Potassium"
    assert k_obs.code_loinc == "2823-3"
    assert k_obs.numeric_value == 6.4
    assert k_obs.flag == ObservationFlag.CRITICAL_HIGH


@pytest.mark.asyncio
async def test_pdf_lab_parser_missing_file():
    """Non-existent file raises IngestionCorruptedException."""
    parser = PDFLabParser()
    with pytest.raises(IngestionCorruptedException):
        await parser.parse_pdf("non_existent_file.pdf")
