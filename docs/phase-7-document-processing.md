# ScholarAI — Phase 7: PDF Processing and Document Intelligence

**Phase:** 7  
**Objective:** Build a secure, reliable document-processing foundation for ScholarAI.  
**Status:** Implementation and regression verification completed; final documentation and Git checkpoint in progress.

---

# 1. Phase Overview

Phase 7 establishes the document intelligence infrastructure required for ScholarAI to process academic PDFs.

The system supports document upload, validation, secure storage, text extraction, OCR, text normalization, document structure extraction, chunking, database persistence, processing lifecycle management, retry handling and processing observability.

The output of this phase provides the foundation for Phase 8 (Embeddings and Vector Search) and Phase 9 (Retrieval-Augmented Generation).

## 1.1 Major Capabilities

- PDF upload and validation.
- Secure document storage.
- PDF text extraction.
- OCR for scanned documents.
- Text cleaning and normalization.
- Document structure extraction.
- Configurable document chunking.
- Chunk metadata generation.
- Document database integration.
- Processing status management.
- Concurrent processing protection.
- Retry and failure handling.
- Processing metrics and diagnostics.
- Document APIs and owner-scoped retrieval.

## 1.2 Architectural Overview

```text
Client
  |
  v
FastAPI Document API
  |
  v
Upload and Validation
  |
  v
Document Storage
  |
  v
Document Database
  |
  v
Processing Orchestration
  |
  +---- PDF Text Extraction
  |
  +---- OCR Processing
  |
  +---- Text Cleaning
  |
  +---- Structure Extraction
  |
  +---- Document Chunking
  |
  +---- Artifact Generation
  |
  v
Processed Document Artifacts
  |
  v
Future Phase 8: Embeddings
  |
  v
Future Phase 9: RAG
```

---

# 2. Technology and Infrastructure

## 2.1 Backend Technologies

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- PyMuPDF
- Pytest
- HTTPX

## 2.2 Storage Architecture

The document-processing infrastructure separates physical document storage from database metadata.

Conceptual storage structure:

```text
storage/
    documents/
    processed/
    temporary/
```

Physical PDFs and processing artifacts are stored separately from PostgreSQL records.

## 2.3 Configuration

Document-processing configuration is centralized.

The implementation includes:

- Document size limits.
- PDF page-count limits.
- Storage directory configuration.
- OCR configuration.
- Text-cleaning configuration.
- Chunking configuration.
- Retry configuration.

Environment-based configuration is used where appropriate.

Secrets and database credentials must never be committed to Git.

---

# 3. Document Upload and Validation

## 3.1 Implemented Functionality

The document storage and validation infrastructure includes:

- Filename sanitization.
- File-size validation.
- MIME-type validation.
- PDF signature validation.
- PDF structural validation.
- Encrypted PDF rejection.
- Zero-page PDF rejection.
- Maximum page-count validation.
- SHA-256 checksum generation.
- UUID-based storage identifiers.
- Atomic file writes.
- Document retrieval.
- Document deletion.
- Safe storage-path resolution.

## 3.2 Security Measures

The implementation avoids trusting user-supplied filenames as physical storage paths.

Additional protections include:

- Windows and POSIX path traversal rejection.
- Absolute-path rejection.
- Storage-root boundary validation.
- File-size enforcement.
- PDF structural inspection.
- Checksum verification.
- Atomic file publication.
- Protection against overwriting existing storage targets.

## 3.3 Integrity Verification

Document integrity is verified using SHA-256 checksums.

The storage service includes checksum verification against the stored file.

A checksum mismatch raises a document integrity error.

---

# 4. PDF Text Extraction

## 4.1 Objective

Extract text from native PDF documents while retaining relevant document information.

## 4.2 Implemented Functionality

- PDF opening and validation.
- Page-by-page text extraction.
- Page-count handling.
- Extraction error handling.
- Extraction result generation.
- Extraction testing.

PyMuPDF is used for PDF processing.

---

