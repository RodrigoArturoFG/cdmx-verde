"""
Genera mosaicos Sentinel-2 por temporada con Google Earth Engine y devuelve
la URL de tiles XYZ para visualizarlos en el frontend.

A diferencia de los mosaicos anuales de EOX (que no permiten elegir estacion),
aqui construimos un composite con los MISMOS meses para cualquier anio, de modo
que 2016 y 2024 sean comparables en la misma temporada (lluvias = pasto verde).

Usamos la coleccion TOA COPERNICUS/S2_HARMONIZED porque cubre tanto 2016 como
2024 (la version Surface Reflectance no tiene datos de 2016). El enmascarado de
nubes usa COPERNICUS/S2_CLOUD_PROBABILITY (s2cloudless), que cubre ambos anios.
"""
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

router = APIRouter()

BASE = Path(__file__).resolve().parents[2]
load_dotenv(BASE / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")

# Temporada de lluvias en CDMX (pasto verde). Mismos meses para todos los anios.
MES_INICIO = 7   # julio
MES_FIN = 10     # octubre (inclusive)

# Bounding box que cubre las 16 alcaldias de CDMX.
CDMX_BBOX = [-99.37, 19.02, -98.93, 19.61]

# Umbral de probabilidad de nube (0-100). Pixeles por encima se descartan.
UMBRAL_NUBE = 40

_ee_listo = False
_cache_url: dict[int, str] = {}


def _init_ee():
    global _ee_listo
    if _ee_listo:
        return
    if not GEE_PROJECT:
        raise HTTPException(
            status_code=503,
            detail="GEE_PROJECT no esta definido en .env",
        )
    import ee
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Earth Engine no esta autenticado. Corre 'earthengine authenticate' "
                f"una vez en la terminal y reinicia el backend. ({e})"
            ),
        )
    _ee_listo = True


def _composite_temporada(anio: int):
    import ee

    aoi = ee.Geometry.Rectangle(CDMX_BBOX)
    inicio = ee.Date.fromYMD(anio, MES_INICIO, 1)
    fin = ee.Date.fromYMD(anio, MES_FIN, 1).advance(1, "month")

    s2 = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
          .filterBounds(aoi)
          .filterDate(inicio, fin))
    nubes = (ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")
             .filterBounds(aoi)
             .filterDate(inicio, fin))

    unidos = ee.Join.saveFirst("nube").apply(
        primary=s2,
        secondary=nubes,
        condition=ee.Filter.equals(leftField="system:index", rightField="system:index"),
    )

    def enmascarar(img):
        img = ee.Image(img)
        prob = ee.Image(img.get("nube")).select("probability")
        return img.updateMask(prob.lt(UMBRAL_NUBE))

    coleccion = ee.ImageCollection(unidos).map(enmascarar)
    return coleccion.median().clip(aoi)


@router.get("/mosaico")
def mosaico(anio: int = Query(..., ge=2015, le=2025)):
    """Devuelve la URL de tiles XYZ de un composite Sentinel-2 de temporada
    de lluvias (jul-oct) para el anio dado."""
    if anio in _cache_url:
        return {"anio": anio, "url": _cache_url[anio], "temporada": "jul-oct"}

    _init_ee()
    try:
        comp = _composite_temporada(anio)
        mapid = comp.getMapId({
            "bands": ["B4", "B3", "B2"],
            "min": 0,
            "max": 3000,
            "gamma": 1.2,
        })
        url = mapid["tile_fetcher"].url_format
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando mosaico GEE: {e}")

    _cache_url[anio] = url
    return {"anio": anio, "url": url, "temporada": "jul-oct"}
