"""
AI Search models - tracks generated answers and source citations.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AIAnswer(Base):
    __tablename__ = "ai_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    provider = Column(String(64), nullable=False, default="ollama")
    model_used = Column(String(64), nullable=False, default="llama3.2")
    generation_time_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    citations = relationship("AnswerCitation", back_populates="ai_answer", cascade="all, delete-orphan")


class AnswerCitation(Base):
    __tablename__ = "answer_citations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    answer_id = Column(String(36), ForeignKey("ai_answers.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(512), nullable=False, default="")
    snippet = Column(Text, nullable=False)
    relevance_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    ai_answer = relationship("AIAnswer", back_populates="citations")
    document = relationship("Document", back_populates="citations")

