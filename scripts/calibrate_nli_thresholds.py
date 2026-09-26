"""NLI Decision Boundary and Threshold Calibration Harness."""

import asyncio
from pathlib import Path
import sys
from typing import Dict, List, Tuple

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medrag.domain.citation import ClinicalClaim, VerificationStatus
from medrag.domain.literature import MedicalChunk
from medrag.infrastructure.models.nli_verifier import DeterministicNLIVerifier

# Gold calibration dataset: (claim_text, premise_text, expected_status)
CALIBRATION_SET: List[Tuple[str, str, VerificationStatus]] = [
    (
        "Discontinue Lisinopril immediately in hyperkalemic crisis [^1].",
        "Discontinue Lisinopril promptly in the setting of severe hyperkalemia.",
        VerificationStatus.VERIFIED,
    ),
    (
        "Continue Lisinopril at maximum dosage [^1].",
        "Discontinue Lisinopril promptly in the setting of severe hyperkalemia.",
        VerificationStatus.CONTRADICTED,
    ),
    (
        "Consider dietary modifications and hydration [^1].",
        "Discontinue Lisinopril promptly in the setting of severe hyperkalemia.",
        VerificationStatus.UNCERTAIN,
    ),
    (
        "Patient underwent prior appendectomy without complications.",
        "Discontinue Lisinopril promptly in the setting of severe hyperkalemia.",
        VerificationStatus.UNGROUNDED,
    ),
]


async def run_calibration() -> Dict[str, float]:
    """Test standard thresholds against gold clinical set."""
    verifier = DeterministicNLIVerifier(entailment_threshold=0.85, contradiction_threshold=0.60)
    correct = 0
    total = len(CALIBRATION_SET)

    for idx, (claim_text, premise_text, expected) in enumerate(CALIBRATION_SET):
        chunk = MedicalChunk(
            chunk_id="chk-calib-1",
            document_id="doc-calib",
            title="Calibration Reference",
            chapter="Ch. 1",
            page_number=1,
            text_content=premise_text,
            specialty="Internal Medicine",
        )
        claim = ClinicalClaim(
            claim_id=f"clm-calib-{idx}",
            sentence_text=claim_text,
            sentence_index=idx,
            cited_chunk_ids=["chk-calib-1"] if "[^1]" in claim_text else [],
        )

        fn = await verifier.verify_claim(claim, [chunk])
        if fn.status == expected:
            correct += 1

    accuracy = correct / total
    return {
        "entailment_threshold": 0.85,
        "contradiction_threshold": 0.60,
        "calibration_accuracy": accuracy,
        "cases_evaluated": total,
    }


if __name__ == "__main__":
    res = asyncio.run(run_calibration())
    print("NLI Calibration Result:", res)