# 5. OCR and Scanned Document Processing

## 5.1 Objective

Support documents where text cannot be extracted through ordinary PDF text extraction.

## 5.2 Implemented Functionality

The OCR service provides the scanned-document processing component.

It is integrated into the document-processing workflow alongside native PDF extraction.

The processing pipeline can therefore handle documents requiring OCR rather than relying exclusively on native text extraction.

## 5.3 Testing

OCR-related tests cover the implemented OCR service and its error-handling behaviour.

---

# 6. Text Cleaning and Normalization

## 6.1 Objective

Prepare extracted text for downstream document intelligence.

## 6.2 Implemented Functionality

- Text normalization.
- Cleaning of extracted content.
- Handling of unwanted formatting artefacts.
- Configurable cleaning behaviour.
- Structured cleaning results.
- Cleaning error handling.

The cleaned text is used by subsequent document structure extraction and chunking stages.

---

# 7. Document Structure Extraction

## 7.1 Objective

Extract useful structural information from processed document text.

## 7.2 Implemented Functionality

A dedicated document structure service processes extracted and cleaned text.

Its outputs are incorporated into the unified document-processing workflow.

Structure extraction is kept separate from PDF extraction and text cleaning to maintain service boundaries.

---

# 8. Document Chunking and Metadata

## 8.1 Objective

Divide processed document content into manageable segments for future embedding generation and retrieval.

## 8.2 Implemented Components

- Centralized chunking configuration.
- Dedicated document chunking service.
- Configurable chunking behaviour.
- Chunk metadata generation.
- Chunking validation.
- Chunking error handling.
- Chunking artifact storage.

## 8.3 Downstream Integration

The chunking output is intended to become the input to Phase 8.

**Important:** Chunk generation does not mean vector embeddings or semantic vector search have already been implemented.

Those capabilities belong to Phase 8.

---

# 9. Database Integration

## 9.1 Objective

Integrate document storage and processing with the ScholarAI PostgreSQL database.

## 9.2 Document Database Model

The document database model stores information including:

- Document identifier.
- User ownership.
- Original filename and document metadata.
- Storage information.
- Checksum information.
- Processing status.
- Processing timestamps.
- Processing attempts.
- Processing error information.
- Page count and relevant processing metadata.

The document belongs to a user through the `user_id` foreign-key relationship.

## 9.3 Database Service

Implemented database operations include:

- Document metadata persistence.
- UUID-based retrieval.
- Owner-scoped retrieval.
- User document listing.
- Paginated queries.
- Document count queries.
- SQLAlchemy transaction handling.
- Rollback handling.
- Storage cleanup after failed metadata persistence.
- Consistency error handling.

## 9.4 Transaction and Storage Consistency

Physical storage and database persistence are separate operations.

When physical storage succeeds but metadata persistence fails, the system attempts to remove the physical file.

If cleanup also fails, a consistency error is raised and the document identifier is logged for reconciliation.

This is a compensation strategy, not a distributed atomic transaction.

---

# 10. Database Migration

## 10.1 Processing Recovery Migration

Migration:

`alembic/versions/f3a9c7d21b60_phase_7_8_processing_recovery.py`

Revision:

`f3a9c7d21b60`

Down revision:

`ee9982c493e2`

The migration introduces processing lifecycle fields:

- `processing_started_at`
- `processing_completed_at`
- `processing_error`
- `processing_attempts`

It also introduces a nonnegative processing-attempt constraint.

## 10.2 Migration Verification

The following checks were executed:

```powershell
alembic current
alembic heads
alembic check
```

Observed results:

```text
f3a9c7d21b60 (head)
f3a9c7d21b60 (head)

No new upgrade operations detected.
```

The current database revision matches the migration head.

Alembic reported no new upgrade operations.

---

# 11. Document Processing Status Lifecycle

## 11.1 Supported States

The document-processing lifecycle supports:

- `pending`
- `processing`
- `completed`
- `failed`

## 11.2 Permitted Transitions

