"""
IMARA ONE Web Spider
Crawls permitted public websites within authorized domain boundaries.
"""

from urllib.parse import urlparse
import scrapy
from scrapy.linkextractors import LinkExtractor
from crawler.extractors import ContentExtractor
from crawler.items import ImaraWebPageItem


class ImaraWebSpider(scrapy.Spider):
    name = "web_spider"

    def __init__(self, start_url=None, max_pages=50, max_depth=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("start_url argument is required.")

        self.start_urls = [start_url]
        parsed = urlparse(start_url)
        self.allowed_domains = [parsed.netloc.lower()]
        self.max_pages = int(max_pages)
        self.max_depth = int(max_depth)
        self.pages_crawled = 0

        self.link_extractor = LinkExtractor(
            allow_domains=self.allowed_domains,
            canonicalize=True,
            unique=True,
            deny_extensions=[
                "pdf", "zip", "exe", "dmg", "mp4", "mp3", "jpg", "jpeg",
                "png", "gif", "svg", "webp", "tar", "gz", "rar", "7z", "iso"
            ],
        )

    def parse(self, response):
        if self.pages_crawled >= self.max_pages:
            self.logger.info(f"Reached max pages quota ({self.max_pages}). Stopping spider.")
            return

        self.pages_crawled += 1
        url = response.url
        html_content = response.text

        # Extract content using ContentExtractor
        extracted = ContentExtractor.extract_page_data(html_content, url)

        domain = urlparse(url).netloc.lower()

        # Build item
        item = ImaraWebPageItem(
            url=url,
            canonical_url=extracted["canonical_url"],
            title=extracted["title"],
            meta_description=extracted["meta_description"],
            clean_text=extracted["clean_text"],
            content_hash=extracted["content_hash"],
            language=extracted["language"],
            http_status=response.status,
            word_count=extracted["word_count"],
            domain=domain,
        )

        yield item

        # Follow internal links if within page limit and depth
        current_depth = response.meta.get("depth", 0)
        if current_depth < self.max_depth and self.pages_crawled < self.max_pages:
            links = self.link_extractor.extract_links(response)
            for link in links:
                yield response.follow(link.url, callback=self.parse)

