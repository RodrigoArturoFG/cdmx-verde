"""
Script de visualización personal — NO genera entregables.

Salidas en viz/ (excluida en .gitignore). Útil para inspeccionar el dataset
y los polígonos antes de pasarlos al Rol 4 y Rol 8.

Genera:
  viz/01_alcaldias_mapa.png     - Mapa estático de las 16 alcaldías
  viz/02_muestras_scatter.png   - Puntos de entrenamiento sobre alcaldías
  viz/03_ndvi_por_clase.png     - Histograma NDVI por clase
  viz/04_firmas_espectrales.png - Reflectancia media por banda y clase
  viz/05_mapa_interactivo.html  - Mapa folium (abrir en el navegador)
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium

ROOT = Path(__file__).resolve().parents[1]
ALC = ROOT / "data" / "alcaldias" / "alcaldias_cdmx.geojson"
TRAIN = ROOT / "data" / "training" / "training_samples.csv"
OUT = ROOT / "viz"
OUT.mkdir(exist_ok=True)

# Paleta de clases
COLORES = {
    "bosque": "#1b7837",
    "deforestado": "#c2002f",
    "pastizal": "#a6dba0",
    "urbano": "#404040",
    "suelo_desnudo": "#d8b365",
    "agua": "#2166ac",
    "__none__": "#cccccc",
}


def cargar():
    alc = gpd.read_file(ALC)
    df = pd.read_csv(TRAIN)
    return alc, df


def fig1_alcaldias(alc):
    fig, ax = plt.subplots(figsize=(10, 10))
    alc.plot(ax=ax, column="area_ha", cmap="YlGn", edgecolor="black",
             legend=True, legend_kwds={"label": "Hectáreas", "shrink": 0.6})
    for _, row in alc.iterrows():
        c = row.geometry.centroid
        ax.annotate(row["alcaldia"], (c.x, c.y), fontsize=7,
                    ha="center", color="black")
    ax.set_title("Alcaldías de la CDMX (entregable Rol 3)")
    ax.set_axis_off()
    fig.tight_layout()
    out = OUT / "01_alcaldias_mapa.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"   {out.name}")


def fig2_scatter(alc, df):
    fig, ax = plt.subplots(figsize=(10, 10))
    alc.boundary.plot(ax=ax, color="black", linewidth=0.5)
    for clase, sub in df.groupby("clase"):
        ax.scatter(sub.lon, sub.lat, s=4, alpha=0.6,
                   color=COLORES.get(clase, "#888"), label=f"{clase} ({len(sub)})")
    ax.set_title("Muestras de entrenamiento sobre la CDMX")
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_aspect("equal")
    fig.tight_layout()
    out = OUT / "02_muestras_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"   {out.name}")


def fig3_ndvi(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    clases_orden = ["bosque", "pastizal", "deforestado", "suelo_desnudo", "urbano", "agua"]
    datos = [df[df["clase"] == c]["NDVI"].dropna().values for c in clases_orden]
    bp = ax.boxplot(datos, labels=clases_orden, patch_artist=True)
    for patch, clase in zip(bp["boxes"], clases_orden):
        patch.set_facecolor(COLORES.get(clase, "#888"))
        patch.set_alpha(0.7)
    ax.set_ylabel("NDVI")
    ax.set_title("Distribución de NDVI por clase — separabilidad del kNN")
    ax.axhline(0.3, color="gray", linestyle="--", linewidth=0.7,
               label="Umbral típico bosque (NDVI=0.3)")
    ax.legend()
    fig.tight_layout()
    out = OUT / "03_ndvi_por_clase.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"   {out.name}")


def fig4_firmas(df):
    bandas = ["B02", "B03", "B04", "B08", "B11", "B12"]
    fig, ax = plt.subplots(figsize=(10, 6))
    for clase in ["bosque", "deforestado", "urbano", "agua", "suelo_desnudo", "pastizal"]:
        sub = df[df["clase"] == clase]
        if sub.empty:
            continue
        ax.plot(bandas, sub[bandas].mean(), marker="o",
                color=COLORES.get(clase, "#888"), label=clase, linewidth=2)
    ax.set_xlabel("Banda Sentinel-2")
    ax.set_ylabel("Reflectancia media (×10000)")
    ax.set_title("Firmas espectrales medias por clase")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = OUT / "04_firmas_espectrales.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"   {out.name}")


def fig5_folium(alc, df):
    centro = [19.35, -99.15]
    m = folium.Map(location=centro, zoom_start=10, tiles="OpenStreetMap")

    # Alcaldías
    folium.GeoJson(
        alc,
        name="Alcaldías",
        style_function=lambda f: {"color": "black", "weight": 1.5, "fillOpacity": 0.0},
        tooltip=folium.GeoJsonTooltip(fields=["alcaldia", "area_ha"],
                                      aliases=["Alcaldía:", "Hectáreas:"]),
    ).add_to(m)

    # Muestras: submuestreamos a 1000 puntos para que el HTML no pese mucho.
    df_s = df.sample(n=min(1000, len(df)), random_state=42)
    for clase, sub in df_s.groupby("clase"):
        fg = folium.FeatureGroup(name=f"{clase} ({len(sub)})")
        color = COLORES.get(clase, "#888")
        for _, row in sub.iterrows():
            folium.CircleMarker(
                location=(row.lat, row.lon),
                radius=3,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"{clase}<br>NDVI={row.NDVI:.2f}",
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl().add_to(m)
    out = OUT / "05_mapa_interactivo.html"
    m.save(str(out))
    print(f"   {out.name}  <-- abre este en el navegador")


def main():
    print("Cargando datos ...")
    alc, df = cargar()
    print(f"   alcaldías: {len(alc)} polígonos")
    print(f"   muestras:  {len(df)} puntos")
    print("Generando visualizaciones en viz/ ...")
    fig1_alcaldias(alc)
    fig2_scatter(alc, df)
    fig3_ndvi(df)
    fig4_firmas(df)
    fig5_folium(alc, df)
    print(f"\nListo. Abre la carpeta: {OUT}")


if __name__ == "__main__":
    main()
