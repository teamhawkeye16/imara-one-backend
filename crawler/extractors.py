"""
IMARA ONE Crawler - Content Extractor
Extracts clean readability text, metadata, titles, canonical URLs,
and computes SHA-256 content hashes.
"""

import hashlib
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup


class ContentExtractor:
    @staticmethod
    def extract_page_data(html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract clean readable text and structured metadata from raw HTML.
        Uses BeautifulSoup with robust fallback.
        """
        if not html_content:
            return {
                "title": "",
                "meta_description": "",
                "clean_text": "",
                "canonical_url": None,
                "content_hash": "",
                "word_count": 0,
                "language": "en",
            }

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Canonical URL
        canonical_tag = soup.find("link", rel=lambda x: x and "canonical" in x.lower())
        canonical_url = canonical_tag.get("href") if canonical_tag else None

        # 2. Page Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text().strip()
        if not title:
            title = url

        # 3. Meta Description
        meta_description = ""
        meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_desc and meta_desc.get("content"):
            meta_description = meta_desc["content"].strip()
        if not meta_description:
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                meta_description = og_desc["content"].strip()

        # 4. Language
        html_tag = soup.find("html")
        lang = "en"
        if html_tag and html_tag.get("lang"):
            lang = html_tag["lang"][:2].lower()

        # 5. Clean Readable Text
        # Decompose non-content and clutter tags
        for unwanted in soup([
            "script", "style", "noscript", "svg", "iframe",
            "nav", "footer", "header", "aside", "form"
        ]):
            unwanted.decompose()

        # Extract text blocks
        text_lines = [line.strip() for line in soup.stripped_strings if len(line.strip()) > 0]
        clean_text = " ".join(text_lines)

        # Normalize whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # Word count
        words = clean_text.split()
        word_count = len(words)

        # 6. Content Hash (SHA-256 for deduplication)
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

        return {
            "title": title[:512],
            "meta_description": meta_description[:1000] if meta_description else None,
            "clean_text": clean_text,
            "canonical_url": canonical_url,
            "content_hash": content_hash,
            "word_count": word_count,
            "language": lang,
        }

