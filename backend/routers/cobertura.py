from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from .. import pipeline
from ..models import ComparativaResult, JobStatus

router = APIRouter()


@router.get("/comparativa", response_model=ComparativaResult)
def get_comparativa(alcaldia: str = Query(...)):
    if pipeline.comparativa_exists(alcaldia):
        return pipeline.load_comparativa(alcaldia)
    raise HTTPException(
        status_code=404,
        detail=f"Sin datos para {alcaldia}. Usa POST /cobertura/procesar.",
    )


@router.get("/perdida")
def get_puntos_perdida(alcaldia: str = Query(...)):
    """
    Devuelve los puntos donde hubo pérdida de bosque 2016->2024.
    Cada punto tiene lon, lat, clase_base, clase_actual, NDVI_base, NDVI_actual.
    """
    puntos = pipeline.load_puntos_perdida(alcaldia)
    return JSONResponse(content={
        "alcaldia": alcaldia,
        "puntos": puntos,
        "total": len(puntos)
    })


@router.post("/procesar", response_model=JobStatus, status_code=202)
def procesar(
    alcaldia: str = Query(...),
    background_tasks: BackgroundTasks = None,
):
    job_id = pipeline.create_job()
    background_tasks.add_task(pipeline.run_pipeline, job_id, alcaldia)
    return pipeline.get_job(job_id)