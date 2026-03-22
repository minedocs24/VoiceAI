# Code Review Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 11 issues (4 critical, 7 important, 5 minor) identified in the initial code review, covering security vulnerabilities, data-loss bugs, async correctness, and code quality.

**Architecture:** Changes are spread across 6 services (api-gateway, job-orchestrator, audio-preprocessor, export-service, quota-manager, infra). Each task is self-contained and produces passing tests before committing. No new dependencies required — all fixes use libraries already declared in `pyproject.toml`.

**Tech Stack:** Python 3.11, FastAPI, asyncpg, redis>=5.0.0 (with `redis.asyncio`), PyJWT, pytest, Docker Compose.

---

## File Map

| File | Change |
|------|--------|
| `voicescribe-infra/docker-compose.yml:120` | Remove JWT fallback secret (C2) |
| `voicescribe-api-gateway/config/gateway.yml:32` | Remove `json` from Free Tier formats (C4/M2) |
| `voicescribe-quota-manager/requirements.txt` | Delete file (M5) |
| `voicescribe-api-gateway/app/core/config.py` | `swagger_ui_enabled=False`, startup validation (M6 + bonus) |
| `.gitignore` (root) | New file — standard Python gitignore (I1) |
| `voicescribe-job-orchestrator/app/core/database.py:128` | `json.dumps(history)` (I2) |
| `voicescribe-audio-preprocessor/app/tasks.py:158` | Remove `_rollback_quota` call (I3) |
| `voicescribe-audio-preprocessor/app/services/ffmpeg_pipeline.py:29` | Rename `SystemError` → `FFmpegTransientError` (M3) |
| `voicescribe-audio-preprocessor/app/tasks.py:17` | Update import of renamed exception (M3) |
| `voicescribe-job-orchestrator/app/api/jobs.py:40-47` | Remove dead `else` branch (I6) |
| `voicescribe-job-orchestrator/app/api/callbacks.py:30-33` | Add logging to `_do_rollback` (M4) |
| `voicescribe-job-orchestrator/app/services/http_client.py:61` | Add comment on CB per-process scope (I4) |
| `voicescribe-api-gateway/app/services/svc02_client.py` | Forward `X-Request-Id` (M1) |
| `voicescribe-api-gateway/app/services/svc03_client.py` | Forward `X-Request-Id` (M1) |
| `voicescribe-api-gateway/app/services/svc05_client.py` | Forward `X-Request-Id` (already done — verify) |
| `voicescribe-job-orchestrator/app/core/redis_client.py` | Switch to `redis.asyncio` (I5) |
| `voicescribe-job-orchestrator/app/api/callbacks.py` | `await publish_job_status(...)` (I5) |
| `voicescribe-api-gateway/app/api/routers/websocket.py` | JWT auth via `?token=` (C1) |
| `voicescribe-export-service/app/api/routers.py` | New `GET /download/{job_id}/{fmt}` endpoint (C3) |
| `voicescribe-api-gateway/app/core/config.py` | Add `svc08_url` field (C3) |
| `voicescribe-infra/docker-compose.yml` | Add `SVC08_URL` env to api-gateway service (C3) |
| `voicescribe-api-gateway/app/api/routers/jobs.py:229-234` | Proxy download to SVC-08 (C3) |
| `voicescribe-infra/tests/e2e/conftest.py` | Add `free_tier_quota_limit` fixture (I7) |
| `voicescribe-infra/tests/e2e/test_scenario1_free_tier.py` | Use fixture for quota limit (I7) |

---

## Task 1: C2 + C4 — Remove JWT fallback secret and fix Free Tier formats

**Files:**
- Modify: `voicescribe-infra/docker-compose.yml:120`
- Modify: `voicescribe-api-gateway/config/gateway.yml:32`

These are config-only changes with no runtime test needed — verified by inspection and docker-compose validation.

- [ ] **Step 1: Remove JWT fallback secret**

In `voicescribe-infra/docker-compose.yml` line 120, change:
```yaml
JWT_SECRET_KEY: ${JWT_SECRET_KEY:-dev-jwt-secret-change-in-production}
```
to:
```yaml
JWT_SECRET_KEY: ${JWT_SECRET_KEY}
```

- [ ] **Step 2: Fix Free Tier export formats**

In `voicescribe-api-gateway/config/gateway.yml` line 32, change:
```yaml
export_formats: ["txt", "srt", "json"]
```
to:
```yaml
export_formats: ["txt", "srt"]
```

This also fixes M2 (format conflict between gateway config and export service — both now say `["txt", "srt"]` for Free Tier).

- [ ] **Step 3: Validate docker-compose syntax**

```bash
cd voicescribe-infra && docker compose config --quiet
```
Expected: exits 0 (no output means valid).

- [ ] **Step 4: Commit**

```bash
git add voicescribe-infra/docker-compose.yml voicescribe-api-gateway/config/gateway.yml
git commit -m "fix(security): remove JWT fallback secret and align Free Tier export formats"
```

---

## Task 2: M5 + M6 — Remove duplicate requirements.txt and fix swagger default

**Files:**
- Delete: `voicescribe-quota-manager/requirements.txt`
- Modify: `voicescribe-api-gateway/app/core/config.py:63`

- [ ] **Step 1: Delete requirements.txt from quota-manager**

```bash
rm voicescribe-quota-manager/requirements.txt
git rm voicescribe-quota-manager/requirements.txt
```

- [ ] **Step 2: Set swagger_ui_enabled to False by default**

In `voicescribe-api-gateway/app/core/config.py` line 63, change:
```python
swagger_ui_enabled: bool = Field(default=True)
```
to:
```python
swagger_ui_enabled: bool = Field(default=False)
```

- [ ] **Step 3: Add startup validation for critical secrets**

In `voicescribe-api-gateway/app/core/config.py`, add a `model_post_init` method to the `Settings` class after the `redis_url` property:

