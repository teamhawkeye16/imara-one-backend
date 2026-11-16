"""
Scrapy Settings for IMARA ONE Crawler
"""

import os
import sys

# Ensure root workspace is available on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BOT_NAME = "imara_crawler"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

# Politeness and Identity
USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT",
    "IMARA-ONE-Bot/0.1 (+https://imaraone.com/bot; bot@imaraone.com)",
)

# Obey robots.txt rules strictly
ROBOTSTXT_OBEY = True

# Concurrency & Rate Limiting
CONCURRENT_REQUESTS = int(os.getenv("CRAWLER_CONCURRENT_REQUESTS", "4"))
DOWNLOAD_DELAY = float(os.getenv("CRAWLER_DOWNLOAD_DELAY", "1.0"))
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Network timeouts
DOWNLOAD_TIMEOUT = 15

# Cookies & Sessions
COOKIES_ENABLED = False

# Retries
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Downloader Middlewares (SSRF protection first)
DOWNLOADER_MIDDLEWARES = {
    "crawler.middlewares.ssrf_middleware.SSRFProtectionMiddleware": 100,
    "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": 150,
    "scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware": None,
}

# Item Pipelines
ITEM_PIPELINES = {
    "crawler.pipelines.index_pipeline.IndexPipeline": 300,
}

# AutoThrottle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.5

# Feed & Logging
LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

