"""
Crawl models - tracks crawl jobs, page discoveries, and execution stats.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(String(36), ForeignKey("domains.id", ondelete="SET NULL"), nullable=True, index=True)
    target_url = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    pages_crawled = Column(Integer, nullable=False, default=0)
    pages_indexed = Column(Integer, nullable=False, default=0)
    errors_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    config_json = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="crawl_jobs")
    pages = relationship("CrawlPage", back_populates="job", cascade="all, delete-orphan")


class CrawlPage(Base):
    __tablename__ = "crawl_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    content_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    discovered_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    job = relationship("CrawlJob", back_populates="pages")