```python
def model_post_init(self, __context) -> None:
    if not self.jwt_secret_key:
        raise ValueError("JWT_SECRET_KEY must be set — refusing to start with empty JWT secret")
    if not self.internal_service_token:
        raise ValueError("INTERNAL_SERVICE_TOKEN must be set — refusing to start with empty internal token")
```

- [ ] **Step 4: Write test for startup validation**

Create `voicescribe-api-gateway/tests/test_config.py`.

IMPORTANT: pydantic-settings reads env vars at `__init__` time (not at class-definition time), so calling `Settings()` directly inside the test with monkeypatched env vars is correct. The module-level `settings = Settings()` has already run (with valid conftest vars), but that does not affect our test's new `Settings()` call.

```python
"""Tests for startup validation in Settings."""
import pytest


def test_settings_rejects_empty_jwt_secret(monkeypatch):
    """Settings must raise ValueError if JWT_SECRET_KEY is empty."""
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "some-token")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    # Import the class (not the module-level instance) — each call to Settings()
    # re-reads env vars, so monkeypatch takes effect here.
    from app.core.config import Settings
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings()


def test_settings_rejects_empty_internal_token(monkeypatch):
    """Settings must raise ValueError if INTERNAL_SERVICE_TOKEN is empty."""
    monkeypatch.setenv("JWT_SECRET_KEY", "valid-secret")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    from app.core.config import Settings
    with pytest.raises(ValueError, match="INTERNAL_SERVICE_TOKEN"):
        Settings()


def test_settings_ok_with_valid_secrets(monkeypatch):
    """Settings instantiates when both secrets are provided."""
    monkeypatch.setenv("JWT_SECRET_KEY", "valid-secret")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "valid-token")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    from app.core.config import Settings
    s = Settings()
    assert s.jwt_secret_key == "valid-secret"
    assert s.internal_service_token == "valid-token"
    assert s.swagger_ui_enabled is False
```

- [ ] **Step 5: Run tests**

```bash
cd voicescribe-api-gateway && pytest tests/test_config.py -v
```
Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add voicescribe-quota-manager/requirements.txt voicescribe-api-gateway/app/core/config.py voicescribe-api-gateway/tests/test_config.py
git commit -m "fix(config): swagger off by default, require non-empty JWT/token secrets at startup, remove duplicate requirements.txt"
```

---

## Task 3: I1 — Root .gitignore and clean up committed artifacts

**Files:**
- Create: `.gitignore` (root)

- [ ] **Step 1: Create root .gitignore**

Create `C:\Users\ivana\Desktop\Progetti\VoiceAI\.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
*.egg
.eggs/
dist/
build/
*.whl

# Environments
.env
.env.*
!.env.example
*.local

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# IDEs
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.override.yml.local
```

- [ ] **Step 2: Remove committed .pyc and __pycache__ from git index**

```bash
cd C:\Users\ivana\Desktop\Progetti\VoiceAI
git rm -r --cached "**/__pycache__" "**/*.pyc" "**/*.egg-info" 2>/dev/null || true
git ls-files --others --ignored --exclude-standard | grep -E "\.(pyc|pyo)$|__pycache__|\.egg-info" | head -20
```

- [ ] **Step 3: Verify nothing sensitive is tracked**

```bash
git diff --cached --stat | head -30
```
Expected: only deletions of `.pyc`, `__pycache__/`, `.egg-info/` entries.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(repo): add root .gitignore and remove committed Python artifacts"
```

---

## Task 4: I2 — Fix asyncpg JSON serialization in transition_job

**Files:**
- Modify: `voicescribe-job-orchestrator/app/core/database.py:128`
- Test: `voicescribe-job-orchestrator/tests/unit/test_state_machine.py`

Without this fix, every job silently stalls after its first state transition because asyncpg cannot serialize a Python `list` to `::jsonb` without explicit `json.dumps()`.

- [ ] **Step 1: Write the failing-scenario test**

Add to `voicescribe-job-orchestrator/tests/unit/test_state_machine.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_transition_job_serializes_history_as_json():
    """
    transition_job must call conn.execute with json.dumps(history), not the raw list.
    asyncpg cannot serialize a Python list to ::jsonb without explicit json.dumps().
    """
    job_id = uuid4()
    existing_history = [{"from": "QUEUED", "to": "PREPROCESSING", "at": "2026-01-01T00:00:00+00:00", "stage_duration_seconds": None}]

    mock_row = {"id": job_id, "status": "PREPROCESSING", "status_history": existing_history}
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=mock_row)
    mock_conn.execute = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=None), __aexit__=AsyncMock(return_value=False)))

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=False)))

    with patch("app.core.database.get_pool", return_value=mock_pool):
        from app.core.database import transition_job
        result = await transition_job(job_id, "PREPROCESSING", "TRANSCRIBING")

    assert result is True
    call_args = mock_conn.execute.call_args
    # conn.execute(query, *params) → call_args[0] = (query, job_id, to_status, history, ...)
    # index 0 = SQL string, 1 = job_id ($1), 2 = to_status ($2), 3 = history ($3)
    params = call_args[0]  # positional args to execute(query, *params)
    history_param = params[3]  # index 3 = $3 in the query (0=query, 1=$1, 2=$2, 3=$3)
    assert isinstance(history_param, str), f"Expected str (JSON), got {type(history_param)}: {history_param!r}"
    parsed = json.loads(history_param)
    assert len(parsed) == 2  # existing entry + new entry appended
    assert parsed[-1]["from"] == "PREPROCESSING"
    assert parsed[-1]["to"] == "TRANSCRIBING"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd voicescribe-job-orchestrator && pytest tests/unit/test_state_machine.py::test_transition_job_serializes_history_as_json -v
```
Expected: FAIL — `AssertionError: Expected str (JSON), got <class 'list'>`.

