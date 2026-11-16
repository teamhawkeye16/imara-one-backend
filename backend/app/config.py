"""
IMARA ONE Search - Configuration Module
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "IMARA ONE Search"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "imara_one_super_secret_development_key_not_for_production_32chars"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
    RATE_LIMIT_PER_MINUTE: int = 60

    # Database (Supabase PostgreSQL / Cloud PostgreSQL)
    DATABASE_URL: str = "sqlite:///./imara_search.db"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None

    # Meilisearch
    MEILI_HOST: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str = "imara_meili_master_key_secret_32_chars_min"
    MEILI_DOCS_INDEX: str = "imara_documents"

    # AI Search (RAG)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "ollama"  # ollama, local, etc.
    AI_BASE_URL: str = "http://localhost:11434"
    AI_MODEL: str = "llama3.2"
    AI_TIMEOUT_SECONDS: int = 15

    # Crawler Settings
    CRAWLER_USER_AGENT: str = "IMARA-ONE-Bot/0.1 (+https://imaraone.com/bot; bot@imaraone.com)"
    CRAWLER_MAX_PAGES_PER_JOB: int = 50
    CRAWLER_DOWNLOAD_DELAY: float = 1.0
    CRAWLER_CONCURRENT_REQUESTS: int = 2
    CRAWLER_MAX_DEPTH: int = 2
    CRAWLER_ALLOW_EXTERNAL_LINKS: bool = False

    # Privacy & Security
    PRIVACY_DEFAULT_RAW_QUERY_LOGGING: bool = False
    PRIVACY_DEFAULT_IP_STORAGE: bool = False
    SECURITY_STRICT_SSRF_ENFORCEMENT: bool = True

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
