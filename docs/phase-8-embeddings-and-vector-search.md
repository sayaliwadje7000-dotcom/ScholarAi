## Step 8.2 — Embedding Configuration and Service

### Objective

Implement an independently configurable, provider-agnostic
embedding service for ScholarAI.

### Primary provider

Google Gemini Embedding 2.

Model identifier: `gemini-embedding-2`

Initial output dimension: 1536.

### Architecture

The embedding subsystem consists of:

- Centralized embedding settings.
- Typed embedding request and response contracts.
- Provider abstraction.
- Gemini provider implementation.
- Application-facing embedding service.
- Structured exception hierarchy.
- Bounded retry and concurrency policies.

### Supported operations

- Single document embedding.
- Single query embedding.
- Multiple document embeddings.
- Provider lifecycle management.

### Validation

The subsystem validates:

- Input type.
- Empty input.
- Configured character limit.
- Output vector presence.
- Output dimensionality.
- Numeric vector values.
- Finite floating-point values.
- Response cardinality.

### Reliability

- Asynchronous SDK operations.
- Bounded concurrent execution.
- Configurable timeout.
- Bounded retry attempts.
- Exponential backoff with jitter.
- Sanitized provider errors.

### Important limitations

- No database persistence is implemented in this step.
- No pgvector dependency is introduced.
- No empirical model-quality claim is made.
- Token count is not inferred from character count.
- No automatic truncation is performed.
- Batch operations use bounded independent requests.
- Live API behavior requires a separate integration test.

### Future integration

Step 8.3 will establish chunk-to-embedding data modeling.

Step 8.4 will install and configure pgvector.

Step 8.5 will integrate the embedding service into the
document embedding pipeline.

Step 8.9 will evaluate model quality and retrieval performance.
## Step 8.3 — Chunk-to-Embedding Data Modeling

### Objective

Establish persistent relational data models connecting
processed document chunks with versioned embedding metadata.

### New tables

- document_chunks
- chunk_embeddings

### DocumentChunk

Stores:

- Deterministic chunk identifier
- Document foreign key
- Chunk index
- Extracted text
- SHA-256 content hash
- Page metadata
- Character count
- Word count
- Optional token count
- Chunking version
- Creation timestamp

### ChunkEmbedding

Stores:

- Embedding identifier
- Chunk foreign key
- Content hash
- Provider
- Model identifier
- Model version
- Embedding dimensions
- Pipeline version
- Processing status
- Error code
- Creation timestamp
- Update timestamp

### Relationships

Document -> DocumentChunk -> ChunkEmbedding

Document ownership is inherited through the document relationship.
No redundant user identifier is stored in the chunk tables.

### Integrity

- Foreign keys with cascading deletion.
- Unique document/chunk-index combination.
- Unique embedding identity.
- SHA-256 content integrity.
- Valid embedding status constraints.
- Positive dimension constraints.
- Indexed chunk, model and status fields.

### Vector storage limitation

The chunk embedding table stores embedding metadata only.

The actual vector column and vector indexes are deferred until
pgvector installation in Step 8.4.

### Versioning

Embedding identity includes:

- Content hash
- Provider
- Model
- Model version
- Dimensions
- Pipeline version

This allows multiple compatible embedding generations to be
tracked without confusing vectors generated from different
content or configurations.
## Phase 8.4 — Vector Database Infrastructure

### 1. Objective

Establish PostgreSQL pgvector infrastructure for persistent,
versioned document chunk embeddings.

This phase establishes vector storage and indexing infrastructure.
Embedding generation and similarity retrieval are outside its scope.

### 2. Technology

| Component | Implementation |
|---|---|
| Database | PostgreSQL 18 |
| Vector extension | pgvector 0.8.7 |
| Python integration | pgvector |
| ORM | SQLAlchemy |
| Migration | Alembic |
| Vector dimensions | 1536 |
| Index algorithm | HNSW |
| Similarity metric | Cosine distance |

### 3. Database Schema

The `chunk_embeddings` table contains a nullable vector column:

    embedding VECTOR(1536)

The vector column is nullable because embedding records may exist
in pending, failed, or stale states without a generated vector.

A database check constraint ensures that non-null vectors use
the configured 1536-dimensional storage strategy.

### 4. HNSW Index

Index name:

    ix_chunk_embeddings_embedding_hnsw

Configuration:

| Parameter | Value |
|---|---|
| Index method | HNSW |
| Operator class | vector_cosine_ops |
| m | 16 |
| ef_construction | 64 |

The index is partial and includes only records satisfying:

    embedding IS NOT NULL AND status = 'ready'

This avoids indexing incomplete embedding records.

### 5. Migration

Revision:

    b7c4e91a2d60

Previous revision:

    06b0f8605b90

The migration:

1. Checks that the PostgreSQL vector extension is activated.
2. Adds the nullable VECTOR(1536) column.
3. Adds the vector dimension check constraint.
4. Creates the partial HNSW cosine index.

