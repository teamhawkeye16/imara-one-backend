"""
SSRF Protection and Safe URL Validation Tests
"""

import pytest
from backend.app.security.ssrf import validate_url_safe


def test_ssrf_blocks_localhost():
    is_safe, msg, ip = validate_url_safe("http://localhost:8000/internal")
    assert not is_safe
    assert "localhost" in msg.lower() or "loopback" in msg.lower()


def test_ssrf_blocks_loopback_ip():
    is_safe, msg, ip = validate_url_safe("http://127.0.0.1:8000/")
    assert not is_safe
    assert "loopback" in msg.lower() or "private" in msg.lower()


def test_ssrf_blocks_cloud_metadata():
    is_safe, msg, ip = validate_url_safe("http://169.254.169.254/latest/meta-data/")
    assert not is_safe
    assert "reserved" in msg.lower() or "private" in msg.lower() or "link-local" in msg.lower()


def test_ssrf_blocks_private_networks():
    is_safe_10, _, _ = validate_url_safe("http://10.0.0.1/admin")
    assert not is_safe_10

    is_safe_192, _, _ = validate_url_safe("http://192.168.1.1/router")
    assert not is_safe_192

    is_safe_172, _, _ = validate_url_safe("http://172.16.0.5/api")
    assert not is_safe_172


def test_ssrf_blocks_non_http_schemes():
    is_safe, msg, _ = validate_url_safe("ftp://ftp.example.com/file")
    assert not is_safe
    assert "scheme" in msg.lower()

    is_safe_file, msg_file, _ = validate_url_safe("file:///etc/passwd")
    assert not is_safe_file


def test_ssrf_permits_public_domains():
    is_safe, url, ip = validate_url_safe("https://example.com")
    assert is_safe
    assert "https://example.com" in url
    assert ip is not None

