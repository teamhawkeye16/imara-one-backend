"""
AI Search Schemas (RAG)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    citation_id: int
    title: str
    url: str
    snippet: str
    relevance_score: float = 1.0


class AISearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=300)
    max_citations: int = Field(default=4, ge=1, le=10)


class AISearchResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem]
    model_used: str
    provider: str
    is_available: bool
    generation_time_ms: float
    message: Optional[str] = None

