# Phase 7.3 - PDF Text Extraction and Quality Analysis

## Objective

Implement page-wise text extraction and quality analysis
for PDFs stored by the ScholarAI document storage service.

## Features

1. Page-wise PDF text extraction.
2. Unicode text normalization.
3. Page-level metadata extraction.
4. Character and word counting.
5. Empty-page detection.
6. Extraction warning generation.
7. Document-level quality classification.
8. Structured JSON artifact generation.

## Technology

- Python
- PyMuPDF
- JSON
- Pytest

## Input

A previously stored and validated PDF file.

## Processing

The extraction service:

1. Reads the stored PDF.
2. Opens the PDF using PyMuPDF.
3. Checks the page count.
4. Extracts text from each page.
5. Normalizes extracted text.
6. Calculates page-level statistics.
7. Detects empty pages.
8. Determines overall extraction quality.
9. Generates a structured result.

## Output

A JSON artifact is generated in:

storage/processed/

The artifact contains:

- Document UUID
- Page count
- Total character count
- Total word count
- Pages with text
- Empty page numbers
- Quality status
- Extraction warnings
- Page-level text and metadata

## Quality statuses

### good

All pages contain extractable text without detected warnings.

### partial

Some pages are empty or have extraction warnings.

### needs_ocr

No pages contain extractable text.

This status indicates that OCR may be required.
It does not necessarily indicate PDF corruption.

## Error Handling

The service handles:

- Missing PDF files
- Empty files
- Invalid PDFs
- Invalid document UUIDs
- Encrypted PDFs
- Zero-page PDFs
- PDFs exceeding the configured page limit
- Extraction failures
- Artifact storage failures

## Storage

Original PDFs remain in:

storage/documents/

Extraction artifacts are stored separately in:

storage/processed/

Temporary artifact files are replaced atomically.

## Scope Exclusions

The following are not part of Phase 7.3:

- OCR for scanned documents
- Embedding generation
- Vector database integration
- Semantic search
- Retrieval-Augmented Generation
- AI-generated summaries

These will be addressed in subsequent phases.

## Testing

Automated tests are maintained in:

tests/test_pdf_extraction_service.py

Run:

python -m pytest tests/test_pdf_extraction_service.py -v