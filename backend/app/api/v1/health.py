"""
Health Check Endpoint
"""

import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.schemas.health import HealthResponse, ComponentHealth
from backend.app.services.indexing_service import indexing_service
from backend.app.services.ai_service import ai_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def check_health(db: Session = Depends(get_db)):
    """Check health of backend, database, Meilisearch, and AI provider."""
    services = {}

    # Check Database
    db_start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        services["database"] = ComponentHealth(
            status="healthy",
            latency_ms=db_latency,
            details="Connected to database engine",
        )
    except Exception as e:
        services["database"] = ComponentHealth(
            status="error",
            details=f"Database unreachable: {str(e)[:100]}",
        )

    # Check Meilisearch
    meili_start = time.perf_counter()
    if indexing_service.is_reachable():
        meili_latency = round((time.perf_counter() - meili_start) * 1000, 2)
        services["search_index"] = ComponentHealth(
            status="healthy",
            latency_ms=meili_latency,
            details="Meilisearch cluster active and responsive",
        )
    else:
        services["search_index"] = ComponentHealth(
            status="degraded",
            details="Meilisearch offline; using relational database search fallback",
        )

    # Check AI Provider
    if settings.AI_ENABLED:
        ai_available = ai_service.is_provider_available()
        services["ai_service"] = ComponentHealth(
            status="healthy" if ai_available else "degraded",
            details=f"Provider '{settings.AI_PROVIDER}' (Model: {settings.AI_MODEL}) is {'active' if ai_available else 'offline'}",
        )
    else:
        services["ai_service"] = ComponentHealth(
            status="disabled",
            details="AI service is disabled in configuration (AI_ENABLED=false)",
        )

    overall_status = "ok"
    if services["database"].status == "error":
        overall_status = "error"
    elif any(s.status == "degraded" for s in services.values()):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services=services,
    )

