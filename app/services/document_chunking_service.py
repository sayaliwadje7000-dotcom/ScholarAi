import json
import os
import tempfile
import hashlib

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.chunking_config import ChunkingSettings


# ==========================================================
# EXCEPTIONS
# ==========================================================

class DocumentChunkingError(Exception):
    """Base exception for document chunking."""


class DocumentChunkingInputError(DocumentChunkingError):
    """Raised when chunking input is invalid."""


class DocumentChunkingStorageError(DocumentChunkingError):
    """Raised when chunk artifacts cannot be stored."""


# ==========================================================
# RESULT MODELS
# ==========================================================

@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    page_numbers: list[int]
    character_count: int
    word_count: int
    start_page: int
    end_page: int


@dataclass(frozen=True)
class DocumentChunkingResult:
    document_id: str
    chunk_count: int
    total_characters: int
    total_words: int
    chunk_size: int
    chunk_overlap: int
    chunks: list[DocumentChunk]


# ==========================================================
# INPUT VALIDATION
# ==========================================================

def _validate_document_id(document_id: str) -> str:
    if not isinstance(document_id, str) or not document_id.strip():
        raise DocumentChunkingInputError(
            "A valid document ID is required."
        )

    try:
        return str(UUID(document_id))

    except (ValueError, TypeError, AttributeError) as exc:
        raise DocumentChunkingInputError(
            "Document ID must be a valid UUID."
        ) from exc


def _validate_pages(pages: list[Any]) -> list[tuple[int, str]]:
    if not isinstance(pages, list):
        raise DocumentChunkingInputError(
            "Pages must be provided as a list."
        )

    validated = []

    for page in pages:
        page_number = getattr(page, "page_number", None)
        text = getattr(page, "text", None)

        if isinstance(page, dict):
            page_number = page.get("page_number")
            text = page.get("text")

        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            raise DocumentChunkingInputError(
                "Every page must have a positive integer page number."
            )

        if not isinstance(text, str):
            raise DocumentChunkingInputError(
                "Every page must contain string text."
            )

        validated.append((page_number, text))

    page_numbers = [number for number, _ in validated]

    if len(page_numbers) != len(set(page_numbers)):
        raise DocumentChunkingInputError(
            "Page numbers must be unique."
        )

    return sorted(validated, key=lambda item: item[0])


# ==========================================================
# TEXT BOUNDARY HELPERS
# ==========================================================