- [ ] **Step 3: Fix the bug**

In `voicescribe-job-orchestrator/app/core/database.py`, add `import json` after the existing imports (line ~9), then change line 128 from:

```python
params: list[Any] = [job_id, to_status, history]
```
to:
```python
params: list[Any] = [job_id, to_status, json.dumps(history)]
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd voicescribe-job-orchestrator && pytest tests/unit/test_state_machine.py -v
```
Expected: all tests pass including the new one.

- [ ] **Step 5: Commit**

```bash
git add voicescribe-job-orchestrator/app/core/database.py voicescribe-job-orchestrator/tests/unit/test_state_machine.py
git commit -m "fix(orchestrator): serialize status_history as JSON string for asyncpg ::jsonb cast"
```

---

## Task 5: I3 — Remove incorrect quota rollback from preprocessor secondary check

**Files:**
- Modify: `voicescribe-audio-preprocessor/app/tasks.py:154-166`
- Test: `voicescribe-audio-preprocessor/tests/unit/test_api.py`

The secondary quota check in the Celery task incorrectly calls `_rollback_quota` when the quota appears exhausted. This is wrong because the quota was already consumed at the gateway layer — rolling it back here grants the tenant a free extra job. The correct behavior: log a warning, reject the task, do NOT rollback.

- [ ] **Step 1: Write the failing test**

Add to `voicescribe-audio-preprocessor/tests/unit/test_api.py`:

```python
from unittest.mock import MagicMock, patch
import pytest


def test_secondary_quota_check_does_not_rollback():
    """
    When the secondary quota check fails, _rollback_quota must NOT be called.
    The quota was already consumed at the gateway — rolling back grants a free job.
    """
    with (
        patch("app.tasks._get_input_path", return_value="/tmp/audio.mp3"),
        patch("app.tasks._check_quota", return_value=False),
        patch("app.tasks._rollback_quota") as mock_rollback,
        patch("app.tasks._notify_svc05") as mock_notify,
        patch("app.tasks.QUOTA_CHECK_FAILURES_TOTAL") as mock_metric,
        patch("app.tasks.PREPROCESS_TASKS_TOTAL") as mock_tasks_metric,
    ):
        mock_metric.inc = MagicMock()
        mock_tasks_metric.labels = MagicMock(return_value=MagicMock(inc=MagicMock()))
        from celery.exceptions import Reject
        from app.tasks import preprocess_task
        # preprocess_task is bound with bind=True, so __wrapped__ is the raw function
        # that expects (self, job_id, tenant_id). Pass a mock self.
        mock_self = MagicMock()
        mock_self.request.retries = 0
        with pytest.raises(Reject):
            preprocess_task.__wrapped__(mock_self, "job-123", "tenant-456")
        mock_rollback.assert_not_called()
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs.get("success") is False
        assert call_kwargs.get("error_code") == "quota_exceeded"
```

- [ ] **Step 2: Run to confirm it fails (rollback is currently called)**

```bash
cd voicescribe-audio-preprocessor && pytest tests/unit/test_api.py::test_secondary_quota_check_does_not_rollback -v
```
Expected: FAIL — `AssertionError: Expected _rollback_quota not called, but it was`.

- [ ] **Step 3: Remove the _rollback_quota call**

In `voicescribe-audio-preprocessor/app/tasks.py`, change lines 154-166 from:

```python
    # Guardia quota secondaria
    if not _check_quota(tenant_id):
        QUOTA_CHECK_FAILURES_TOTAL.inc()
        PREPROCESS_TASKS_TOTAL.labels(status="quota_exceeded").inc()
        _rollback_quota(tenant_id)
        _notify_svc05(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="quota_exceeded",
            error_message="Quota check failed before processing",
        )
        raise Reject(reason="Quota exceeded", requeue=False)
```
to:
```python
    # Secondary quota guard — check only, do NOT rollback.
    # Quota was already consumed at the gateway layer; rolling back here
    # would grant the tenant a free extra job if Redis evicted the key.
    if not _check_quota(tenant_id):
        QUOTA_CHECK_FAILURES_TOTAL.inc()
        PREPROCESS_TASKS_TOTAL.labels(status="quota_exceeded").inc()
        logger.warning("secondary_quota_check_failed", job_id=job_id, tenant_id=tenant_id)
        _notify_svc05(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="quota_exceeded",
            error_message="Quota check failed before processing",
        )
        raise Reject(reason="Quota exceeded", requeue=False)
```

- [ ] **Step 4: Run tests**

```bash
cd voicescribe-audio-preprocessor && pytest tests/unit/ -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add voicescribe-audio-preprocessor/app/tasks.py voicescribe-audio-preprocessor/tests/unit/test_api.py
git commit -m "fix(preprocessor): secondary quota guard must not rollback already-consumed quota"
```

---

## Task 6: M3 — Rename SystemError to FFmpegTransientError

**Files:**
- Modify: `voicescribe-audio-preprocessor/app/services/ffmpeg_pipeline.py:29`
- Modify: `voicescribe-audio-preprocessor/app/tasks.py:17`
- Test: `voicescribe-audio-preprocessor/tests/unit/test_ffmpeg_pipeline.py`

The local `SystemError` class shadows Python's builtin, risking accidental exception swallowing by any C extension or `ctypes` call.

- [ ] **Step 1: Write test that uses the renamed exception**

Open `voicescribe-audio-preprocessor/tests/unit/test_ffmpeg_pipeline.py` and add:

