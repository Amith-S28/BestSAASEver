"""MedQA Clinical Benchmark and Faithfulness Evaluation Harness."""

import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medrag.application.services.claim_auditor import ClaimAuditor
from medrag.domain.citation import VerificationStatus
from medrag.domain.literature import MedicalChunk
from medrag.infrastructure.models.nli_verifier import DeterministicNLIVerifier

# Sample curated clinical USMLE/MedQA questions with verified gold citations
SAMPLE_BENCHMARKS = [
    {
        "case_id": "medqa-001",
        "question": "A 58-year-old male with acute decompensated heart failure presents with hyperkalemia (K+ 6.2 mEq/L) and elevated creatinine (3.4 mg/dL). Should ACE inhibitors be continued?",
        "ground_truth_directive": "discontinue",
        "evidence": MedicalChunk(
            chunk_id="chk-kdigo-aki-1",
            document_id="kdigo-2023",
            title="KDIGO Clinical Practice Guideline for Acute Kidney Injury",
            chapter="Chapter 3.2: Drug-Induced AKI",
            page_number=45,
            text_content="Discontinue ACE inhibitors and ARBs promptly in setting of severe hyperkalemia or acute renal deterioration.",
            specialty="Nephrology",
            corpus_license_tier="tier1_open",
        ),
        "candidate_synthesis": "Discontinue ACE inhibitors promptly in setting of acute renal deterioration [^1]. Discontinue ARBs promptly in setting of severe hyperkalemia [^1].",
    },
    {
        "case_id": "medqa-002",
        "question": "A 45-year-old female presents with acute coronary syndrome and signs of ST-elevation myocardial infarction. What initial antiplatelet loading regimen is recommended?",
        "ground_truth_directive": "aspirin",
        "evidence": MedicalChunk(
            chunk_id="chk-acc-aha-stemi-1",
            document_id="acc-aha-2022",
            title="ACC/AHA Guideline for Management of STEMI",
            chapter="Chapter 4: Acute Pharmacotherapy",
            page_number=112,
            text_content="Aspirin 162 to 325 mg should be administered immediately to all patients with suspected STEMI unless contraindications exist.",
            specialty="Cardiology",
            corpus_license_tier="tier1_open",
        ),
        "candidate_synthesis": "Aspirin 162 to 325 mg should be administered immediately to patients with suspected STEMI [^1]. Suspected STEMI requires immediate Aspirin administration [^1].",
    },
]


async def evaluate_medqa_benchmarks() -> Dict[str, Any]:
    """Execute MedQA clinical scenario evaluation."""
    verifier = DeterministicNLIVerifier()
    auditor = ClaimAuditor(verifier=verifier)

    results: List[Dict[str, Any]] = []
    total_claims = 0
    verified_claims = 0
    contradicted_claims = 0

    start_time = time.time()

    for item in SAMPLE_BENCHMARKS:
        report = await auditor.audit_synthesis(
            query_text=item["question"],
            raw_synthesis=item["candidate_synthesis"],
            evidence_chunks=[item["evidence"]],
        )

        for fn in report.verified_footnotes:
            total_claims += 1
            if fn.status == VerificationStatus.VERIFIED:
                verified_claims += 1
            elif fn.status == VerificationStatus.CONTRADICTED:
                contradicted_claims += 1

        results.append({
            "case_id": item["case_id"],
            "query": item["question"][:60] + "...",
            "claims_count": len(report.verified_footnotes),
            "redacted_count": report.redacted_claim_count,
            "faithfulness": report.overall_faithfulness,
        })

    elapsed_ms = int((time.time() - start_time) * 1000)
    faithfulness_rate = (verified_claims / total_claims) if total_claims > 0 else 0.0
    contradiction_rate = (contradicted_claims / total_claims) if total_claims > 0 else 0.0

    summary = {
        "benchmark_suite": "MedQA-Mini-Validation-v2",
        "total_cases": len(SAMPLE_BENCHMARKS),
        "total_claims_evaluated": total_claims,
        "overall_faithfulness": round(faithfulness_rate, 4),
        "contradiction_rate": round(contradiction_rate, 4),
        "elapsed_ms": elapsed_ms,
        "passed": faithfulness_rate >= 0.85 and contradiction_rate == 0.0,
        "cases": results,
    }
    return summary


if __name__ == "__main__":
    result = asyncio.run(evaluate_medqa_benchmarks())
    print(json.dumps(result, indent=2))
