"""
Engine Statistics Endpoint
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.domain import Domain
from backend.app.models.document import Document
from backend.app.models.crawl import CrawlJob
from backend.app.schemas.stats import StatsResponse
from backend.app.services.indexing_service import indexing_service

router = APIRouter(tags=["Statistics"])


@router.get("/stats", response_model=StatsResponse)
def get_engine_statistics(db: Session = Depends(get_db)):
    """
    Returns high-level statistics for index size, domains, and jobs.
    """
    total_docs = db.query(Document).count()
    total_domains = db.query(Domain).count()
    total_jobs = db.query(CrawlJob).count()

    # Aggregate pages crawled from all jobs
    jobs = db.query(CrawlJob).all()
    total_crawled = sum(j.pages_crawled for j in jobs)

    # Search index stats
    meili_stats = indexing_service.get_stats()
    index_docs = meili_stats.get("numberOfDocuments", total_docs)

    return StatsResponse(
        total_indexed_documents=max(total_docs, index_docs),
        total_domains=total_domains,
        total_crawl_jobs=total_jobs,
        total_pages_crawled=total_crawled,
        search_index_size_bytes=total_docs * 2048,  # approximate
        privacy_mode="Strict (Zero Query & IP Storage by default)",
        ai_status="Enabled" if settings.AI_ENABLED else "Disabled (Configurable)",
    )

