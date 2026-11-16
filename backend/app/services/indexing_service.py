"""
IMARA ONE Search - Indexing Service
Manages Meilisearch index lifecycle, documents schema, ranking rules,
and resilient search retrieval with fallback support.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import meilisearch
from sqlalchemy.orm import Session

from backend.app.config import settings

logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(self):
        self.host = settings.MEILI_HOST
        self.api_key = settings.MEILI_MASTER_KEY
        self.index_name = settings.MEILI_DOCS_INDEX
        self._client: Optional[meilisearch.Client] = None

    @property
    def client(self) -> meilisearch.Client:
        if self._client is None:
            self._client = meilisearch.Client(self.host, self.api_key, timeout=1.0)
        return self._client

    def is_reachable(self) -> bool:
        """Check if Meilisearch instance is reachable."""
        try:
            health = self.client.health()
            return health.get("status") == "available"
        except Exception as e:
            logger.debug(f"Meilisearch unreachable at {self.host}: {e}")
            return False

    def init_index(self) -> bool:
        """Ensure search index exists with optimal search, ranking, and filter rules."""
        if not self.is_reachable():
            logger.warning("Meilisearch is not reachable; skipping index initialization.")
            return False

        try:
            # Create index if it does not exist
            try:
                self.client.get_index(self.index_name)
            except meilisearch.errors.MeiliSearchApiError:
                self.client.create_index(uid=self.index_name, options={"primaryKey": "id"})

            index = self.client.index(self.index_name)

            # Configure searchable attributes (ranked by priority)
            index.update_searchable_attributes([
                "title",
                "clean_text",
                "meta_description",
                "url",
            ])

            # Configure filterable attributes
            index.update_filterable_attributes([
                "domain",
                "language",
                "http_status",
                "is_safe",
            ])

            # Configure sortable attributes
            index.update_sortable_attributes([
                "indexed_at",
                "word_count",
            ])

            # Configure ranking rules
            index.update_ranking_rules([
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
            ])

            logger.info(f"Meilisearch index '{self.index_name}' configured successfully.")
            return True

        except Exception as e:
            logger.error(f"Failed to configure Meilisearch index: {e}")
            return False

    def index_document(self, doc_data: Dict[str, Any]) -> bool:
        """Index or update a single document."""
        if not self.is_reachable():
            logger.warning("Meilisearch offline; document queued in database only.")
            return False

        try:
            index = self.client.index(self.index_name)
            # Meilisearch document requirements
            document = {
                "id": doc_data["id"],
                "url": doc_data["url"],
                "title": doc_data["title"],
                "meta_description": doc_data.get("meta_description") or "",
                "clean_text": doc_data["clean_text"][:20000],  # index first 20k chars
                "domain": doc_data.get("domain", ""),
                "language": doc_data.get("language", "en"),
                "http_status": doc_data.get("http_status", 200),
                "word_count": doc_data.get("word_count", 0),
                "is_safe": doc_data.get("is_safe", True),
                "indexed_at": int(time.time()),
            }
            index.add_documents([document])
            return True
        except Exception as e:
            logger.error(f"Error indexing document {doc_data.get('id')}: {e}")
            return False

    def batch_index_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Bulk index documents."""
        if not self.is_reachable() or not documents:
            return 0

        try:
            index = self.client.index(self.index_name)
            payload = []
            for doc in documents:
                payload.append({
                    "id": doc["id"],
                    "url": doc["url"],
                    "title": doc["title"],
                    "meta_description": doc.get("meta_description") or "",
                    "clean_text": doc["clean_text"][:20000],
                    "domain": doc.get("domain", ""),
                    "language": doc.get("language", "en"),
                    "http_status": doc.get("http_status", 200),
                    "word_count": doc.get("word_count", 0),
                    "is_safe": doc.get("is_safe", True),
                    "indexed_at": int(time.time()),
                })
            task = index.add_documents(payload)
            logger.info(f"Batched {len(payload)} documents to Meilisearch (Task: {task.task_uid})")
            return len(payload)
        except Exception as e:
            logger.error(f"Failed to batch index documents: {e}")
            return 0

    def delete_document(self, document_id: str) -> bool:
        """Remove a document from index."""
        if not self.is_reachable():
            return False
        try:
            self.client.index(self.index_name).delete_document(document_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from Meilisearch: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Fetch index stats."""
        if not self.is_reachable():
            return {"numberOfDocuments": 0, "isIndexing": False, "status": "offline"}
        try:
            stats = self.client.index(self.index_name).get_stats()
            return dict(stats)
        except Exception as e:
            return {"numberOfDocuments": 0, "isIndexing": False, "error": str(e)}

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute search in Meilisearch."""
        if not self.is_reachable():
            return {"hits": [], "estimatedTotalHits": 0, "fallback": True}

        try:
            index = self.client.index(self.index_name)
            search_params = {
                "limit": limit,
                "offset": offset,
                "attributesToHighlight": ["title", "clean_text", "meta_description"],
                "highlightPreTag": "<mark class='bg-blue-500/20 text-blue-300 rounded px-1'>",
                "highlightPostTag": "</mark>",
                "attributesToCrop": ["clean_text"],
                "cropLength": 40,
            }
            if filters:
                search_params["filter"] = filters

            results = index.search(query, search_params)
            return results
        except Exception as e:
            logger.error(f"Meilisearch search execution error: {e}")
            return {"hits": [], "estimatedTotalHits": 0, "error": str(e), "fallback": True}


indexing_service = IndexingService()

