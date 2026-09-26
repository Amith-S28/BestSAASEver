"""Port protocol for clinical ontology entity linking (SNOMED, RxNorm, LOINC)."""

from typing import List, Protocol, Tuple


class IEntityLinker(Protocol):
    """Abstract interface for clinical entity extraction and standard ontology linking."""

    async def extract_snomed(self, text: str) -> List[Tuple[str, str]]:
        """Extract SNOMED-CT disorder/finding codes: returns list of (code, display_name)."""
        ...

    async def extract_rxnorm(self, text: str) -> List[Tuple[str, str]]:
        """Extract RxNorm pharmaceutical ingredient codes: returns list of (code, drug_name)."""
        ...

    async def extract_loinc(self, text: str) -> List[Tuple[str, str]]:
        """Extract LOINC lab observation codes: returns list of (code, test_name)."""
        ...
