# Phase 7 — PDF Processing and Document Intelligence

## Objective

Build the document intelligence foundation of ScholarAI.

The system will eventually support PDF uploads, secure document
storage, text extraction, OCR, document chunking and preparation
for retrieval-augmented generation.

---

## 7.1 — Document Processing Infrastructure

Status: complete and verified

### Dependencies

- python-multipart
- PyMuPDF

### Configuration

- Centralized document settings
- Configurable storage directory
- Maximum document size
- Maximum PDF page count
- Environment-based configuration

### Storage Architecture

storage/
    documents/
    processed/
    temporary/

### Testing

- Integer configuration validation
- Boolean configuration validation
- Storage directory generation
- Storage initialization
- Idempotent directory creation
- Optional storage initialization

---

## Future Subphases

## Completed Subphases

| Subphase | Description | Status |
|---|---|---|
| 7.1 | Document Processing Infrastructure | Complete |
| 7.2 | PDF Upload and Validation | Complete |
| 7.3 | PDF Text Extraction | Complete |
| 7.4 | OCR and Scanned Document Processing | Complete |
| 7.5 | Unified Document Processing Pipeline | Complete |
| 7.6 | Document Structure Extraction | Complete |
| 7.7 | Document Text Cleaning and Normalization | Complete |

## Upcoming Subphases

### 7.8 – Processing Status and Failure Recovery
### 7.9 – Document Text Normalization
### 7.10 – Document Chunking and Chunk Metadata
---

## 7.2 — PDF Upload and Validation

### Objective

Implement secure validation and storage of PDF documents.

### Implemented Components

- Filename sanitization
- File-size validation
- MIME type validation
- PDF signature validation
- PDF structural validation
- Encrypted PDF rejection
- Zero-page PDF rejection
- Maximum page count validation
- SHA-256 checksum generation
- UUID-based storage identifiers
- Atomic file writes
- Safe storage path resolution
- Document retrieval
- Document deletion

### Security Measures

- User filenames are not used as physical storage paths.
- Windows and POSIX path traversal attempts are rejected.
- PDF content is parsed rather than trusting MIME type.
- File-size and page-count limits are enforced.
- Files are written atomically.
- Storage paths are constrained to the configured storage root.

### Testing

- Filename validation
- File-size validation
- MIME validation
- PDF signature validation
- PDF structure validation
- Encryption rejection
- Page-count validation
- Checksum validation
- Storage and retrieval
- Deletion
- Path traversal protection

### Architectural Boundary

This subphase implements the storage service.

It does not yet implement:

- FastAPI upload endpoint
- Database persistence
- PDF text extraction
- OCR
- Document chunking
- Vector embeddings

These are handled by subsequent subphases.

## Phase 7.12 — Database Integration

### Objective

Integrate the document storage and processing infrastructure with the ScholarAI PostgreSQL database.

The database stores document metadata, ownership information, processing status, timestamps, and file integrity information. Physical PDF files remain in the configured document storage system.

### Implemented Components

- Document database service.
- Document metadata persistence.
- UUID-based document retrieval.
- Owner-scoped document retrieval.
- User document listing.
- Paginated document queries.
- Document count queries.
- SQLAlchemy transaction handling.
- Database rollback handling.
- Storage cleanup after failed metadata persistence.
- Explicit consistency error handling.
- Unit tests for database service operations.
- Opt-in PostgreSQL integration tests.

### Database Relationships

The `documents` table is associated with the `users` table through the `user_id` foreign key.

Each document belongs to one user.

A user can own multiple documents.

The database maintains document metadata independently of the physical PDF file.

### Transaction Management

Document metadata is persisted using SQLAlchemy sessions.

Successful persistence commits the transaction.

Database failures trigger rollback.

When physical storage succeeds but metadata persistence fails, the service attempts to remove the physical file.

If physical-file cleanup also fails, a consistency error is raised and the document identifier is logged for manual reconciliation.

This is a best-effort compensation strategy rather than a distributed atomic transaction.

### Access Control Boundary

Document retrieval can be scoped by both document ID and owner ID.

The owner-scoped retrieval function returns the same not-found response for nonexistent documents and documents belonging to another user.

Authentication and API-level authorization are handled in later roadmap phases.

### Testing

Unit tests cover:

- Document record creation.
- Invalid user ID handling.
- Invalid stored-document input.
- Database commit failure.
- Transaction rollback.
- Storage/database consistency.
- Cleanup failure handling.
- Document retrieval.
- Missing document handling.
- Owner-scoped retrieval.
- Document listing.
- Pagination validation.
- Document count.

PostgreSQL integration tests verify actual persistence and retrieval using the configured development database.

### Architectural Boundary

This subphase implements the database service layer.

It does not yet implement:

- FastAPI PDF upload endpoint.
- FastAPI document retrieval endpoint.
- Authentication and authorization middleware.
- Embedding generation.
- Vector database persistence.
- RAG retrieval.

These capabilities belong to their respective later roadmap subphases.

### Completion Criteria

Phase 7.12 is complete after:

1. Database service implementation.
2. Unit tests passing.
3. Full existing test suite passing.
4. PostgreSQL integration test passing.
5. Documentation updated.
6. Git changes reviewed and committed.