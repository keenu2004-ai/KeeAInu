"""KeeAInu Main API Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="KeeAInu — AI-Assisted Industrial Visual Inspection & Videoscope Intelligence Platform API",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container readiness and monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@app.get(f"{settings.API_V1_PREFIX}/status", tags=["System"])
async def system_status():
    """Returns platform operational status and active capabilities."""
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "development",
        "features": {
            "evidence_hashing": True,
            "ingestion_validator": True,
            "inference_engine_manager": True,
            "mock_inference_engine": True
        }
    }
