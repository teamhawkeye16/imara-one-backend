"""
Document schemas for indexing and retrieval.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


class DocumentBase(BaseModel):
    url: str
    title: str = Field(..., max_length=512)
    meta_description: Optional[str] = None
    clean_text: str
    language: str = "en"
    http_status: int = 200
    word_count: int = 0


class DocumentCreate(DocumentBase):
    domain_name: str
    raw_content: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str
    domain_name: str
    content_hash: str
    indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

