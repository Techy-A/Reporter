"""Shared hardening applied to every app (admin, portal, webhooks)."""
from __future__ import annotations

import ipaddress
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings
from ..security.redact import install_log_redaction

log = logging.getLogger("peoplepilot")

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

CSRF_HEADER = "x-pp-request"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if "server" in response.headers:
            del response.headers["server"]
        return response


class CSRFHeaderMiddleware(BaseHTTPMiddleware):
    """Writes must carry a custom header. Browsers can't add it cross-site without a CORS
    preflight, and CORS only allows the portal's own origin. Combined with SameSite=Strict
    cookies this blocks CSRF."""

    def __init__(self, app, exempt_prefixes: tuple[str, ...] = ()):
        super().__init__(app)
        self.exempt = exempt_prefixes

    async def dispatch(self, request: Request, call_next):
        if request.method in UNSAFE_METHODS and not request.url.path.startswith(self.exempt):
            if request.headers.get(CSRF_HEADER) != "1":
                return JSONResponse({"detail": "Missing request header"}, status_code=403)
        return await call_next(request)


class IPAllowListMiddleware(BaseHTTPMiddleware):
    """Admin portal is reachable only from configured networks (office / VPN).
    Behind a reverse proxy, run uvicorn with --proxy-headers and --forwarded-allow-ips
    set to the proxy address so request.client.host is the real client."""

    async def dispatch(self, request: Request, call_next):
        host = request.client.host if request.client else ""
        try:
            ip = ipaddress.ip_address(host)
            allowed = any(ip in net for net in get_settings().admin_networks)
        except ValueError:
            allowed = host == "testclient" and get_settings().env == "test"
        if not allowed:
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return await call_next(request)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In production the restricted DB roles can't create tables; `python -m peoplepilot.migrate`
    # runs first as the owner. In dev/test, create tables on startup for convenience.
    if get_settings().env != "prod":
        from ..db import init_db

        init_db()
    yield


def harden(app: FastAPI, *, origin: str | None, csrf_exempt: tuple[str, ...] = ()) -> FastAPI:
    install_log_redaction()

    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError):
        # Report which fields are wrong, but never echo submitted values back.
        fields = [".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()]
        return JSONResponse({"detail": "Invalid input", "fields": fields}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse({"detail": "Something went wrong"}, status_code=500)

    app.add_middleware(CSRFHeaderMiddleware, exempt_prefixes=csrf_exempt)
    if origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["content-type", CSRF_HEADER],
        )
    app.add_middleware(SecurityHeadersMiddleware)
    return app


def set_session_cookie(response, name: str, token: str, max_age: int) -> None:
    # __Host- prefix: Secure, Path=/, no Domain -> cookie can't leak to other subdomains,
    # so the admin and employee portals never see each other's cookies.
    response.set_cookie(name, token, max_age=max_age, path="/", secure=True, httponly=True, samesite="strict")


def clear_session_cookie(response, name: str) -> None:
    response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="strict")
