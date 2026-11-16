"""
IMARA ONE Crawler - Indexing Pipeline
Persists crawled items to Database and indexes them into Meilisearch.
"""

import logging
from datetime import datetime, timezone
from scrapy.exceptions import DropItem

from backend.app.database import SessionLocal
from backend.app.models.domain import Domain
from backend.app.models.document import Document
from backend.app.models.document_version import DocumentVersion
from backend.app.services.indexing_service import indexing_service

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


class IndexPipeline:
    def open_spider(self, spider):
        self.db = SessionLocal()
        self.seen_hashes = set()

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        # 1. Minimum content check
        if item.get("word_count", 0) < 15:
            raise DropItem(f"Insufficient readable text ({item.get('word_count')} words): {item.get('url')}")

        content_hash = item["content_hash"]
        if content_hash in self.seen_hashes:
            raise DropItem(f"Duplicate content within current crawl run: {item.get('url')}")
        self.seen_hashes.add(content_hash)

        url = item["url"]
        domain_name = item["domain"]

        try:
            # 2. Get or create domain
            domain = self.db.query(Domain).filter(Domain.domain_name == domain_name).first()
            if not domain:
                domain = Domain(domain_name=domain_name, is_allowed=True)
                self.db.add(domain)
                self.db.commit()
                self.db.refresh(domain)

            # 3. Upsert document in database
            existing_doc = self.db.query(Document).filter(Document.url == url).first()
            if existing_doc:
                if existing_doc.content_hash != content_hash:
                    # Save version
                    version = DocumentVersion(
                        document_id=existing_doc.id,
                        version_num=len(existing_doc.versions) + 1,
                        title=existing_doc.title,
                        clean_text=existing_doc.clean_text,
                        content_hash=existing_doc.content_hash,
                    )
                    self.db.add(version)

                    existing_doc.title = item["title"]
                    existing_doc.meta_description = item.get("meta_description")
                    existing_doc.clean_text = item["clean_text"]
                    existing_doc.content_hash = content_hash
                    existing_doc.word_count = item["word_count"]
                    existing_doc.language = item.get("language", "en")
                    existing_doc.http_status = item.get("http_status", 200)
                    existing_doc.indexed_at = utcnow()
                    self.db.commit()

                    doc_id = existing_doc.id
                else:
                    return item
            else:
                new_doc = Document(
                    domain_id=domain.id,
                    url=url,
                    canonical_url=item.get("canonical_url"),
                    title=item["title"],
                    meta_description=item.get("meta_description"),
                    clean_text=item["clean_text"],
                    content_hash=content_hash,
                    language=item.get("language", "en"),
                    http_status=item.get("http_status", 200),
                    word_count=item["word_count"],
                    indexed_at=utcnow(),
                )
                self.db.add(new_doc)
                self.db.commit()
                self.db.refresh(new_doc)
                doc_id = new_doc.id

            # 4. Push to Meilisearch
            indexing_service.index_document({
                "id": doc_id,
                "url": url,
                "title": item["title"],
                "meta_description": item.get("meta_description"),
                "clean_text": item["clean_text"],
                "domain": domain_name,
                "language": item.get("language", "en"),
                "http_status": item.get("http_status", 200),
                "word_count": item["word_count"],
            })

            logger.info(f"Indexed document into search index: {url}")
            return item

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error persisting crawled document {url}: {e}")
            raise DropItem(f"Database/Index error: {e}")

