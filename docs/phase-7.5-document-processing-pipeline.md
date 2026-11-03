# Phase 7.5 - Document Processing Pipeline Integration

## Objective

Integrate PDF storage, native text extraction, OCR,
quality analysis, artifact generation, and database
status management into one processing workflow.

## Components

- Document storage service
- PDF extraction service
- OCR service
- Document processing service
- SQLAlchemy database session
- JSON artifact storage

## Processing Workflow

1. Receive a stored PDF and its database record.
2. Validate the document UUID and storage path.
3. Mark the document as processing.
4. Extract native PDF text.
5. Run native and OCR processing.
6. Combine page-level extraction results.
7. Analyze document quality.
8. Generate the unified JSON artifact.
9. Update document page count.
10. Mark processing as completed.

## Processing Status

### pending

The document is waiting to be processed.

### processing

The document is actively being processed.

### completed

Extraction and artifact generation succeeded.

### failed

An unrecoverable processing error occurred.

## Unified Artifact

Location:

storage/processed/

Filename:

{document_uuid}_processed.json

The artifact contains:

- Document UUID
- Processing timestamps
- Page count
- Total words
- Total characters
- Pages with text
- Extraction method
- OCR pages
- Failed pages
- Average OCR confidence
- Extraction quality status
- Page-level extraction output
- Warnings

## Database Integration

The existing Document model is reused.

Updated fields:

- processing_status
- page_count

No new database migration is required.

## Error Handling

The service handles:

- Invalid document UUID
- Missing stored PDF
- Native extraction failure
- OCR processing failure
- Artifact storage failure
- Database update failure

## Scope Exclusions

- Background task queues
- Automatic retry scheduling
- Distributed processing
- Embeddings
- Vector search
- RAG

These will be addressed in later phases.

## Testing

Run:

python -m pytest tests/test_document_processing_service.py -v