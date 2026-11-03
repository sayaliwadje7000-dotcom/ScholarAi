# Phase 7.4 - OCR and Scanned PDF Intelligence

## Objective

Implement OCR-based text extraction for scanned PDFs
and image-based document pages.

## Technology

- Python
- PyMuPDF
- Tesseract OCR
- pytesseract
- Pillow
- JSON
- Pytest

## Features

1. Detect pages without native text.
2. Render PDF pages into RGB images.
3. Extract text through Tesseract.
4. Support mixed PDFs.
5. Preserve native text when OCR is unnecessary.
6. Calculate word-level OCR confidence.
7. Identify low-confidence extraction.
8. Track failed OCR pages.
9. Generate structured OCR JSON artifacts.

## Processing Architecture

PDF
  |
  v
Native Text Extraction
  |
  v
Page Analysis
  |
  +--> Native text available
  |        |
  |        v
  |     Preserve text
  |
  +--> Native text unavailable
           |
           v
       Render PDF page
           |
           v
       Tesseract OCR
           |
           v
       Extract text
           |
           v
       Calculate confidence
           |
           v
       Generate OCR result

## OCR Configuration

Tesseract executable is configured through:

TESSERACT_CMD

Other settings:

OCR_LANGUAGE
OCR_DPI
OCR_TIMEOUT_SECONDS
OCR_MINIMUM_CONFIDENCE
OCR_FORCE

## Quality Status

### good

All pages contain readable text without detected
low-confidence or extraction warnings.

### partial

Some pages are empty, have failed extraction,
or have low OCR confidence.

### needs_ocr

No readable text was obtained from the document.

### ocr_failed

OCR processing failed on all pages for which
text was required.

## Artifact Storage

OCR artifacts are stored in:

storage/processed/

Artifact naming:

{document_uuid}_ocr.json

## Error Handling

- Missing PDF
- Invalid PDF
- Invalid document UUID
- Encrypted PDF
- Page count exceeding configured limit
- Missing Tesseract executable
- Missing OCR language data
- Page rendering failure
- OCR processing failure
- OCR timeout
- Artifact storage failure

## Scope Exclusions

- Handwriting recognition
- Mathematical formula recognition
- Table reconstruction
- Diagram understanding
- Image caption generation
- Semantic embeddings
- Vector search
- RAG integration

These capabilities require separate processing stages.

## Testing

Automated tests:

tests/test_ocr_service.py

Run:

python -m pytest tests/test_ocr_service.py -v