"""Dynamic Medical Model Router — selects verified free LLM tiers by complexity."""

from __future__ import annotations

from medrag.config import settings

TIER_1_MODEL = "inclusionai/ling-3.0-flash:free"        # 262k ctx, NovitaAI / InclusionAI
TIER_2_MODEL = "poolside/laguna-s-2.1:free"              # 262k ctx, Poolside
TIER_3_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  # 1M ctx, NVIDIA

RISK_KEYWORDS = frozenset({
    "risk", "future", "prognosis", "lifestyle", "complication",
    "hereditary", "genetics", "genetic", "longitudinal", "outcome",
    "family history", "cancer", "cardiovascular", "stroke", "diabetes risk",
    "prediction", "screening", "preventive",
})

LARGE_CONTEXT_THRESHOLD = 20_000


class LLMRouter:
    """Classifies query intent & context token volume to select optimal LLM tier.

    Routing priority (first match wins):
      1. MODE=local → local LM Studio model (bypass cloud routing)
      2. Risk keywords or cross_folders → Tier 3 (Nemotron reasoning)
      3. Context > 20k tokens → Tier 2 (Laguna multi-doc synthesis)
      4. Everything else → Tier 1 (Ling Flash fast lookup)
    """

    @staticmethod
    def select_model(
        query: str,
        context_documents: list[tuple[str, str, str]],
        cross_folders: bool = False,
    ) -> tuple[str, str]:
        """Return (model_id, human_readable_reason).

        When MODE=local, returns the local LM Studio model regardless of query.
        When ROUTER_MODE != "auto", returns the specified tier's model.
        """
        # ── Local/offline mode: bypass cloud routing entirely ────────
        if settings.mode.lower() == "local":
            return settings.lmstudio_model, "MODE=local (Offline LM Studio)"

        # ── Manual tier override ──────────────────────────────────────
        if settings.router_mode == "tier1":
            return TIER_1_MODEL, "Manual override (tier1)"
        if settings.router_mode == "tier2":
            return TIER_2_MODEL, "Manual override (tier2)"
        if settings.router_mode == "tier3":
            return TIER_3_MODEL, "Manual override (tier3)"

        query_lower = query.lower()

        # ── Tier 3: Complex risk / hereditary reasoning ──────────────
        if cross_folders or any(kw in query_lower for kw in RISK_KEYWORDS):
            return TIER_3_MODEL, "Tier 3: Reasoning & Prognosis -> Nemotron 3 Ultra (550B MoE CoT)"

        # ── Tier 2: Large context volume ─────────────────────────────
        total_tokens = sum(len(md) // 4 for _, md, _ in context_documents)
        if total_tokens > LARGE_CONTEXT_THRESHOLD:
            return TIER_2_MODEL, f"Tier 2: Large Context ({total_tokens:,} tokens) -> Laguna S 2.1"

        # ── Tier 1: Fast routine lookups ─────────────────────────────
        return TIER_1_MODEL, "Tier 1: Fast Lookup -> Ling 3.0 Flash"
