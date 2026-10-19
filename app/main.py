from fastapi import FastAPI

from app.api.chat import router as chat_router


app = FastAPI(
    title="ScholarAI",
    description="An AI-powered academic learning platform",
    version="0.1.0",
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

