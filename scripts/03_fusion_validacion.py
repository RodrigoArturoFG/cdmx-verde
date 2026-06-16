"""
Rol 3 - Script 03: Fusión y comparativa temporal 2016 vs 2024.

Cruza los dos CSVs por coordenada más cercana y detecta cambios de cobertura.

Uso:
    python scripts/03_fusion_validacion.py --alcaldia "Tlalpan" --anio-base 2016 --anio-actual 2024
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import ee
from dotenv import load_dotenv
from pathlib import Path
from shapely.geometry import Point
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
ALC  = ROOT / "data" / "alcaldias" / "alcaldias_cdmx.geojson"
OUT  = ROOT / "data" / "training"

load_dotenv(ROOT / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")

BANDAS = ["B02", "B03", "B04", "B08", "B11", "B12"]
CONSERVACION = {
    "Tlalpan", "Milpa Alta", "Xochimilco",
    "La Magdalena Contreras", "Magdalena Contreras",
    "Cuajimalpa de Morelos", "Cuajimalpa",
    "Álvaro Obregón", "Alvaro Obregon",
    "Tláhuac", "Tlahuac",
}

# Dynamic World labels -> clases del proyecto (mismo remapeo que el script 02):
# 0=agua,1=arboles,2=pasto,3=veg_inundada,4=cultivos,5=arbusto,6=construido,7=desnudo
# se remapea a: 1=bosque, 2=pastizal, 3=urbano, 4=suelo_desnudo, 5=agua
DW_KEYS   = [0, 1, 2, 3, 4, 5, 6, 7]
DW_VALUES = [5, 1, 2, 2, 2, 2, 3, 4]
# id de clase -> nombre usado en el JSON de métricas (6 = deforestado, derivado del cambio)
CLASE_POR_ID = {1: "bosque", 2: "pastizal", 3: "urbano", 4: "suelo_desnudo", 5: "agua", 6: "deforestado"}
CLASES = ["bosque", "pastizal", "urbano", "suelo_desnudo", "agua", "deforestado"]


def slug(nombre: str) -> str:
    return (nombre.lower()
            .replace(" ", "_")
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ü", "u")
            .replace("ñ", "n").replace(".", ""))


def normalizar(texto: str) -> str:
    return slug(texto).replace("_", " ")


def cargar_csv(alcaldia: str, anio: int) -> pd.DataFrame:
    # Busca el archivo con slug directo
    path = OUT / f"muestras_{slug(alcaldia)}_{anio}.csv"
    if not path.exists():
        # Busca cualquier archivo que matchee al normalizar
        patron = str(OUT / f"muestras_*_{anio}.csv")
        norm_input = normalizar(alcaldia)
        for c in glob.glob(patron):
            nombre_archivo = Path(c).stem
            nombre_archivo = nombre_archivo.replace(f"_{anio}", "").replace("muestras_", "")
            if normalizar(nombre_archivo.replace("_", " ")) == norm_input:
                path = Path(c)
                break
    if not path.exists():
        sys.exit(
            f"ERROR: no existe muestras para '{alcaldia}' año {anio}.\n"
            f"Ejecuta: python scripts/02_muestras_gee.py --alcaldia \"{alcaldia}\" --anio {anio}"
        )
    df = pd.read_csv(path)
    df["lon"] = df["lon"].astype(float)
    df["lat"] = df["lat"].astype(float)
    return df


def asignar_alcaldia(df: pd.DataFrame) -> pd.DataFrame:
    gdf = gpd.GeoDataFrame(
        df, geometry=[Point(x, y) for x, y in zip(df.lon, df.lat)], crs="EPSG:4326"
    )
    alc = gpd.read_file(ALC)[["alcaldia", "geometry"]]
    joined = gpd.sjoin(gdf, alc, how="left", predicate="within")
    df = df.copy()
    df["alcaldia"] = joined["alcaldia"].values
    return df


def cruzar_anios(base: pd.DataFrame, actual: pd.DataFrame, tolerancia_m: float = 50.0) -> pd.DataFrame:
    """Cruza puntos de dos años por coordenada más cercana con KDTree."""
    lat_rad = np.radians(19.35)
    m_per_deg_lon = 111320 * np.cos(lat_rad)
    m_per_deg_lat = 111320.0

    coords_base   = np.column_stack([base["lon"]   * m_per_deg_lon, base["lat"]   * m_per_deg_lat])
    coords_actual = np.column_stack([actual["lon"] * m_per_deg_lon, actual["lat"] * m_per_deg_lat])

    tree = cKDTree(coords_base)
    dist, idx = tree.query(coords_actual, k=1, workers=-1)
    mascara = dist <= tolerancia_m

    actual_f = actual[mascara].copy().reset_index(drop=True)
    base_f   = base.iloc[idx[mascara]].copy().reset_index(drop=True)

    comparativa = pd.DataFrame({
        "lon":          actual_f["lon"].values,
        "lat":          actual_f["lat"].values,
        "alcaldia":     actual_f["alcaldia"].values,
        "clase_base":   base_f["clase"].values,
        "clase_actual": actual_f["clase"].values,
        "NDVI_base":    base_f["NDVI"].values,
        "NDVI_actual":  actual_f["NDVI"].values,
        "B08_base":     base_f["B08"].values,
        "B08_actual":   actual_f["B08"].values,
    })

    comparativa["cambio"] = comparativa["clase_base"] != comparativa["clase_actual"]
    comparativa["perdida_bosque"] = (
        (comparativa["clase_base"] == "bosque") &
        (comparativa["clase_actual"] != "bosque")
    )
    comparativa["ganancia_bosque"] = (
        (comparativa["clase_base"] != "bosque") &
        (comparativa["clase_actual"] == "bosque")
    )
    return comparativa


def marcar_deforestado(df: pd.DataFrame, alcaldia: str) -> pd.DataFrame:
    """Reetiqueta como deforestado puntos en zonas de conservación donde se perdió bosque."""
    alc_norm = normalizar(alcaldia)
    en_conservacion = any(normalizar(c) == alc_norm for c in CONSERVACION)
    if en_conservacion:
        msk = (
            (df["clase_actual"].isin({"pastizal", "suelo_desnudo", "urbano"})) &
            (df["clase_base"] == "bosque")
        )
        df.loc[msk, "clase_actual"] = "deforestado"
    return df


def inicializar_ee() -> bool:
    """Inicializa Earth Engine. Devuelve False si no es posible (se usará el método legado)."""
    if not GEE_PROJECT:
        return False
    try:
        ee.Initialize(project=GEE_PROJECT)
        return True
    except Exception as exc:
        print(f"   AVISO: no se pudo inicializar GEE ({exc}); se usará el método legado.")
        return False


def cargar_aoi_y_area(nombre_alcaldia: str):
    """Devuelve (geometría EE, nombre_real, area_ha) leídos del GeoJSON oficial."""
    with open(ALC, "r", encoding="utf-8") as f:
        gj = json.load(f)
    norm = normalizar(nombre_alcaldia)
    for feat in gj["features"]:
        props = feat["properties"]
        if normalizar(str(props.get("alcaldia", ""))) == norm:
            area_ha = props.get("area_ha")
            area_ha = float(area_ha) if area_ha is not None else None
            return ee.Geometry(feat["geometry"]), props["alcaldia"], area_ha
    return None, None, None


def clasificacion_dw(aoi, anio: int):
    """Clasificación Dynamic World (moda ene-may) remapeada a las clases del proyecto."""
    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
          .filterBounds(aoi)
          .filterDate(f"{anio}-01-01", f"{anio}-05-31"))
    moda = dw.select("label").mode()
    return moda.remap(DW_KEYS, DW_VALUES, defaultValue=0).rename("clase_id")


def _histograma(img, aoi) -> dict[int, float]:
    """frequencyHistogram de clase_id sobre todo el polígono (wall-to-wall, scale=10m)."""
    d = img.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=aoi,
        scale=10,
        maxPixels=int(1e10),
    ).get("clase_id")
    crudo = ee.Dictionary(d).getInfo() or {}
    return {int(float(k)): float(v) for k, v in crudo.items()}


def _hist_a_ha(hist: dict[int, float], area_ha: float) -> dict:
    """Convierte conteos de píxeles por clase a hectáreas escalando por el área oficial.

    Se usan solo las clases válidas (1-6) como denominador; los píxeles sin dato
    (clase 0) se ignoran y el total se reparte sobre el `area_ha` oficial del polígono.
    """
    validos = {k: v for k, v in hist.items() if k in CLASE_POR_ID}
    total = sum(validos.values())
    out = {nombre: 0.0 for nombre in CLASES}
    if total > 0:
        for k, v in validos.items():
            out[CLASE_POR_ID[k]] = round((v / total) * area_ha, 2)
    return out


def areas_wall_to_wall(aoi, ab: int, aa: int, area_ha: float, es_conservacion: bool):
    """Calcula hectáreas por clase contando TODOS los píxeles del polígono (no muestras).

    Para alcaldías de conservación, los píxeles que eran bosque en el año base y
    pasaron a pastizal/urbano/suelo en el año actual se reetiquetan como 'deforestado'
    (clase 6) en el año actual, de modo que las clases siguen siendo mutuamente
    excluyentes y suman el área total.
    """
    base_img   = clasificacion_dw(aoi, ab)
    actual_img = clasificacion_dw(aoi, aa)

    if es_conservacion:
        defor = base_img.eq(1).And(actual_img.gte(2)).And(actual_img.lte(4))
        actual_img = actual_img.where(defor, 6)

    areas_base   = _hist_a_ha(_histograma(base_img, aoi),   area_ha)
    areas_actual = _hist_a_ha(_histograma(actual_img, aoi), area_ha)
    return areas_base, areas_actual


def calcular_metricas(comp: pd.DataFrame, alcaldia: str, ab: int, aa: int,
                      areas_base: dict | None = None, areas_actual: dict | None = None) -> dict:
    """Calcula métricas combinando dos fuentes:

    - Hectáreas por clase: conteo wall-to-wall en GEE escalado por el área oficial
      (`areas_base`/`areas_actual`). Si no se proveen (GEE no disponible), se cae al
      método legado donde cada muestra cruzada equivale a 0.01 ha (pixel 10×10 m).
    - Conteos de puntos de pérdida/ganancia: siempre del cruce de muestras 2016 vs 2024
      (son los marcadores que dibuja el mapa).
    """
    muestras_totales = len(comp)

    if areas_base is None or areas_actual is None:
        # Modo legado: cada muestra cruzada = 0.01 ha (pixel 10×10 m)
        ha_pixel = 0.01

        def ha_clase(col, clase):
            return round(int((comp[col] == clase).sum()) * ha_pixel, 2)

        areas_base   = {c: ha_clase("clase_base", c)   for c in CLASES}
        areas_actual = {c: ha_clase("clase_actual", c) for c in CLASES}
        metodo = "muestras_0.01ha"
    else:
        metodo = "wall_to_wall"

    hb  = areas_base["bosque"]
    ha_ = areas_actual["bosque"]
    delta_ha  = round(ha_ - hb, 2)
    delta_pct = round((delta_ha / hb * 100) if hb > 0 else 0.0, 2)

    return {
        "alcaldia":           alcaldia,
        "anio_base":          ab,
        "anio_actual":        aa,
        "total_puntos":       muestras_totales,
        "metodo_ha":          metodo,
        "ha_bosque_base":     hb,
        "ha_bosque_actual":   ha_,
        "delta_ha":           delta_ha,
        "delta_pct":          delta_pct,
        "puntos_perdida":     int(comp["perdida_bosque"].sum()),
        "puntos_ganancia":    int(comp["ganancia_bosque"].sum()),
        "ha_urbano_base":     areas_base["urbano"],
        "ha_urbano_actual":   areas_actual["urbano"],
        "ha_pastizal_base":   areas_base["pastizal"],
        "ha_pastizal_actual": areas_actual["pastizal"],
        "ha_agua_base":       areas_base["agua"],
        "ha_agua_actual":     areas_actual["agua"],
        "ha_suelo_base":      areas_base["suelo_desnudo"],
        "ha_suelo_actual":    areas_actual["suelo_desnudo"],
        "ha_deforestado":     areas_actual["deforestado"],
    }


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument("--alcaldia",    type=str, default=os.environ.get("ALCALDIA", ""))
    parser.add_argument("--anio-base",   type=int, default=int(os.environ.get("ANIO_BASE",   2016)))
    parser.add_argument("--anio-actual", type=int, default=int(os.environ.get("ANIO_ACTUAL", 2024)))
    args = parser.parse_args()

    if not args.alcaldia:
        sys.exit("ERROR: especifica --alcaldia NombreAlcaldia")

    alc = args.alcaldia
    ab  = args.anio_base
    aa  = args.anio_actual
    s   = slug(alc)

    print(f"[1/5] Cargando muestras '{alc}' {ab} y {aa}...")
    df_base   = cargar_csv(alc, ab)
    df_actual = cargar_csv(alc, aa)
    print(f"   Base {ab}: {len(df_base):,} pts  |  Actual {aa}: {len(df_actual):,} pts")

    print("[2/5] Asignando alcaldía por intersección espacial...")
    df_base   = asignar_alcaldia(df_base)
    df_actual = asignar_alcaldia(df_actual)

    print("[3/5] Cruzando años por coordenada más cercana...")
    comparativa = cruzar_anios(df_base, df_actual)
    print(f"   Puntos cruzados:    {len(comparativa):,}")
    print(f"   Pérdida de bosque:  {comparativa['perdida_bosque'].sum():,} puntos")
    print(f"   Ganancia de bosque: {comparativa['ganancia_bosque'].sum():,} puntos")

    print("[4/5] Marcando deforestado en zonas de conservación...")
    comparativa = marcar_deforestado(comparativa, alc)

    print("[5/5] Guardando resultados...")
    comparativa.to_csv(OUT / f"comparativa_{s}_{ab}vs{aa}.csv", index=False)

    perdida = comparativa[comparativa["perdida_bosque"]].copy()
    perdida.to_csv(OUT / f"perdida_{s}_{ab}vs{aa}.csv", index=False)

    df_actual["confianza"] = 1.0
    df_actual.to_csv(OUT / f"training_samples_{s}.csv", index=False)

    # Hectáreas por clase: conteo wall-to-wall en GEE escalado por el área oficial
    # (area_ha del GeoJSON). Si GEE no está disponible, se usa el método legado.
    areas_base = areas_actual = None
    es_conservacion = any(normalizar(c) == normalizar(alc) for c in CONSERVACION)
    if inicializar_ee():
        aoi, _nombre, area_ha = cargar_aoi_y_area(alc)
        if aoi is not None and area_ha:
            print(f"   Área oficial: {area_ha:,.1f} ha — contando píxeles wall-to-wall en GEE...")
            try:
                areas_base, areas_actual = areas_wall_to_wall(aoi, ab, aa, area_ha, es_conservacion)
            except Exception as exc:
                print(f"   AVISO: wall-to-wall falló ({exc}); se usará el método legado.")
                areas_base = areas_actual = None
        else:
            print("   AVISO: no se encontró geometría/area_ha de la alcaldía; método legado.")

    metricas = calcular_metricas(comparativa, alc, ab, aa, areas_base, areas_actual)
    (OUT / f"metricas_{s}_{ab}vs{aa}.json").write_text(
        json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    rep = [
        f"REPORTE COMPARATIVA {alc.upper()} — {ab} vs {aa}",
        "=" * 50,
        f"Puntos analizados  : {metricas['total_puntos']:,}",
        f"Bosque {ab}         : {metricas['ha_bosque_base']:,.1f} ha",
        f"Bosque {aa}         : {metricas['ha_bosque_actual']:,.1f} ha",
        f"Delta bosque       : {metricas['delta_ha']:+.1f} ha ({metricas['delta_pct']:+.1f}%)",
        f"Puntos pérdida     : {metricas['puntos_perdida']:,}",
        f"Puntos ganancia    : {metricas['puntos_ganancia']:,}",
        "",
        f"Urbano  {ab}->{aa}   : {metricas['ha_urbano_base']:,.1f} -> {metricas['ha_urbano_actual']:,.1f} ha",
        f"Pastizal {ab}->{aa}  : {metricas['ha_pastizal_base']:,.1f} -> {metricas['ha_pastizal_actual']:,.1f} ha",
        f"Deforestado        : {metricas['ha_deforestado']:,.1f} ha (zonas conservación)",
    ]
    (OUT / f"reporte_{s}.txt").write_text("\n".join(rep), encoding="utf-8")
    print("\n" + "\n".join(rep))
    print(f"\nArchivos en: {OUT}")


if __name__ == "__main__":
    main()