```text
pending
   |
   v
processing
   |
   +------> completed
   |
   +------> failed
                |
                v
             processing
```

Completed documents cannot be restarted through the normal processing workflow.

## 11.3 Status Management

The centralized status service provides:

- Status validation.
- Transition validation.
- PostgreSQL row locking.
- UTC timestamps.
- Processing attempt tracking.
- Failure descriptions.
- Completed page-count updates.
- Status retrieval.
- Database rollback handling.

## 11.4 Timestamp Management

When processing starts:

- Start timestamp is updated.
- Completion timestamp is cleared.
- Previous processing error is cleared.
- Processing attempts are incremented.

When processing completes:

- Completion timestamp is updated.
- Processing error is cleared.
- Page count is updated when supplied.

When processing fails:

- Completion timestamp is updated.
- A bounded failure description is recorded.

---

# 12. Concurrency Protection

## 12.1 Objective

Prevent multiple workers from claiming the same document for processing.

## 12.2 Implemented Functionality

- Atomic processing claim.
- Row-locked status transitions.
- Duplicate processing claim detection.
- Explicit already-claimed exceptions.
- Centralized processing attempt management.

The processing service claims a document before starting the main processing pipeline.

A duplicate claim is rejected rather than treated as a normal retryable processing failure.

## 12.3 Attempt Management

The status service increments the processing-attempt counter when a document transitions to `processing`.

The processing orchestration service does not independently increment the persisted counter.

This prevents double-counting during a successful processing claim.

---

# 13. Retry and Error Handling

## 13.1 Configuration

Retry behaviour is centralized in:

`app/core/retry_config.py`

The configured defaults are:

| Setting | Value |
|---|---:|
| Retry enabled | True |
| Maximum attempts | 3 |
| Initial delay | 5 seconds |
| Backoff multiplier | 2 |
| Maximum delay | 60 seconds |

Configuration can be supplied through environment variables.

## 13.2 Retry Service

Implementation:

`app/services/document_retry_service.py`

The service provides:

- Retry eligibility checks.
- Maximum-attempt enforcement.
- Exponential backoff.
- Maximum retry delay.
- Configurable sleep injection.
- Retry exhaustion handling.
- Duplicate-claim protection.

## 13.3 Error Classification

Implementation:

`app/services/document_error_service.py`

The service distinguishes transient failures from permanent failures.

It considers selected network, timeout, operating-system and database errors.

Unknown errors default to permanent classification rather than being indiscriminately retried.

## 13.4 Retry Limitations

Retry execution currently uses the application process and `time.sleep()`.

This is not equivalent to a durable distributed job scheduler.

A durable background-processing architecture remains future production-hardening work.

---

# 14. Document API Integration

Implementation:

`app/api/documents.py`

## 14.1 Implemented Functionality

The document API includes:

- Document upload handling.
- Bounded upload reading.
- Document processing initiation.
- Background processing integration.
- Document metadata retrieval.
- Processing-status retrieval.
- Owner-scoped document queries.

The background processing integration uses a separate database session through `SessionLocal`.

Processing is executed through the retry service.

## 14.2 Access-Control Boundary

Document ownership is represented through the document's user relationship.

The API uses the current user's identifier when performing owner-scoped operations.

However, the authentication dependency currently returns HTTP 501 because authentication has not yet been implemented.

Therefore:

**Owner-scoped query logic is implemented, but production authenticated access control is not complete.**

Authentication and authorization must be completed under the appropriate later roadmap phase.

---

# 15. Processing Observability

Implementation:

`app/services/document_observability_service.py`

## 15.1 Metrics

The observability service records:

- Processing started.
- Processing completed.
- Processing failed.
- Stage executions.
- Stage failures.
- Total stage duration.
- Average stage duration.
- Maximum stage duration.

## 15.2 Processing Stages

The instrumented processing stages include:

