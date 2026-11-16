"""
IMARA ONE Search - SSRF Protection and URL Security Validator
Strictly guards against server-side request forgery, private network scans,
cloud metadata access, and unauthorized internal IP access.
"""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional


# Blocked IPv4 and IPv6 networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (includes Cloud metadata 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private-use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Network Interconnect Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


class SSRFValidationError(ValueError):
    """Raised when a URL or resolved destination IP violates security policies."""
    pass


def is_ip_blocked(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls within any prohibited network."""
    if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_link_local or ip_addr.is_multicast or ip_addr.is_reserved:
        return True
    for net in BLOCKED_NETWORKS:
        if ip_addr in net:
            return True
    return False


def validate_url_safe(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates a URL for safe crawling and fetching.
    Returns: (is_safe: bool, normalized_url_or_error: Optional[str], resolved_ip: Optional[str])
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL provided", None

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {e}", None

    # Enforce allowed schemes: strictly HTTP and HTTPS
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme: {parsed.scheme}. Only http and https are permitted.", None

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname.", None

    hostname_clean = hostname.lower().strip()

    # Disallow known localhost aliases
    if hostname_clean in ("localhost", "local", "ip6-localhost", "ip6-loopback", "broadcasthost"):
        return False, "Access to localhost or loopback domains is strictly prohibited.", None

    # Check if literal IP address is blocked before checking ports
    try:
        literal_ip = ipaddress.ip_address(hostname_clean)
        if is_ip_blocked(literal_ip):
            return False, f"Destination IP {hostname_clean} belongs to a private, loopback, or reserved address block.", None
    except ValueError:
        pass

    # Check port
    port = parsed.port
    if port and port not in (80, 443, 8080, 8443):
        return False, f"Prohibited port: {port}. Only standard web ports (80, 443, 8080, 8443) are allowed.", None

    # Resolve hostname to IP to prevent DNS rebinding / SSRF
    try:
        addr_info = socket.getaddrinfo(hostname_clean, port or (443 if parsed.scheme == "https" else 80), socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return False, f"Failed to resolve hostname: {hostname_clean}", None

        resolved_ip_str = None
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            if is_ip_blocked(ip_obj):
                return False, f"Resolved IP {ip_str} belongs to a private, loopback, or reserved address block.", None
            
            if not resolved_ip_str:
                resolved_ip_str = ip_str

        return True, parsed.geturl(), resolved_ip_str

    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname {hostname_clean}: {e}", None
    except Exception as e:
        return False, f"URL security validation error: {e}", None
