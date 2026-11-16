"""
IMARA ONE Search - FastAPI Backend Entrypoint
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.services.indexing_service import indexing_service
from backend.app.security.headers import SecurityHeadersMiddleware
from backend.app.security.rate_limiter import limiter
from backend.app.security.sanitizer import sanitize_error_detail

# Import routers
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.search import router as search_router
from backend.app.api.v1.suggestions import router as suggestions_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.crawler import router as crawler_router
from backend.app.api.v1.stats import router as stats_router
from backend.app.api.v1.settings import router as settings_router
from backend.app.api.v1.proxy import router as proxy_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("imara_one")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    try:
        indexing_service.init_index()
    except Exception as e:
        logger.warning(f"Meilisearch index initialization skipped/failed: {e}")

    yield

    # Shutdown tasks
    logger.info("Shutting down IMARA ONE Search Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Independent, Privacy-First Intelligent Search Engine API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate Limiter State
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# Global Exception Handler (sanitizes error details)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": sanitize_error_detail(exc, is_debug=settings.DEBUG),
            "status": "error",
        },
    )


# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(search_router, prefix=api_v1_prefix)
app.include_router(suggestions_router, prefix=api_v1_prefix)
app.include_router(documents_router, prefix=api_v1_prefix)
app.include_router(crawler_router, prefix=api_v1_prefix)
app.include_router(stats_router, prefix=api_v1_prefix)
app.include_router(settings_router, prefix=api_v1_prefix)
app.include_router(proxy_router, prefix=api_v1_prefix)


@app.get("/")
def root():
    return {
        "brand": "IMARA ONE",
        "product": "IMARA ONE Search",
        "tagline": "One Ecosystem. Endless Protection.",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

