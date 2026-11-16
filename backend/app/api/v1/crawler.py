"""
Crawler Management Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.crawler import (
    CrawlSubmitRequest,
    CrawlSubmitResponse,
    CrawlJobStatusResponse,
)
from backend.app.services.crawler_service import crawler_service
from backend.app.security.rate_limiter import limiter

router = APIRouter(tags=["Crawler"])


@router.post("/crawler/submit", response_model=CrawlSubmitResponse)
@limiter.limit("10/minute")
def submit_crawl_job(
    request: Request,
    payload: CrawlSubmitRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a permitted public URL for crawling.
    Strictly protected with SSRF defenses and domain authorization checks.
    """
    try:
        result = crawler_service.submit_crawl_job(
            db=db,
            url=payload.url,
            max_pages=payload.max_pages or 25,
            max_depth=payload.max_depth or 2,
        )
        return CrawlSubmitResponse(**result)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule crawl: {str(e)}")


@router.get("/crawler/status/{job_id}", response_model=CrawlJobStatusResponse)
def get_crawl_job_status(
    job_id: str = Path(..., description="Crawl job ID"),
    db: Session = Depends(get_db),
):
    """
    Query the progress and metrics of an active or completed crawl job.
    """
    status = crawler_service.get_job_status(db=db, job_id=job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    return CrawlJobStatusResponse(**status)

