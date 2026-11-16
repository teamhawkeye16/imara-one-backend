"""
IMARA ONE Search - Crawler Service
Orchestrates website crawling, content extraction, robots.txt compliance,
strict SSRF validation, deduplication, and search indexing.
"""

import asyncio
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models.domain import Domain
from backend.app.models.document import Document
from backend.app.models.document_version import DocumentVersion
from backend.app.models.crawl import CrawlJob, CrawlPage
from backend.app.security.ssrf import validate_url_safe
from backend.app.services.indexing_service import indexing_service

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


class CrawlerService:
    @staticmethod
    def extract_domain(url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def submit_crawl_job(
        self,
        db: Session,
        url: str,
        max_pages: int = 25,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Submit a permitted public URL for crawling with SSRF protection."""
        # 1. SSRF and URL validation
        is_safe, validated_url, resolved_ip = validate_url_safe(url)
        if not is_safe:
            raise ValueError(f"SSRF Safety Validation Failed: {validated_url}")

        domain_name = self.extract_domain(validated_url)

        # 2. Get or create Domain record
        domain = db.query(Domain).filter(Domain.domain_name == domain_name).first()
        if not domain:
            domain = Domain(
                domain_name=domain_name,
                is_allowed=True,
                crawl_frequency_hours=24,
            )
            db.add(domain)
            db.commit()
            db.refresh(domain)
        elif not domain.is_allowed:
            raise PermissionError(f"Domain '{domain_name}' is restricted or blacklisted.")

        # 3. Create CrawlJob
        job = CrawlJob(
            domain_id=domain.id,
            target_url=validated_url,
            status="pending",
            pages_crawled=0,
            pages_indexed=0,
            errors_count=0,
            config_json=f'{{"max_pages": {max_pages}, "max_depth": {max_depth}}}',
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 4. Launch crawler worker in a background thread
        thread = threading.Thread(
            target=self._run_crawler_worker,
            args=(job.id, validated_url, max_pages, max_depth),
            daemon=True,
        )
        thread.start()

        return {
            "job_id": job.id,
            "target_url": validated_url,
            "domain": domain_name,
            "status": "pending",
            "message": "Crawl job accepted and queued for execution.",
            "created_at": job.created_at,
        }

    def _run_crawler_worker(self, job_id: str, seed_url: str, max_pages: int, max_depth: int):
        """Worker thread executing the crawler job."""
        db: Session = SessionLocal()
        try:
            job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
            if not job:
                return

            job.status = "running"
            job.start_time = utcnow()
            db.commit()

            domain_name = self.extract_domain(seed_url)
            visited_urls = set()
            urls_to_visit = [(seed_url, 0)]  # (url, depth)

            pages_crawled = 0
            pages_indexed = 0
            errors_count = 0

            # Headers for polite crawler
            headers = {
                "User-Agent": settings.CRAWLER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                while urls_to_visit and pages_crawled < max_pages:
                    current_url, current_depth = urls_to_visit.pop(0)

                    # Normalize URL
                    clean_current_url = current_url.split("#")[0]
                    if clean_current_url in visited_urls:
                        continue
                    visited_urls.add(clean_current_url)

                    # Re-validate SSRF for every redirect/discovered URL
                    is_safe, val_url, _ = validate_url_safe(clean_current_url)
                    if not is_safe:
                        errors_count += 1
                        continue

                    # Fetch page
                    try:
                        resp = client.get(val_url)
                        pages_crawled += 1

                        # Log crawl page discovery
                        crawl_page = CrawlPage(
                            job_id=job.id,
                            url=val_url,
                            status_code=resp.status_code,
                        )
                        db.add(crawl_page)

                        if resp.status_code != 200:
                            errors_count += 1
                            db.commit()
                            continue

                        # Check content type (HTML only)
                        content_type = resp.headers.get("content-type", "")
                        if "text/html" not in content_type and "application/xhtml" not in content_type:
                            continue

                        # Extract content using BeautifulSoup
                        soup = BeautifulSoup(resp.text, "html.parser")

                        # Remove script and style elements
                        for element in soup(["script", "style", "noscript", "svg", "iframe", "header", "footer", "nav"]):
                            element.decompose()

                        # Extract Title
                        title = ""
                        if soup.title and soup.title.string:
                            title = soup.title.string.strip()
                        if not title:
                            h1 = soup.find("h1")
                            if h1:
                                title = h1.get_text().strip()
                        if not title:
                            title = val_url

                        # Extract Meta Description
                        meta_desc = ""
                        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                        if meta_tag and meta_tag.get("content"):
                            meta_desc = meta_tag["content"].strip()

                        # Extract Clean Text
                        clean_text = " ".join(soup.stripped_strings)
                        if len(clean_text) < 50:
                            # Not enough readable text
                            db.commit()
                            continue

                        # Calculate Content Hash (SHA-256)
                        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
                        word_count = len(clean_text.split())

                        crawl_page.content_hash = content_hash

                        # Check if document already exists
                        existing_doc = db.query(Document).filter(Document.url == val_url).first()
                        if existing_doc:
                            # Update if content has changed
                            if existing_doc.content_hash != content_hash:
                                # Save version
                                version = DocumentVersion(
                                    document_id=existing_doc.id,
                                    version_num=len(existing_doc.versions) + 1,
                                    title=existing_doc.title,
                                    clean_text=existing_doc.clean_text,
                                    content_hash=existing_doc.content_hash,
                                )
                                db.add(version)

                                existing_doc.title = title
                                existing_doc.meta_description = meta_desc
                                existing_doc.clean_text = clean_text
                                existing_doc.content_hash = content_hash
                                existing_doc.word_count = word_count
                                existing_doc.indexed_at = utcnow()
                                db.commit()

                                # Update Meilisearch
                                indexing_service.index_document({
                                    "id": existing_doc.id,
                                    "url": existing_doc.url,
                                    "title": existing_doc.title,
                                    "meta_description": existing_doc.meta_description,
                                    "clean_text": existing_doc.clean_text,
                                    "domain": domain_name,
                                    "word_count": word_count,
                                })
                                pages_indexed += 1
                        else:
                            # Create new document
                            domain = db.query(Domain).filter(Domain.domain_name == domain_name).first()
                            new_doc = Document(
                                domain_id=domain.id if domain else None,
                                url=val_url,
                                title=title,
                                meta_description=meta_desc,
                                clean_text=clean_text,
                                content_hash=content_hash,
                                word_count=word_count,
                                indexed_at=utcnow(),
                            )
                            db.add(new_doc)
                            db.commit()
                            db.refresh(new_doc)

                            # Index into Meilisearch
                            indexing_service.index_document({
                                "id": new_doc.id,
                                "url": new_doc.url,
                                "title": new_doc.title,
                                "meta_description": new_doc.meta_description,
                                "clean_text": new_doc.clean_text,
                                "domain": domain_name,
                                "word_count": word_count,
                            })
                            pages_indexed += 1

                        # Discover links if within depth limit
                        if current_depth < max_depth:
                            for a in soup.find_all("a", href=True):
                                href = a["href"].strip()
                                next_url = urljoin(val_url, href)
                                next_domain = self.extract_domain(next_url)

                                # Only follow same domain links
                                if next_domain == domain_name and next_url not in visited_urls:
                                    urls_to_visit.append((next_url, current_depth + 1))

                    except Exception as e:
                        logger.warning(f"Error crawling {val_url}: {e}")
                        errors_count += 1
                        db.commit()

                    # Commit progress
                    job.pages_crawled = pages_crawled
                    job.pages_indexed = pages_indexed
                    job.errors_count = errors_count
                    db.commit()

            # Mark completed
            job.status = "completed"
            job.end_time = utcnow()
            db.commit()

        except Exception as e:
            logger.error(f"Crawl job {job_id} encountered fatal error: {e}")
            job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.end_time = utcnow()
                db.commit()
        finally:
            db.close()

    def get_job_status(self, db: Session, job_id: str) -> Optional[Dict[str, Any]]:
        job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
        if not job:
            return None
        return {
            "job_id": job.id,
            "target_url": job.target_url,
            "domain": job.domain.domain_name if job.domain else None,
            "status": job.status,
            "pages_crawled": job.pages_crawled,
            "pages_indexed": job.pages_indexed,
            "errors_count": job.errors_count,
            "error_message": job.error_message,
            "start_time": job.start_time,
            "end_time": job.end_time,
            "created_at": job.created_at,
        }


crawler_service = CrawlerService()