def _select_boundary(text: str, limit: int) -> int:
    """
    Select a natural chunk boundary.

    Priority:
    1. Paragraph boundary.
    2. Sentence boundary.
    3. Word boundary.
    4. Hard character boundary.
    """

    if limit >= len(text):
        return len(text)

    minimum_boundary = max(1, limit // 2)

    paragraph_boundary = text.rfind(
        "\n\n",
        minimum_boundary,
        limit,
    )

    if paragraph_boundary != -1:
        return paragraph_boundary + 2

    sentence_positions = [
        text.rfind(marker, minimum_boundary, limit)
        for marker in (". ", "? ", "! ", ".\n", "?\n", "!\n")
    ]

    sentence_boundary = max(sentence_positions)

    if sentence_boundary != -1:
        return sentence_boundary + 1

    word_boundary = text.rfind(
        " ",
        minimum_boundary,
        limit,
    )

    if word_boundary != -1:
        return word_boundary

    return limit


def _split_text(
    text: str,
    settings: ChunkingSettings,
) -> list[str]:
    """Split text into overlapping chunks."""

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        end = min(
            start + settings.chunk_size,
            len(text),
        )

        if end < len(text):
            relative_boundary = _select_boundary(
                text[start:end + 1],
                end - start,
            )

            end = start + relative_boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = end - settings.chunk_overlap

        # Guarantee forward progress.
        if next_start <= start:
            next_start = end

        start = next_start

    # Merge a very small final chunk into the previous chunk
    # where the configured maximum size permits it.
    if len(chunks) > 1:
        final_chunk = chunks[-1]

        if len(final_chunk) < settings.minimum_chunk_size:
            previous = chunks[-2]
            merged = f"{previous} {final_chunk}"

            if len(merged) <= settings.chunk_size:
                chunks[-2] = merged
                chunks.pop()

    return chunks


# ==========================================================
# PAGE-AWARE CHUNKING
# ==========================================================

def chunk_document_pages(
    document_id: str,
    pages: list[Any],
    settings: ChunkingSettings | None = None,
) -> DocumentChunkingResult:

    document_id = _validate_document_id(document_id)

    settings = settings or ChunkingSettings()

    if not isinstance(settings, ChunkingSettings):
        raise DocumentChunkingInputError(
            "Invalid chunking settings."
        )

    validated_pages = _validate_pages(pages)

    chunks: list[DocumentChunk] = []

    current_index = 0

    if settings.preserve_page_boundaries:

        for page_number, page_text in validated_pages:

            page_chunks = _split_text(
                page_text,
                settings,
            )

            for chunk_text in page_chunks:

                chunk_id = _generate_chunk_id(
                    document_id,
                    current_index,
                    chunk_text,
                    [page_number],
                )

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        chunk_index=current_index,
                        text=chunk_text,
                        page_numbers=[page_number],
                        character_count=len(chunk_text),
                        word_count=len(chunk_text.split()),
                        start_page=page_number,
                        end_page=page_number,
                    )
                )

                current_index += 1

    else:

        combined_text = []
        character_pages = []

        for page_number, page_text in validated_pages:

            if not page_text.strip():
                continue

            if combined_text:
                combined_text.append("\n\n")
                character_pages.extend([page_number] * 2)

            combined_text.append(page_text)
            character_pages.extend([page_number] * len(page_text))

        full_text = "".join(combined_text)

        text_chunks = _split_text(
            full_text,
            settings,
        )

        cursor = 0

        for chunk_text in text_chunks:

            # Locate the chunk's first occurrence from the current
            # position. This preserves source-page mapping.
            start = full_text.find(chunk_text, cursor)

            if start == -1:
                start = cursor

            end = min(
                start + len(chunk_text),
                len(character_pages),
            )

            page_numbers = sorted(
                set(character_pages[start:end])
            )

            if not page_numbers:
                page_numbers = [validated_pages[0][0]]

            chunk_id = _generate_chunk_id(
                document_id,
                current_index,
                chunk_text,
                page_numbers,
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=current_index,
                    text=chunk_text,
                    page_numbers=page_numbers,
                    character_count=len(chunk_text),
                    word_count=len(chunk_text.split()),
                    start_page=page_numbers[0],
                    end_page=page_numbers[-1],
                )
            )

            cursor = max(start + 1, end - settings.chunk_overlap)
            current_index += 1

    return DocumentChunkingResult(
        document_id=document_id,
        chunk_count=len(chunks),
        total_characters=sum(
            chunk.character_count for chunk in chunks
        ),
        total_words=sum(
            chunk.word_count for chunk in chunks
        ),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunks=chunks,
    )


# ==========================================================
# STABLE CHUNK IDENTIFIERS
# ==========================================================

def _generate_chunk_id(
    document_id: str,
    chunk_index: int,
    text: str,
    page_numbers: list[int],
) -> str:

    source = (
        f"{document_id}:"
        f"{chunk_index}:"
        f"{','.join(map(str, page_numbers))}:"
        f"{text}"
    )

    digest = hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()

    return digest


# ==========================================================
# ARTIFACT STORAGE
# ==========================================================

def save_chunking_artifact(
    result: DocumentChunkingResult,
    storage_root: Path,
) -> Path:

    if not isinstance(result, DocumentChunkingResult):
        raise DocumentChunkingInputError(
            "A valid chunking result is required."
        )

    try:
        document_id = _validate_document_id(
            result.document_id
        )

    except DocumentChunkingInputError:
        raise

    processed_directory = (
        Path(storage_root) / "processed"
    )

    destination = (
        processed_directory
        / f"{document_id}_chunks.json"
    )

    temporary_path = None

    try:
        processed_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = asdict(result)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f"{document_id}_",
            dir=processed_directory,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(
                temporary_file.name
            )

            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(
            temporary_path,
            destination,
        )

        return destination

    except Exception as exc:

        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise DocumentChunkingStorageError(
            "Unable to save document chunking artifact."
        ) from exc


# ==========================================================
# COMPLETE CHUNKING WORKFLOW
# ==========================================================

def chunk_document_text(
    document_id: str,
    pages: list[Any],
    storage_root: Path,
    settings: ChunkingSettings | None = None,
) -> tuple[DocumentChunkingResult, Path]:

    result = chunk_document_pages(
        document_id=document_id,
        pages=pages,
        settings=settings,
    )

    artifact_path = save_chunking_artifact(
        result=result,
        storage_root=storage_root,
    )

    return result, artifact_path