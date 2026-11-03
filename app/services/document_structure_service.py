import json
import logging
import os
import re
import tempfile

from pathlib import Path
from uuid import UUID
from dataclasses import asdict, is_dataclass
from typing import Any

import pymupdf

from app.core.structure_config import StructureSettings


logger = logging.getLogger(__name__)


class DocumentStructureError(Exception):
    """Base exception for document structure errors."""


class DocumentStructureInputError(DocumentStructureError):
    """Raised for invalid document input."""


class DocumentStructureStorageError(DocumentStructureError):
    """Raised when structure artifact storage fails."""


# --------------------------------------------------
# HEADING PATTERNS
# --------------------------------------------------

NUMBERED_HEADING = re.compile(
    r"^(?:(?:UNIT|CHAPTER|MODULE|PART)\s+[\w.-]+:?"
    r"|\d+(?:\.\d+){0,5}[.)]?)\s+.+$",
    re.IGNORECASE,
)

BULLET_PATTERN = re.compile(
    r"^\s*([•●▪◦‣⁃*-])\s+(.+)$"
)

NUMBERED_LIST_PATTERN = re.compile(
    r"^\s*((?:\d+|[A-Za-z]|[ivxlcdmIVXLCDM]+)[.)])\s+(.+)$"
)


# --------------------------------------------------
# OCR PAGE NORMALIZATION
# --------------------------------------------------

def normalize_ocr_pages(ocr_pages=None):

    result = {}

    for page in ocr_pages or []:

        if is_dataclass(page):
            page = asdict(page)

        if isinstance(page, dict):

            page_number = page.get("page_number")
            text = page.get("text", "")

        else:

            page_number = getattr(
                page,
                "page_number",
                None,
            )

            text = getattr(
                page,
                "text",
                "",
            )

        if isinstance(page_number, int):

            result[page_number] = str(text or "")

    return result


# --------------------------------------------------
# HEADING DETECTION
# --------------------------------------------------

def detect_heading(
    text: str,
    font_size: float = 0,
    median_font_size: float = 0,
    bold: bool = False,
    settings=None,
):

    settings = settings or StructureSettings()

    text = " ".join(text.split()).strip()

    if not text:
        return None

    if len(text) > settings.heading_max_characters:
        return None

    if len(text.split()) > 24:
        return None

    if text.endswith((".", ",", ";")):
        return None

    numbered = bool(
        NUMBERED_HEADING.match(text)
    )

    uppercase = (
        text.upper() == text
        and any(character.isalpha() for character in text)
    )

    larger_font = (
        median_font_size > 0
        and font_size >= (
            median_font_size
            * settings.heading_min_font_ratio
        )
    )

    score = 0.0
    signals = []

    if numbered:
        score += 0.65
        signals.append("numbering")

    if uppercase:
        score += 0.25
        signals.append("uppercase")

    if bold:
        score += 0.20
        signals.append("bold")

    if larger_font:
        score += 0.30
        signals.append("larger_font")

    score = min(score, 1.0)

    if score < settings.heading_min_confidence:
        return None

    match = re.match(
        r"^\s*(\d+(?:\.\d+)*)",
        text,
    )

    if match:

        level = min(
            match.group(1).count(".") + 1,
            6,
        )

    elif re.match(
        r"^\s*(UNIT|CHAPTER|MODULE|PART)\b",
        text,
        re.IGNORECASE,
    ):

        level = 1

    elif larger_font:

        level = 2

    else:

        level = 3

    return {
        "type": "heading",
        "text": text,
        "level": level,
        "confidence": round(score, 2),
        "detection_signals": signals,
    }


# --------------------------------------------------
# LIST DETECTION
# --------------------------------------------------

