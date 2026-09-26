"""Port protocol for LLM text synthesis."""

from typing import AsyncIterator, Protocol
from medrag.domain.synthesis import StreamChunk, SynthesisRequest


class ILanguageModel(Protocol):
    """Abstract interface for clinical LLM inference."""

    async def generate(self, request: SynthesisRequest) -> str:
        """Non-streaming complete synthesis generation."""
        ...

    async def generate_stream(self, request: SynthesisRequest) -> AsyncIterator[StreamChunk]:
        """Streaming token-by-token generation for Server-Sent Events."""
        ...

    def model_name(self) -> str:
        """Return active model identifier for provenance logging."""
        ...
