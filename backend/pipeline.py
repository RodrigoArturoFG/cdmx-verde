"""
Orquestador del pipeline — llama 02 dos veces (2016 y 2024) y luego 03.
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

from .models import CoberturaResult, ComparativaResult, JobStatus

BASE    = Path(__file__).resolve().parents[1]
CACHE   = BASE / "cache"
SCRIPTS = BASE / "scripts"
DATA    = BASE / "data" / "training"
PYTHON  = sys.executable

load_dotenv(BASE / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")
if not GEE_PROJECT:
    sys.exit("ERROR: la variable GEE_PROJECT no esta definida. "
             "Crea un archivo .env en la raiz del proyecto (copia .env.example "
             "y pon el ID de tu proyecto de Google Earth Engine).")

_jobs: Dict[str, JobStatus] = {}

CACHE.mkdir(exist_ok=True)


# ── slug ──────────────────────────────────────────────────────────────────────

def _slug(nombre: str) -> str:
    return (nombre.lower().replace(" ", "_")
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u").replace("ü","u")
            .replace("ñ","n").replace(".",""))


# ── cache paths ───────────────────────────────────────────────────────────────

def _comparativa_json(alcaldia: str) -> Path:
    return CACHE / f"comparativa_{_slug(alcaldia)}.json"


def _perdida_csv(alcaldia: str) -> Path:
    return DATA / f"perdida_{_slug(alcaldia)}_2016vs2024.csv"


def _metricas_json(alcaldia: str) -> Path:
    return DATA / f"metricas_{_slug(alcaldia)}_2016vs2024.json"


# ── public API ────────────────────────────────────────────────────────────────

def comparativa_exists(alcaldia: str) -> bool:
    return _comparativa_json(alcaldia).exists()


def load_comparativa(alcaldia: str) -> ComparativaResult:
    return ComparativaResult(
        **json.loads(_comparativa_json(alcaldia).read_text(encoding="utf-8"))
    )


def load_puntos_perdida(alcaldia: str) -> list[dict]:
    path = _perdida_csv(alcaldia)
    if not path.exists():
        # busca con slug alternativo
        import glob
        patron = str(DATA / f"perdida_*_2016vs2024.csv")
        norm = _slug(alcaldia)
        for c in glob.glob(patron):
            if norm in Path(c).stem:
                path = Path(c)
                break
    if not path.exists():
        return []
    import csv
    puntos = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                puntos.append({
                    "lon":          float(row["lon"]),
                    "lat":          float(row["lat"]),
                    "clase_base":   row.get("clase_base", "bosque"),
                    "clase_actual": row.get("clase_actual", ""),
                    "NDVI_base":    float(row.get("NDVI_base", 0)),
                    "NDVI_actual":  float(row.get("NDVI_actual", 0)),
                })
            except (ValueError, KeyError):
                pass
    return puntos


def perdida_csv_path(alcaldia: str) -> Path | None:
    """Resuelve el CSV de pérdida, con fallback por substring del slug."""
    path = _perdida_csv(alcaldia)
    if path.exists():
        return path
    import glob
    norm = _slug(alcaldia)
    for c in glob.glob(str(DATA / "perdida_*_2016vs2024.csv")):
        if norm in Path(c).stem:
            return Path(c)
    return None


def create_job() -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = JobStatus(job_id=job_id, status="pending")
    return job_id


def get_job(job_id: str) -> JobStatus | None:
    return _jobs.get(job_id)


# ── subprocess runner ─────────────────────────────────────────────────────────

def _run(cmd: list[str], env: dict | None = None) -> None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env={**os.environ, **(env or {})},
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:] or result.stdout[-3000:])


# ── pipeline ──────────────────────────────────────────────────────────────────

async def run_pipeline(job_id: str, alcaldia: str) -> None:
    job  = _jobs[job_id]
    loop = asyncio.get_event_loop()
    env  = {"GEE_PROJECT": GEE_PROJECT}

    try:
        # Paso 1 — muestras 2016
        job.status  = "running"
        job.message = f"Descargando Sentinel-2 2016 para {alcaldia}..."
        await loop.run_in_executor(None, _run, [
            PYTHON, str(SCRIPTS / "02_muestras_gee.py"),
            "--alcaldia", alcaldia,
            "--anio", "2016",
        ], env)

        # Paso 2 — muestras 2024
        job.message = f"Descargando Sentinel-2 2024 para {alcaldia}..."
        await loop.run_in_executor(None, _run, [
            PYTHON, str(SCRIPTS / "02_muestras_gee.py"),
            "--alcaldia", alcaldia,
            "--anio", "2024",
        ], env)

        # Paso 3 — fusión y comparativa real
        job.message = "Cruzando años y detectando cambios de cobertura..."
        await loop.run_in_executor(None, _run, [
            PYTHON, str(SCRIPTS / "03_fusion_validacion.py"),
            "--alcaldia",    alcaldia,
            "--anio-base",   "2016",
            "--anio-actual", "2024",
        ], env)

        # Paso 4 — leer métricas y construir comparativa
        job.message = "Calculando métricas finales..."
        met_path = _metricas_json(alcaldia)

        # busca con slug alternativo si no encuentra exacto
        if not met_path.exists():
            import glob
            norm = _slug(alcaldia)
            for c in glob.glob(str(DATA / "metricas_*_2016vs2024.json")):
                if norm in Path(c).stem:
                    met_path = Path(c)
                    break

        if not met_path.exists():
            raise FileNotFoundError(
                f"No se generó el archivo de métricas para {alcaldia}. "
                f"Revisa la salida del script 03."
            )

        m = json.loads(met_path.read_text(encoding="utf-8"))

        base = CoberturaResult(
            alcaldia=alcaldia, anio=2016,
            ha_bosque=m["ha_bosque_base"],
            ha_deforestado=0.0,
            ha_urbano=m["ha_urbano_base"],
            ha_pastizal=m["ha_pastizal_base"],
            ha_agua=m["ha_agua_base"],
            ha_suelo_desnudo=m["ha_suelo_base"],
            total_ha=round(sum([
                m["ha_bosque_base"], m["ha_urbano_base"],
                m["ha_pastizal_base"], m["ha_agua_base"], m["ha_suelo_base"]
            ]), 2),
        )
        actual = CoberturaResult(
            alcaldia=alcaldia, anio=2024,
            ha_bosque=m["ha_bosque_actual"],
            ha_deforestado=m["ha_deforestado"],
            ha_urbano=m["ha_urbano_actual"],
            ha_pastizal=m["ha_pastizal_actual"],
            ha_agua=m["ha_agua_actual"],
            ha_suelo_desnudo=m["ha_suelo_actual"],
            total_ha=round(sum([
                m["ha_bosque_actual"], m["ha_deforestado"],
                m["ha_urbano_actual"], m["ha_pastizal_actual"],
                m["ha_agua_actual"], m["ha_suelo_actual"]
            ]), 2),
        )
        comparativa = ComparativaResult(
            alcaldia=alcaldia,
            base=base,
            actual=actual,
            delta_ha=m["delta_ha"],
            delta_pct=m["delta_pct"],
            puntos_perdida=m["puntos_perdida"],
            puntos_ganancia=m["puntos_ganancia"],
            png_comparativa_url=None,
        )
        _comparativa_json(alcaldia).write_text(
            comparativa.model_dump_json(indent=2), encoding="utf-8"
        )

        job.status     = "done"
        job.message    = "Listo"
        job.result_url = f"/cobertura/comparativa?alcaldia={alcaldia}"

    except Exception as exc:
        job.status  = "error"
        job.message = str(exc)[:3000]