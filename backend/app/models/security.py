"""
Security events model - logs security violations, blocked SSRF attempts, and rate limiting events.
Never logs raw IP addresses in plaintext; uses salted HMAC / one-way hashing.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text
from backend.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), nullable=False, index=True)  # SSRF_BLOCKED, RATE_LIMIT_EXCEEDED, MALFORMED_QUERY
    severity = Column(String(16), nullable=False, default="warning")  # low, warning, critical
    client_ip_hash = Column(String(64), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

