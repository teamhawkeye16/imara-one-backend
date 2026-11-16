"""
Engine Statistics Schemas
"""

from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_indexed_documents: int
    total_domains: int
    total_crawl_jobs: int
    total_pages_crawled: int
    search_index_size_bytes: int
    privacy_mode: str
    ai_status: str