```python
def test_ffmpeg_transient_error_is_distinct_from_builtin_system_error():
    """FFmpegTransientError must not shadow the builtin SystemError."""
    from app.services.ffmpeg_pipeline import FFmpegTransientError
    # The builtin must still be accessible and different
    assert FFmpegTransientError is not SystemError
    # It must be a subclass of PreprocessError, not of builtin SystemError
    from app.services.ffmpeg_pipeline import PreprocessError
    assert issubclass(FFmpegTransientError, PreprocessError)
    assert not issubclass(FFmpegTransientError, SystemError)
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd voicescribe-audio-preprocessor && pytest tests/unit/test_ffmpeg_pipeline.py::test_ffmpeg_transient_error_is_distinct_from_builtin_system_error -v
```
Expected: FAIL — `ImportError: cannot import name 'FFmpegTransientError'`.

- [ ] **Step 3: Rename the exception in ffmpeg_pipeline.py**

In `voicescribe-audio-preprocessor/app/services/ffmpeg_pipeline.py` line 29, change:
```python
class SystemError(PreprocessError):
    """System/temporary error - retry with backoff."""
    pass
```
to:
```python
class FFmpegTransientError(PreprocessError):
    """Transient system error (FFmpeg crash, resource exhaustion) — retry with backoff."""
    pass
```

- [ ] **Step 4: Update import in tasks.py**

In `voicescribe-audio-preprocessor/app/tasks.py` line 17, change:
```python
from app.services.ffmpeg_pipeline import InputError, SystemError, run_preprocess
```
to:
```python
from app.services.ffmpeg_pipeline import FFmpegTransientError, InputError, run_preprocess
```

Also update the usage in `tasks.py` — find `except SystemError as e:` (in the `preprocess_task` function) and change it to `except FFmpegTransientError as e:`.

- [ ] **Step 5: Run all preprocessor unit tests**

```bash
cd voicescribe-audio-preprocessor && pytest tests/unit/ -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add voicescribe-audio-preprocessor/app/services/ffmpeg_pipeline.py voicescribe-audio-preprocessor/app/tasks.py voicescribe-audio-preprocessor/tests/unit/test_ffmpeg_pipeline.py
git commit -m "fix(preprocessor): rename SystemError to FFmpegTransientError to avoid shadowing builtin"
```

---

## Task 7: I6 — Remove dead code from create_job_endpoint

**Files:**
- Modify: `voicescribe-job-orchestrator/app/api/jobs.py:40-47`
- Test: `voicescribe-job-orchestrator/tests/unit/test_api.py`

The `else` branch that creates a job when `body.job_id` is absent is dead code — the gateway always passes a `job_id`. Removing it prevents future callers from accidentally creating orphan jobs.

- [ ] **Step 1: Write test confirming the endpoint rejects missing job_id**

Add to `voicescribe-job-orchestrator/tests/unit/test_api.py`:

```python
def test_create_job_requires_job_id(client, auth_headers):
    """POST /jobs without job_id must return 422 — dead code path removed."""
    r = client.post("/jobs", json={"tenant_id": "t1", "tier": "FREE"}, headers=auth_headers)
    assert r.status_code == 422
```

- [ ] **Step 2: Run to confirm it currently passes or fails**

```bash
cd voicescribe-job-orchestrator && pytest tests/unit/test_api.py::test_create_job_requires_job_id -v
```

Note the current behavior. After the fix it must return 422.

- [ ] **Step 3: Remove dead else branch and make job_id required**

In `voicescribe-job-orchestrator/app/api/jobs.py`, update `create_job_endpoint`:

The `JobCreateRequest` schema likely has `job_id: str | None = None`. Change the schema or add an explicit check. In the endpoint, replace the `if body.job_id: ... else: ...` pattern with:

```python
if not body.job_id:
    raise HTTPException(status_code=422, detail="job_id is required — job must be pre-created by api-gateway")

job_id = UUID(body.job_id)
job = await get_job_for_update(job_id)
if not job:
    raise HTTPException(status_code=404, detail="Job not found")
if job["status"] != "QUEUED":
    raise HTTPException(
        status_code=422,
        detail=f"Job already in state {job['status']}, cannot dispatch",
    )
```

Then proceed with the existing `call_svc04_preprocess` + `transition_job` logic.

- [ ] **Step 4: Run all orchestrator unit tests**

```bash
cd voicescribe-job-orchestrator && pytest tests/unit/ -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add voicescribe-job-orchestrator/app/api/jobs.py voicescribe-job-orchestrator/tests/unit/test_api.py
git commit -m "fix(orchestrator): require job_id in create_job_endpoint, remove dead else branch"
```

---

## Task 8: M4 — Add logging to _do_rollback

**Files:**
- Modify: `voicescribe-job-orchestrator/app/api/callbacks.py:30-33`

Silent rollback failures lead to orphaned input files on the storage volume with no alerting.

- [ ] **Step 1: Update _do_rollback to log outcomes**

In `voicescribe-job-orchestrator/app/api/callbacks.py`, replace:

```python
def _do_rollback(job_id: str) -> None:
    """Best-effort rollback: SVC-02 delete files, SVC-08 cleanup."""
    call_svc02_delete_files(job_id)
    call_svc08_cleanup(job_id)
```
with:
```python
def _do_rollback(job_id: str) -> None:
    """Best-effort rollback: SVC-02 delete files, SVC-08 cleanup. Logs failures."""
    ok_svc02 = call_svc02_delete_files(job_id)
    if not ok_svc02:
        logger.error("rollback_svc02_failed", job_id=job_id, detail="file deletion failed — orphaned input files possible")
    else:
        logger.info("rollback_svc02_ok", job_id=job_id)

    ok_svc08 = call_svc08_cleanup(job_id)
    if not ok_svc08:
        logger.warning("rollback_svc08_failed", job_id=job_id, detail="export cleanup failed — orphaned output files possible")
    else:
        logger.info("rollback_svc08_ok", job_id=job_id)
```

- [ ] **Step 2: Run orchestrator tests**

```bash
cd voicescribe-job-orchestrator && pytest tests/ -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add voicescribe-job-orchestrator/app/api/callbacks.py
git commit -m "fix(orchestrator): log rollback outcomes to surface orphaned file failures"
```

