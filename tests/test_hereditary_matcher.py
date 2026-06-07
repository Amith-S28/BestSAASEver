"""Unit tests for hereditary_matcher.py — query-time relevance matching."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from medrag.synthesis.hereditary_cache import HereditaryCondition, save_cache
from medrag.synthesis.hereditary_matcher import (
    build_relevant_reference,
    build_fallback_reference,
    _cosine_similarity,
    _format_condition_entry,
    _format_header,
    _build_inheritance_description,
    MEDICAL_DISCLAIMER,
    RISK_COMMUNICATION_RULES,
    HEREDITARY_SEARCH_DISCLAIMER,
)


def _make_condition(cui: str = "C0000001", title: str = "Test Disease") -> HereditaryCondition:
    """Create a test HereditaryCondition."""
    return HereditaryCondition(
        cui=cui,
        title=title,
        definition="A test disease",
        inheritance_modes=("autosomal dominant",),
        genes=("GENE1",),
        clinical_features=("fever", "fatigue"),
        sources=("medgen", "hpo"),
        last_updated="2026-01-01",
    )


class TestCosineSimilarity:
    """Tests for _cosine_similarity()."""

    def test_identical_vectors(self) -> None:
        vec = np.array([1.0, 0.0, 0.0])
        embeddings = np.array([[1.0, 0.0, 0.0]])
        scores = _cosine_similarity(vec, embeddings)
        assert scores[0] == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors(self) -> None:
        vec = np.array([1.0, 0.0, 0.0])
        embeddings = np.array([[0.0, 1.0, 0.0]])
        scores = _cosine_similarity(vec, embeddings)
        assert scores[0] == pytest.approx(0.0, abs=1e-5)

    def test_multiple_embeddings(self) -> None:
        vec = np.array([1.0, 0.0, 0.0])
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
        ])
        scores = _cosine_similarity(vec, embeddings)
        assert scores[0] == pytest.approx(1.0, abs=1e-5)
        assert scores[1] == pytest.approx(0.0, abs=1e-5)
        assert scores[2] == pytest.approx(0.707, abs=0.01)


class TestFormatConditionEntry:
    """Tests for _format_condition_entry()."""

    def test_includes_cui_and_sources(self) -> None:
        cond = _make_condition(cui="C0020179", title="Huntington disease")
        entry = _format_condition_entry(cond)
        assert "Huntington disease" in entry
        assert "C0020179" in entry
        assert "medgen" in entry

    def test_includes_clinical_features(self) -> None:
        cond = _make_condition()
        entry = _format_condition_entry(cond)
        assert "fever" in entry
        assert "fatigue" in entry

    def test_includes_inheritance_description(self) -> None:
        cond = _make_condition()
        entry = _format_condition_entry(cond)
        assert "50% probability" in entry
        assert "pathogenic variant" in entry


class TestFormatHeader:
    """Tests for _format_header()."""

    def test_includes_all_info(self) -> None:
        header = _format_header(
            total_conditions=3500,
            shown_count=15,
            last_sync="2026-06-07T12:00:00Z",
        )
        assert "3500" in header
        assert "15" in header
        assert "2026-06-07" in header
        assert "MedGen" in header
        assert "HPO" in header
        assert "GeneReviews" in header


class TestBuildInheritanceDescription:
    """Tests for _build_inheritance_description()."""

    def test_autosomal_dominant(self) -> None:
        desc = _build_inheritance_description(("autosomal dominant",))
        assert "50% probability" in desc
        assert "pathogenic variant" in desc

    def test_autosomal_recessive(self) -> None:
        desc = _build_inheritance_description(("autosomal recessive",))
        assert "25% probability" in desc

    def test_multifactorial(self) -> None:
        desc = _build_inheritance_description(("multifactorial",))
        assert "multifactorial" in desc.lower()

    def test_multiple_modes(self) -> None:
        desc = _build_inheritance_description(("autosomal dominant", "mitochondrial"))
        assert "50% probability" in desc
        assert "maternally" in desc.lower()

    def test_empty(self) -> None:
        assert _build_inheritance_description(()) == ""


class TestBuildRelevantReference:
    """Tests for build_relevant_reference()."""

    def test_fallback_when_no_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("medrag.synthesis.hereditary_cache.settings.hereditary_cache_dir", str(tmp_path))
        ref = build_relevant_reference(query_vector=None, query_text="test")
        # Should contain fallback data
        assert "fallback" in ref.lower() or "FALLBACK" in ref
        assert MEDICAL_DISCLAIMER in ref

    def test_relevance_matching(self, tmp_path: Path, monkeypatch: pytest.MonkeyFit) -> None:
        # Create a small test cache
        conditions = [
            _make_condition("C0000001", "Breast Cancer"),
            _make_condition("C0000002", "Huntington Disease"),
            _make_condition("C0000003", "Diabetes Type 2"),
        ]
        # Create embeddings where breast cancer is most similar to "cancer" query
        embeddings = np.zeros((3, 384), dtype=np.float32)
        embeddings[0, 0] = 1.0  # breast cancer — high similarity with [1,0,...]
        embeddings[1, 1] = 1.0  # huntington
        embeddings[2, 2] = 1.0  # diabetes

        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)
        monkeypatch.setattr("medrag.synthesis.hereditary_cache.settings.hereditary_cache_dir", str(tmp_path))

        # Query vector pointing toward breast cancer
        query_vec = np.zeros(384, dtype=np.float32)
        query_vec[0] = 1.0

        ref = build_relevant_reference(
            query_vector=query_vec, query_text="breast cancer", max_conditions=2,
        )
        assert "Breast Cancer" in ref
        assert "Huntington Disease" not in ref

    def test_includes_disclaimer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("medrag.synthesis.hereditary_cache.settings.hereditary_cache_dir", str(tmp_path))
        ref = build_relevant_reference(query_vector=None, query_text="test")
        assert MEDICAL_DISCLAIMER in ref
        assert RISK_COMMUNICATION_RULES in ref

    def test_includes_source_attribution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        conditions = [_make_condition("C0020179", "Huntington disease")]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)
        monkeypatch.setattr("medrag.synthesis.hereditary_cache.settings.hereditary_cache_dir", str(tmp_path))

        query_vec = embeddings[0]  # perfect match
        ref = build_relevant_reference(query_vector=query_vec, query_text="huntington")
        assert "MedGen" in ref
        assert "C0020179" in ref


class TestBuildFallbackReference:
    """Tests for build_fallback_reference()."""

    def test_contains_conditions(self) -> None:
        ref = build_fallback_reference()
        # Should contain at least some of the fallback conditions
        assert "Breast" in ref or "Diabetes" in ref or "Huntington" in ref

    def test_contains_disclaimer(self) -> None:
        ref = build_fallback_reference()
        assert MEDICAL_DISCLAIMER in ref
        assert "NOT personalized medical advice" in ref

    def test_contains_risk_rules(self) -> None:
        ref = build_fallback_reference()
        assert RISK_COMMUNICATION_RULES in ref
        assert "NEVER state" in ref

    def test_no_patient_specific_language_in_conditions(self) -> None:
        ref = build_fallback_reference()
        # Split into sections — the disclaimer/rules sections contain
        # negative examples ("Do NOT say: 'You have...'"), which is fine.
        # Only check the condition entries section.
        parts = ref.split("IMPORTANT MEDICAL DISCLAIMERS")
        conditions_section = parts[0] if parts else ref
        lower = conditions_section.lower()
        assert "you have" not in lower
        assert "your chance" not in lower
        assert "your risk" not in lower

    def test_includes_fallback_notice(self) -> None:
        ref = build_fallback_reference()
        assert "fallback" in ref.lower()
        assert "sync-hereditary" in ref


class TestDisclaimerText:
    """Tests for the disclaimer text content."""

    def test_disclaimer_mentions_gina(self) -> None:
        assert "GINA" in MEDICAL_DISCLAIMER

    def test_disclaimer_mentions_medgen(self) -> None:
        assert "MedGen" in MEDICAL_DISCLAIMER

    def test_disclaimer_mentions_hpo(self) -> None:
        assert "HPO" in MEDICAL_DISCLAIMER

    def test_search_disclaimer_is_shorter(self) -> None:
        assert len(HEREDITARY_SEARCH_DISCLAIMER) < len(MEDICAL_DISCLAIMER)
        assert "educational purposes" in HEREDITARY_SEARCH_DISCLAIMER

    def test_risk_rules_ban_patient_specific(self) -> None:
        assert "NEVER" in RISK_COMMUNICATION_RULES
        assert "50% probability of inheriting the pathogenic variant" in RISK_COMMUNICATION_RULES