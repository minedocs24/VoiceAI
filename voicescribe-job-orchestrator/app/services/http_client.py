"""HTTP client with retry and circuit breaker."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple in-memory circuit breaker."""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def _can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.last_failure_time = time.time()
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("circuit_breaker_open", service=self.name, failures=self.failures)

    def call(self, fn: Callable[[], Any]) -> Any:
        """Execute fn with circuit breaker. Raises if circuit open."""
        if not self._can_attempt():
            raise httpx.HTTPError(f"Circuit breaker open for {self.name}")
        try:
            result = fn()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


# Per-process in-memory circuit breaker state.
# IMPORTANT: This state is NOT shared across multiple Uvicorn worker processes
# or container replicas. If the orchestrator is scaled horizontally, each process
# tracks failures independently and the threshold may never be reached collectively.
# For horizontal scaling, replace with a Redis-backed implementation using
# INCR/EXPIRE to share failure counts across all workers.
# By design, this service runs as a single-worker container (see docker-compose.yml).
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    global _circuit_breakers
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name,
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )
    return _circuit_breakers[service_name]


def _retry_request(
    method: str,
    url: str,
    *,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
    service_name: str = "unknown",
) -> httpx.Response:
    """Make HTTP request with tenacity retry."""
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    @retry(
        stop=stop_after_attempt(settings.http_retry_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    def _do():
        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                r = client.get(url, headers=headers)
            elif method.upper() == "POST":
                r = client.post(url, json=json, headers=headers)
            elif method.upper() == "DELETE":
                r = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method {method}")
            if r.status_code >= 500:
                r.raise_for_status()
            if r.status_code == 429:
                r.raise_for_status()
            return r

    cb = get_circuit_breaker(service_name)
    return cb.call(_do)


def call_svc04_preprocess(job_id: str, tenant_id: str, input_path: str | None = None) -> str:
    """Call SVC-04 POST /preprocess. Returns Celery task_id."""
    from app.core.config import settings

    url = f"{settings.svc04_url.rstrip('/')}/preprocess"
    r = _retry_request(
        "POST",
        url,
        json={"job_id": job_id, "tenant_id": tenant_id, "input_path": input_path},
        headers={"X-Internal-Token": settings.internal_service_token},
        timeout=60.0,
        service_name="svc04",
    )
    r.raise_for_status()
    data = r.json()
    return data["task_id"]


def call_svc02_delete_files(job_id: str) -> bool:
    """Call SVC-02 DELETE /files/{job_id}. Best-effort, returns True on success."""
    from app.core.config import settings

    try:
        url = f"{settings.svc02_url.rstrip('/')}/files/{job_id}"
        r = _retry_request(
            "DELETE",
            url,
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=30.0,
            service_name="svc02",
        )
        return r.status_code in (200, 204)
    except Exception as e:
        logger.warning("svc02_delete_failed", job_id=job_id, error=str(e))
        return False


def call_svc08_cleanup(job_id: str) -> bool:
    """Call SVC-08 cleanup endpoint if exists. Best-effort."""
    from app.core.config import settings

    try:
        url = f"{settings.svc08_url.rstrip('/')}/cleanup/{job_id}"
        r = _retry_request(
            "DELETE",
            url,
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=30.0,
            service_name="svc08",
        )
        return r.status_code in (200, 204, 404)
    except Exception:
        return False
