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

# CORS Middleware configuration (explicit allowed origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from backend.app.api.sessions import router as sessions_router
from backend.app.api.media import router as media_router
from backend.app.api.inference import router as inference_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.discovery import router as discovery_router
from backend.app.api.acquisition import router as acquisition_router
from backend.app.api.taxonomy import router as taxonomy_router
from backend.app.api.evaluation import router as evaluation_router
from backend.app.api.findings import router as findings_router

# Include API v1 Routers
app.include_router(sessions_router, prefix=settings.API_V1_PREFIX)
app.include_router(media_router, prefix=settings.API_V1_PREFIX)
app.include_router(inference_router, prefix=settings.API_V1_PREFIX)
app.include_router(reviews_router, prefix=settings.API_V1_PREFIX)
app.include_router(discovery_router, prefix=settings.API_V1_PREFIX)
app.include_router(acquisition_router, prefix=settings.API_V1_PREFIX)
app.include_router(taxonomy_router, prefix=settings.API_V1_PREFIX)
app.include_router(evaluation_router, prefix=settings.API_V1_PREFIX)
app.include_router(findings_router, prefix=settings.API_V1_PREFIX)


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
            "mock_inference_engine": True,
            "sqlite_repository": True,
            "thumbnail_pipeline": True,
            "review_workflow": True
        }
    }