1. Stored document validation.
2. Native PDF extraction.
3. OCR processing.
4. Text cleaning.
5. Cleaned-text artifact storage.
6. Document structure extraction.
7. Document chunking.
8. Chunking artifact storage.
9. Unified artifact serialization.
10. Unified artifact storage.

## 15.3 Implementation Characteristics

- Thread-safe metric updates.
- Lock-protected snapshots.
- Per-stage timing.
- Structured logging.
- Exception preservation.
- Metric reset functionality.

## 15.4 Observability Limitations

Metrics are currently held in process memory.

They are not yet:

- Persisted in PostgreSQL.
- Aggregated across multiple application instances.
- Exported through a Prometheus endpoint.
- Connected to a production monitoring dashboard.

These are future monitoring and deployment improvements.

---

# 16. Failure Recovery and Known Limitations

## 16.1 Failure Persistence

The processing service attempts to persist failure information.

If persistence fails:

- The database transaction is rolled back.
- The persistence failure is logged.
- The original processing exception is preserved.

This avoids replacing the original processing exception with the secondary database failure.

## 16.2 Stale Processing Limitation

The database tracks `processing_started_at`.

However, the current implementation does not provide a complete stale-worker recovery mechanism.

The following are not yet implemented:

- Worker heartbeat.
- Worker lease management.
- Lease expiration.
- Fencing or worker ownership tokens.
- Automatic abandoned-job recovery.
- Durable job scheduling.

A document can remain in `processing` if a worker terminates unexpectedly or the database remains unavailable when failure information is being persisted.

## 16.3 Why Timestamp-Only Recovery Is Not Sufficient

Automatically marking every old processing record as failed is unsafe.

A long-running worker could still be active when a recovery process changes its status.

A robust future implementation must distinguish an abandoned worker from an active worker.

## 16.4 Future Reliability Architecture

The recommended future architecture includes:

1. Durable background job processing.
2. Worker ownership or lease management.
3. Periodic heartbeats.
4. Lease-expiration detection.
5. Fencing tokens to reject stale workers.
6. Safe retry and recovery scheduling.
7. Persistent operational metrics.

These capabilities are documented as deferred improvements, not completed functionality.

---

# 17. Testing and Verification

## 17.1 Test Coverage Areas

The Phase 7 implementation includes tests covering:

- Document configuration.
- Chunking configuration.
- Document validation.
- Document storage.
- Checksum verification.
- Path traversal protection.
- PDF extraction.
- OCR.
- Text cleaning.
- Document structure extraction.
- Document chunking.
- Database persistence.
- Document models.
- Processing status transitions.
- Processing orchestration.
- Retry configuration.
- Retry execution.
- Error classification.
- Concurrency protection.
- Processing observability.
- API integration.
- Processing reliability.

## 17.2 Focused Reliability Test Run

Reported result:

```text
77 passed, 9 skipped in 1.82s
```

## 17.3 Full Project Regression Test Run

Command:

```powershell
python -m pytest
```

Reported result:

```text
746 passed, 12 skipped, 1 warning in 8.65s
```

The warning originated from the installed Google GenAI package's use of Python's deprecated `_UnionGenericAlias`.

It was a deprecation warning, not a test failure.

Some integration tests are opt-in and were skipped in this run. The reported full-suite result must not be interpreted as proof that every live PostgreSQL integration scenario ran.

## 17.4 Additional Verification

Command:

```powershell
git diff --check
```

Result: No reported whitespace errors.

Commands:

```powershell
alembic current
alembic heads
alembic check
```

Result:

- Current migration matches migration head.
- No new upgrade operations detected.

---

# 18. Important Source Files

## Configuration

```text
app/core/
    chunking_config.py
    retry_config.py
```

## Database and API

```text
app/
    api/
        documents.py

    models/
        document.py
```

## Document Processing Services

```text
app/services/
    document_storage_service.py
    document_processing_service.py
    document_status_service.py
    document_chunking_service.py
    document_error_service.py
    document_retry_service.py
    document_observability_service.py
```

