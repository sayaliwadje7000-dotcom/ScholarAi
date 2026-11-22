# Phase 21.1 — Infrastructure Decisions and Trade-offs

## 1. Purpose

Record the architectural decisions that guide ScholarAI production
deployment.

## ADR-001: Static Frontend Hosting

Decision:
Retain the existing HTML, CSS and JavaScript frontend.

Reason:
The current frontend does not require a JavaScript build system.

Consequences:
- Static hosting is sufficient.
- Nginx can serve the frontend.
- API requests must use a deployment-aware URL.
- Existing frontend behavior must be preserved.

## ADR-002: FastAPI Backend Container

Decision:
Deploy the existing FastAPI application in a Python container.

Reason:
The backend already has a modular application structure and
a defined ASGI entry point.

Consequences:
- Uvicorn serves the application.
- The container listens on port 8000 internally.
- The reverse proxy handles public traffic.
- The application runs as a non-root user.

## ADR-003: PostgreSQL with pgvector

Decision:
Keep PostgreSQL as the relational and vector database.

Reason:
Existing models and semantic retrieval services use pgvector.

Consequences:
- Production PostgreSQL must support pgvector.
- Existing migrations must be retained.
- Database backups must include vector data.
- A second vector database is unnecessary initially.

## ADR-004: Persistent Document Storage

Decision:
Use persistent mounted storage for the initial deployment.

Reason:
The existing document storage service writes PDF files to
the filesystem.

Consequences:
- The storage directory must survive container replacement.
- Storage permissions must allow the application user to write.
- Backup procedures must include document files.
- Database and file backups must be coordinated.

Future option:
Introduce object storage behind the existing storage abstraction.

## ADR-005: Controlled Alembic Migrations

Decision:
Run migrations as an explicit deployment operation.

Reason:
Automatic migration execution during every application startup
can cause race conditions and unsafe schema changes.

Consequences:
- Migration execution is a deployment responsibility.
- Migration history must be validated.
- Rollback plans must be documented.
- Application and schema compatibility must be considered.

## ADR-006: Single-Origin Initial Deployment

Decision:
Serve frontend and API through one public origin.

Reason:
This reduces CORS complexity and simplifies browser security.

Consequences:
- Reverse proxy routes API requests.
- Backend remains private.
- Production frontend uses relative API paths.

## ADR-007: Provider-Independent Architecture

Decision:
Do not hard-code a hosting provider into the application.

Reason:
Infrastructure selection requires evaluation of database,
storage, pricing, region and operational capabilities.

Consequences:
- Docker images remain portable.
- Environment variables define deployment configuration.
- Provider-specific configuration is isolated.

## 2. Known Technical Risks

### RISK-001: Local Filesystem Persistence

Impact:
High.

Risk:
Container replacement may delete uploaded documents if storage
is not mounted persistently.

Mitigation:
Use persistent storage and test container replacement.

### RISK-002: Database and File Backup Consistency

Impact:
High.

Risk:
A database backup without the corresponding document files
may leave document records pointing to missing files.

Mitigation:
Coordinate database and document storage backup procedures.

### RISK-003: Frontend API URL

Impact:
High.

Risk:
The current frontend API client references localhost.

Mitigation:
Use relative API paths in production.

### RISK-004: Migration Graph

Impact:
High.

Risk:
A broken or branched migration history can prevent deployment.

Mitigation:
Inspect Alembic heads and history before production rollout.

### RISK-005: Production Dependencies

Impact:
Medium to high.

Risk:
The development requirements file contains notebook and
platform-specific dependencies.

Mitigation:
Create and validate a production-specific dependency manifest.

### RISK-006: External AI Provider Availability

Impact:
Medium to high.

Risk:
External provider downtime can affect AI workflows.

Mitigation:
Preserve provider abstraction, retries, timeouts and
fault-tolerance behavior.

### RISK-007: Long-Running Requests

Impact:
Medium.

Risk:
Document processing and AI requests may exceed default
reverse-proxy timeouts.

Mitigation:
Configure timeouts based on actual workload measurements.

## 3. Deferred Decisions

Hosting provider:
Deferred to Phase 21.4.

Frontend hosting:
Final provider deferred to Phase 21.5.

Database provider:
Final provider deferred to Phase 21.6.

Domain and HTTPS:
Deferred to Phase 21.7.

Monitoring provider:
Deferred to Phase 21.8.

Backup retention:
Final policy deferred to Phase 21.9.

## 4. Decision Review

All decisions must be reviewed against the actual application
before production deployment.

No infrastructure choice may compromise existing application
features or persistent user data.
