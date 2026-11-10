from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.hybrid_recommendations import (
    router as hybrid_recommendations_router,
)
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.retrieval import router as retrieval_router
from app.api.rag import router as rag_router
from app.api.recommendations import (
    router as recommendations_router,
)

from app.api.content_recommendations import (
    router as content_recommendations_router,
)

from app.api.resource_recommendations import (
    router as resource_recommendations_router,
)

from app.core.config import settings

from app.database.session import engine

from app.integrations.opportunities.registry import (
    OpportunityProviderRegistry,
)

from app.api.opportunities import (
    router as opportunities_router,
)

from app.api.ml_recommendations import (
    router as ml_recommendations_router,
)

from app.api.learning_profile import (
    router as learning_profile_router,
)

from app.api.learning_activities import (
    router as learning_activities_router,
)

from app.api.personalization_controls import (
    router as personalization_controls_router,
)

from app.services.llm_providers.provider_setup import (
    register_default_llm_providers,
)


from app.security.permissions import require_student_or_admin


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown resources.

    Initializes the LLM provider registry and the
    educational opportunity provider registry.
    """

    opportunity_registry = OpportunityProviderRegistry()

    app.state.opportunity_provider_registry = (
        opportunity_registry
    )

    # Register configured default LLM providers.
    # Registration is idempotent in provider_setup.py.
    register_default_llm_providers()

    try:
        yield

    finally:
        await opportunity_registry.close()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="An AI-powered academic learning platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)


# ============================================================
# APPLICATION HEALTH
# ============================================================

@app.get("/")
def home():
    return {
        "application": "ScholarAI",
        "message": "Welcome to ScholarAI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.get("/health/database")
def database_health_check():
    """
    Check whether PostgreSQL is reachable.
    """

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }


# ============================================================
# API ROUTERS
# ============================================================

app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    retrieval_router,
    prefix="/api/v1/retrieval",
    tags=["Retrieval"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    rag_router,
    prefix="/api/v1/rag",
    tags=["RAG"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    recommendations_router,
    prefix="/api/v1/recommendations",
    tags=["Recommendations"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    content_recommendations_router,

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    resource_recommendations_router,
    prefix="/api/v1",

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    opportunities_router,
    prefix="/api/v1/opportunities",
    tags=["Opportunities"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    ml_recommendations_router,
    prefix="/api/v1/recommendations",

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    hybrid_recommendations_router,
    prefix="/api/v1",

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    learning_profile_router,
    prefix="/api/v1/learning-profile",
    tags=["Learning Profile"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    learning_activities_router,
    prefix="/api/v1/learning-activities",
    tags=["Learning Activities"],

    dependencies=[Depends(require_student_or_admin)],)

app.include_router(
    personalization_controls_router,
    prefix="/api/v1/personalization-controls",
    tags=["Personalization Controls"],

    dependencies=[Depends(require_student_or_admin)],)
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
from app.api.role_management import router as role_management_router

app.include_router(
    role_management_router,
    prefix="/api/v1/admin",
    tags=["Role Management"],
)
