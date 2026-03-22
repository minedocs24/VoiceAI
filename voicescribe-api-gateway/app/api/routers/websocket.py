"""WebSocket endpoint for job status updates."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from structlog import get_logger

from app.core.database import get_job
from app.services.redis_client import get_redis

logger = get_logger(__name__)

ws_router = APIRouter()


async def _get_tenant_from_ws(websocket: WebSocket) -> str | None:
    """
    Extract and verify tenant from JWT token in query string.
    Clients must pass ?token=<access_jwt>.
    Returns tenant_id on success, None if token is missing or invalid.
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


@ws_router.websocket("/ws/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """WebSocket for real-time job status updates. Subscribes to Redis job:{job_id}:status."""
    await websocket.accept()
    request_id = str(uuid.uuid4())

    # Verify job exists and tenant owns it
    job = await get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    tenant_id = await _get_tenant_from_ws(websocket)
    if not tenant_id or job["tenant_id"] != tenant_id:
        await websocket.close(code=4003, reason="Unauthorized")
        return

    channel = f"job:{job_id}:status"
    pubsub = None
    heartbeat_task = None

    async def send_heartbeat():
        """Ping every 30s to detect zombie connections."""
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    try:
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        heartbeat_task = asyncio.create_task(send_heartbeat())

        # Send initial status
        await websocket.send_json({
            "type": "status",
            "job_id": job_id,
            "status": job["status"],
            "message": "Connected",
        })

        async for msg in pubsub.listen():
            if msg and msg.get("type") == "message":
                data = json.loads(msg["data"]) if isinstance(msg["data"], str) else msg["data"]
                await websocket.send_json(data)
                if data.get("status") in ("DONE", "FAILED"):
                    break
    except WebSocketDisconnect:
        logger.info("ws_disconnect", job_id=job_id, request_id=request_id)
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        logger.error("ws_error", job_id=job_id, error=str(e), request_id=request_id)
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        try:
            await websocket.close()
        except Exception:
            pass
