from fastapi import APIRouter, HTTPException
from ..models import JobStatus
from .. import pipeline

router = APIRouter()


@router.get("/{job_id}/status", response_model=JobStatus)
def job_status(job_id: str):
    """Polling del estado de un job del pipeline."""
    job = pipeline.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado.")
    return job
