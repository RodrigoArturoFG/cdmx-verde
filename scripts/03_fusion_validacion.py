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
from pathlib import Path
from shapely.geometry import Point
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
ALC  = ROOT / "data" / "alcaldias" / "alcaldias_cdmx.geojson"
OUT  = ROOT / "data" / "training"

BANDAS = ["B02", "B03", "B04", "B08", "B11", "B12"]
CONSERVACION = {
    "Tlalpan", "Milpa Alta", "Xochimilco",
    "La Magdalena Contreras", "Magdalena Contreras",
    "Cuajimalpa de Morelos", "Cuajimalpa",
    "Álvaro Obregón", "Alvaro Obregon",
    "Tláhuac", "Tlahuac",
}


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


def calcular_metricas(comp: pd.DataFrame, alcaldia: str, ab: int, aa: int) -> dict:
    ha = 0.01  # pixel 10×10 m

    def ha_clase(col, clase):
        return round((comp[col] == clase).sum() * ha, 2)

    hb = ha_clase("clase_base",   "bosque")
    ha_ = ha_clase("clase_actual", "bosque")
    delta_ha  = round(ha_ - hb, 2)
    delta_pct = round((delta_ha / hb * 100) if hb > 0 else 0.0, 2)

    return {
        "alcaldia":           alcaldia,
        "anio_base":          ab,
        "anio_actual":        aa,
        "total_puntos":       len(comp),
        "ha_bosque_base":     hb,
        "ha_bosque_actual":   ha_,
        "delta_ha":           delta_ha,
        "delta_pct":          delta_pct,
        "puntos_perdida":     int(comp["perdida_bosque"].sum()),
        "puntos_ganancia":    int(comp["ganancia_bosque"].sum()),
        "ha_urbano_base":     ha_clase("clase_base",   "urbano"),
        "ha_urbano_actual":   ha_clase("clase_actual", "urbano"),
        "ha_pastizal_base":   ha_clase("clase_base",   "pastizal"),
        "ha_pastizal_actual": ha_clase("clase_actual", "pastizal"),
        "ha_agua_base":       ha_clase("clase_base",   "agua"),
        "ha_agua_actual":     ha_clase("clase_actual", "agua"),
        "ha_suelo_base":      ha_clase("clase_base",   "suelo_desnudo"),
        "ha_suelo_actual":    ha_clase("clase_actual", "suelo_desnudo"),
        "ha_deforestado":     ha_clase("clase_actual", "deforestado"),
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

    metricas = calcular_metricas(comparativa, alc, ab, aa)
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