---

## Task 9: I4 — Document circuit breaker per-process limitation

**Files:**
- Modify: `voicescribe-job-orchestrator/app/services/http_client.py:61`

The circuit breaker is in-process memory. In multi-worker deployments failures are spread across N independent counters, so the threshold is never reached collectively. For the orchestrator (single-container, typically 1 Uvicorn worker), this is not a problem in practice. The fix is to document this clearly so future engineers don't scale this service horizontally without addressing it.

- [ ] **Step 1: Add documentation comment**

In `voicescribe-job-orchestrator/app/services/http_client.py`, replace:

```python
_circuit_breakers: dict[str, CircuitBreaker] = {}
```
with:
```python
# Per-process in-memory circuit breaker state.
# IMPORTANT: This state is NOT shared across multiple Uvicorn worker processes
# or container replicas. If the orchestrator is scaled horizontally, each process
# tracks failures independently and the threshold may never be reached collectively.
# For horizontal scaling, replace this with a Redis-backed circuit breaker using
# INCR/EXPIRE to share failure counts across all workers.
# By design, this service runs as a single-worker container (see docker-compose.yml).
_circuit_breakers: dict[str, CircuitBreaker] = {}
```

- [ ] **Step 2: Commit**

```bash
git add voicescribe-job-orchestrator/app/services/http_client.py
git commit -m "docs(orchestrator): document circuit breaker per-process scope limitation"
```

---

## Task 10: M1 — Forward X-Request-Id in all svc clients

**Files:**
- Modify: `voicescribe-api-gateway/app/services/svc02_client.py`
- Modify: `voicescribe-api-gateway/app/services/svc03_client.py`
- Verify: `voicescribe-api-gateway/app/services/svc05_client.py` (already has it)

Without propagating `X-Request-Id`, distributed tracing across services is broken — each hop gets a new ID.

- [x] **Step 1: Read the existing svc02 and svc03 clients**

Read both files to see their current header handling before editing.

- [x] **Step 2: Add X-Request-Id to svc02_client.py**

Find the `upload_file` function. Ensure it accepts `request_id: str | None = None` and adds `"X-Request-Id": request_id` to headers when present. Apply the same pattern to any other functions in the file that accept `request_id`.

Typical pattern to add where headers are built:
```python
if request_id:
    headers["X-Request-Id"] = request_id
```

- [x] **Step 3: Add X-Request-Id to svc03_client.py**

Same as svc02 — find all functions that accept `request_id` and add the header.

- [x] **Step 4: Verify svc05_client.py already does it**

`svc05_client.py` already sets `headers["X-Request-Id"] = request_id` when `request_id` is truthy. Confirm and move on.

- [x] **Step 5: Run gateway tests**

```bash
cd voicescribe-api-gateway && pytest tests/ -v
```
Expected: all tests pass.

- [x] **Step 6: Commit**

```bash
git add voicescribe-api-gateway/app/services/svc02_client.py voicescribe-api-gateway/app/services/svc03_client.py
git commit -m "fix(gateway): propagate X-Request-Id to SVC-02 and SVC-03 for distributed tracing"
```

---

## Task 11: I5 — Switch orchestrator Redis client to async

**Files:**
- Modify: `voicescribe-job-orchestrator/app/core/redis_client.py`
- Modify: `voicescribe-job-orchestrator/app/api/callbacks.py` (await the publish call)

`publish_job_status` uses the synchronous `redis.Redis` client called from an async FastAPI route handler. This blocks the event loop during the publish, causing latency spikes under load.

- [ ] **Step 1: Write test confirming publish_job_status is awaitable**

Add to `voicescribe-job-orchestrator/tests/unit/test_api.py`:

```python
import asyncio
import inspect

def test_publish_job_status_is_coroutine():
    """publish_job_status must be an async function (coroutine) to avoid blocking the event loop."""
    from app.core.redis_client import publish_job_status
    assert asyncio.iscoroutinefunction(publish_job_status), \
        "publish_job_status must be async — sync Redis blocks the event loop in FastAPI routes"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd voicescribe-job-orchestrator && pytest tests/unit/test_api.py::test_publish_job_status_is_coroutine -v
```
Expected: FAIL — `AssertionError: publish_job_status must be async`.

- [ ] **Step 3: Rewrite redis_client.py with redis.asyncio**

Replace `voicescribe-job-orchestrator/app/core/redis_client.py` entirely:

```python
"""Async Redis client for pub/sub job status."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_client: Redis | None = None


async def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def publish_job_status(job_id: str, status: str, payload: dict[str, Any] | None = None) -> None:
    """Publish job status to Redis channel job:{job_id}:status."""
    try:
        r = await get_redis()
        msg = {"status": status, **(payload or {})}
        channel = f"job:{job_id}:status"
        await r.publish(channel, json.dumps(msg))
    except Exception as e:
        logger.warning("redis_publish_failed", job_id=job_id, error=str(e))
```

- [ ] **Step 4: Update callbacks.py to await publish_job_status**

In `voicescribe-job-orchestrator/app/api/callbacks.py`, the `export_complete` handler calls `publish_job_status(...)` at line 263. Add `await`:

```python
        if ok:
            await publish_job_status(
                str(job_id),
                "DONE",
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "download_urls": body.download_urls or {},
                },
            )
```

- [ ] **Step 5: Fix close_redis call in main.py**

In `voicescribe-job-orchestrator/app/main.py` line 40, `close_redis()` is called without `await` inside the `async def lifespan` function. Since `close_redis` is now async, fix it:

```python
# Before:
    close_redis()

# After:
    await close_redis()
```

The import on line 38 (`from app.core.redis_client import close_redis`) stays the same.

- [ ] **Step 6: Run all orchestrator tests**

```bash
cd voicescribe-job-orchestrator && pytest tests/ -v
```
Expected: all tests pass, including the new coroutine check.

