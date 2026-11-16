"""
Document model - stores parsed, cleaned, and indexed web documents.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(String(36), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False, unique=True, index=True)
    canonical_url = Column(Text, nullable=True)
    title = Column(String(512), nullable=False, default="")
    meta_description = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    language = Column(String(16), nullable=False, default="en")
    http_status = Column(Integer, nullable=False, default=200)
    word_count = Column(Integer, nullable=False, default=0)
    indexed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    domain = relationship("Domain", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("AnswerCitation", back_populates="document")


Index("ix_documents_domain_hash", Document.domain_id, Document.content_hash)

