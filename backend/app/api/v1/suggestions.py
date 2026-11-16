"""
Search Suggestions Endpoint
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.search import SuggestResponse
from backend.app.services.search_service import search_service
from backend.app.security.rate_limiter import limiter

router = APIRouter(tags=["Search"])


@router.get("/search/suggest", response_model=SuggestResponse)
@limiter.limit("120/minute")
def get_search_suggestions(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="Query prefix"),
    limit: int = Query(default=6, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """
    Returns search suggestions for auto-completion without storing user history.
    """
    return search_service.suggest(db=db, prefix=q, limit=limit)

