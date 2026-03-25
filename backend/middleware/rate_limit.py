"""
In-memory rate limiter for CodeProbe's POST /review endpoint.

Configuration (environment variables):
  REVIEW_RATE_LIMIT   — max requests per window per IP (default: 10)
  REVIEW_RATE_WINDOW  — window size in seconds (default: 60)

Note: This is a single-process in-memory counter. For multi-worker
deployments, replace with a Redis-backed solution (e.g. slowapi + Redis).
"""
import os
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_RATE_LIMIT = int(os.getenv("REVIEW_RATE_LIMIT", "10"))
_RATE_WINDOW = int(os.getenv("REVIEW_RATE_WINDOW", "60"))

# {ip: [timestamp, ...]}  — keeps only timestamps within the current window
_counters: dict[str, list[float]] = defaultdict(list)

# Only these method+path combinations are rate-limited
_LIMITED_ROUTES = {("POST", "/review")}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        route_key = (request.method, request.url.path)
        if route_key not in _LIMITED_ROUTES:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.monotonic()
        window_start = now - _RATE_WINDOW

        # Evict timestamps outside the window
        hits = _counters[client_ip]
        _counters[client_ip] = [t for t in hits if t > window_start]

        if len(_counters[client_ip]) >= _RATE_LIMIT:
            return JSONResponse(
                {
                    "detail": (
                        f"Rate limit exceeded: max {_RATE_LIMIT} reviews "
                        f"per {_RATE_WINDOW}s per IP."
                    )
                },
                status_code=429,
                headers={"Retry-After": str(_RATE_WINDOW)},
            )

        _counters[client_ip].append(now)
        return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Return the real client IP, honouring X-Forwarded-For if present."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
