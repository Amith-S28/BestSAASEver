"""Unit tests for Dynamic Medical Model Router."""

from medrag.config import settings
from medrag.synthesis.router import (
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    LLMRouter,
)


def test_router_routine_lookup():
    """Simple lab value queries route to Tier 1 (fast)."""
    model, reason = LLMRouter.select_model("What is my blood glucose value?", [])
    assert model == TIER_1_MODEL
    assert "Tier 1" in reason


def test_router_risk_keyword():
    """Risk-related queries route to Tier 3 (reasoning)."""
    model, reason = LLMRouter.select_model("What future cardiovascular risks do I face?", [])
    assert model == TIER_3_MODEL
    assert "Tier 3" in reason


def test_router_cross_folders():
    """cross_folders=True forces Tier 3 (hereditary analysis)."""
    model, reason = LLMRouter.select_model(
        "Compare lab results across family", [], cross_folders=True
    )
    assert model == TIER_3_MODEL
    assert "Tier 3" in reason


def test_router_large_context():
    """Large context (>20k tokens) routes to Tier 2 (multi-doc synthesis)."""
    long_docs = [("file1.pdf", "x" * 100000, "default")]
    model, reason = LLMRouter.select_model("Summarize my full medical history", long_docs)
    assert model == TIER_2_MODEL
    assert "Tier 2" in reason


def test_router_local_mode_override():
    """MODE=local bypasses cloud routing entirely."""
    original_mode = settings.mode
    try:
        settings.mode = "local"
        model, reason = LLMRouter.select_model("What is my blood pressure?", [])
        assert "MODE=local" in reason
    finally:
        settings.mode = original_mode


def test_router_manual_tier_override():
    """ROUTER_MODE=tierN correctly maps to the corresponding model (not a single default)."""
    original_router_mode = settings.router_mode
    original_mode = settings.mode
    try:
        settings.mode = "cloud"  # Ensure local mode doesn't take precedence

        settings.router_mode = "tier3"
        model, reason = LLMRouter.select_model("What is my blood pressure?", [])
        assert model == TIER_3_MODEL
        assert "tier3" in reason.lower()

        settings.router_mode = "tier2"
        model, _ = LLMRouter.select_model("What is my blood pressure?", [])
        assert model == TIER_2_MODEL

        settings.router_mode = "tier1"
        model, _ = LLMRouter.select_model("What is my blood pressure?", [])
        assert model == TIER_1_MODEL
    finally:
        settings.router_mode = original_router_mode
        settings.mode = original_mode
