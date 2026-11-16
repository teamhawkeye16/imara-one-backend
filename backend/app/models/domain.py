"""
Domain model - stores permitted and discovered domain properties.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Domain(Base):
    __tablename__ = "domains"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_name = Column(String(255), unique=True, nullable=False, index=True)
    is_allowed = Column(Boolean, default=True, nullable=False, index=True)
    robots_txt = Column(Text, nullable=True)
    crawl_frequency_hours = Column(Integer, default=24, nullable=False)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    documents = relationship("Document", back_populates="domain", cascade="all, delete-orphan")
    crawl_jobs = relationship("CrawlJob", back_populates="domain")

