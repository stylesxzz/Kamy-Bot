"""Local-only access boundary and security headers for the single-user Kamy desktop app."""
import ipaddress
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class LocalOnlyMiddleware(BaseHTTPMiddleware):
    """Only accept requests originating from loopback interfaces."""
    async def dispatch(self, request, call_next):
        host = request.client.host if request.client else ""
        try:
            is_local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_local = False
        if not is_local:
            return JSONResponse({"detail": "Kamy Bot is local-only. Connect through localhost."}, status_code=403)
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'")
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
