"""Unit tests for download.py — PMC fetch, category mapping, synthetic PDF generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from medrag.download import (
    CATEGORY_FOLDERS,
    FOLDER_ORDER,
    PmcArticle,
    _parse_pmc_list,
    filter_medical_articles,
    get_folder_info,
    generate_synthetic_docs,
)


# ── PmcArticle parsing ──────────────────────────────────────────────────────


class TestParsePmcList:
    """Tests for _parse_pmc_list()."""

    def test_parses_valid_lines(self) -> None:
        text = (
            "File\tPMCID\tDOI\tCitation\n"
            "archive/PMC1234567.tar.gz\tPMC1234567\t10.1234/test\tDiabetes care in adults\n"
            "archive/PMC2345678.tar.gz\tPMC2345678\t10.5678/test\tCardiovascular risk factors\n"
        )
        result = _parse_pmc_list(text)
        assert len(result) == 2
        assert result[0].pmcid == "PMC1234567"
        assert result[0].doi == "10.1234/test"
        assert result[0].citation == "Diabetes care in adults"
        assert result[1].pmcid == "PMC2345678"

    def test_skips_header_line(self) -> None:
        text = "File\tPMCID\tDOI\tCitation\narchive/PMC123.tar.gz\tPMC123\t10.1\tTest article\n"
        result = _parse_pmc_list(text)
        assert len(result) == 1

    def test_skips_comment_lines(self) -> None:
        text = "# comment\narchive/PMC123.tar.gz\tPMC123\t10.1\tTest article\n"
        result = _parse_pmc_list(text)
        assert len(result) == 1

    def test_skips_short_lines(self) -> None:
        text = "only\ttwo\tcolumns\n"
        result = _parse_pmc_list(text)
        assert len(result) == 0

    def test_empty_input(self) -> None:
        assert _parse_pmc_list("") == []


# ── Category mapping ────────────────────────────────────────────────────────


class TestCategoryFolders:
    """Tests for CATEGORY_FOLDERS mapping."""

    def test_all_folders_have_keys(self) -> None:
        """Every category maps to a known folder key."""
        for cat, info in CATEGORY_FOLDERS.items():
            assert "key" in info
            assert info["key"] in FOLDER_ORDER

    def test_four_folders_exist(self) -> None:
        assert len(FOLDER_ORDER) == 4
        assert "me" in FOLDER_ORDER
        assert "mom" in FOLDER_ORDER
        assert "dad" in FOLDER_ORDER
        assert "sister" in FOLDER_ORDER

    def test_metabolic_maps_to_me(self) -> None:
        assert CATEGORY_FOLDERS["metabolic"]["key"] == "me"

    def test_breast_cancer_maps_to_mom(self) -> None:
        assert CATEGORY_FOLDERS["breast cancer"]["key"] == "mom"

    def test_cardiovascular_maps_to_dad(self) -> None:
        assert CATEGORY_FOLDERS["cardiovascular"]["key"] == "dad"

    def test_neurology_maps_to_sister(self) -> None:
        assert CATEGORY_FOLDERS["neurology"]["key"] == "sister"

    def test_respiratory_maps_to_me(self) -> None:
        assert CATEGORY_FOLDERS["respiratory"]["key"] == "me"


class TestGetFolderInfo:
    """Tests for get_folder_info()."""

    def test_me_folder(self) -> None:
        info = get_folder_info("me")
        assert info["name"] == "Me"
        assert info["relationship"] == "self"

    def test_mom_folder(self) -> None:
        info = get_folder_info("mom")
        assert info["name"] == "Mom"
        assert info["relationship"] == "mother"

    def test_dad_folder(self) -> None:
        info = get_folder_info("dad")
        assert info["name"] == "Dad"
        assert info["relationship"] == "father"

    def test_sister_folder(self) -> None:
        info = get_folder_info("sister")
        assert info["name"] == "Sister"
        assert info["relationship"] == "sibling"

    def test_unknown_folder(self) -> None:
        info = get_folder_info("unknown")
        assert info["name"] == "Unknown"
        assert info["relationship"] == "other"


# ── Article filtering ───────────────────────────────────────────────────────


class TestFilterMedicalArticles:
    """Tests for filter_medical_articles()."""

    def _make_articles(self, citations: list[str]) -> list[PmcArticle]:
        return [
            PmcArticle(pmcid=f"PMC{i:07d}", doi="10.1/test", citation=c)
            for i, c in enumerate(citations)
        ]

    def test_matches_diabetes_to_me(self) -> None:
        articles = self._make_articles([
            "Diabetes management in primary care",
            "Osteoporosis screening guidelines",
        ])
        result = filter_medical_articles(articles, limit=2)
        assert len(result) == 2
        # Diabetes should map to "me"
        assert result[0][1] == "me"

    def test_matches_breast_cancer_to_mom(self) -> None:
        articles = self._make_articles(["Breast cancer genetic testing"])
        result = filter_medical_articles(articles, limit=1)
        assert result[0][1] == "mom"

    def test_matches_heart_to_dad(self) -> None:
        articles = self._make_articles(["Heart failure treatment protocols"])
        result = filter_medical_articles(articles, limit=1)
        assert result[0][1] == "dad"

    def test_matches_epilepsy_to_sister(self) -> None:
        articles = self._make_articles(["Epilepsy seizure classification update"])
        result = filter_medical_articles(articles, limit=1)
        assert result[0][1] == "sister"

    def test_matches_asthma_to_me(self) -> None:
        articles = self._make_articles(["Asthma inhaler technique review"])
        result = filter_medical_articles(articles, limit=1)
        assert result[0][1] == "me"

    def test_respects_limit(self) -> None:
        articles = self._make_articles([f"Article {i}" for i in range(100)])
        result = filter_medical_articles(articles, limit=10)
        assert len(result) <= 10

    def test_distributes_across_folders(self) -> None:
        articles = self._make_articles([f"Generic article {i}" for i in range(25)])
        result = filter_medical_articles(articles, limit=25)
        folder_counts: dict[str, int] = {}
        for _, folder_key in result:
            folder_counts[folder_key] = folder_counts.get(folder_key, 0) + 1
        # Should have at least some docs in multiple folders
        assert len(folder_counts) > 1

    def test_empty_articles(self) -> None:
        assert filter_medical_articles([], limit=10) == []


# ── Synthetic PDF generation ────────────────────────────────────────────────


class TestGenerateSyntheticDocs:
    """Tests for generate_synthetic_docs()."""

    def test_generates_pdfs_for_me(self, tmp_path: Path) -> None:
        paths = generate_synthetic_docs(tmp_path, "me", count=2)
        assert len(paths) >= 1
        for p in paths:
            assert p.exists()
            assert p.suffix == ".pdf"
            assert p.stat().st_size > 0

    def test_generates_pdfs_for_mom(self, tmp_path: Path) -> None:
        paths = generate_synthetic_docs(tmp_path, "mom", count=2)
        assert len(paths) >= 1
        for p in paths:
            assert p.exists()

    def test_generates_pdfs_for_dad(self, tmp_path: Path) -> None:
        paths = generate_synthetic_docs(tmp_path, "dad", count=2)
        assert len(paths) >= 1

    def test_generates_pdfs_for_sister(self, tmp_path: Path) -> None:
        paths = generate_synthetic_docs(tmp_path, "sister", count=2)
        assert len(paths) >= 1

    def test_respects_count(self, tmp_path: Path) -> None:
        paths = generate_synthetic_docs(tmp_path, "me", count=1)
        assert len(paths) <= 1

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        dest = tmp_path / "new_dir"
        paths = generate_synthetic_docs(dest, "me", count=1)
        assert dest.exists()