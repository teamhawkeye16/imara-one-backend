"""
Crawler Schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CrawlSubmitRequest(BaseModel):
    url: str = Field(..., description="Permitted public target URL to crawl")
    max_pages: Optional[int] = Field(default=25, ge=1, le=200)
    max_depth: Optional[int] = Field(default=2, ge=1, le=5)
    allow_subdomains: Optional[bool] = False


class CrawlSubmitResponse(BaseModel):
    job_id: str
    target_url: str
    domain: str
    status: str
    message: str
    created_at: datetime


class CrawlJobStatusResponse(BaseModel):
    job_id: str
    target_url: str
    domain: Optional[str] = None
    status: str  # pending, running, completed, failed
    pages_crawled: int
    pages_indexed: int
    errors_count: int
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime

