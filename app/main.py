from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    description="An AI-powered academic learning platform",
    version=settings.APP_VERSION,
)


# Allow the local frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def home():
    return {
        "application": "ScholarAI",
        "message": "Welcome to ScholarAI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],
)