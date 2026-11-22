# Phase 21.2 — Environment and Configuration Management

## 1. Objective

Implement secure and environment-specific configuration
management for ScholarAI.

Supported environments:

- Development
- Testing
- Production

Supported execution environments:

- Local Python execution
- Docker containers
- Cloud deployment

## 2. Configuration Architecture

Environment Variables
        |
        v
python-dotenv
        |
        v
app/core/config.py
        |
        v
Application Settings

Specialized configuration modules remain responsible
for their own configuration domains.

Examples:

- jwt_config.py
- document_config.py
- embedding_config.py
- llm_provider_config.py
- resource_provider_config.py
- opportunity_provider_config.py
- security_config.py
- session_config.py
- ocr_config.py
- conversation_context_config.py

## 3. Environment Types

### Development

Used for local development.

Example:

SCHOLARAI_ENVIRONMENT=development
SCHOLARAI_DEBUG=false
SCHOLARAI_FRONTEND_ORIGIN=http://127.0.0.1:5500

### Testing

Used by automated tests.

Example:

SCHOLARAI_ENVIRONMENT=testing

Tests should use isolated databases and controlled
environment variables.

### Production

Used by deployed application instances.

Requirements:

- Debug disabled.
- HTTPS frontend origin.
- Production database URL.
- Strong JWT secret.
- Production database password.
- Valid AI provider credentials.
- Persistent document storage.

## 4. Environment Files

.env.example

Purpose:
Reusable configuration template.

.env

Purpose:
Local development configuration containing actual credentials.

Production secrets:

Must be supplied through a deployment platform's secret
management facility or an equivalent secure mechanism.

The production environment file must never be committed.

## 5. Environment Variables

### Application

- SCHOLARAI_ENVIRONMENT
- SCHOLARAI_DEBUG
- SCHOLARAI_FRONTEND_ORIGIN
- SCHOLARAI_BACKEND_HOST
- SCHOLARAI_BACKEND_PORT
- LOG_LEVEL

### Database

- DATABASE_URL
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

### Authentication

- SCHOLARAI_JWT_SECRET_KEY
- SCHOLARAI_JWT_ALGORITHM
- SCHOLARAI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES
- SCHOLARAI_JWT_ISSUER
- SCHOLARAI_JWT_AUDIENCE
- SCHOLARAI_REFRESH_TOKEN_EXPIRE_DAYS

### Documents

- DOCUMENT_STORAGE_ROOT

### AI and embeddings

- GEMINI_API_KEY
- GEMINI_MODEL
- GEMINI_TEMPERATURE
- GEMINI_MAX_OUTPUT_TOKENS
- GEMINI_TIMEOUT_SECONDS
- SCHOLARAI_LLM_FALLBACK_PROVIDERS
- EMBEDDING_PROVIDER
- EMBEDDING_MODEL
- EMBEDDING_DIMENSIONS
- EMBEDDING_TIMEOUT_SECONDS
- EMBEDDING_MAX_RETRIES
- EMBEDDING_RETRY_BASE_DELAY
- EMBEDDING_RETRY_MAX_DELAY
- EMBEDDING_MAX_CONCURRENCY
- EMBEDDING_MAX_INPUT_CHARACTERS

### OCR

- TESSERACT_CMD
- OCR_LANGUAGE
- OCR_DPI
- OCR_TIMEOUT_SECONDS
- OCR_MINIMUM_CONFIDENCE
- OCR_FORCE

### Conversation context

- SCHOLARAI_MAX_HISTORY_MESSAGES
- SCHOLARAI_MAX_CONTEXT_TOKENS
- SCHOLARAI_MAX_HISTORY_MESSAGE_CHARACTERS
- SCHOLARAI_CHARACTERS_PER_TOKEN

### Educational resources

