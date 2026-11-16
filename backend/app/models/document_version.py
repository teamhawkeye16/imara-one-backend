"""
DocumentVersion model - tracks historical versions and changes of documents.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_num = Column(Integer, nullable=False, default=1)
    title = Column(String(512), nullable=False)
    clean_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="versions")

