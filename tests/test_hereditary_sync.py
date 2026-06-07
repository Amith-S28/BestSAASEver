"""Unit tests for hereditary_sync.py — MedGen/HPO/GeneReviews sync pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from medrag.synthesis.hereditary_sync import (
    parse_mgconso,
    parse_mgsat_inheritance,
    parse_mgdef,
    parse_hpo_mapping,
    parse_genereviews,
    merge_conditions,
    _normalize_inheritance,
)


class TestParseMgconso:
    """Tests for MGCONSO.RRF parser.

    MGCONSO is pipe-delimited with many columns.
    Column 0 = CUI, Column 1 = ISPREF, Column 2 = STT, Column 14 = STR (name).
    We provide 17 columns (0-16) to match the expected format.
    """

    def test_extracts_preferred_names(self) -> None:
        # MGCONSO needs 16 fields (15 pipe separators) for index 14 = STR
        lines = [
            "C0000001|Y|PF||||||||||||Huntington disease|",
            "C0000002|N|PF||||||||||||Non-preferred name|",
            "C0000003|Y|SY||||||||||||Synonym name|",
        ]
        result = parse_mgconso(lines)
        assert "C0000001" in result
        assert result["C0000001"] == "Huntington disease"
        # C0000002 has ISPREF=N, should be excluded
        assert "C0000002" not in result
        # C0000003 has STT=SY (not PF), should be excluded
        assert "C0000003" not in result

    def test_empty_input(self) -> None:
        assert parse_mgconso([]) == {}


class TestParseMgsatInheritance:
    """Tests for MGSAT.RRF inheritance parser."""

    def test_extracts_inheritance_modes(self) -> None:
        lines = [
            "C0000001||||||||Mode_of_inheritance|Autosomal dominant inheritance|",
            "C0000002||||||||Mode_of_inheritance|Autosomal recessive inheritance|",
            "C0000001||||||||Other_attribute|Some value|",
        ]
        result = parse_mgsat_inheritance(lines)
        assert "C0000001" in result
        assert result["C0000001"] == ["Autosomal dominant inheritance"]
        assert "C0000002" in result
        assert result["C0000002"] == ["Autosomal recessive inheritance"]

    def test_ignores_non_inheritance_attributes(self) -> None:
        lines = [
            "C0000001||||||||Some_other_attr|Value|",
        ]
        result = parse_mgsat_inheritance(lines)
        assert result == {}


class TestParseMgdef:
    """Tests for MGDEF.RRF definition parser."""

    def test_extracts_definitions(self) -> None:
        lines = [
            "C0000001|A neurodegenerative disorder|",
            "C0000002|An autoimmune condition|",
        ]
        result = parse_mgdef(lines)
        assert result["C0000001"] == "A neurodegenerative disorder"
        assert result["C0000002"] == "An autoimmune condition"


class TestParseHpoMapping:
    """Tests for MedGen_HPO_Mapping.txt parser."""

    def test_extracts_phenotypes(self) -> None:
        lines = [
            "C0000001\tHP:0000001\tChorea",
            "C0000001\tHP:0000002\tDementia",
            "C0000002\tHP:0000003\tAnemia",
        ]
        result = parse_hpo_mapping(lines)
        assert "C0000001" in result
        assert "Chorea" in result["C0000001"]
        assert "Dementia" in result["C0000001"]
        assert result["C0000002"] == ["Anemia"]


class TestParseGenereviews:
    """Tests for GeneReviews_short_names.txt parser."""

    def test_extracts_gene_symbols(self) -> None:
        lines = [
            "Huntington Disease\tHTT\t143100\tC0000001",
            "Cystic Fibrosis\tCFTR\t219700\tC0000002",
            "Some Disease\t-\t-\tC0000003",
        ]
        result = parse_genereviews(lines)
        assert "C0000001" in result
        assert "HTT" in result["C0000001"]
        assert "C0000002" in result
        # Gene symbol "-" should be excluded
        assert "C0000003" not in result


class TestMergeConditions:
    """Tests for merge_conditions()."""

    def test_merges_data_sources(self) -> None:
        cui_to_name = {"C0000001": "Huntington disease"}
        cui_to_inheritance = {"C0000001": ["Autosomal dominant inheritance"]}
        cui_to_def = {"C0000001": "A neurodegenerative disorder"}
        cui_to_hpo = {"C0000001": ["Chorea", "Dementia"]}
        cui_to_genes = {"C0000001": ["HTT"]}

        result = merge_conditions(
            cui_to_name, cui_to_inheritance, cui_to_def,
            cui_to_hpo, cui_to_genes,
        )
        assert len(result) == 1
        assert result[0].cui == "C0000001"
        assert result[0].title == "Huntington disease"
        assert result[0].inheritance_modes == ("autosomal dominant",)
        assert result[0].genes == ("HTT",)
        assert "Chorea" in result[0].clinical_features
        assert "hpo" in result[0].sources
        assert "genereviews" in result[0].sources

    def test_excludes_conditions_without_names(self) -> None:
        cui_to_name = {}  # No names
        cui_to_inheritance = {"C0000001": ["Autosomal dominant inheritance"]}
        result = merge_conditions(cui_to_name, cui_to_inheritance, {}, {}, {})
        assert len(result) == 0

    def test_excludes_conditions_without_inheritance(self) -> None:
        cui_to_name = {"C0000001": "Some Disease"}
        cui_to_inheritance = {}  # No inheritance
        result = merge_conditions(cui_to_name, cui_to_inheritance, {}, {}, {})
        assert len(result) == 0


class TestNormalizeInheritance:
    """Tests for _normalize_inheritance()."""

    def test_exact_match(self) -> None:
        assert _normalize_inheritance("Autosomal dominant inheritance") == "autosomal dominant"
        assert _normalize_inheritance("Autosomal recessive inheritance") == "autosomal recessive"
        assert _normalize_inheritance("X-linked dominant inheritance") == "X-linked dominant"
        assert _normalize_inheritance("Mitochondrial inheritance") == "mitochondrial"
        assert _normalize_inheritance("Multifactorial inheritance") == "multifactorial"

    def test_partial_match(self) -> None:
        # Partial match — longer key wins
        assert _normalize_inheritance("Autosomal dominant inheritance, late onset") == "autosomal dominant"

    def test_unknown_returns_lowercase(self) -> None:
        assert _normalize_inheritance("Some Unknown Pattern") == "some unknown pattern"