def detect_list_item(text: str):

    bullet_match = BULLET_PATTERN.match(text)

    if bullet_match:

        return {
            "type": "list_item",
            "marker_type": "bullet",
            "marker": bullet_match.group(1),
            "text": bullet_match.group(2).strip(),
        }

    numbered_match = NUMBERED_LIST_PATTERN.match(text)

    if numbered_match:

        marker = numbered_match.group(1)

        if marker[:-1].isdigit():
            marker_type = "numbered"

        elif marker[:-1].lower() in (
            "i", "ii", "iii", "iv",
            "v", "vi", "vii", "viii",
            "ix", "x",
        ):
            marker_type = "roman"

        else:
            marker_type = "alphabetic"

        return {
            "type": "list_item",
            "marker_type": marker_type,
            "marker": marker,
            "text": numbered_match.group(2).strip(),
        }

    return None


# --------------------------------------------------
# PDF LAYOUT EXTRACTION
# --------------------------------------------------

def extract_page_layout(page):

    page_data = page.get_text(
        "dict",
        sort=True,
    )

    lines = []

    block_number = 0

    for block in page_data.get("blocks", []):

        if block.get("type", 0) != 0:
            continue

        for line in block.get("lines", []):

            spans = line.get("spans", [])

            text = "".join(
                span.get("text", "")
                for span in spans
            ).strip()

            if not text:
                continue

            font_sizes = [
                float(span.get("size", 0))
                for span in spans
                if span.get("text", "").strip()
            ]

            fonts = [
                span.get("font", "")
                for span in spans
            ]

            bold = any(
                "bold" in font.lower()
                or "black" in font.lower()
                for font in fonts
            )

            lines.append({
                "text": text,
                "font_size": max(
                    font_sizes,
                    default=0,
                ),
                "bold": bold,
                "bbox": [
                    float(value)
                    for value in line.get(
                        "bbox",
                        [0, 0, 0, 0],
                    )
                ],
                "block_number": block_number,
            })

        block_number += 1

    return lines


# --------------------------------------------------
# OCR FALLBACK LAYOUT
# --------------------------------------------------

def create_ocr_layout(text):

    return [
        {
            "text": line.strip(),
            "font_size": 0,
            "bold": False,
            "bbox": None,
            "block_number": index,
        }

        for index, line in enumerate(
            text.splitlines()
        )

        if line.strip()
    ]


# --------------------------------------------------
# ELEMENT CLASSIFICATION
# --------------------------------------------------

