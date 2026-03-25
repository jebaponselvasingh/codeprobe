"""
API key authentication middleware for CodeProbe.

Configuration:
  Set the CODEPROBE_API_KEY environment variable to enable auth.
  If the variable is empty or unset, auth is disabled (dev mode).

Clients must send:  X-API-Key: <key>

Exempt paths (no key required regardless of config):
  GET  /health
  GET  /docs
  GET  /openapi.json
  GET  /redoc
"""
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = os.getenv("CODEPROBE_API_KEY", "").strip()

        # Auth disabled in dev mode
        if not api_key:
            return await call_next(request)

        # Exempt paths bypass auth
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "").strip()
        if provided != api_key:
            return JSONResponse(
                {"detail": "Invalid or missing API key"},
                status_code=401,
            )

        return await call_next(request)
