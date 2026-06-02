
from pathlib import Path
import sys
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "inegi"
OUT = ROOT / "data" / "alcaldias"
OUT.mkdir(parents=True, exist_ok=True)

CVE_CDMX = "09"
CRS_GEO = "EPSG:4326"
CRS_UTM = "EPSG:32614"  # UTM zona 14N, acordado con Rol 2


CANDIDATOS = [
    RAW / "09_ciudaddemexico" / "conjunto_de_datos" / "09mun.shp",
    RAW / "09mun.shp",
    RAW / "00mun.shp",
    RAW / "mg2024_integrado" / "conjunto_de_datos" / "00mun.shp",
]


def localizar_shapefile() -> Path:
    for p in CANDIDATOS:
        if p.exists():
            return p
    print("ERROR: No se encontró el shapefile de municipios del INEGI.")
    print("Rutas buscadas:")
    for p in CANDIDATOS:
        print(f"   - {p}")
    print("\nDescarga el Marco Geoestadístico Nacional desde:")
    print("   https://www.inegi.org.mx/temas/mg/")
    print(f"y descomprime en: {RAW}")
    sys.exit(1)


def main() -> None:
    src = localizar_shapefile()
    print(f"[1/4] Leyendo {src.name} ...")
    gdf = gpd.read_file(src)

    print(f"[2/4] Filtrando alcaldías de la CDMX (CVE_ENT = {CVE_CDMX}) ...")
    if "CVE_ENT" in gdf.columns:
        gdf = gdf[gdf["CVE_ENT"] == CVE_CDMX].copy()
    elif "CVEGEO" in gdf.columns:
        gdf = gdf[gdf["CVEGEO"].str.startswith(CVE_CDMX)].copy()
    else:
        raise RuntimeError(
            "El shapefile no tiene columna CVE_ENT ni CVEGEO. "
            "Revisa la versión del Marco Geoestadístico."
        )

    if len(gdf) != 16:
        print(f"   AVISO: se esperaban 16 alcaldías, se obtuvieron {len(gdf)}")

    # Normaliza el nombre a una columna estable `alcaldia`.
    nombre_col = next((c for c in ("NOMGEO", "NOM_MUN", "NOMBRE") if c in gdf.columns), None)
    if nombre_col is None:
        raise RuntimeError("No se encontró columna de nombre (NOMGEO/NOM_MUN/NOMBRE).")
    gdf["alcaldia"] = gdf[nombre_col].str.strip()

    # Garantiza CRS geográfico de entrada.
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    gdf_utm = gdf.to_crs(CRS_UTM)
    gdf["area_ha"] = gdf_utm.geometry.area / 10_000.0
    gdf_utm["area_ha"] = gdf["area_ha"].values
    gdf_geo = gdf.to_crs(CRS_GEO)

    columnas = ["alcaldia", "CVE_ENT", "CVE_MUN", "CVEGEO", "area_ha", "geometry"]
    columnas = [c for c in columnas if c in gdf_utm.columns or c == "geometry"]

    out_shp = OUT / "alcaldias_cdmx.shp"
    out_geojson = OUT / "alcaldias_cdmx.geojson"
    out_utm = OUT / "alcaldias_cdmx_utm14n.shp"

    print(f"[3/4] Escribiendo {out_shp.name}, {out_geojson.name}, {out_utm.name} ...")
    gdf_geo[columnas].to_file(out_shp)
    gdf_geo[columnas].to_file(out_geojson, driver="GeoJSON")
    gdf_utm[columnas].to_file(out_utm)

    print("[4/4] Resumen por alcaldía (hectáreas):")
    resumen = (
        gdf_utm[["alcaldia", "area_ha"]]
        .sort_values("area_ha", ascending=False)
        .to_string(index=False, float_format=lambda x: f"{x:,.0f}")
    )
    print(resumen)


if __name__ == "__main__":
    main()
