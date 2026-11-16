"""
User Settings Schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class UserSettingsSchema(BaseModel):
    safe_search: str = Field(default="moderate", pattern="^(strict|moderate|off)$")
    privacy_level: str = Field(default="maximum", pattern="^(standard|high|maximum)$")
    ai_enabled: bool = True
    results_per_page: int = Field(default=10, ge=5, le=50)
    theme: str = Field(default="dark", pattern="^(dark|light|system)$")
    allow_anonymous_metrics: bool = False


class UpdateSettingsSchema(BaseModel):
    client_id: Optional[str] = None
    safe_search: Optional[str] = Field(default=None, pattern="^(strict|moderate|off)$")
    privacy_level: Optional[str] = Field(default=None, pattern="^(standard|high|maximum)$")
    ai_enabled: Optional[bool] = None
    results_per_page: Optional[int] = Field(default=None, ge=5, le=50)
    theme: Optional[str] = Field(default=None, pattern="^(dark|light|system)$")
    allow_anonymous_metrics: Optional[bool] = None

