"""
DEMO PERSONAL — vista previa del resultado final del proyecto.

Lo que hace:
  1. Baja dos imágenes Sentinel-2 (2015 y actual) de UNA alcaldía pequeña.
  2. Entrena un kNN con TUS muestras (training_samples.csv).
  3. Clasifica cada imagen por bloques.
  4. Genera la máscara de pérdida: bosque_2015 AND NOT bosque_actual.
  5. Dibuja la imagen tipo "antes vs después" con deforestación en rojo.

Salidas en viz/demo/.
"""
from __future__ import annotations
from pathlib import Path
import os, sys, urllib.request, tempfile
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
import ee
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")
if not GEE_PROJECT:
    sys.exit("ERROR: la variable GEE_PROJECT no esta definida. "
             "Crea un archivo .env en la raiz del proyecto (copia .env.example "
             "y pon el ID de tu proyecto de Google Earth Engine).")
TRAIN_CSV = ROOT / "data" / "training" / "training_samples.csv"
ALC_GEOJSON = ROOT / "data" / "alcaldias" / "alcaldias_cdmx.geojson"
OUT = ROOT / "viz" / "demo"
OUT.mkdir(parents=True, exist_ok=True)

# Alcaldía a analizar. Cambia si quieres ver otra (Milpa Alta, Tlalpan, etc.).
ALCALDIA = "Tlalpan"

# Ventanas temporales: Sentinel-2 inició en jun 2015, así que mar-dic 2016
# es el primer año completo. Usamos 2016 como "base" para tener data limpia.
ANIO_BASE = 2016
ANIO_ACTUAL = 2024

# Resolución del análisis. 30 m mantiene la descarga bajo el límite de 50 MB de GEE
# incluso para alcaldías grandes (Milpa Alta, Tlalpan). Usa 20 m sólo para alcaldías
# pequeñas (Cuajimalpa, Iztacalco, Benito Juárez).
ESCALA = 30

BANDAS = ["B02", "B03", "B04", "B08", "B11", "B12"]
BANDAS_GEE = ["B2", "B3", "B4", "B8", "B11", "B12"]


def init_ee():
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        ee.Authenticate(); ee.Initialize(project=GEE_PROJECT)


def aoi_alcaldia():
    import json
    with open(ALC_GEOJSON, "r", encoding="utf-8") as f:
        gj = json.load(f)
    for feat in gj["features"]:
        if feat["properties"]["alcaldia"] == ALCALDIA:
            return ee.Feature(feat).geometry()
    sys.exit(f"No encontré alcaldía {ALCALDIA}")


def mask_clouds(img):
    scl = img.select("SCL")
    mala = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))
    return img.updateMask(mala.Not())


