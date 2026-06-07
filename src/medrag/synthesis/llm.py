"""Synthesis engine — generates cited answers using local LLM via LM Studio.

Connects to LM Studio's OpenAI-compatible server running a local model.
Supports both blocking and streaming (token-by-token) responses.
Folder-scoped and hereditary (cross-family) prompts with medical disclaimers.
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field

import numpy as np
from openai import OpenAI

from medrag.config import settings
from medrag.synthesis.hereditary import build_hereditary_reference
from medrag.synthesis.hereditary_matcher import HEREDITARY_SEARCH_DISCLAIMER


BASE_SYSTEM_PROMPT = """\
You are a precise medical document assistant. You answer questions by citing \
exact content from the provided context documents.

RULES:
1. ONLY use information from the provided context. Never hallucinate or use outside knowledge.
2. CITE your sources — reference the document filename when providing information.
3. If the context doesn't contain the answer, say "The provided documents do not contain \
information about that."
4. Preserve all numbers, units, and medical terminology EXACTLY as written.
5. For lab values, always include units and reference ranges when available.
6. Structure your answer clearly with headers and bullet points when appropriate.
7. When comparing values across documents, present them side by side in a table.
"""

FOLDER_SYSTEM_PROMPT = """\
You are a precise medical document assistant for {name} ({relationship}). \
You answer questions by citing exact content from their medical documents only.

RULES:
1. ONLY use information from the provided context. Never hallucinate or use outside knowledge.
2. CITE your sources — reference the document filename when providing information.
3. If the context doesn't contain the answer, say "The provided documents for {name} do not contain \
information about that."
4. Preserve all numbers, units, and medical terminology EXACTLY as written.
5. For lab values, always include units and reference ranges when available.
6. Structure your answer clearly with headers and bullet points when appropriate.
7. When comparing values across documents, present them side by side in a table.
"""

HEREDITARY_SYSTEM_PROMPT = """\
You are a precise medical document assistant analyzing documents across multiple \
family members. Compare findings across the following family members:
{family_members}

Your job is to identify HEREDITARY CONDITIONS — diseases that can run in families. \
Use the hereditary conditions reference below to know which conditions are genetic \
and what markers to look for in the documents.

ANALYSIS PROCESS:
1. First, scan each family member's documents for the markers listed in the reference
2. If you find a matching condition in ONE member, check if OTHER members also have it
3. When a hereditary condition appears in multiple members, EXPLICITLY flag the hereditary connection
4. Include the inheritance pattern from the reference — frame as population-level education
5. If a condition appears in only one member but is strongly hereditary, NOTE that other \
family members may be at risk even if not yet documented

{hereditary_reference}