- [ ] **Step 7: Commit**

```bash
git add voicescribe-job-orchestrator/app/core/redis_client.py \
        voicescribe-job-orchestrator/app/api/callbacks.py \
        voicescribe-job-orchestrator/app/main.py \
        voicescribe-job-orchestrator/tests/unit/test_api.py
git commit -m "fix(orchestrator): switch Redis client to redis.asyncio to avoid blocking event loop"
```

---

## Task 12: C1 — WebSocket JWT authentication

**Files:**
- Modify: `voicescribe-api-gateway/app/api/routers/websocket.py`
- Test: `voicescribe-api-gateway/tests/` (new test file)

Currently `_get_tenant_from_ws` reads `tenant_id` directly from the query string without verifying any token. Any caller who knows a `job_id` can subscribe to that job's status stream for any tenant. Fix: require a valid JWT `?token=<jwt>` and extract `tenant_id` from the verified payload.

- [ ] **Step 1: Write the failing security test**

Create `voicescribe-api-gateway/tests/test_websocket_auth.py`:

```python
"""Tests for WebSocket JWT authentication."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_HOST", "localhost")


def _ws_close_code(client: TestClient, url: str) -> int:
    """
    Connect to a WebSocket endpoint and return the close code.
    Starlette's TestClient raises WebSocketDisconnect when the server closes
    the connection — we catch it and return the code.
    """
    try:
        with client.websocket_connect(url) as ws:
            ws.receive_json()  # Server should close before sending anything
    except WebSocketDisconnect as exc:
        return exc.code
    return 1000  # Normal close — means auth was accepted (test failure)


def test_websocket_rejects_connection_without_token():
    """WS must reject connections that don't provide a ?token= JWT."""
    from app.main import app
    job_id = str(uuid4())
    fake_job = {"id": job_id, "tenant_id": str(uuid4()), "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"


def test_websocket_rejects_invalid_token():
    """WS must reject connections with a malformed JWT."""
    from app.main import app
    job_id = str(uuid4())
    fake_job = {"id": job_id, "tenant_id": str(uuid4()), "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}?token=not-a-valid-jwt")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"


def test_websocket_rejects_wrong_tenant_token():
    """WS must reject a valid JWT whose tenant_id doesn't match the job owner."""
    import jwt as pyjwt
    from app.main import app
    job_id = str(uuid4())
    real_tenant = str(uuid4())
    other_tenant = str(uuid4())

    token = pyjwt.encode(
        {"sub": other_tenant, "tenant_id": other_tenant, "tier": "FREE", "type": "access"},
        "test-secret-key-for-testing-only",
        algorithm="HS256",
    )
    fake_job = {"id": job_id, "tenant_id": real_tenant, "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}?token={token}")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"
```

- [ ] **Step 2: Run to confirm failures**

```bash
cd voicescribe-api-gateway && pytest tests/test_websocket_auth.py -v
```
Expected: tests fail because current code accepts tenant_id from query string, not a verified JWT.

- [ ] **Step 3: Rewrite websocket.py to verify JWT**

Replace `_get_tenant_from_ws` in `voicescribe-api-gateway/app/api/routers/websocket.py`:

```python
async def _get_tenant_from_ws(websocket: WebSocket) -> str | None:
    """
    Extract and verify tenant from JWT token in query string.
    Clients must pass ?token=<access_jwt>.
    Returns tenant_id on success, None on failure.
    """
    query = websocket.scope.get("query_string", b"").decode()
    params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
    token = params.get("token")
    if not token:
        return None
    try:
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
        return payload.get("tenant_id")
    except Exception:
        return None
```

- [ ] **Step 4: Run the tests**

```bash
cd voicescribe-api-gateway && pytest tests/test_websocket_auth.py tests/test_auth.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add voicescribe-api-gateway/app/api/routers/websocket.py voicescribe-api-gateway/tests/test_websocket_auth.py
git commit -m "fix(security): WebSocket auth via verified JWT token instead of unauthenticated tenant_id param"
```

---

## Task 13: C3 — SVC-08 download endpoint

**Files:**
- Modify: `voicescribe-export-service/app/api/routers.py`
- Modify: `voicescribe-export-service/app/core/config.py` (verify `output_base_path` is accessible)

SVC-08 writes files to `/data/output/{tenant_id}/{job_id}/`. Add a `GET /download/{job_id}/{fmt}` endpoint that:
1. Verifies the internal token (internal-only endpoint)
2. Resolves the file path from `output_base_path` + `job_id` (requires `tenant_id` in the request)
3. Streams the file back with the correct `Content-Type`

- [ ] **Step 1: Check what filenames SVC-08 writes**

Read `voicescribe-export-service/config/export.yml` to confirm the filename mapping (e.g., `txt → transcript.txt`, `srt → transcript.srt`).

- [ ] **Step 2: Write the test**

Create `voicescribe-export-service/tests/unit/test_download.py` (or add to existing test file):

```python
"""Tests for the download endpoint."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-token")
os.environ.setdefault("OUTPUT_BASE_PATH", "/tmp/voicescribe-test-output")


def test_download_returns_file_content(tmp_path):
    """GET /download/{job_id}/{fmt} must return file content when it exists."""
    from fastapi.testclient import TestClient
    from app.main import app

    job_id = "test-job-123"
    tenant_id = "tenant-abc"
    fmt = "txt"

    # Create the file in the expected location
    out_dir = tmp_path / tenant_id / job_id
    out_dir.mkdir(parents=True)
    (out_dir / "transcript.txt").write_text("Hello transcription")

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.output_base_path = str(tmp_path)
        mock_settings.internal_service_token = "test-token"
        client = TestClient(app)
        r = client.get(
            f"/download/{job_id}/{fmt}",
            params={"tenant_id": tenant_id},
            headers={"X-Internal-Token": "test-token"},
        )
    assert r.status_code == 200
    assert b"Hello transcription" in r.content


def test_download_returns_404_for_missing_file(tmp_path):
    """GET /download/{job_id}/{fmt} returns 404 when file does not exist."""
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.output_base_path = str(tmp_path)
        mock_settings.internal_service_token = "test-token"
        client = TestClient(app)
        r = client.get(
            "/download/nonexistent-job/txt",
            params={"tenant_id": "tenant-xyz"},
            headers={"X-Internal-Token": "test-token"},
        )
    assert r.status_code == 404


def test_download_requires_internal_token():
    """GET /download must reject requests without X-Internal-Token."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/download/some-job/txt", params={"tenant_id": "t1"})
    assert r.status_code == 401
```

