from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.retrieval import router as retrieval_router
from app.api.rag import router as rag_router
from app.api.recommendations import router as recommendations_router

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


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown resources.
    """

    opportunity_registry = OpportunityProviderRegistry()

    app.state.opportunity_provider_registry = (
        opportunity_registry
    )

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
    Checks whether PostgreSQL is reachable.
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
)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)

app.include_router(
    retrieval_router,
    prefix="/api/v1/retrieval",
    tags=["Retrieval"],
)

app.include_router(
    rag_router,
    prefix="/api/v1/rag",
    tags=["RAG"],
)

app.include_router(
    recommendations_router,
    prefix="/api/v1/recommendations",
    tags=["Recommendations"],
)

app.include_router(
    content_recommendations_router,
)

app.include_router(
    resource_recommendations_router,
    prefix="/api/v1",
)