"""Synthesis engine — generates cited answers via LM Studio or OpenRouter.

Connects to OpenRouter (cloud) or LM Studio (local) for LLM inference.
Supports both blocking and streaming (token-by-token) responses.
Folder-scoped and hereditary (cross-family) prompts with medical disclaimers.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from dataclasses import dataclass

import numpy as np
from openai import OpenAI

from medrag.config import settings
from medrag.synthesis.hereditary import build_hereditary_reference
from medrag.synthesis.hereditary_matcher import HEREDITARY_SEARCH_DISCLAIMER
from medrag.synthesis.router import LLMRouter

BASE_SYSTEM_PROMPT = """\
You are a precise, board-certified medical doctor and clinical document assistant. \
You answer questions with absolute professionalism and brutal clinical honesty. \
You never sugarcoat findings, downplay risks, or hide critical diagnostic possibilities; \
you speak with direct, clear, and professional clinical truth.

RULES:
1. If context documents are provided:
   - Base your answer primarily on the provided context, citing the exact document filenames.
   - Preserve all numbers, units, and medical terminology EXACTLY as written.
2. If NO context documents are provided (or if the query is a general medical question):
   - Explicitly prefix your answer by stating: "Note: Since no medical documents are uploaded or matching, I am answering based on general medical knowledge and clinical guidelines."
   - Rely on your general medical training to answer the user's question directly, accurately, and professionally.
3. Be completely honest and direct about patient risks, standard treatments, and potential outcomes.
4. For lab values, always include units and reference ranges when available.
5. Structure your answer clearly with headers and bullet points when appropriate.
6. When comparing values across documents, present them side by side in a table.
"""

FOLDER_SYSTEM_PROMPT = """\
You are a precise, board-certified medical doctor and clinical document assistant for {name} ({relationship}). \
You answer questions with absolute professionalism and brutal clinical honesty. \
You never sugarcoat findings, downplay risks, or hide critical diagnostic possibilities; \
you speak with direct, clear, and professional clinical truth.

RULES:
1. If context documents are provided:
   - Base your answer primarily on the provided context, citing the exact document filenames.
   - Preserve all numbers, units, and medical terminology EXACTLY as written.
2. If NO context documents are provided for {name} (or if the query is a general medical question):
   - Explicitly prefix your answer by stating: "Note: Since no medical documents are uploaded for {name}, I am answering based on general medical knowledge and clinical guidelines."
   - Rely on your general medical training to answer the user's question directly, accurately, and professionally.
3. Be completely honest and direct about patient risks, standard treatments, and potential outcomes.
4. For lab values, always include units and reference ranges when available.
5. Structure your answer clearly with headers and bullet points when appropriate.
6. When comparing values across documents, present them side by side in a table.
"""

HEREDITARY_SYSTEM_PROMPT = """\
You are a precise, board-certified medical doctor and clinical document assistant analyzing documents across multiple \
family members. You answer questions with absolute professionalism and brutal clinical honesty. \
You never sugarcoat findings, downplay risks, or hide critical diagnostic possibilities; \
you speak with direct, clear, and professional clinical truth.

Compare findings across the following family members:
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
1. Use the provided context documents as PRIMARY evidence. If no documents are uploaded, \
explicitly note that you are assessing general hereditary guidelines without patient records.
2. CITE your sources — reference the document filename AND family member when providing information.
3. If no documents are uploaded (or if the query is a general medical question):
   - Explicitly prefix your answer by stating: "Note: Since no medical documents are uploaded, I am answering based on general medical knowledge and clinical guidelines."
   - Rely on your general medical training to answer the user's question directly, accurately, and professionally.
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
    """LLM synthesizer connecting to OpenRouter (cloud) or LM Studio (local)."""

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
        """Lazy-init OpenAI client pointed at LM Studio or cloud provider."""
        if self._client is None:
            api_key = settings.openai_api_key or "lm-studio"
            default_headers = {}
            if "openrouter.ai" in self.base_url:
                default_headers = {
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "MedRAG Medical Assistant",
                }
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=api_key,
                default_headers=default_headers if default_headers else None,
            )
        return self._client

    def check_connection(self) -> bool:
        """Verify LLM server is running and model is loaded."""
        try:
            models = self.client.models.list()
            available = [m.id for m in models.data]
            print(f"[medrag] Connection OK. Models available: {available}")
            return True
        except Exception as e:
            provider = "OpenRouter" if "openrouter" in self.base_url else "LM Studio"
            print(f"[medrag] Cannot connect to {provider} at {self.base_url}: {e}")
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
        # Dynamic model routing
        selected_model, route_reason = LLMRouter.select_model(
            query, context_documents, cross_folders=cross_folders,
        )
        print(f"[medrag] Router: {route_reason} -> {selected_model}")

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

        # Exponential backoff retry loop (3 attempts)
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=selected_model,
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
                    model=selected_model,
                    tokens_used=tokens_used,
                    disclaimer=disclaimer,
                )
            except Exception as e:
                if attempt == 2:
                    raise e
                print(f"[medrag] Synthesis attempt {attempt + 1} failed ({e}). Retrying...")
                time.sleep(2 ** attempt)

        raise RuntimeError("Synthesis failed after 3 attempts")

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
          - {"type": "error", "data": {"message": "..."}} — stream failure

        Args:
            query: User's medical question.
            context_documents: List of (filename, markdown, folder_id) tuples from retrieval.
            folder_context: Optional dict with patient name/relationship or family_members.
            cross_folders: If True, use hereditary-aware prompt.
            query_vector: Precomputed query embedding for hereditary relevance matching.
        """
        # Dynamic model routing
        selected_model, route_reason = LLMRouter.select_model(
            query, context_documents, cross_folders=cross_folders,
        )
        print(f"[medrag] Router: {route_reason} -> {selected_model}")

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

        # Stream connection initialization with retry loop
        stream = None
        for attempt in range(3):
            try:
                stream = self.client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=2048,
                    stream=True,
                )
                break
            except Exception as e:
                if attempt == 2:
                    yield {
                        "type": "error",
                        "data": {"message": f"Stream connection failed after 3 attempts: {e}"},
                    }
                    return
                print(f"[medrag] Stream attempt {attempt + 1} failed ({e}). Retrying...")
                time.sleep(2 ** attempt)

        tokens_used = 0
        try:
            for chunk in stream:
                if chunk.usage:
                    tokens_used = chunk.usage.total_tokens
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield {"type": "token", "data": {"content": delta.content}}
        except Exception as e:
            yield {"type": "error", "data": {"message": f"Stream interrupted: {e}"}}
            return

        done_data: dict = {"model": selected_model, "tokens_used": tokens_used}
        if cross_folders:
            done_data["disclaimer"] = HEREDITARY_SEARCH_DISCLAIMER
        yield {"type": "done", "data": done_data}
