"""
IMARA ONE Crawler - SSRF Protection Downloader Middleware
Guarantees crawler never accesses private internal IP addresses,
cloud metadata endpoints, or unauthorized internal infrastructure.
"""

from scrapy.exceptions import IgnoreRequest
import logging
from backend.app.security.ssrf import validate_url_safe

logger = logging.getLogger(__name__)


class SSRFProtectionMiddleware:
    def process_request(self, request, spider):
        url = request.url

        # Validate URL scheme and DNS resolution
        is_safe, message, resolved_ip = validate_url_safe(url)

        if not is_safe:
            logger.warning(
                f"[SSRF BLOCKED] Disallowed crawler request to {url}: {message}"
            )
            raise IgnoreRequest(f"SSRF Safety Policy Blocked URL: {url} ({message})")

        return None