- RESOURCE_DISCOVERY_ENABLED
- YOUTUBE_API_KEY
- OPENALEX_API_KEY
- CROSSREF_MAILTO
- GOOGLE_BOOKS_API_KEY
- RESOURCE_DISCOVERY_TIMEOUT_SECONDS
- RESOURCE_DISCOVERY_MAX_RETRIES
- RESOURCE_DISCOVERY_BASE_RETRY_DELAY
- RESOURCE_DISCOVERY_MAX_RETRY_DELAY
- RESOURCE_DISCOVERY_MAX_CONCURRENCY
- RESOURCE_DISCOVERY_MAX_RESULTS

### Opportunities

- OPPORTUNITY_DISCOVERY_ENABLED
- ADZUNA_PROVIDER_ENABLED
- ADZUNA_APP_ID
- ADZUNA_APP_KEY
- ADZUNA_COUNTRY
- OPPORTUNITY_TIMEOUT_SECONDS
- OPPORTUNITY_MAX_RETRIES
- OPPORTUNITY_BASE_RETRY_DELAY
- OPPORTUNITY_MAX_RETRY_DELAY
- OPPORTUNITY_MAX_CONCURRENCY
- OPPORTUNITY_MAX_RESULTS

## 6. Secret Management

Sensitive values include:

- Database credentials.
- JWT signing secret.
- Gemini API key.
- YouTube API key.
- Adzuna credentials.
- Future external provider credentials.

Security rules:

1. Never hard-code secrets.
2. Never commit .env.
3. Never print credentials in logs.
4. Never expose credentials in API responses.
5. Use separate development and production credentials.
6. Rotate exposed credentials.
7. Restrict secret access.
8. Use deployment-platform secret management in production.

## 7. JWT Secret Generation

Generate a cryptographically random secret:

python -c "import secrets; print(secrets.token_urlsafe(48))"

Store the generated value securely.

Never reuse an exposed JWT secret.

## 8. Database Configuration

Local example:

postgresql+psycopg://scholarai:PASSWORD@localhost:5432/scholarai

Docker example:

postgresql+psycopg://scholarai:PASSWORD@db:5432/scholarai

The hostname must match the database service reachable
from the backend network.

Production must use the deployed database endpoint.

Credentials containing reserved URL characters must be
properly URL-encoded.

## 9. Docker Environment Integration

Docker Compose receives environment variables from its
environment configuration.

The backend must receive a database hostname reachable
inside its Docker network.

The database password must not be committed to source control.

The actual Compose configuration will be verified in Phase 21.3.

## 10. Production Validation

Execute:

python scripts/deployment/validate_environment.py

The validator checks:

- Required production variables.
- JWT secret length.
- Debug mode.
- HTTPS origin.
- PostgreSQL URL scheme.
- Database hostname.
- Database name.
- Placeholder credentials.

Secret values are never printed.

## 11. Automated Tests

Execute:

python -m pytest tests/deployment/test_environment_validation.py -q

Test coverage:

- Development environment.
- Testing environment.
- Valid production configuration.
- Missing required variables.
- JWT validation.
- Debug validation.
- HTTPS validation.
- Database URL validation.
- Database password validation.
- Gemini credential validation.
- Invalid environment names.

## 12. Production Security Checklist

- [ ] Production environment selected.
- [ ] Debug disabled.
- [ ] HTTPS origin configured.
- [ ] Database credentials configured.
- [ ] JWT secret generated.
- [ ] Gemini API key configured.
- [ ] Required provider credentials configured.
- [ ] Secrets stored outside Git.
- [ ] Document storage is persistent.
- [ ] Logging level reviewed.
- [ ] Production validator passes.

## 13. Acceptance Criteria

Phase 21.2 is accepted when:

1. Central application settings are environment-aware.
2. Existing settings imports remain compatible.
3. Environment template exists.
4. Production validation works.
5. Missing or unsafe production values are rejected.
6. Secret values are not printed.
7. Automated configuration tests pass.
8. Configuration documentation is complete.
9. Docker environment integration is verified.
10. Existing application tests remain unaffected.

## 14. Scope Boundaries

This phase establishes configuration management.

It does not deploy ScholarAI.

Container builds and Compose verification belong to Phase 21.3.

Production hosting belongs to Phase 21.4 and Phase 21.5.
