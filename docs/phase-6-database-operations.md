# ScholarAI Database Operations

## 1. Database Technology

- PostgreSQL 18
- SQLAlchemy ORM
- Alembic migrations
- Psycopg 3
- FastAPI database integration

## 2. Database Architecture

The database layer consists of:

- Base: Declarative SQLAlchemy model base.
- Session: Database engine and session factory.
- Query Options: Reusable relationship loading strategies.
- Models: Database entity definitions.
- Alembic: Schema migration management.

## 3. Database Tables

ScholarAI currently contains the following 12 tables:

1. users
2. user_preferences
3. conversations
4. messages
5. documents
6. learning_activities
7. study_resources
8. resource_categories
9. study_resource_categories
10. user_resource_interactions
11. recommendations
12. recommendation_feedback

## 4. Database Session Management

The application uses a centralized SQLAlchemy engine
and SessionLocal factory.

Database sessions are provided through get_db().

Sessions are closed after request processing.

Failed transactions are rolled back.

## 5. Connection Management

The engine uses:

- pool_pre_ping
- pool_recycle

These settings support connection health checking
and connection recycling.

## 6. Transaction Management

Database transactions should be committed explicitly
by the service or repository performing the operation.

Failed transactions should be rolled back.

## 7. Database Migrations

Alembic manages database schema changes.

Commands:

    python -m alembic current

    python -m alembic revision --autogenerate -m "migration message"

    python -m alembic upgrade head

    python -m alembic downgrade -1

    python -m alembic check

Migration files must be reviewed before application.

## 8. Testing

Run the complete test suite:

    python -m pytest -v

Run database integration tests:

    python -m pytest tests/test_phase_6_15_database_integration.py -v

## 9. Database Health

The application exposes:

- GET /
- GET /health
- GET /health/database

The database health endpoint verifies PostgreSQL connectivity.

## 10. Optimization

The database uses:

- Foreign keys
- Unique constraints
- Check constraints
- Composite indexes
- Select-in relationship loading
- Appropriate cascade behavior

## 11. Security

Database credentials must remain in environment configuration.

Credentials must never be committed to Git.

Database exceptions must not expose connection credentials.

## 12. Phase 6 Completion

Phase 6 establishes the relational database foundation
for ScholarAI.

It supports user management, conversations,
documents, learning activities, study resources,
recommendations, and recommendation feedback.