- [ ] **Step 3: Run to confirm failure**

```bash
cd voicescribe-export-service && pytest tests/ -k "download" -v
```
Expected: FAIL — endpoint does not exist yet.

- [ ] **Step 4: Add download endpoint to SVC-08 routers.py**

In `voicescribe-export-service/app/api/routers.py`, add after the existing export endpoint:

```python
from pathlib import Path
from fastapi.responses import FileResponse

FORMAT_TO_FILENAME = {
    "txt": "transcript.txt",
    "srt": "transcript.srt",
    "json": "transcript.json",
    "docx": "transcript.docx",
}

FORMAT_CONTENT_TYPE = {
    "txt": "text/plain; charset=utf-8",
    "srt": "text/plain; charset=utf-8",
    "json": "application/json",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/download/{job_id}/{fmt}")
async def download_export(
    job_id: str,
    fmt: str,
    tenant_id: str,
    _: None = Depends(verify_internal_token),
) -> FileResponse:
    """
    Serve an exported file for a completed job.
    Called internally by the API Gateway — requires X-Internal-Token.
    """
    from app.core.config import settings
    fmt = fmt.lower()
    filename = FORMAT_TO_FILENAME.get(fmt)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")

    file_path = Path(settings.output_base_path) / tenant_id / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Export file not found for job {job_id} format {fmt}")

    return FileResponse(
        path=str(file_path),
        media_type=FORMAT_CONTENT_TYPE[fmt],
        filename=filename,
    )
```

- [ ] **Step 5: Run the tests**

```bash
cd voicescribe-export-service && pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add voicescribe-export-service/app/api/routers.py voicescribe-export-service/tests/
git commit -m "feat(export): add GET /download/{job_id}/{fmt} endpoint served by SVC-08"
```

---

## Task 14: C3 — Gateway download proxy to SVC-08

**Files:**
- Modify: `voicescribe-api-gateway/app/core/config.py` (add `svc08_url`)
- Modify: `voicescribe-infra/docker-compose.yml` (add `SVC08_URL` env var to gateway service)
- Modify: `voicescribe-api-gateway/app/api/routers/jobs.py:203-234`
- Test: `voicescribe-api-gateway/tests/test_integration.py`

- [ ] **Step 1: Add svc08_url to gateway Settings**

In `voicescribe-api-gateway/app/core/config.py`, add to the `Settings` class:

```python
svc08_url: str = Field(default="http://voicescribe-export-service:8007")
```

- [ ] **Step 2: Add SVC08_URL to docker-compose.yml**

In `voicescribe-infra/docker-compose.yml`, under the `voicescribe-api-gateway` service environment, add:
```yaml
SVC08_URL: http://voicescribe-export-service:8007
```

- [ ] **Step 3: Write the test**

Add to `voicescribe-api-gateway/tests/test_integration.py`:

```python
def test_download_proxies_to_svc08(client, mock_redis, mock_db):
    """GET /v1/jobs/{id}/download/{fmt} must proxy to SVC-08, not return 501."""
    import jwt as pyjwt
    from unittest.mock import AsyncMock, patch, MagicMock

    job_id = "test-job-download-123"
    tenant_id = "test-tenant-download"
    token = pyjwt.encode(
        {"sub": tenant_id, "tenant_id": tenant_id, "tier": "FREE", "type": "access"},
        "test-secret-key-for-testing-only",
        algorithm="HS256",
    )

    fake_job = {
        "id": job_id, "tenant_id": tenant_id, "status": "DONE",
        "tier_at_creation": "FREE", "created_at": __import__("datetime").datetime.now(),
        "completed_at": None, "error_message": None,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"hello transcription content"
    mock_response.headers = {"content-type": "text/plain"}

    with (
        patch("app.api.routers.jobs.get_job", new_callable=AsyncMock, return_value=fake_job),
        patch("app.api.routers.jobs.httpx.AsyncClient") as mock_client_class,
    ):
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        r = client.get(
            f"/v1/jobs/{job_id}/download/txt",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.content == b"hello transcription content"
```

- [ ] **Step 4: Run to confirm it fails (501 currently)**

```bash
cd voicescribe-api-gateway && pytest tests/test_integration.py::test_download_proxies_to_svc08 -v
```
Expected: FAIL with `AssertionError: assert 501 == 200`.

- [ ] **Step 5: Implement the proxy in jobs.py**

Replace the `download_job` endpoint body (lines 229-234) in `voicescribe-api-gateway/app/api/routers/jobs.py`:

```python
    # Proxy to SVC-08 Export Service
    svc08_url = f"{settings.svc08_url.rstrip('/')}/download/{job_id}/{fmt.lower()}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as svc08:
            resp = await svc08.get(
                svc08_url,
                params={"tenant_id": tenant.tenant_id},
                headers={
                    "X-Internal-Token": settings.internal_service_token,
                    "X-Request-Id": getattr(request.state, "request_id", ""),
                },
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Export file not ready or not found. Wait for job to reach DONE status.")
            if resp.status_code == 400:
                raise HTTPException(status_code=400, detail=resp.json().get("detail", "Bad request"))
            if resp.status_code != 200:
                logger.error("svc08_download_failed", status=resp.status_code, job_id=job_id)
                raise HTTPException(status_code=502, detail="Export service error")
            from fastapi.responses import Response as FastAPIResponse
            return FastAPIResponse(
                content=resp.content,
                media_type=resp.headers.get("content-type", "application/octet-stream"),
                headers={"Content-Disposition": f'attachment; filename="{job_id}.{fmt.lower()}"'},
            )
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error("svc08_unreachable", error=str(e), job_id=job_id)
        raise HTTPException(status_code=503, detail="Export service unavailable")
```

