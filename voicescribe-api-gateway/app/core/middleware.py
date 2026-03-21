"""Rate limit middleware - applies to authenticated requests only."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit middleware. Skips paths in auth_excluded_paths.
    For authenticated paths, rate limiting is applied per-request in the dependency.
    This middleware does NOT do per-tenant rate limiting - that happens in the
    jobs router via dependency. This middleware can be used for IP-based limiting
    on auth endpoints (login) - but login already has auth_failure rate limit.
    For now this is a no-op placeholder; functional rate limit is in the jobs router.
    """

    def __init__(self, app, config: dict | None = None):
        super().__init__(app)
        self.config = config or {}

    async def dispatch(self, request: Request, call_next) -> Response:
        return await call_next(request)
