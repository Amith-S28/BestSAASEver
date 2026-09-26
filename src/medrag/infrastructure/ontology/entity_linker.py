"""Clinical ontology entity linker extracting SNOMED-CT, RxNorm, and LOINC codes."""

import re
from typing import Dict, List, Tuple


class RuleBasedEntityLinker:
    """Clinical entity linker extracting standard medical ontology codes.

    Implements medrag.ports.ontology.IEntityLinker.
    Maps clinical terms, finding synonyms, and medication names to canonical codes.
    """

    # SNOMED-CT dictionary: lowercase trigger term -> (code, canonical display name)
    SNOMED_MAP: Dict[str, Tuple[str, str]] = {
        "acute kidney injury": ("14669001", "Acute kidney injury"),
        "aki": ("14669001", "Acute kidney injury"),
        "chronic kidney disease": ("709044004", "Chronic kidney disease"),
        "ckd": ("709044004", "Chronic kidney disease"),
        "renal failure": ("709044004", "Chronic kidney disease"),
        "type 2 diabetes": ("44054006", "Type 2 diabetes mellitus"),
        "type 2 diabetes mellitus": ("44054006", "Type 2 diabetes mellitus"),
        "diabetes": ("44054006", "Type 2 diabetes mellitus"),
        "hypertension": ("38341003", "Essential hypertension"),
        "high blood pressure": ("38341003", "Essential hypertension"),
        "heart failure": ("84114007", "Heart failure"),
        "congestive heart failure": ("84114007", "Heart failure"),
        "atrial fibrillation": ("49436004", "Atrial fibrillation"),
        "afib": ("49436004", "Atrial fibrillation"),
        "sepsis": ("91302008", "Sepsis"),
        "pneumonia": ("233604007", "Pneumonia"),
        "proteinuria": ("29738008", "Proteinuria"),
        "edema": ("267038008", "Edema"),
        "hyperkalemia": ("14140009", "Hyperkalemia"),
        "hypokalemia": ("43339006", "Hypokalemia"),
    }

    # RxNorm dictionary: lowercase drug name -> (RxNorm code, drug name)
    RXNORM_MAP: Dict[str, Tuple[str, str]] = {
        "lisinopril": ("316049", "Lisinopril"),
        "amlodipine": ("197361", "Amlodipine"),
        "metformin": ("6809", "Metformin"),
        "furosemide": ("4603", "Furosemide"),
        "lasix": ("4603", "Furosemide"),
        "atorvastatin": ("83367", "Atorvastatin"),
        "lipitor": ("83367", "Atorvastatin"),
        "levothyroxine": ("10582", "Levothyroxine"),
        "aspirin": ("1191", "Aspirin"),
        "heparin": ("5224", "Heparin"),
        "losartan": ("52175", "Losartan"),
        "metoprolol": ("6918", "Metoprolol"),
        "insulin": ("5856", "Insulin"),
    }

    # LOINC dictionary: lowercase analyte / test name -> (LOINC code, test name)
    LOINC_MAP: Dict[str, Tuple[str, str]] = {
        "creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma"),
        "serum creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma"),
        "egfr": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted"),
        "gfr": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted"),
        "potassium": ("2823-3", "Potassium [Moles/volume] in Serum or Plasma"),
        "sodium": ("2951-2", "Sodium [Moles/volume] in Serum or Plasma"),
        "hemoglobin a1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood"),
        "hba1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood"),
        "a1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood"),
        "wbc": ("6690-2", "Leukocytes [#/volume] in Blood by Automated count"),
        "white blood cell": ("6690-2", "Leukocytes [#/volume] in Blood by Automated count"),
        "platelets": ("777-3", "Platelets [#/volume] in Blood by Automated count"),
        "bun": ("3094-0", "Urea nitrogen [Mass/volume] in Serum or Plasma"),
        "blood urea nitrogen": ("3094-0", "Urea nitrogen [Mass/volume] in Serum or Plasma"),
        "urine protein": ("2888-6", "Protein [Mass/volume] in Urine"),
    }

    async def extract_snomed(self, text: str) -> List[Tuple[str, str]]:
        """Extract SNOMED-CT codes found in clinical text."""
        lower_text = text.lower()
        extracted: Dict[str, Tuple[str, str]] = {}

        # Sort keys by length descending to match longest phrases first
        for phrase in sorted(self.SNOMED_MAP.keys(), key=len, reverse=True):
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if re.search(pattern, lower_text):
                code, name = self.SNOMED_MAP[phrase]
                extracted[code] = (code, name)

        return list(extracted.values())

    async def extract_rxnorm(self, text: str) -> List[Tuple[str, str]]:
        """Extract RxNorm drug codes found in clinical text."""
        lower_text = text.lower()
        extracted: Dict[str, Tuple[str, str]] = {}

        for drug in sorted(self.RXNORM_MAP.keys(), key=len, reverse=True):
            pattern = r"\b" + re.escape(drug) + r"\b"
            if re.search(pattern, lower_text):
                code, name = self.RXNORM_MAP[drug]
                extracted[code] = (code, name)

        return list(extracted.values())

    async def extract_loinc(self, text: str) -> List[Tuple[str, str]]:
        """Extract LOINC laboratory observation codes found in clinical text."""
        lower_text = text.lower()
        extracted: Dict[str, Tuple[str, str]] = {}

        for test in sorted(self.LOINC_MAP.keys(), key=len, reverse=True):
            pattern = r"\b" + re.escape(test) + r"\b"
            if re.search(pattern, lower_text):
                code, name = self.LOINC_MAP[test]
                extracted[code] = (code, name)

        return list(extracted.values())
