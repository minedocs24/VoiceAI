"""API documentation landing page - links to all 8 services."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

api_docs_router = APIRouter()


@api_docs_router.get("/api-docs", response_class=HTMLResponse)
async def api_docs_landing():
    """Landing page with links to all service Swagger UIs."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>VoiceScribe API Documentation</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
        h1 { color: #333; }
        .service { margin: 1rem 0; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; }
        .service.public { border-left: 4px solid #0a0; }
        .service.internal { border-left: 4px solid #666; }
        a { color: #06c; }
        .badge { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; }
        .badge-public { background: #cfc; }
        .badge-internal { background: #eee; }
    </style>
</head>
<body>
    <h1>VoiceScribe API Documentation</h1>
    <p>Links to Swagger UI for all VoiceScribe services.</p>

    <div class="service public">
        <div><strong>SVC-01 API Gateway</strong> <span class="badge badge-public">PUBLIC</span></div>
        <p>Single entry point. Auth, orchestration, rate limiting.</p>
        <a href="/docs">Swagger UI</a> | <a href="/openapi.json">OpenAPI JSON</a>
    </div>

    <div class="service internal">
        <div><strong>SVC-02 File Ingestion</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Upload, probe, validation. Internal only.</p>
        <a href="http://voicescribe-file-ingestion:8001/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-03 Quota Manager</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Free tier quota check/consume/rollback.</p>
        <a href="http://voicescribe-quota-manager:8002/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-04 Audio Preprocessor</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Audio preprocessing pipeline.</p>
        <a href="http://voicescribe-audio-preprocessor:8003/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-05 Job Orchestrator</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Job orchestration and Celery coordination.</p>
        <a href="http://voicescribe-job-orchestrator:8004/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-06 Transcription Engine</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Whisper transcription.</p>
        <a href="http://voicescribe-transcription-engine:8005/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-07 Diarization Engine</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Speaker diarization.</p>
        <a href="http://voicescribe-diarization-engine:8006/docs">Swagger UI</a> (internal network)
    </div>

    <div class="service internal">
        <div><strong>SVC-08 Export Service</strong> <span class="badge badge-internal">INTERNAL</span></div>
        <p>Export to TXT, SRT, DOCX, etc.</p>
        <a href="http://voicescribe-export-service:8007/docs">Swagger UI</a> (internal network)
    </div>
</body>
</html>
"""
    return HTMLResponse(html)
