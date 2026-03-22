# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoiceScribe AI is a microservices-based audio transcription platform. It processes uploaded audio files through a pipeline: ingestion → preprocessing → transcription (Faster-Whisper) → optional diarization (Pyannote) → export. The full stack runs via Docker Compose orchestrated from `voicescribe-infra/`.

## First-Time Setup

```bash
cd voicescribe-infra
cp .env.example .env        # Fill in passwords and tokens
make certs-dev              # Generate self-signed TLS certs (dev only)
make ramdisk-setup          # Configure tmpfs ramdisk on host (Linux only)
make up                     # Start full stack
make migrate                # Run DB migrations (first time and after schema changes)
make seed-e2e               # Seed test users (free@test.local / password)
```

## Running the Stack

### Full stack (recommended)

All commands run from `voicescribe-infra/`:

```bash
make up                     # Start all services + infrastructure
make down                   # Stop stack
make reset CONFIRM=yes      # Destroy stack + volumes (destructive)
make health                 # Healthcheck all services
make logs                   # Follow all service logs
make logs-<service>         # Follow specific service logs (e.g. logs-nginx)
make e2e                    # Run E2E tests (requires seed-e2e first)
```

In development, `docker-compose.override.yml` is auto-applied and exposes:
- Nginx on `http://localhost:8080` (HTTP, no TLS check needed)
- PostgreSQL on `localhost:15432`, Redis on `localhost:16379`
- Prometheus on `localhost:9090`, Grafana on `localhost:3000`

### Single service (local dev)

From any service directory (requires infrastructure already running via `make up`):

```bash
pip install -e .[dev]
python run.py                                              # Start HTTP server
pytest tests/                                             # Run all tests
pytest tests/path/to/test_file.py::test_name             # Run single test
```

### Code quality (Python 3.11+, line-length 100)

```bash
black . && isort . && mypy . && bandit -r app/
```

## Architecture

### Services

| Service | Dir | Port | Description |
|---------|-----|------|-------------|
| API Gateway | `voicescribe-api-gateway/` | 8000 | Public entry point, JWT/API-key auth, WebSocket status |
| File Ingestion | `voicescribe-file-ingestion/` | 8001 | Streaming upload, magic-byte validation, SHA-256 |
| Quota Manager | `voicescribe-quota-manager/` | 8002 | Per-tenant quota enforcement by tier |
| Audio Preprocessor | `voicescribe-audio-preprocessor/` | 8003 | FFmpeg → 16kHz mono WAV, EBU R128 loudnorm, ramdisk output |
| Job Orchestrator | `voicescribe-job-orchestrator/` | 8004 | State machine, coordinates callbacks from all downstream services |
| Transcription Engine | `voicescribe-transcription-engine/` | 8005 | Faster-Whisper STT, GPU-only (RTF < 1.0 target) |
| Diarization Engine | `voicescribe-diarization-engine/` | 8006 | Pyannote speaker ID, GPU-only, PRO/Enterprise only |
| Export Service | `voicescribe-export-service/` | 8007 | TXT/SRT (all tiers), JSON/DOCX (PRO+), optional Celery Beat cleanup |

### Infrastructure

- **PostgreSQL 16** (5432) — tenants, users, jobs, metadata
- **Redis 7** (6379) — Celery broker/result backend, response caching
- **Nginx 1.26** (80/443) — TLS termination, reverse proxy, external entry point
- **Prometheus + Grafana** — metrics and dashboards
- **Ramdisk** (`/mnt/ramdisk`, 32G) — ephemeral WAV staging for preprocessor

### Pipeline State Machine (SVC-05)

```
QUEUED → PREPROCESSING → TRANSCRIBING → [DIARIZING] → EXPORTING → DONE
```

Free Tier skips `DIARIZING`. Each stage transition is driven by callbacks from the responsible service back to SVC-05.

### Inter-Service Communication

- All services communicate over the `voicescribe_internal` Docker network using container hostnames
- Internal calls require the `X-Internal-Token` header matching `INTERNAL_SERVICE_TOKEN`
- Redis pub/sub broadcasts real-time job status; API Gateway exposes this via WebSocket

### Tier System

- **Free Tier**: email/password → JWT, duration-limited audio, no diarization, TXT/SRT export only
- **PRO/Enterprise**: API key auth, unlimited duration, full diarization, JSON/DOCX export

### Service Code Layout

Every service follows the same structure:

```
app/
  core/          # config, security, logging, DB session, middleware
  api/
    routers/     # FastAPI route handlers
    dependencies.py
  models/        # Pydantic v2 schemas
  services/      # business logic
  main.py        # app factory
config/          # YAML parameters (FFmpeg profiles, etc.)
tests/
pyproject.toml
Dockerfile
openapi.yaml
run.py
.env.example
```

## Key Environment Variables

Copy `voicescribe-infra/.env.example` to `.env`. Critical variables:

- `INTERNAL_SERVICE_TOKEN` — required on all inter-service HTTP calls
- `JWT_SECRET_KEY` — Free Tier token signing
- `HUGGINGFACE_TOKEN` — required for Pyannote (SVC-07); model EULA must be accepted on HuggingFace
- `RAMDISK_PATH` / `RAMDISK_SIZE` — tmpfs mount for preprocessed WAVs

## Commit & Branch Conventions

```
feat(scope): short summary
fix(scope): short summary
chore(scope): short summary
```

Branches: `feat/<scope>-<description>`, `fix/<scope>-<description>`, `chore/<scope>-<description>`

Gitleaks runs on commit (`.gitleaks.toml`) and detects API keys (`vs_live_*`), HuggingFace tokens, JWT secrets, and DB credentials.
