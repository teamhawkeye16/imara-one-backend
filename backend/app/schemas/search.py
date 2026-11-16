"""
Search Request & Response Schemas
Enhanced with IMARA ONE Shield Security Indicators & Google-Style Knowledge Panel
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    id: str
    url: str
    title: str
    snippet: str
    meta_description: Optional[str] = None
    domain: str
    score: float = 1.0
    published_date: Optional[str] = None
    is_safe: bool = True
    # IMARA ONE Shield Security Layer
    shield_score: int = 95
    shield_status: str = "SAFE"  # SAFE, CAUTION, SUSPICIOUS
    trackers_count: int = 0
    is_https: bool = True
    shield_reasons: List[str] = []
    anonymous_preview_url: Optional[str] = None


class KnowledgePanel(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    source_name: str = "Wikipedia"
    attributes: Dict[str, str] = {}


class PeopleAlsoAskItem(BaseModel):
    question: str
    snippet: str
    url: Optional[str] = None


class InstantAnswer(BaseModel):
    title: str
    result: str
    category: str  # "calculator", "definition", "conversion", "security", "fact"
    source: Optional[str] = None
    detail: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    page: int
    limit: int
    total_pages: int
    response_time_ms: float
    hits: List[SearchHit]
    did_you_mean: Optional[str] = None
    is_empty: bool = False
    message: Optional[str] = None
    # Google-scale rich features
    knowledge_panel: Optional[KnowledgePanel] = None
    people_also_ask: List[PeopleAlsoAskItem] = []
    related_queries: List[str] = []
    instant_answer: Optional[InstantAnswer] = None


class SuggestResponse(BaseModel):
    query: str
    suggestions: List[str]
