"""
Search and AI Search Endpoints
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.search import SearchResponse
from backend.app.schemas.ai import AISearchRequest, AISearchResponse
from backend.app.services.search_service import search_service
from backend.app.services.ai_service import ai_service
from backend.app.security.rate_limiter import limiter

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
def execute_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=250, description="Search query string"),
    page: int = Query(default=1, ge=1, le=100, description="Page number"),
    limit: int = Query(default=10, ge=1, le=50, description="Hits per page"),
    safe_search: str = Query(default="moderate", pattern="^(strict|moderate|off)$"),
    db: Session = Depends(get_db),
):
    """
    Search indexed web documents with configurable ranking,
    safe search filtering, and automatic resilient fallback.
    """
    return search_service.search(
        db=db,
        query=q,
        page=page,
        limit=limit,
        safe_search=safe_search,
    )


@router.post("/search/ai", response_model=AISearchResponse)
@limiter.limit("30/minute")
def execute_ai_search(
    request: Request,
    payload: AISearchRequest,
    db: Session = Depends(get_db),
):
    """
    Perform AI-augmented retrieval search. Grounded exclusively
    in indexed documents with verified citations.
    """
    return ai_service.answer_query(
        db=db,
        question=payload.query,
        max_citations=payload.max_citations,
    )

