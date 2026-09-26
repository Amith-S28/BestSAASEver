"""Unit tests for clinical entity linker adapter."""

import pytest
from medrag.infrastructure.ontology.entity_linker import RuleBasedEntityLinker


@pytest.mark.asyncio
async def test_extract_snomed_codes():
    """Extracts SNOMED-CT clinical disorders and finding codes."""
    linker = RuleBasedEntityLinker()
    text = "Patient presents with acute kidney injury secondary to severe sepsis and type 2 diabetes."

    results = await linker.extract_snomed(text)
    codes = {code for code, name in results}

    assert "14669001" in codes  # Acute kidney injury
    assert "91302008" in codes  # Sepsis
    assert "44054006" in codes  # Type 2 diabetes mellitus


@pytest.mark.asyncio
async def test_extract_rxnorm_codes():
    """Extracts RxNorm pharmaceutical ingredient codes."""
    linker = RuleBasedEntityLinker()
    text = "Patient was prescribed Lisinopril 10mg daily and Metformin 500mg BID."

    results = await linker.extract_rxnorm(text)
    codes = {code for code, name in results}

    assert "316049" in codes  # Lisinopril
    assert "6809" in codes    # Metformin


@pytest.mark.asyncio
async def test_extract_loinc_codes():
    """Extracts LOINC diagnostic laboratory observation codes."""
    linker = RuleBasedEntityLinker()
    text = "Recent lab panel showed serum creatinine elevated to 2.1 mg/dL with eGFR 28 mL/min."

    results = await linker.extract_loinc(text)
    codes = {code for code, name in results}

    assert "2160-0" in codes   # Serum Creatinine
    assert "33914-3" in codes  # eGFR
