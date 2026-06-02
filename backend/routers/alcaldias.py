from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json

router = APIRouter()

BASE = Path(__file__).resolve().parents[2]
GEOJSON = BASE / "data" / "alcaldias" / "alcaldias_cdmx.geojson"


@router.get("/")
def get_alcaldias():
    """Devuelve el GeoJSON completo de las 16 alcaldías."""
    if not GEOJSON.exists():
        raise HTTPException(
            status_code=404,
            detail="GeoJSON no encontrado. Ejecuta primero 01_alcaldias_inegi.py",
        )
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return JSONResponse(content=data)


@router.get("/lista")
def lista_alcaldias():
    """Devuelve solo los nombres y áreas de las 16 alcaldías."""
    if not GEOJSON.exists():
        raise HTTPException(status_code=404, detail="GeoJSON no encontrado.")
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return [
        {
            "alcaldia": f["properties"]["alcaldia"],
            "area_ha": round(f["properties"].get("area_ha", 0), 1),
            "cve_mun": f["properties"].get("CVE_MUN", ""),
        }
        for f in gj["features"]
    ]
