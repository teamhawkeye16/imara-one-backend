"""
Search metrics models - privacy-preserving search statistics.
Strictly avoids raw search history and raw IP collection by default.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, Index
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), nullable=False, index=True)
    query_length = Column(Integer, nullable=False, default=0)
    results_count = Column(Integer, nullable=False, default=0)
    response_time_ms = Column(Float, nullable=False, default=0.0)
    has_results = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class SearchResultMetric(Base):
    __tablename__ = "search_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), nullable=False, index=True)
    document_id = Column(String(36), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    relevance_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
