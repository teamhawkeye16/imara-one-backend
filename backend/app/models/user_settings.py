"""
User settings model - stores privacy preferences, safe search, and display settings.
Can be stored locally or linked via an anonymous client identifier hash.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id_hash = Column(String(64), unique=True, nullable=False, index=True)
    safe_search = Column(String(16), nullable=False, default="moderate")  # strict, moderate, off
    privacy_level = Column(String(16), nullable=False, default="maximum")  # standard, high, maximum
    ai_enabled = Column(Boolean, nullable=False, default=True)
    results_per_page = Column(Integer, nullable=False, default=10)
    theme = Column(String(16), nullable=False, default="dark")
    allow_anonymous_metrics = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

