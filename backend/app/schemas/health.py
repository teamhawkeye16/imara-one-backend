"""
System Health Schemas
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str  # healthy, degraded, unavailable
    details: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    status: str  # ok, degraded, error
    version: str
    environment: str
    services: Dict[str, ComponentHealth]

