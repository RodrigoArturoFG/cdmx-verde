"""
Rol 3 - Script 02: Muestras etiquetadas desde Google Earth Engine.

Usa Dynamic World para AMBOS años (2016 y 2024) para garantizar
comparabilidad real. WorldCover es estatico y no sirve para comparar.

Uso:
    python scripts/02_muestras_gee.py --anio 2016 --alcaldia "Tlalpan"
    python scripts/02_muestras_gee.py --anio 2024 --alcaldia "Tlalpan"

Salida:
    data/training/muestras_{slug}_{anio}.csv
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path

import ee
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")
if not GEE_PROJECT:
    sys.exit("ERROR: la variable GEE_PROJECT no esta definida. "
             "Crea un archivo .env en la raiz del proyecto (copia .env.example "
             "y pon el ID de tu proyecto de Google Earth Engine).")
ALC_GEOJSON = ROOT / "data" / "alcaldias" / "alcaldias_cdmx.geojson"
OUT_DIR = ROOT / "data" / "training"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MUESTRAS_POR_CLASE = 800

# Dynamic World labels:
# 0=agua, 1=arboles, 2=pasto, 3=veg_inundada, 4=cultivos,
# 5=arbusto, 6=construido, 7=desnudo, 8=nieve
# Remapeamos a: 1=bosque, 2=pastizal, 3=urbano, 4=suelo_desnudo, 5=agua
DW_KEYS   = [0, 1, 2, 3, 4, 5, 6, 7]
DW_VALUES = [5, 1, 2, 2, 2, 2, 3, 4]
NOMBRES   = ["__none__", "bosque", "pastizal", "urbano", "suelo_desnudo", "agua"]


def slug(nombre: str) -> str:
    return (nombre.lower()
            .replace(" ", "_")
            .replace("\u00e1", "a").replace("\u00e9", "e")
            .replace("\u00ed", "i").replace("\u00f3", "o")
            .replace("\u00fa", "u").replace("\u00fc", "u")
            .replace("\u00f1", "n").replace(".", ""))


def normalizar(texto: str) -> str:
    return slug(texto).replace("_", " ")


def inicializar_ee() -> None:
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        print("Autenticando con Earth Engine...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)


def cargar_aoi_alcaldia(nombre_alcaldia: str):
    """Carga el poligono de la alcaldia con tolerancia a acentos."""
    if not ALC_GEOJSON.exists():
        sys.exit(f"ERROR: no existe {ALC_GEOJSON}.")
    with open(ALC_GEOJSON, "r", encoding="utf-8") as f:
        gj = json.load(f)
    norm_input = normalizar(nombre_alcaldia)
    for feat in gj["features"]:
        nombre_real = feat["properties"]["alcaldia"]
        if normalizar(nombre_real) == norm_input:
            print(f"   Alcaldia encontrada: {nombre_real}")
            return ee.Feature(feat).geometry(), nombre_real
    nombres = [f["properties"]["alcaldia"] for f in gj["features"]]
    sys.exit(f"ERROR: alcaldia '{nombre_alcaldia}' no encontrada.\nDisponibles: {nombres}")


def mascara_nubes(img):
    scl = img.select("SCL")
    mala = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))
    return img.updateMask(mala.Not())


def imagen_sentinel2(aoi, anio: int):
    fecha_ini = f"{anio}-01-01"
    fecha_fin = f"{anio}-05-31"
    if anio >= 2017:
        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi)
               .filterDate(fecha_ini, fecha_fin)
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25))
               .map(mascara_nubes))
    else:
        col = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
               .filterBounds(aoi)
               .filterDate(fecha_ini, fecha_fin)
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25)))
    mediana = col.median().select(
        ["B2", "B3", "B4", "B8", "B11", "B12"],
        ["B02", "B03", "B04", "B08", "B11", "B12"]
    )
    ndvi = mediana.normalizedDifference(["B08", "B04"]).rename("NDVI")
    ndwi = mediana.normalizedDifference(["B03", "B08"]).rename("NDWI")
    return mediana.addBands([ndvi, ndwi])


def imagen_etiquetas(aoi, anio: int):
    """
    Dynamic World para AMBOS anos -- misma fuente = comparacion real.
    DW tiene datos desde jun-2015, cubre 2016 y 2024 perfectamente.
    """
    fecha_ini = f"{anio}-01-01"
    fecha_fin = f"{anio}-05-31"
    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
          .filterBounds(aoi)
          .filterDate(fecha_ini, fecha_fin))
    moda = dw.select("label").mode()
    return moda.remap(DW_KEYS, DW_VALUES, defaultValue=0).rename("clase_id")


def muestrear(aoi, anio: int):
    s2        = imagen_sentinel2(aoi, anio)
    etiquetas = imagen_etiquetas(aoi, anio)
    stack     = s2.addBands(etiquetas)

    muestras = stack.stratifiedSample(
        numPoints=MUESTRAS_POR_CLASE,
        classBand="clase_id",
        region=aoi,
        scale=10,
        seed=42,
        classValues=[1, 2, 3, 4, 5],
        classPoints=[MUESTRAS_POR_CLASE] * 5,
        geometries=True,
        dropNulls=True,
    )

    def add_coords(f):
        coord = f.geometry().coordinates()
        return f.set({"lon": coord.get(0), "lat": coord.get(1)})

    return muestras.map(add_coords)


def exportar_local(fc, out_csv: Path, anio: int) -> int:
    selectores = ["lon", "lat", "clase_id",
                  "B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDWI"]

    print("Solicitando URL de descarga del CSV...")
    url = fc.getDownloadURL(filetype="CSV", selectors=selectores)
    print("Descargando desde GEE...")
    tmp = out_csv.with_suffix(".raw.csv")
    urllib.request.urlretrieve(url, tmp)

    columnas = ["lon", "lat", "anio", "clase", "fuente",
                "B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDWI"]
    n = 0

    with open(tmp, "r", encoding="utf-8", newline="") as fin, \
         open(out_csv, "w", encoding="utf-8", newline="") as fout:
        r = csv.DictReader(fin)
        w = csv.writer(fout)
        w.writerow(columnas)
        for row in r:
            try:
                cid = int(float(row.get("clase_id", "0") or 0))
            except ValueError:
                cid = 0
            clase = NOMBRES[cid] if 0 <= cid < len(NOMBRES) else "__none__"
            if clase == "__none__":
                continue
            w.writerow([
                row.get("lon", ""), row.get("lat", ""), anio, clase,
                "dynamic_world",
                row.get("B02", ""), row.get("B03", ""), row.get("B04", ""),
                row.get("B08", ""), row.get("B11", ""), row.get("B12", ""),
                row.get("NDVI", ""), row.get("NDWI", ""),
            ])
            n += 1

    tmp.unlink(missing_ok=True)
    print(f"OK: {n:,} muestras -> {out_csv.name}")
    return n


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--anio",     type=int, default=int(os.environ.get("ANIO", 2024)))
    parser.add_argument("--alcaldia", type=str, default=os.environ.get("ALCALDIA", ""))
    args = parser.parse_args()

    if not args.alcaldia:
        sys.exit("ERROR: especifica --alcaldia NombreAlcaldia")

    inicializar_ee()
    aoi, nombre_real = cargar_aoi_alcaldia(args.alcaldia)
    out_csv = OUT_DIR / f"muestras_{slug(nombre_real)}_{args.anio}.csv"

    print(f"Ano    : {args.anio}")
    print(f"Salida : {out_csv.name}")
    print(f"Fuente : Dynamic World (comparable entre anos)")

    muestras = muestrear(aoi, args.anio)
    print("Procesando en GEE (1-3 min)...")
    n = exportar_local(muestras, out_csv, args.anio)
    if n == 0:
        sys.exit("ERROR: sin muestras. Revisa AOI / fechas / proyecto GEE.")


if __name__ == "__main__":
    main()