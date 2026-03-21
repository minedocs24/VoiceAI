"""Queue statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.database import count_jobs_by_status
from app.core.security import verify_internal_token
from app.models.schemas import QueueStatsResponse

router = APIRouter(tags=["queue"])


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    _: None = Depends(verify_internal_token),
) -> QueueStatsResponse:
    """Get job counts per status."""
    counts = await count_jobs_by_status()
    return QueueStatsResponse(
        queued=counts.get("QUEUED", 0),
        preprocessing=counts.get("PREPROCESSING", 0),
        transcribing=counts.get("TRANSCRIBING", 0),
        diarizing=counts.get("DIARIZING", 0),
        exporting=counts.get("EXPORTING", 0),
        done=counts.get("DONE", 0),
        failed=counts.get("FAILED", 0),
    )