The migration does not create or remove the PostgreSQL extension.
Extension installation and activation are administrator-level
infrastructure responsibilities.

### 6. Configuration

The current embedding configuration is:

    EMBEDDING_PROVIDER=gemini
    EMBEDDING_MODEL=gemini-embedding-2
    EMBEDDING_DIMENSIONS=1536

The embedding provider retains support for its existing
768, 1536, and 3072-dimensional output configurations.

The current PostgreSQL storage implementation accepts
1536-dimensional vectors only.

Additional database dimensions require a deliberate schema
and indexing strategy change.

### 7. Verification

Infrastructure verification includes:

- PostgreSQL extension version.
- SQLAlchemy VECTOR(1536) type.
- Physical PostgreSQL vector column.
- Nullable column configuration.
- HNSW index existence.
- Cosine operator class.
- HNSW index parameters.
- Partial index predicate.
- Alembic migration revision.
- Alembic metadata consistency.
- Automated infrastructure tests.

### 8. Scope Boundary

Completed in Phase 8.4:

- pgvector infrastructure.
- SQLAlchemy vector integration.
- Vector column.
- HNSW cosine index.
- Migration and schema verification.

Not implemented in Phase 8.4:

- Persisting generated embedding vectors.
- Embedding batch processing.
- Similarity search queries.
- Semantic retrieval.
- RAG retrieval pipelines.

These remain subsequent roadmap responsibilities.
## Phase 8.5 — Embedding Generation Pipeline

Status: Implementation completed; verification pending.

### Objective

Generate embeddings for persistent document chunks using the
existing embedding provider abstraction.

### Implementation

File:
- app/services/embeddings/embedding_pipeline.py

Test:
- tests/services/embeddings/test_embedding_pipeline.py

### Features

- Asynchronous embedding generation.
- Configurable batch size.
- Reuses EmbeddingService.
- Uses existing provider concurrency and retry mechanisms.
- Deterministic SHA-256 content hash validation.
- Duplicate chunk ID protection.
- Input validation.
- Per-chunk success and failure reporting.
- Embedding model and dimension validation.
- Input-order preservation.
- Cancellation propagation.
- Pipeline execution timing and success rate.

### Result contracts

ChunkEmbeddingOutcome:
- chunk_id
- content_hash
- status
- embedding
- error_code

EmbeddingPipelineResult:
- total_chunks
- successful_chunks
- failed_chunks
- outcomes
- provider
- model
- dimensions
- duration_seconds
- success_rate

### Architectural boundary

Phase 8.5 generates embeddings in memory.

It does not:
- Persist vectors to PostgreSQL.
- Create or update ChunkEmbedding records.
- Implement duplicate database record detection.
- Implement vector similarity retrieval.
- Implement RAG.

These responsibilities remain in subsequent Phase 8 work.

### Verification

Pending execution of dedicated embedding pipeline tests,
existing embedding tests, full regression suite and
migration consistency checks.
## Phase 8.6 — Embedding Persistence

### Objective

Persist generated document chunk embeddings in PostgreSQL
using the pgvector VECTOR(1536) column.

### Implementation

- Added EmbeddingPersistenceService.
- Added chunk existence validation.
- Added content hash verification.
- Added embedding dimension validation.
- Added provider and model metadata persistence.
- Added pipeline version tracking.
- Added ready and failed embedding states.
- Added update and unchanged-record handling.
- Added transaction commit and rollback handling.

### Database Storage

Embedding vectors are stored in the chunk_embeddings table.

Each record maintains:
- chunk_id
- content_hash
- provider
- model
- model_version
- dimensions
- pipeline_version
- status
- error_code
- embedding vector

### Verification

Unit tests and PostgreSQL integration tests must pass.

The existing HNSW index remains available for the
semantic retrieval phase.

### Scope Boundary

Phase 8.6 implements embedding persistence.

Semantic retrieval, similarity ranking, and metadata-filtered
search are handled by subsequent roadmap tasks.
## Phase 8.8 — Retrieval API and Ownership-Aware Access

### Objective

Expose semantic retrieval through FastAPI while enforcing
document ownership boundaries.

### Implementation

- Added retrieval request and response schemas.
- Added RetrievalService orchestration.
- Added authenticated retrieval endpoint.
- Integrated query embedding generation.
- Integrated SemanticSearchService.
- Added single-document filtering.
- Added multi-document filtering.
- Added authenticated user ownership verification.
- Added inaccessible-document handling.
- Added dependency-managed embedding service lifecycle.
- Added retrieval API and service tests.

### Security

Document IDs supplied by the client are validated against
the authenticated user's document records before retrieval.

The existing get_current_user dependency remains mandatory.

Authentication is fail-closed until the dedicated
authentication phase implements genuine JWT authentication.

### Scope Boundary

Phase 8.8 exposes the retrieval API.

RAG orchestration and answer generation remain part of Phase 9.