Also ensure `settings` (not just `get_gateway_config`) is available in the function since we're reading `settings.svc08_url` and `settings.internal_service_token`.

- [ ] **Step 6: Run all gateway tests**

```bash
cd voicescribe-api-gateway && pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add voicescribe-api-gateway/app/core/config.py voicescribe-api-gateway/app/api/routers/jobs.py voicescribe-infra/docker-compose.yml voicescribe-api-gateway/tests/test_integration.py
git commit -m "feat(gateway): implement download proxy to SVC-08, fix 501 stub (C3)"
```

---

## Task 15: I7 — E2E test reads quota limit from config

**Files:**
- Modify: `voicescribe-infra/tests/e2e/conftest.py`
- Modify: `voicescribe-infra/tests/e2e/test_scenario1_free_tier.py`

The test hard-codes that Free Tier allows exactly 2 jobs/day. If `free_tier_daily_limit` in `quota.yml` or the quota-manager settings changes, the test breaks silently or passes incorrectly.

- [ ] **Step 1: Add free_tier_quota_limit fixture to conftest.py**

In `voicescribe-infra/tests/e2e/conftest.py`, add:

```python
import yaml

@pytest.fixture(scope="session")
def free_tier_quota_limit() -> int:
    """
    Read free_tier_daily_limit from quota-manager settings or quota.yml.
    Falls back to 2 (the current default) so tests run without the full stack.
    """
    # Try to read from quota.yml relative to this file
    quota_yml = Path(__file__).resolve().parent.parent.parent.parent / "voicescribe-quota-manager" / "config" / "quota.yml"
    if quota_yml.exists():
        with open(quota_yml) as f:
            cfg = yaml.safe_load(f) or {}
        # quota.yml structure: quota: { daily_limit: 2, ... }
        limit = cfg.get("quota", {}).get("daily_limit")
        if limit is not None:
            return int(limit)
    # Fall back to env var (matches Settings.free_tier_daily_limit default)
    return int(os.environ.get("FREE_TIER_DAILY_LIMIT", "2"))
```

- [ ] **Step 2: Update test_scenario1_free_tier.py to use the fixture**

In `test_free_tier_full_flow`, add `free_tier_quota_limit: int` as a parameter. The test currently uploads 3 files and expects the 3rd to fail (hardcoded at limit=2). Make the limit dynamic:

Change the function signature to:
```python
async def test_free_tier_full_flow(
    base_url: str,
    verify_ssl: bool,
    test_audio_path: Path,
    free_tier_quota_limit: int,
):
```

Then replace the hardcoded upload logic (steps 6 and 7) to upload `free_tier_quota_limit - 1` additional files (all should succeed) and then one more that must return 429:

```python
        # Upload limit-1 more files (starting from job already done = 1 total used)
        for i in range(free_tier_quota_limit - 1):
            with open(test_audio_path, "rb") as f:
                upload_n = await client.post(
                    f"{base_url}/v1/transcribe",
                    headers=headers,
                    files={"file": (f"audio_extra_{i}.mp3", f, "audio/mpeg")},
                )
            assert upload_n.status_code == 202, f"Upload {i+2} failed: {upload_n.text}"
            job_id_n = upload_n.json()["job_id"]
            for _ in range(300):
                r = await client.get(f"{base_url}/v1/jobs/{job_id_n}", headers=headers)
                if r.status_code == 200 and r.json().get("status") == "DONE":
                    break
                await asyncio.sleep(2)

        # One more upload — must return 429 (quota exhausted)
        with open(test_audio_path, "rb") as f:
            upload_over = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("audio_over_limit.mp3", f, "audio/mpeg")},
            )
        assert upload_over.status_code == 429
        assert "Retry-After" in upload_over.headers or "retry-after" in str(upload_over.headers).lower()
```

- [ ] **Step 3: Commit**

```bash
git add voicescribe-infra/tests/e2e/conftest.py voicescribe-infra/tests/e2e/test_scenario1_free_tier.py
git commit -m "fix(e2e): read Free Tier quota limit from config instead of hardcoding 2"
```

---

## Task 16: Final verification

- [ ] **Step 1: Run all unit tests across all services**

```bash
cd voicescribe-api-gateway && pytest tests/ -v && echo "gateway OK"
cd ../voicescribe-job-orchestrator && pytest tests/ -v && echo "orchestrator OK"
cd ../voicescribe-audio-preprocessor && pytest tests/unit/ -v && echo "preprocessor OK"
cd ../voicescribe-export-service && pytest tests/ -v && echo "export OK"
```
Expected: all green.

- [ ] **Step 2: Verify no committed artifacts**

```bash
cd C:\Users\ivana\Desktop\Progetti\VoiceAI
git ls-files | grep -E "\.(pyc|pyo)$|__pycache__" | head -10
```
Expected: no output.

- [ ] **Step 3: Check docker-compose config is valid**

```bash
cd voicescribe-infra && docker compose config --quiet
```
Expected: exits 0.

- [ ] **Step 4: Verify no fallback secrets remain**

```bash
grep -r "dev-jwt-secret\|change-in-production\|changeme" voicescribe-infra/docker-compose.yml
```
Expected: no matches.

- [ ] **Step 5: Final commit if any loose ends**

```bash
git status
```
Commit any remaining unstaged changes with appropriate message.
