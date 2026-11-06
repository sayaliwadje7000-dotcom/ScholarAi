
from __future__ import annotations

import json

from dataclasses import dataclass

from app.schemas.retrieval import RetrievedChunkResponse


@dataclass(frozen=True)
class ContextSource:
    source_id: str
    chunk_id: str
    document_id: str
    page_numbers: list[int]
    similarity: float


@dataclass(frozen=True)
class ContextBuildResult:
    context: str
    sources: list[ContextSource]
    included_chunks: int
    excluded_chunks: int
    total_characters: int


class ContextBuilder:
    """
    Builds bounded, structured context from retrieved chunks.

    Assumes retrieval results are already ordered by relevance.
    Preserves source metadata for subsequent citation processing.
    """

    def __init__(
        self,
        max_chunks: int = 8,
        max_context_chars: int = 24000,
        max_chunk_chars: int = 6000,
    ):
        if max_chunks < 1:
            raise ValueError("max_chunks must be at least 1.")

        if max_context_chars < 1:
            raise ValueError("max_context_chars must be positive.")

        if max_chunk_chars < 1:
            raise ValueError("max_chunk_chars must be positive.")

        self.max_chunks = max_chunks
        self.max_context_chars = max_context_chars
        self.max_chunk_chars = max_chunk_chars

    @staticmethod
    def _serialize_source(
        source_id: str,
        chunk: RetrievedChunkResponse,
        text: str,
    ) -> str:
        """
        Serialize evidence as structured JSON.

        JSON encoding prevents document text from directly
        breaking the surrounding context structure.
        """

        payload = {
            "source_id": source_id,
            "chunk_id": str(chunk.chunk_id),
            "document_id": str(chunk.document_id),
            "pages": chunk.page_numbers or [],
            "similarity": chunk.similarity,
            "document_content": text,
        }

        return (
            f"[EVIDENCE {source_id}]\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def _fit_source(
        self,
        source_id: str,
        chunk: RetrievedChunkResponse,
        available_chars: int,
    ) -> str | None:
        """
        Fit a source within the remaining context budget.

        If necessary, truncate its text without exceeding
        the configured character budget.
        """

        original_text = chunk.text[:self.max_chunk_chars]

        candidate = self._serialize_source(
            source_id,
            chunk,
            original_text,
        )

        if len(candidate) <= available_chars:
            return candidate

        marker = "\n[Document chunk truncated due to context budget.]"

        empty_candidate = self._serialize_source(
            source_id,
            chunk,
            marker,
        )

        if len(empty_candidate) > available_chars:
            return None

        low = 0
        high = len(original_text)
        best = empty_candidate

        while low <= high:
            middle = (low + high) // 2

            truncated_text = original_text[:middle] + marker

            serialized = self._serialize_source(
                source_id,
                chunk,
                truncated_text,
            )

            if len(serialized) <= available_chars:
                best = serialized
                low = middle + 1
            else:
                high = middle - 1

        return best

    def build(
        self,
        chunks: list[RetrievedChunkResponse],
    ) -> ContextBuildResult:

        selected_context = []
        sources = []

        used_chars = 0
        included_chunks = 0

        for index, chunk in enumerate(chunks):

            if included_chunks >= self.max_chunks:
                break

            source_id = f"S{index + 1}"

            separator = "\n\n" if selected_context else ""

            available_chars = (
                self.max_context_chars
                - used_chars
                - len(separator)
            )

            if available_chars <= 0:
                break

            serialized = self._fit_source(
                source_id,
                chunk,
                available_chars,
            )

            if serialized is None:
                break

            selected_context.append(
                separator + serialized
            )

            used_chars += len(separator) + len(serialized)

            sources.append(
                ContextSource(
                    source_id=source_id,
                    chunk_id=str(chunk.chunk_id),
                    document_id=str(chunk.document_id),
                    page_numbers=chunk.page_numbers or [],
                    similarity=chunk.similarity,
                )
            )

            included_chunks += 1

        return ContextBuildResult(
            context="".join(selected_context),
            sources=sources,
            included_chunks=included_chunks,
            excluded_chunks=len(chunks) - included_chunks,
            total_characters=used_chars,
        )
