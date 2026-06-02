from pydantic import BaseModel
from typing import Literal, Optional


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    message: str = ""
    result_url: Optional[str] = None


class CoberturaResult(BaseModel):
    alcaldia: str
    anio: int
    ha_bosque: float
    ha_deforestado: float
    ha_urbano: float
    ha_pastizal: float
    ha_agua: float
    ha_suelo_desnudo: float
    total_ha: float
    png_url: Optional[str] = None


class ComparativaResult(BaseModel):
    alcaldia: str
    base: CoberturaResult       # 2016
    actual: CoberturaResult     # 2024
    delta_ha: float             # negativo = pérdida
    delta_pct: float
    png_comparativa_url: Optional[str] = None
