"""
IMARA ONE Search - Security Headers Middleware
Applies modern defense-in-depth HTTP security headers to all responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Content Security Policy (strict default)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:* https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Anti-clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Privacy: strip referrer to origin only for cross-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser APIs / privacy permissions
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), screen-wake-lock=()"
        )

        # Cross-Origin Protections
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"

        # HTTP Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Server identification suppression
        if "server" in response.headers:
            del response.headers["server"]
        response.headers["X-Powered-By"] = "IMARA-ONE-Core"

        return response

