# Phase 21.3 — Docker Containerization and Application Orchestration

## 1. Objective

Containerize the ScholarAI application and establish a reproducible
multi-service deployment architecture.

The architecture includes:

- FastAPI backend.
- Nginx frontend.
- PostgreSQL database.
- pgvector extension.
- Alembic migration service.
- Persistent document storage.
- Container health checks.
- Internal Docker networking.

## 2. Architecture

The public entry point is the Nginx frontend.

Nginx serves static frontend files and forwards API requests
to the FastAPI backend.

The backend connects to PostgreSQL using the internal Docker
service hostname.

The backend stores uploaded and processed documents in a
persistent Docker volume.

## 3. Services

### db

Image:

pgvector/pgvector:pg16

Responsibilities:

- PostgreSQL database.
- pgvector database extension support.
- Persistent database storage.
- Database readiness checks.

### migrate

Responsibilities:

- Wait for database readiness.
- Execute Alembic migrations.
- Exit after successful schema migration.

Command:

alembic upgrade head

The backend depends on successful migration completion.

### backend

Image:

Built from the root Dockerfile.

Responsibilities:

- FastAPI application.
- Authentication.
- Document processing.
- RAG.
- LLM integration.
- Recommendation services.
- Opportunity discovery.
- Database access.

The service listens internally on port 8000.

### frontend

Image:

Built from frontend/Dockerfile.

Responsibilities:

- Serve HTML.
- Serve CSS and JavaScript.
- Reverse proxy API traffic.
- Expose the public HTTP entry point.

Host port:

8080

Container port:

80

## 4. Network Architecture

All application services use the scholarai_internal Docker network.

The frontend can reach the backend using:

http://backend:8000

The backend can reach PostgreSQL using:

db:5432

The database is not publicly exposed.

The backend is not publicly exposed.

Only the frontend publishes a host port.

## 5. Database Persistence

Docker volume:

scholarai_postgres_data

Mount:

/var/lib/postgresql/data

The database volume survives normal container recreation.

Do not use docker compose down -v unless intentionally deleting
the persistent database and document volumes.

## 6. Document Storage

Docker volume:

scholarai_document_storage

Mount:

/app/storage

The application stores:

- Original documents.
- Processed documents.
- Temporary document-processing files.

The application runs as a non-root user.

Verify that the mounted volume is writable by the application
user before accepting production deployment.

## 7. Database Migrations

The migration service executes:

alembic upgrade head

The migration service waits for PostgreSQL health.

The backend waits for successful migration completion.

Migrations are not automatically executed by the FastAPI
application startup lifecycle.

## 8. Backend Image

The backend image:

- Uses Python 3.12 slim.
- Installs Tesseract OCR.
- Installs production Python dependencies.
- Copies application and migration source.
- Creates document-storage directories.
- Runs under a non-root user.
- Exposes port 8000 internally.
- Provides an HTTP health check.

## 9. Frontend Image

The frontend image uses Nginx.

It serves static frontend assets and forwards:

/api/*

to the backend service.

It also forwards:

/health

and:

/health/database

to the backend.

## 10. Environment Variables

The root .env file is used for Docker Compose interpolation.

Required variables include:

- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD
- SCHOLARAI_JWT_SECRET_KEY

AI and external provider credentials are supplied through
the environment.

Never commit production secrets.

## 11. Build

Build the images:

docker compose build

## 12. Configuration Validation

Validate Compose configuration:

docker compose config --quiet

Inspect the resolved configuration:

docker compose config

Do not share resolved output publicly because it can contain
sensitive environment values.

## 13. Start the Application

Start all services:

docker compose up -d --build

Inspect containers:

docker compose ps

Inspect logs:

docker compose logs --tail=100

Backend logs:

docker compose logs backend

Migration logs:

docker compose logs migrate

Database logs:

docker compose logs db

Frontend logs:

docker compose logs frontend

## 14. Health Checks

Frontend:

http://localhost:8080/

Backend:

http://localhost:8080/health

Database:

http://localhost:8080/health/database

Expected backend health response:

{
  "status": "healthy"
}

Expected database health response:

{
  "status": "healthy",
  "database": "connected"
}

## 15. Container Verification

Execute:

python scripts/deployment/verify_container_deployment.py

The verification script checks:

- Required deployment files.
- Docker engine availability.
- Docker Compose configuration.
- Container inspection.
- Frontend availability.
- Backend health.
- Database health.

## 16. Shutdown

Stop containers without deleting persistent data:

docker compose down

Restart:

docker compose up -d

Do not use:

docker compose down -v

unless intentionally deleting all named volumes.

## 17. Production Considerations

Before production deployment:

- Configure HTTPS termination.
- Configure a production domain.
- Use a strong database password.
- Store secrets in a deployment secret manager.
- Restrict database network access.
- Configure database backups.
- Verify document volume permissions.
- Verify migration behavior.
- Configure resource limits.
- Configure centralized logging.
- Configure monitoring and alerting.

The local HTTP Compose configuration is an integration
environment, not a complete public production deployment.

## 18. Acceptance Criteria

Phase 21.3 is accepted when:

1. Backend Docker image builds.
2. Frontend Docker image builds.
3. Production dependencies install successfully.
4. PostgreSQL starts successfully.
5. pgvector is available.
6. Database health checks pass.
7. Alembic migrations complete successfully.
8. FastAPI backend becomes healthy.
9. Nginx serves the frontend.
10. Nginx correctly proxies backend API requests.
11. Document storage persists across container recreation.
12. Database storage persists across container recreation.
13. Backend executes as a non-root user.
14. Container verification succeeds.
15. Existing project tests remain unaffected.

## 19. Scope Boundaries

Phase 21.3 establishes containerization and local orchestration.

Cloud hosting and infrastructure deployment belong to
the following deployment phases.

Production TLS, domain configuration, backups, monitoring,
and operational alerting require separate verification.
