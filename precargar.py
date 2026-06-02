"""
precargar.py — Pre-procesa todas las alcaldias de la CDMX.

Corre el pipeline completo (02 x2 + 03) para cada alcaldia
sin necesidad de hacer clic en el frontend.

Uso:
    python precargar.py               # todas las alcaldias
    python precargar.py --solo-cache  # solo regenera cache (si ya tienes los CSVs)

Salidas:
    data/training/muestras_{slug}_{anio}.csv  para cada alcaldia
    cache/comparativa_{slug}.json             para cada alcaldia
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT    = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
DATA    = ROOT / "data" / "training"
CACHE   = ROOT / "cache"
PYTHON  = sys.executable

load_dotenv(ROOT / ".env")
GEE = os.environ.get("GEE_PROJECT")
if not GEE:
    sys.exit("ERROR: la variable GEE_PROJECT no esta definida. "
             "Crea un archivo .env en la raiz del proyecto (copia .env.example "
             "y pon el ID de tu proyecto de Google Earth Engine).")

ALCALDIAS = [
    "Tlalpan",
    "Milpa Alta",
    "Xochimilco",
    "Iztapalapa",
    "Álvaro Obregón",
    "Gustavo A. Madero",
    "Tláhuac",
    "Cuajimalpa de Morelos",
    "La Magdalena Contreras",
    "Coyoacán",
    "Miguel Hidalgo",
    "Venustiano Carranza",
    "Azcapotzalco",
    "Cuauhtémoc",
    "Benito Juárez",
    "Iztacalco",
]


def slug(nombre: str) -> str:
    return (nombre.lower().replace(" ", "_")
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u").replace("ü","u")
            .replace("ñ","n").replace(".",""))


def csv_existe(alcaldia: str, anio: int) -> bool:
    return (DATA / f"muestras_{slug(alcaldia)}_{anio}.csv").exists()


def cache_existe(alcaldia: str) -> bool:
    return (CACHE / f"comparativa_{slug(alcaldia)}.json").exists()


def run(cmd: list, desc: str) -> bool:
    print(f"    {desc}...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "GEE_PROJECT": GEE},
    )
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr[-500] or result.stdout[-500]}")
        return False
    return True


def procesar_alcaldia(alcaldia: str, solo_cache: bool) -> bool:
    print(f"\n{'='*50}")
    print(f"  {alcaldia}")
    print(f"{'='*50}")

    if cache_existe(alcaldia) and not solo_cache:
        print("  Ya tiene cache. Saltando.")
        return True

    if not solo_cache:
        # Descarga 2016 si no existe
        if csv_existe(alcaldia, 2016):
            print("  CSV 2016 ya existe. Saltando descarga.")
        else:
            ok = run([
                PYTHON, str(SCRIPTS / "02_muestras_gee.py"),
                "--alcaldia", alcaldia, "--anio", "2016"
            ], "Descargando Sentinel-2 2016")
            if not ok:
                return False

        # Descarga 2024 si no existe
        if csv_existe(alcaldia, 2024):
            print("  CSV 2024 ya existe. Saltando descarga.")
        else:
            ok = run([
                PYTHON, str(SCRIPTS / "02_muestras_gee.py"),
                "--alcaldia", alcaldia, "--anio", "2024"
            ], "Descargando Sentinel-2 2024")
            if not ok:
                return False

    # Fusion y comparativa
    ok = run([
        PYTHON, str(SCRIPTS / "03_fusion_validacion.py"),
        "--alcaldia", alcaldia,
        "--anio-base", "2016",
        "--anio-actual", "2024",
    ], "Cruzando 2016 vs 2024")
    if not ok:
        return False

    # Genera cache JSON para el backend
    met_path = DATA / f"metricas_{slug(alcaldia)}_2016vs2024.json"
    if not met_path.exists():
        print("  ERROR: no se genero el archivo de metricas.")
        return False

    m = json.loads(met_path.read_text(encoding="utf-8"))

    cache_data = {
        "alcaldia": alcaldia,
        "base": {
            "alcaldia": alcaldia, "anio": 2016,
            "ha_bosque":       m["ha_bosque_base"],
            "ha_deforestado":  0.0,
            "ha_urbano":       m["ha_urbano_base"],
            "ha_pastizal":     m["ha_pastizal_base"],
            "ha_agua":         m["ha_agua_base"],
            "ha_suelo_desnudo":m["ha_suelo_base"],
            "total_ha": round(sum([
                m["ha_bosque_base"], m["ha_urbano_base"],
                m["ha_pastizal_base"], m["ha_agua_base"], m["ha_suelo_base"]
            ]), 2),
            "png_url": None,
        },
        "actual": {
            "alcaldia": alcaldia, "anio": 2024,
            "ha_bosque":       m["ha_bosque_actual"],
            "ha_deforestado":  m["ha_deforestado"],
            "ha_urbano":       m["ha_urbano_actual"],
            "ha_pastizal":     m["ha_pastizal_actual"],
            "ha_agua":         m["ha_agua_actual"],
            "ha_suelo_desnudo":m["ha_suelo_actual"],
            "total_ha": round(sum([
                m["ha_bosque_actual"], m["ha_deforestado"],
                m["ha_urbano_actual"], m["ha_pastizal_actual"],
                m["ha_agua_actual"], m["ha_suelo_actual"]
            ]), 2),
            "png_url": None,
        },
        "delta_ha":        m["delta_ha"],
        "delta_pct":       m["delta_pct"],
        "puntos_perdida":  m["puntos_perdida"],
        "puntos_ganancia": m["puntos_ganancia"],
        "png_comparativa_url": None,
    }

    CACHE.mkdir(exist_ok=True)
    out = CACHE / f"comparativa_{slug(alcaldia)}.json"
    out.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Cache generado: {out.name}")
    print(f"  Bosque 2016: {m['ha_bosque_base']:.1f} ha -> 2024: {m['ha_bosque_actual']:.1f} ha")
    print(f"  Delta: {m['delta_ha']:+.1f} ha ({m['delta_pct']:+.1f}%)")
    print(f"  Puntos perdida: {m['puntos_perdida']}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo-cache", action="store_true",
                        help="Solo regenera el cache JSON sin bajar datos de GEE")
    parser.add_argument("--alcaldia", type=str, default="",
                        help="Procesar solo una alcaldia especifica")
    args = parser.parse_args()

    alcaldias = [args.alcaldia] if args.alcaldia else ALCALDIAS

    print(f"CDMX Verde — Pre-carga de {len(alcaldias)} alcaldia(s)")
    print(f"Modo: {'solo cache' if args.solo_cache else 'descarga completa'}")
    print(f"GEE Project: {GEE}")

    exitosas = []
    fallidas  = []

    for alc in alcaldias:
        ok = procesar_alcaldia(alc, args.solo_cache)
        if ok:
            exitosas.append(alc)
        else:
            fallidas.append(alc)

    print(f"\n{'='*50}")
    print(f"RESUMEN")
    print(f"{'='*50}")
    print(f"Exitosas : {len(exitosas)}")
    print(f"Fallidas : {len(fallidas)}")
    if fallidas:
        print(f"Fallidas : {fallidas}")


if __name__ == "__main__":
    main()
