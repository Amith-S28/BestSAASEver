"""Benchmark integration test evaluating MedQA clinical scenarios and threshold calibration."""

import pytest
from scripts.calibrate_nli_thresholds import run_calibration
from scripts.run_medqa_benchmarks import evaluate_medqa_benchmarks
from scripts.verify_corpus_licenses import audit_chunks_licensing
from medrag.domain.literature import MedicalChunk


@pytest.mark.asyncio
async def test_medqa_benchmark_evaluation():
    """MedQA scenarios meet institutional faithfulness >= 0.85 and zero unredacted contradictions."""
    result = await evaluate_medqa_benchmarks()
    assert result["passed"] is True
    assert result["overall_faithfulness"] >= 0.85
    assert result["contradiction_rate"] == 0.0


@pytest.mark.asyncio
async def test_nli_threshold_calibration():
    """Calibration set verifies expected statuses with accuracy >= 0.75."""
    res = await run_calibration()
    assert res["calibration_accuracy"] >= 0.75


def test_corpus_licensing_audit():
    """All institutional chunks must carry valid licensing tier."""
    chunks = [
        MedicalChunk(
            chunk_id="chk-1",
            document_id="doc-1",
            title="Harrison's",
            chapter="Ch. 1",
            page_number=1,
            text_content="content",
            specialty="Internal Medicine",
            corpus_license_tier="tier1_open",
        ),
        MedicalChunk(
            chunk_id="chk-2",
            document_id="doc-2",
            title="Guyton",
            chapter="Ch. 2",
            page_number=2,
            text_content="content",
            specialty="Physiology",
            corpus_license_tier="tier2_institutional",
        ),
    ]
    report = audit_chunks_licensing(chunks)
    assert report["valid_compliance"] is True
    assert report["invalid_license_count"] == 0