RULES:
1. Use the provided context documents as PRIMARY evidence. The reference above tells you \
WHAT to look for — the documents tell you IF it's there.
2. CITE your sources — reference the document filename AND family member when providing information.
3. If the context doesn't contain the answer, say "The provided documents do not contain \
information about that."
4. Preserve all numbers, units, and medical terminology EXACTLY as written.
5. For lab values, always include units and reference ranges when available.
6. Structure your answer clearly with headers and bullet points when appropriate.
7. When comparing values across documents or family members, present them side by side in a table.
8. When mentioning a finding for one family member, ALWAYS check if other members have similar findings.
9. If you identify a hereditary pattern, include: the condition, which members have it, \
inheritance pattern, and recommended screening for unaffected members.
10. ALWAYS include this disclaimer at the end of your response: "This information is for \
educational purposes only and does not constitute medical advice, diagnosis, or individual \
risk assessment. Consult a qualified healthcare professional or genetic counselor for \
personal medical guidance."
"""


def _build_system_prompt(
    folder_context: dict | None = None,
    cross_folders: bool = False,
    query_vector: np.ndarray | None = None,
    query_text: str = "",
) -> str:
    """Build the appropriate system prompt based on search context."""
    if cross_folders and folder_context and "family_members" in folder_context:
        members = folder_context["family_members"]
        member_lines = "\n".join(
            f"  - {m['name']} ({m['relationship']})" for m in members
        )
        hereditary_ref = build_hereditary_reference(
            query_vector=query_vector,
            query_text=query_text,
        )
        return HEREDITARY_SYSTEM_PROMPT.format(
            family_members=member_lines,
            hereditary_reference=hereditary_ref,
        )

    if folder_context and "name" in folder_context:
        return FOLDER_SYSTEM_PROMPT.format(
            name=folder_context["name"],
            relationship=folder_context["relationship"],
        )

    return BASE_SYSTEM_PROMPT


@dataclass
class SynthesisResult:
    """Result from the synthesis LLM."""

    answer: str
    sources: list[str]
    model: str
    tokens_used: int
    disclaimer: str = ""


class Synthesizer:
    """Local LLM synthesizer connecting to LM Studio's OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        max_context: int | None = None,
        temperature: float | None = None,
    ):
        self.base_url = base_url or settings.lmstudio_base_url
        self.model = model or settings.lmstudio_model
        self.max_context = max_context or settings.lmstudio_max_context
        self.temperature = temperature or settings.lmstudio_temperature
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy-init OpenAI client pointed at LM Studio."""
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key="lm-studio",  # LM Studio doesn't require a real key
            )
        return self._client

    def check_connection(self) -> bool:
        """Verify LM Studio server is running and model is loaded."""
        try:
            models = self.client.models.list()
            available = [m.id for m in models.data]
            print(f"[medrag] LM Studio models available: {available}")
            return True
        except Exception as e:
            print(f"[medrag] Cannot connect to LM Studio: {e}")
            print(f"[medrag] Make sure LM Studio is running with a model loaded on {self.base_url}")
            return False

    def _build_context_block(
        self,
        context_documents: list[tuple[str, str, str]],  # (filename, markdown, folder_id)
    ) -> tuple[str, list[str]]:
        """Build the context block for the LLM prompt.

        Returns:
            (context_block_text, source_filenames)
        """
        source_filenames: list[str] = []
        context_parts: list[str] = []

        for filename, markdown, folder_id in context_documents:
            max_doc_chars = (self.max_context * 4) // max(len(context_documents), 1)
            truncated = markdown[:max_doc_chars]
            # Include folder_id in source label for hereditary context
            source_label = f"{filename} [{folder_id}]" if folder_id != "default" else filename
            context_parts.append(f"### Source: {source_label}\n\n{truncated}")
            source_filenames.append(filename)

        context_block = "\n\n---\n\n".join(context_parts)
        return context_block, source_filenames

    def synthesize(
        self,
        query: str,
        context_documents: list[tuple[str, str, str]],  # (filename, markdown, folder_id)
        folder_context: dict | None = None,
        cross_folders: bool = False,
        query_vector: np.ndarray | None = None,
    ) -> SynthesisResult:
        """Generate a cited answer from retrieved context documents.

        Args:
            query: User's medical question.
            context_documents: List of (filename, markdown, folder_id) tuples from retrieval.
            folder_context: Optional dict with patient name/relationship or family_members.
            cross_folders: If True, use hereditary-aware prompt.
            query_vector: Precomputed query embedding for hereditary relevance matching.

        Returns:
            SynthesisResult with the answer and metadata.
        """
        system_prompt = _build_system_prompt(
            folder_context, cross_folders,
            query_vector=query_vector, query_text=query,
        )
        context_block, source_filenames = self._build_context_block(context_documents)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Context Documents:\n\n{context_block}\n\n---\n\nQuestion: {query}",
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
        )

        choice = response.choices[0]
        answer = choice.message.content or "No response generated."

        tokens_used = response.usage.total_tokens if response.usage else 0

        disclaimer = HEREDITARY_SEARCH_DISCLAIMER if cross_folders else ""

        return SynthesisResult(
            answer=answer,
            sources=source_filenames,
            model=self.model,
            tokens_used=tokens_used,
            disclaimer=disclaimer,
        )

    def synthesize_stream(
        self,
        query: str,
        context_documents: list[tuple[str, str, str]],  # (filename, markdown, folder_id)
        folder_context: dict | None = None,
        cross_folders: bool = False,
        query_vector: np.ndarray | None = None,
    ) -> Generator[dict, None, None]:
        """Stream a cited answer token-by-token from retrieved context documents.

        Yields dicts with keys:
          - {"type": "source", "data": {"filename": "..."}} — source document
          - {"type": "token", "data": {"content": "..."}} — answer token
          - {"type": "done", "data": {"model": "...", "tokens_used": N}} — completion
          - {"type": "done", "data": {"model": "...", "tokens_used": N, "disclaimer": "..."}} — with disclaimer

        Args:
            query: User's medical question.
            context_documents: List of (filename, markdown, folder_id) tuples from retrieval.
            folder_context: Optional dict with patient name/relationship or family_members.
            cross_folders: If True, use hereditary-aware prompt.
            query_vector: Precomputed query embedding for hereditary relevance matching.
        """
        system_prompt = _build_system_prompt(
            folder_context, cross_folders,
            query_vector=query_vector, query_text=query,
        )
        context_block, source_filenames = self._build_context_block(context_documents)

        # Yield source events first
        for src in source_filenames:
            yield {"type": "source", "data": {"filename": src}}

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Context Documents:\n\n{context_block}\n\n---\n\nQuestion: {query}",
            },
        ]

        # Stream tokens
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
            stream=True,
        )

        tokens_used = 0
        for chunk in stream:
            if chunk.usage:
                tokens_used = chunk.usage.total_tokens
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield {"type": "token", "data": {"content": delta.content}}

        done_data: dict = {"model": self.model, "tokens_used": tokens_used}
        if cross_folders:
            done_data["disclaimer"] = HEREDITARY_SEARCH_DISCLAIMER
        yield {"type": "done", "data": done_data}