def classify_page_elements(
    lines,
    page_number,
    settings,
):

    if not lines:
        return []

    sizes = [
        line["font_size"]
        for line in lines
        if line["font_size"] > 0
    ]

    median_size = (
        sorted(sizes)[len(sizes) // 2]
        if sizes
        else 0
    )

    elements = []

    for line in lines:

        text = line["text"].strip()

        if not text:
            continue

        heading = detect_heading(
            text=text,
            font_size=line["font_size"],
            median_font_size=median_size,
            bold=line["bold"],
            settings=settings,
        )

        if heading:

            heading["page_number"] = page_number
            heading["bbox"] = line["bbox"]

            elements.append(heading)

            continue

        list_item = (
            detect_list_item(text)
            if settings.detect_lists
            else None
        )

        if list_item:

            list_item["page_number"] = page_number
            list_item["bbox"] = line["bbox"]

            elements.append(list_item)

            continue

        paragraph = {
            "type": "paragraph",
            "text": text,
            "page_number": page_number,
            "bbox": line["bbox"],
            "_block_number": line["block_number"],
        }

        # Join consecutive visual lines from the same PDF
        # text block into one paragraph.
        if (
            elements
            and elements[-1]["type"] == "paragraph"
            and elements[-1].get("_block_number")
            == line["block_number"]
        ):

            elements[-1]["text"] += " " + text

            previous = elements[-1].get("bbox")
            current = line["bbox"]

            if previous and current:

                elements[-1]["bbox"] = [
                    min(previous[0], current[0]),
                    min(previous[1], current[1]),
                    max(previous[2], current[2]),
                    max(previous[3], current[3]),
                ]

        else:

            elements.append(paragraph)

    for element in elements:
        element.pop("_block_number", None)

    return elements


# --------------------------------------------------
# TABLE EXTRACTION
# --------------------------------------------------

def extract_page_tables(page, page_number):

    if not hasattr(page, "find_tables"):
        return []

    try:

        finder = page.find_tables()

        tables = []

        for index, table in enumerate(
            finder.tables,
            start=1,
        ):

            rows = table.extract() or []

            normalized_rows = [
                [
                    str(cell).strip()
                    if cell is not None
                    else ""
                    for cell in row
                ]

                for row in rows
            ]

            if not normalized_rows:
                continue

            tables.append({
                "table_id": (
                    f"page_{page_number}_table_{index}"
                ),
                "page_number": page_number,
                "row_count": len(normalized_rows),
                "column_count": max(
                    len(row)
                    for row in normalized_rows
                ),
                "rows": normalized_rows,
                "bbox": [
                    float(value)
                    for value in table.bbox
                ],
            })

        return tables

    except Exception:

        logger.warning(
            "Table extraction failed on page %s.",
            page_number,
            exc_info=True,
        )

        return []


# --------------------------------------------------
# DOCUMENT HIERARCHY
# --------------------------------------------------

def build_document_hierarchy(elements):

    sections = []
    unsectioned_content = []
    lists = []

    stack = []

    current_list = None

    for element in elements:

        if element["type"] == "heading":

            current_list = None

            section = {
                "section_id": (
                    f"section_{len(sections) + 1}"
                ),
                "heading": element["text"],
                "level": element["level"],
                "page_number": element["page_number"],
                "confidence": element["confidence"],
                "subsections": [],
                "content": [],
            }

            while (
                stack
                and stack[-1]["level"] >= section["level"]
            ):
                stack.pop()

            if stack:

                stack[-1]["subsections"].append(section)

            else:

                sections.append(section)

            stack.append(section)

            continue

        target = (
            stack[-1]["content"]
            if stack
            else unsectioned_content
        )

        if element["type"] == "list_item":

            if (
                current_list is None
                or current_list["page_number"]
                != element["page_number"]
                or current_list["marker_type"]
                != element["marker_type"]
            ):

                current_list = {
                    "list_id": f"list_{len(lists) + 1}",
                    "page_number": element["page_number"],
                    "marker_type": element["marker_type"],
                    "items": [],
                }

                lists.append(current_list)

                target.append(current_list)

            current_list["items"].append({
                "marker": element.get("marker"),
                "text": element["text"],
                "page_number": element["page_number"],
            })

            continue

        current_list = None

        target.append(element)

    return (
        sections,
        unsectioned_content,
        lists,
    )


# --------------------------------------------------
# MAIN STRUCTURE EXTRACTION
# --------------------------------------------------

def extract_document_structure(
    pdf_path: Path,
    document_id: str,
    *,
    ocr_pages=None,
    settings=None,
):

    settings = settings or StructureSettings()

    try:

        document_id = str(
            UUID(str(document_id))
        )

    except (ValueError, TypeError, AttributeError) as exc:

        raise DocumentStructureInputError(
            "A valid document UUID is required."
        ) from exc

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():

        raise DocumentStructureInputError(
            "The PDF file does not exist."
        )

    ocr_map = normalize_ocr_pages(ocr_pages)

    all_elements = []
    all_tables = []
    page_summaries = []
    warnings = []

    try:

        pdf = pymupdf.open(
            filename=str(pdf_path)
        )

    except Exception as exc:

        raise DocumentStructureInputError(
            "Unable to open PDF."
        ) from exc

    try:

        with pdf:

            if pdf.is_encrypted:

                raise DocumentStructureInputError(
                    "Encrypted PDFs cannot be processed."
                )

            for index in range(pdf.page_count):

                page_number = index + 1

                page = pdf.load_page(index)

                try:

                    lines = extract_page_layout(page)

                except Exception:

                    logger.warning(
                        "Native layout extraction failed.",
                        exc_info=True,
                    )

                    lines = []

                native_text = "\n".join(
                    line["text"]
                    for line in lines
                ).strip()

                source = "native_layout"

                if (
                    not native_text
                    and ocr_map.get(page_number, "").strip()
                ):

                    lines = create_ocr_layout(
                        ocr_map[page_number]
                    )

                    source = "ocr_text"

                elif not native_text:

                    source = "empty"

                elements = classify_page_elements(
                    lines=lines,
                    page_number=page_number,
                    settings=settings,
                )

                all_elements.extend(elements)

                tables = (
                    extract_page_tables(
                        page,
                        page_number,
                    )
                    if settings.detect_tables
                    else []
                )

                all_tables.extend(tables)

                page_summaries.append({
                    "page_number": page_number,
                    "source": source,
                    "element_count": len(elements),
                    "table_count": len(tables),
                    "width": round(
                        float(page.rect.width),
                        2,
                    ),
                    "height": round(
                        float(page.rect.height),
                        2,
                    ),
                    "rotation": int(page.rotation),
                })

                if source == "empty":

                    warnings.append(
                        f"Page {page_number}: "
                        "No native or OCR text found."
                    )

    except DocumentStructureInputError:
        raise

    except Exception as exc:

        raise DocumentStructureError(
            "Unexpected document structure extraction failure."
        ) from exc

    (
        sections,
        unsectioned_content,
        lists,
    ) = build_document_hierarchy(
        all_elements
    )

    heading_count = sum(
        element["type"] == "heading"
        for element in all_elements
    )

    paragraph_count = sum(
        element["type"] == "paragraph"
        for element in all_elements
    )

    return {
        "document_id": document_id,
        "structure_version": "1.0",
        "page_count": len(page_summaries),
        "document_title": (
            sections[0]["heading"]
            if sections
            else None
        ),
        "summary": {
            "heading_count": heading_count,
            "paragraph_count": paragraph_count,
            "list_count": len(lists),
            "table_count": len(all_tables),
            "page_count": len(page_summaries),
        },
        "sections": sections,
        "unsectioned_content": unsectioned_content,
        "lists": lists,
        "tables": all_tables,
        "pages": page_summaries,
        "warnings": warnings,
    }


# --------------------------------------------------
# ATOMIC JSON STORAGE
# --------------------------------------------------

def save_structure_artifact(
    structure: dict,
    storage_root: Path,
):

    try:

        document_id = str(
            UUID(str(structure["document_id"]))
        )

    except (KeyError, ValueError, TypeError, AttributeError) as exc:

        raise DocumentStructureStorageError(
            "Invalid document ID in structure result."
        ) from exc

    processed_directory = (
        Path(storage_root)
        / "processed"
    )

    destination = (
        processed_directory
        / f"{document_id}_structure.json"
    )

    temporary_path = None

    try:

        processed_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix="structure_",
            dir=processed_directory,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(
                temporary_file.name
            )

            json.dump(
                structure,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_file.flush()

            os.fsync(
                temporary_file.fileno()
            )

        os.replace(
            temporary_path,
            destination,
        )

        return destination

    except Exception as exc:

        if temporary_path is not None:

            try:

                temporary_path.unlink(
                    missing_ok=True
                )

            except OSError:

                logger.exception(
                    "Unable to remove temporary structure artifact."
                )

        raise DocumentStructureStorageError(
            "Unable to save structure artifact."
        ) from exc


# --------------------------------------------------
# COMPLETE STRUCTURE PROCESSING
# --------------------------------------------------

def process_document_structure(
    pdf_path: Path,
    document_id: str,
    storage_root: Path,
    *,
    ocr_pages=None,
    settings=None,
):

    structure = extract_document_structure(
        pdf_path=pdf_path,
        document_id=document_id,
        ocr_pages=ocr_pages,
        settings=settings,
    )

    artifact_path = save_structure_artifact(
        structure=structure,
        storage_root=storage_root,
    )

    return structure, artifact_path