def mediana_s2(aoi, anio: int):
    """Composite mediano de S2 para enero-mayo del año dado (temporada seca)."""
    if anio >= 2017:
        col_id = "COPERNICUS/S2_SR_HARMONIZED"
    else:
        col_id = "COPERNICUS/S2_HARMONIZED"
    col = (
        ee.ImageCollection(col_id)
        .filterBounds(aoi)
        .filterDate(f"{anio}-01-01", f"{anio}-05-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
    )
    if anio >= 2017:
        col = col.map(mask_clouds)
    return col.median().select(BANDAS_GEE, BANDAS).clip(aoi)


def descargar_tiff(img, aoi, nombre: str) -> Path:
    """Baja la imagen como GeoTIFF usando getDownloadURL."""
    url = img.getDownloadURL({
        "scale": ESCALA,
        "region": aoi,
        "format": "GEO_TIFF",
        "bands": BANDAS,
    })
    print(f"   Descargando {nombre} ...")
    out = OUT / f"s2_{nombre}.tif"
    urllib.request.urlretrieve(url, out)
    print(f"   {out.name}  ({out.stat().st_size/1e6:.1f} MB)")
    return out


def cargar_imagen(path: Path):
    with rasterio.open(path) as src:
        arr = src.read().astype(np.float32)  # (bandas, H, W)
        profile = src.profile
    return arr, profile


def features_por_bloque(arr: np.ndarray, block: int = 4):
    """Reduce la imagen a vectores promedio por bloque NxN.
    Devuelve (features [n_bloques, n_features], shape_bloques (Hb, Wb))."""
    _, H, W = arr.shape
    Hb, Wb = H // block, W // block
    arr = arr[:, :Hb * block, :Wb * block]
    # Reshape a bloques: (bandas, Hb, block, Wb, block) -> promedio por bloque.
    arr_b = arr.reshape(arr.shape[0], Hb, block, Wb, block).mean(axis=(2, 4))
    # NDVI y NDWI por bloque.
    b03, b04, b08 = arr_b[1], arr_b[2], arr_b[3]
    ndvi = (b08 - b04) / (b08 + b04 + 1e-6)
    ndwi = (b03 - b08) / (b03 + b08 + 1e-6)
    feats = np.concatenate([arr_b, ndvi[None], ndwi[None]], axis=0)  # (8, Hb, Wb)
    feats = feats.transpose(1, 2, 0).reshape(-1, feats.shape[0])  # (Hb*Wb, 8)
    return feats, (Hb, Wb)


def entrenar_knn():
    df = pd.read_csv(TRAIN_CSV)
    # Reducimos a clases binarias: bosque vs todo lo demás (incluido deforestado/urbano/etc.)
    df = df[df["clase"] != "__none__"].copy()
    df["y"] = (df["clase"] == "bosque").astype(int)
    X = df[["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDWI"]].values
    y = df["y"].values
    print(f"   Entrenando kNN con {len(df)} muestras (bosque={y.sum()}, otro={len(y)-y.sum()})")
    knn = KNeighborsClassifier(n_neighbors=7, weights="distance", n_jobs=-1)
    knn.fit(X, y)
    return knn


def clasificar(arr, knn, block=4):
    feats, (Hb, Wb) = features_por_bloque(arr, block=block)
    # NDVI guardado en feats[:,6]. Bloques sin datos válidos (todos NaN) -> 0.
    mask_valido = ~np.isnan(feats).any(axis=1)
    pred = np.zeros(feats.shape[0], dtype=np.uint8)
    pred[mask_valido] = knn.predict(feats[mask_valido])
    return pred.reshape(Hb, Wb)


def normalizar_rgb(arr):
    """Composición RGB para visualización (B04, B03, B02)."""
    rgb = arr[[2, 1, 0]].astype(np.float32)  # R,G,B = B04,B03,B02
    # Percentiles para stretch.
    lo, hi = np.nanpercentile(rgb, (2, 98))
    rgb = np.clip((rgb - lo) / (hi - lo + 1e-6), 0, 1)
    return rgb.transpose(1, 2, 0)


def main():
    print("[1/5] Inicializando Earth Engine ...")
    init_ee()
    aoi = aoi_alcaldia()

    print(f"[2/5] Descargando S2 de {ALCALDIA} ({ANIO_BASE} y {ANIO_ACTUAL}) ...")
    img_base = mediana_s2(aoi, ANIO_BASE)
    img_act = mediana_s2(aoi, ANIO_ACTUAL)
    tif_base = descargar_tiff(img_base, aoi, f"{ANIO_BASE}")
    tif_act = descargar_tiff(img_act, aoi, f"{ANIO_ACTUAL}")

    print("[3/5] Cargando imágenes y entrenando kNN ...")
    arr_base, _ = cargar_imagen(tif_base)
    arr_act, _ = cargar_imagen(tif_act)
    knn = entrenar_knn()

    print("[4/5] Clasificando por bloques ...")
    BLOCK = 4
    bosque_base = clasificar(arr_base, knn, block=BLOCK)
    bosque_act = clasificar(arr_act, knn, block=BLOCK)
    perdida = (bosque_base == 1) & (bosque_act == 0)
    n_bloques_base = int(bosque_base.sum())
    n_perdidos = int(perdida.sum())
    pct = 100.0 * n_perdidos / max(n_bloques_base, 1)
    area_perdida_ha = n_perdidos * (BLOCK * ESCALA) ** 2 / 10_000.0
    print(f"   Bosque {ANIO_BASE}: {n_bloques_base} bloques")
    print(f"   Pérdida detectada: {n_perdidos} bloques ({pct:.2f}%)")
    print(f"   Área perdida estimada: {area_perdida_ha:,.1f} ha")

    print("[5/5] Generando visualización ...")
    rgb_base = normalizar_rgb(arr_base)
    rgb_act = normalizar_rgb(arr_act)

    # Upsample máscara al tamaño RGB para overlay (recorte por si hay diferencia de 1-3 px).
    factor = BLOCK
    perdida_full = np.kron(perdida, np.ones((factor, factor), dtype=np.uint8))
    H = min(perdida_full.shape[0], rgb_act.shape[0])
    W = min(perdida_full.shape[1], rgb_act.shape[1])
    perdida_full = perdida_full[:H, :W]
    rgb_act = rgb_act[:H, :W]
    rgb_base = rgb_base[:H, :W]
    alpha = 0.65
    overlay_blend = np.where(perdida_full[..., None] == 1,
                             alpha * np.array([1, 0, 0]) + (1 - alpha) * rgb_act,
                             rgb_act)

    fig, axes = plt.subplots(2, 1, figsize=(9, 11))
    axes[0].imshow(rgb_base)
    axes[0].set_title(f"{ALCALDIA} — Sentinel-2 {ANIO_BASE} (referencia)")
    axes[0].axis("off")
    axes[1].imshow(overlay_blend)
    axes[1].set_title(
        f"{ALCALDIA} — {ANIO_ACTUAL}\n"
        f"Zonas deforestadas en rojo: {pct:.2f}% ({area_perdida_ha:,.0f} ha)"
    )
    axes[1].axis("off")
    fig.tight_layout()
    out_png = OUT / f"demo_{ALCALDIA.replace(' ', '_')}_{ANIO_BASE}vs{ANIO_ACTUAL}.png"
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"\nListo. Abre: {out_png}")
    print("\nRecuerda: esto es un demo personal, NO un entregable del Rol 3.")


if __name__ == "__main__":
    main()
