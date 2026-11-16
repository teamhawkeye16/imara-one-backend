"""
IMARA ONE Search - Rate Limiter Configuration
Uses SlowAPI to prevent denial of service and scraping abuses.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
import hashlib


def get_privacy_safe_client_identifier(request: Request) -> str:
    """
    Computes a privacy-preserving one-way hash of client connection details
    so IP addresses are never kept or exposed in raw form.
    """
    ip = get_remote_address(request) or "127.0.0.1"
    # Salted hash
    salt = "imara_one_rate_limit_salt"
    return hashlib.sha256(f"{salt}_{ip}".encode()).hexdigest()[:32]


limiter = Limiter(
    key_func=get_privacy_safe_client_identifier,
    default_limits=["120/minute"],
    storage_uri="memory://",
)