Additional PDF extraction, OCR, text-cleaning, structure extraction and document database services support the processing pipeline.

## Migration

```text
alembic/versions/
    f3a9c7d21b60_phase_7_8_processing_recovery.py
```

## Tests

```text
tests/
    test_chunking_config.py
    test_document_chunking_service.py
    test_document_error_service.py
    test_document_observability_service.py
    test_document_processing_e2e.py
    test_document_processing_hardening.py
    test_document_reliability_integration.py
    test_document_reliability_unit.py
    test_document_retry_service.py
    test_retry_config.py
```

Other document-related tests are also present in the project.

---

# 19. Phase Completion Assessment

The document-processing implementation has a substantial automated test record and verified database migration consistency.

| Area | Assessment |
|---|---|
| Upload and validation | Implemented |
| Secure document storage | Implemented |
| PDF extraction | Implemented |
| OCR integration | Implemented |
| Text normalization | Implemented |
| Structure extraction | Implemented |
| Chunking | Implemented |
| Database integration | Implemented |
| Processing lifecycle | Implemented |
| Atomic processing claims | Implemented |
| Retry and error classification | Implemented |
| Processing observability | Implemented |
| Document API integration | Implemented |
| Authenticated production access | Deferred |
| Durable background job execution | Deferred |
| Stale-worker recovery | Deferred |
| Distributed observability | Deferred |

The implementation and reported regression results support completion of the document-processing foundation.

Production authentication, durable background execution and stale-worker recovery remain explicit limitations.

---

# 20. Git Checkpoint

Previously recorded local Git history:

| Commit | Description |
|---|---|
| `aa558ef` | Complete Phase 7.12 document database integration |
| `282915d` | Complete Phase 7.13 document processing status management |
| `bd7cac5` | Complete Phase 7.16 document API integration |

The repository was previously reported as three commits ahead of `origin/master`.

These are historical checkpoint details. The current branch, working tree, staged changes and latest commit must be verified before committing.

## Final Git procedure

1. Review all changed files.
2. Exclude scratch audit files and temporary bundles.
3. Stage intended Phase 7 source files, tests, migration and documentation.
4. Review the staged diff.
5. Commit with a descriptive message.
6. Verify the commit.
7. Push to the existing GitHub remote.
8. Confirm repository synchronization.

Do not stage temporary audit files or unrelated changes.

---

# 21. Transition to Phase 8

## Phase 8 — Embeddings and Vector Search

Phase 7 produces structured, cleaned and chunked document content.

Phase 8 will transform that content into vector representations and establish semantic retrieval infrastructure.

### Planned Phase 8 work

1. Define embedding architecture.
2. Evaluate embedding model options.
3. Select an embedding provider and model.
4. Establish embedding configuration.
5. Design vector metadata.
6. Select and integrate vector storage.
7. Generate embeddings from document chunks.
8. Persist embeddings.
9. Implement similarity search.
10. Implement metadata filtering.
11. Establish retrieval result schemas.
12. Integrate vector retrieval with document ownership constraints.
13. Add embedding and retrieval tests.
14. Document indexing and re-indexing workflows.

### Important architectural requirement

Each embedding must retain a reliable association with:

- Its source document.
- Its source chunk.
- Its document owner.
- Relevant chunk metadata.
- The embedding model and version.

This relationship will be essential for document-grounded retrieval and access control.

Do not begin RAG implementation before the embedding and retrieval foundation is established.

---

# 22. Final Phase 7 Statement

Phase 7 establishes ScholarAI's document-processing foundation.

It provides the upload, storage, extraction, OCR, normalization, structure extraction, chunking, database integration, processing lifecycle, retry and observability components required by later AI workflows.

The implementation has passed the reported automated regression suite and database migration checks.

The remaining production-hardening limitations are explicitly recorded and must be addressed in the relevant later phases.

**Next development phase: Phase 8 — Embeddings and Vector Search.**

**Overall project objective: Complete all 22 phases of the original ScholarAI roadmap.**