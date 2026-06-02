"""
CDMX Verde — Backend principal
Levanta con: uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routers import alcaldias, cobertura, jobs

BASE = Path(__file__).resolve().parents[1]
CACHE = BASE / "cache"
CACHE.mkdir(exist_ok=True)

app = FastAPI(
    title="CDMX Verde API",
    description="Comparativa de cobertura vegetal 2016 vs 2024 por alcaldía",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alcaldias.router, prefix="/alcaldias", tags=["alcaldias"])
app.include_router(cobertura.router, prefix="/cobertura", tags=["cobertura"])
app.include_router(jobs.router, prefix="/job", tags=["jobs"])

app.mount("/cache", StaticFiles(directory=str(CACHE)), name="cache")


@app.get("/health")
def health():
    return {"status": "ok"}
