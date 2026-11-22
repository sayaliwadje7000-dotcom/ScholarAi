# Phase 21.1 — Production Deployment Architecture

## 1. Objective

Define a production deployment architecture for ScholarAI while
preserving the existing application, API contracts, database models,
document processing services, and recommendation systems.

## 2. Existing Application Architecture

### Frontend
- HTML
- CSS
- JavaScript
- frontend/index.html
- frontend/js/api.js
- frontend/js/app.js

### Backend
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- Psycopg 3
- Alembic
- pgvector

### AI and document processing
- Google GenAI integration
- PDF processing with PyMuPDF
- Embedding and semantic retrieval services
- Recommendation and personalization services
- Opportunity provider integrations

## 3. Production Deployment Topology

Internet
  |
  | HTTPS
  v
Nginx Reverse Proxy
  |
  |-- Static frontend
  |
  |-- /api/* ------> FastAPI / Uvicorn
  |-- /health -----> FastAPI
  |
  v
FastAPI Application
  |
  |-- PostgreSQL + pgvector
  |-- Persistent document storage
  |-- External AI providers
  |-- Educational resource providers
  |-- Opportunity providers

## 4. Container Architecture

Initial containers:

1. frontend
   - Nginx
   - Serves static frontend assets
   - Proxies API requests to backend

2. backend
   - Python runtime
   - FastAPI
   - Uvicorn
   - Application dependencies

3. database
   - PostgreSQL 16
   - pgvector extension
   - Persistent database volume

## 5. Persistent Storage

The existing document storage service uses DOCUMENT_STORAGE_ROOT.

Production storage must be mounted outside the disposable container
filesystem.

The initial Compose deployment uses a persistent Docker volume.

Database data must also use a persistent volume.

## 6. Database Migrations

Alembic remains the schema migration authority.

Production migrations must run as a controlled deployment operation.

The application container must not automatically generate migrations
or modify database schemas during application startup.

## 7. Network Design

- Only the frontend web server is exposed publicly.
- Backend communication occurs over the internal Docker network.
- PostgreSQL is not exposed publicly by default.
- HTTPS termination will be configured at the production edge.
- Secrets must be provided through environment configuration.

## 8. Health and Reliability

Existing endpoints:
- /
- /health
- /health/database

Container health checks will use /health.

Database readiness must be checked separately.

## 9. Deployment Principles

- Immutable application images.
- Explicit dependency installation.
- Persistent database and document storage.
- Environment-based configuration.
- No secrets in source control.
- Controlled database migrations.
- Health checks and structured logs.
- Reproducible deployment configuration.

## 10. Deferred Decisions

The following will be finalized in later subphases:

- Hosting provider and region.
- Production domain.
- TLS certificate and renewal.
- External managed database versus container database.
- Object storage versus persistent filesystem.
- Monitoring and alerting provider.
- Backup retention policy.

## 11. Completion Criteria

- Existing frontend and backend architecture documented.
- PostgreSQL and pgvector deployment requirements documented.
- Document persistence requirement documented.
- Network boundaries defined.
- Migration strategy defined.
- Container architecture established.
