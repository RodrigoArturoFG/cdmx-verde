# Arreglo: Hectáreas estimadas y plan de corrección

Fecha: 2026-06-16
Autor: GitHub Copilot (asistente)

> **ACTUALIZACIÓN 2026-06-16 (Claude / Opus 4.8) — método sustituido.**
> El escalado por proporción de muestras documentado abajo se **descartó** porque
> el muestreo del pipeline es estratificado con asignación igual (~800 puntos por
> clase), por lo que la proporción de muestras **no** representa la fracción de área.
> Se reemplazó por un **conteo wall-to-wall en Google Earth Engine** escalado por el
> `area_ha` oficial del GeoJSON. La justificación detallada, el código y el track por
> archivo/línea están en la sección [**"Solución definitiva: wall-to-wall (Claude)"**](#solución-definitiva-wall-to-wall-claude)
> al final de este documento. Lo anterior se conserva como contexto histórico.

## Resumen ejecutivo

Se detectó que los valores de hectáreas reportados por la aplicación eran inconsistentes con la realidad territorial: los valores eran del orden de decenas de hectáreas mientras que las alcaldías tienen decenas de miles de hectáreas. El origen del error era que el pipeline sumaba el área equivalente a las *muestras* (cada muestra = 1 píxel de Sentinel-2 ≈ 10×10 m = 0.01 ha) sin escalar por la representatividad ni por el área total del polígono de la alcaldía.

Se aplicaron cambios para:
- Estimar las hectáreas totales de cada clase escalando la proporción de muestras por el área real del polígono de la alcaldía cuando la geometría está disponible.
- Mantener compatibilidad con el método original (cada muestra = 0.01 ha) cuando no exista la geometría.
- Aclarar en la UI que las hectáreas mostradas son estimadas por muestreo.

## Plan (registrado)

1. Revisar código y detectar origen del bug — completado.
2. Implementar escalado de muestras a área de alcaldía (backend) — completado.
3. Actualizar frontend para indicar "ha estimadas" y opción de ver "muestras" — pendiente (se agregó texto aclaratorio en la UI).
4. Agregar pruebas rápidas/locales para validar resultados en 2–3 alcaldías — pendiente.
5. Actualizar documentación / registrar referencia sobre GSD y método — pendiente (este documento).
6. Investigar soluciones alternativas (muestreo, wall-to-wall, GEE area) — en progreso.

Estado: pasos 1 y 2 completados; resto pendiente según prioridad.

## Archivos modificados

- [scripts/03_fusion_validacion.py](scripts/03_fusion_validacion.py)
- [frontend/src/components/MapaAlcaldias.jsx](frontend/src/components/MapaAlcaldias.jsx)
- [frontend/src/components/ComparativaPanel.jsx](frontend/src/components/ComparativaPanel.jsx)

> Nota: los enlaces apuntan a los archivos en el repositorio de trabajo.

## Qué cambié (detallado)

### Backend (`scripts/03_fusion_validacion.py`)

1. Nueva firma para `calcular_metricas`:

- Antes: `calcular_metricas(comp, alcaldia, ab, aa)` — retornaba áreas calculadas como `count * 0.01` ha.
- Ahora: `calcular_metricas(comp, alcaldia, ab, aa, area_alcaldia_ha=None)` — si `area_alcaldia_ha` se proporciona, estima áreas por clase como `(n_clase / n_muestras) * area_alcaldia_ha`.

2. Cálculo del área del polígono de la alcaldía (en ha):

- El script intenta cargar `data/alcaldias/alcaldias_cdmx_utm14n.shp` (si existe) para obtener áreas en metros cuadrados (m²). Si no existe, carga el GeoJSON `data/alcaldias/alcaldias_cdmx.geojson` y lo reproyecta a EPSG:3857 para obtener áreas aproximadas en metros.
- Convierte `area_m2` a hectáreas: `area_ha = area_m2 / 10000`.
- Si no encuentra la geometría o ocurre un error, `area_alcaldia_ha` queda `None` y se usa el comportamiento antiguo (cada muestra = 0.01 ha).

3. Escritura de `metricas_{alcaldia}_2016vs2024.json` con los nuevos campos calculados.

Código clave (extracto modificado):

```python
# calcular_metricas (extracto)

def calcular_metricas(comp: pd.DataFrame, alcaldia: str, ab: int, aa: int, area_alcaldia_ha: float | None = None) -> dict:
    """Si area_alcaldia_ha es None: cada muestra = 0.01 ha; si no, escala por proporción."""

    muestras_totales = len(comp)

    def count_clase(col, clase):
        return int((comp[col] == clase).sum())

    if area_alcaldia_ha is None or muestras_totales == 0:
        ha_pixel = 0.01
        def ha_clase(col, clase):
            return round(count_clase(col, clase) * ha_pixel, 2)
        hb = ha_clase("clase_base", "bosque")
        # ... resto del cálculo (modo antiguo)

    # Modo estimación por proporción sobre área real
    area = float(area_alcaldia_ha)
    def ha_prop(col, clase):
        cnt = count_clase(col, clase)
        return round((cnt / muestras_totales) * area, 2) if muestras_totales > 0 else 0.0
    hb = ha_prop("clase_base", "bosque")
    # ... resto del cálculo (modo escalado)
```

Y el bloque que resuelve el área de la alcaldía (en `main`), antes de llamar a `calcular_metricas`:

```python
# Intentar obtener el área real de la alcaldía (en ha) para escalar
area_alcaldia_ha = None
try:
    shp_utm = ROOT / "data" / "alcaldias" / "alcaldias_cdmx_utm14n.shp"
    if shp_utm.exists():
        alc_gdf = gpd.read_file(shp_utm)
    else:
        alc_gdf = gpd.read_file(ALC)
        alc_gdf = alc_gdf.to_crs(epsg=3857)

    target = alc_gdf[alc_gdf["alcaldia"].apply(lambda x: normalizar(str(x))) == normalizar(alc)]
    if len(target) == 1:
        geom = target.iloc[0].geometry
        area_m2 = geom.area
        area_alcaldia_ha = round(area_m2 / 10000.0, 2)
except Exception:
    area_alcaldia_ha = None

metricas = calcular_metricas(comparativa, alc, ab, aa, area_alcaldia_ha)
```

### Frontend

- `frontend/src/components/MapaAlcaldias.jsx` — Actualicé el texto explicativo en el panel CAPAS para indicar: "hectáreas estimadas por muestreo; no son medición wall-to-wall." También cambié la etiqueta en la badge delta para mostrar `ha (estimadas)`.

- `frontend/src/components/ComparativaPanel.jsx` — En el tab `Descargar` la línea de resumen ahora incluye `ha (estimadas)`.

Estos cambios son puramente informativos para evitar confusión al usuario sobre la naturaleza estimada de las hectáreas.

## Justificación técnica y fuentes

- Ground Sample Distance (GSD) — relación con área de píxel:
  - Sentinel-2 tiene resolución espacial de 10 m en bandas visibles e infrarrojo cercano. Un píxel de 10×10 m representa 100 m² = 0.01 ha. Por tanto, al usar muestreos basados en píxeles de Sentinel-2, cada muestra individual representa 0.01 ha en el terreno. Fuente conceptual: https://xrtechgroup.com/ground-sample-distance/

- Por qué el escalado por proporción es razonable:
  - Si las muestras se tomaron de forma aleatoria o bien distribuidas (o si provienen de un muestreo sistemático que cubre la alcaldía), la proporción de muestras en una clase aproxima la fracción de área de esa clase en la alcaldía. Multiplicando esta fracción por el área total del polígono se obtiene una estimación del área por clase (método de upscaling simple).

- Limitaciones y cuando preferir soluciones alternativas:
  - Si las muestras no son representativas espacialmente (por ejemplo, sesgo hacia ciertas zonas), la estimación por proporción será sesgada.
  - Para obtener áreas exactas, la recomendación técnica es realizar un análisis wall-to-wall (clasificar todos los píxeles dentro del polígono) o usar funciones zonales en Google Earth Engine (`reduceRegion`, `reduceConnectedComponents`, `frequencyHistogram`) sobre el mapa clasificado.

## Alternativas (detalladas)

1. Wall-to-wall en Google Earth Engine (recomendado para precisión)
   - Ejecutar un `ee.Image` con la clasificación (p. ej. Dynamic World o WorldCover), recortar al polígono y usar `reduceRegion` con `ee.Reducer.frequencyHistogram()` o `ee.Reducer.sum()` para contar píxeles por clase, luego convertir a área multiplicando por el área por píxel.
   - Pros: más preciso, no depende de muestras. Contras: requiere credenciales GEE y más tiempo de cómputo.

2. Aumentar densidad de muestreo / muestreo estratificado
   - Tomar más muestras distribuidas de forma estratificada (por grilla o por subzonas) para reducir sesgo y mejorar la estimación por proporción.

3. Modelos de upscaling espacial
   - Usar técnicas estadísticas (interpolación, kriging, modelos de regresión espacial) para estimar la cobertura a todo el polígono a partir de las muestras.
   - Pros: puede corregir sesgo si se tiene covariables; Contras: mayor complejidad y necesidad de validación.

## Comandos para probar localmente

Desde la carpeta raíz del proyecto:

```bash
# Regenerar comparativa para Tlalpan (usa archivos de muestras ya generados en data/training)
python scripts/03_fusion_validacion.py --alcaldia "Tlalpan" --anio-base 2016 --anio-actual 2024

# Resultado: data/training/metricas_tlalpan_2016vs2024.json
```

## Código modificado completo (extractos relevantes)

- `calcular_metricas` (ver arriba) — implementa los dos modos.
- Bloque de obtención de área de la alcaldía (ver arriba).

## Próximos pasos recomendados

- Ejecutar el script para 2–3 alcaldías y comparar los resultados con áreas oficiales o con un análisis wall-to-wall por muestreo en GEE.
- Añadir en la UI un toggle para mostrar "Valores brutos por muestras (ha, muestras)" vs "Estimado (proporción × área poligonal)".
- Implementar job opcional en el pipeline que invoque GEE para obtener áreas wall-to-wall cuando se requiera mayor precisión.

---

Documento generado automáticamente por la intervención de corrección de métricas.

---

# Solución definitiva: wall-to-wall (Claude)

Fecha: 2026-06-16
Autor: Claude (Opus 4.8)

## Por qué se descartó el escalado por proporción

El parche anterior estimaba el área de cada clase como `(n_clase / n_muestras) * area_alcaldia_ha`.
Eso **solo es válido si las muestras son espacialmente representativas** (muestreo aleatorio o
sistemático proporcional al área). En este proyecto **no lo son**: el script de muestreo pide un
número fijo de puntos por clase.

Extracto de [scripts/02_muestras_gee.py](../scripts/02_muestras_gee.py#L135-L145):

```python
muestras = stack.stratifiedSample(
    numPoints=MUESTRAS_POR_CLASE,
    classBand="clase_id",
    region=aoi,
    scale=10,
    seed=42,
    classValues=[1, 2, 3, 4, 5],
    classPoints=[MUESTRAS_POR_CLASE] * 5,   # ← 800 puntos por clase, fijo
    geometries=True,
    dropNulls=True,
)
```

Esto es **muestreo estratificado con asignación igual** (`classPoints = [800]*5`). Es la práctica
correcta para *entrenar un clasificador* (se quiere representación balanceada de cada clase), pero
hace que `n_clase / n_muestras ≈ 1/5` para todas las clases, **independientemente de su superficie
real**. Evidencia empírica en Tlalpan (`data/training/muestras_tlalpan_2024.csv`):

```
372 agua          800 bosque      800 pastizal
800 suelo_desnudo 800 urbano
```

Con esos conteos, el escalado por proporción repartía el área casi por igual entre clases
(~6,000 ha cada una en una alcaldía de 31,425 ha), cuando Tlalpan es ~40% bosque. El número dejaba
de ser absurdo en magnitud, pero la **distribución por clase seguía siendo falsa**.

**Fuentes / fundamento:**
- El muestreo estratificado asigna tamaños de muestra por estrato según el diseño, no según el área;
  para que las proporciones muestrales estimen proporciones poblacionales se requiere muestreo
  proporcional/aleatorio o ponderar por la inversa de la probabilidad de inclusión. Ver
  *Olofsson et al. (2014), "Good practices for estimating area and assessing accuracy of land
  change", Remote Sensing of Environment 148:42-57* — explica por qué el área debe estimarse con
  estimadores que respeten el diseño de muestreo, no contando muestras por clase.
- La práctica recomendada para área por clase a partir de un mapa clasificado es el conteo de
  píxeles (pixel counting) wall-to-wall, opcionalmente ajustado por exactitud. Misma referencia y
  GFOI MGD (https://www.reddcompass.org/).

## En qué consiste la solución wall-to-wall

En lugar de inferir el área desde las muestras, se **clasifica todo el polígono** (todos los
píxeles, no una muestra) con Dynamic World — la misma fuente que ya usa el pipeline para 2016 y 2024 —
y se cuentan los píxeles por clase con `reduceRegion` + `frequencyHistogram`. Las fracciones
resultantes se escalan por el `area_ha` **oficial** que ya está precalculado en el GeoJSON, de modo
que las clases siempre suman el área real de la alcaldía.

> "wall-to-wall" = se evalúa cada píxel del área de interés, en contraste con un muestreo. Es el
> método que el propio documento original recomendaba como opción 1 para precisión.

## Cambios realizados (track por archivo y línea)

Todos los cambios de cálculo viven en **[scripts/03_fusion_validacion.py](../scripts/03_fusion_validacion.py)**.
Se eliminó por completo la lógica de proporción y el bloque que calculaba el área reproyectando el
shapefile a EPSG:3857 (Web Mercator), que además sobreestimaba ~12% el área a la latitud de CDMX.

### 1. Configuración de Earth Engine en el script de fusión

[scripts/03_fusion_validacion.py:18-29](../scripts/03_fusion_validacion.py#L18-L29) — se añadió `import ee`
y la carga de `GEE_PROJECT` desde `.env` (el pipeline ya inyecta esta variable al subproceso):

```python
import ee
from dotenv import load_dotenv
...
load_dotenv(ROOT / ".env")
GEE_PROJECT = os.environ.get("GEE_PROJECT")
```

### 2. Remapeo de clases idéntico al del muestreo

[scripts/03_fusion_validacion.py:42-49](../scripts/03_fusion_validacion.py#L42-L49) — se replicó el mismo
remapeo de etiquetas Dynamic World que usa el script 02, para que la clasificación wall-to-wall sea
coherente con las muestras. Se añadió la clase `6 = deforestado` (derivada del cambio, ver punto 5):

```python
DW_KEYS   = [0, 1, 2, 3, 4, 5, 6, 7]
DW_VALUES = [5, 1, 2, 2, 2, 2, 3, 4]
CLASE_POR_ID = {1: "bosque", 2: "pastizal", 3: "urbano", 4: "suelo_desnudo", 5: "agua", 6: "deforestado"}
```

### 3. Lectura del área oficial desde el GeoJSON (no recálculo)

[scripts/03_fusion_validacion.py:162-174](../scripts/03_fusion_validacion.py#L162-L174) — el área se toma
de la propiedad `area_ha` ya presente en `data/alcaldias/alcaldias_cdmx.geojson` (autoritativa),
en lugar de recalcularla por geometría como hacía el parche anterior:

```python
def cargar_aoi_y_area(nombre_alcaldia: str):
    ...
    for feat in gj["features"]:
        props = feat["properties"]
        if normalizar(str(props.get("alcaldia", ""))) == norm:
            area_ha = props.get("area_ha")
            area_ha = float(area_ha) if area_ha is not None else None
            return ee.Geometry(feat["geometry"]), props["alcaldia"], area_ha
```

### 4. Clasificación y conteo wall-to-wall en GEE

[scripts/03_fusion_validacion.py:176-209](../scripts/03_fusion_validacion.py#L176-L209) — se clasifica
todo el polígono (moda de Dynamic World, ene-may, igual que el script 02) y se cuentan **todos** los
píxeles con `frequencyHistogram` a 10 m. Las fracciones se escalan por `area_ha`, ignorando los
píxeles sin dato (clase 0) en el denominador:

```python
def clasificacion_dw(aoi, anio: int):
    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
          .filterBounds(aoi).filterDate(f"{anio}-01-01", f"{anio}-05-31"))
    moda = dw.select("label").mode()
    return moda.remap(DW_KEYS, DW_VALUES, defaultValue=0).rename("clase_id")

def _histograma(img, aoi) -> dict[int, float]:
    d = img.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=aoi, scale=10, maxPixels=int(1e10),
    ).get("clase_id")
    ...

def _hist_a_ha(hist, area_ha):
    validos = {k: v for k, v in hist.items() if k in CLASE_POR_ID}
    total = sum(validos.values())
    ...
    out[CLASE_POR_ID[k]] = round((v / total) * area_ha, 2)   # fracción × área oficial
```

### 5. Deforestado como cambio píxel a píxel (no relabel de muestras)

[scripts/03_fusion_validacion.py:212-228](../scripts/03_fusion_validacion.py#L212-L228) — en alcaldías de
conservación, los píxeles que eran bosque en el año base y pasaron a pastizal/urbano/suelo en el año
actual se reetiquetan a la clase 6 (`deforestado`) **antes** de contar, de modo que las clases siguen
siendo mutuamente excluyentes y suman el área total:

```python
def areas_wall_to_wall(aoi, ab, aa, area_ha, es_conservacion):
    base_img   = clasificacion_dw(aoi, ab)
    actual_img = clasificacion_dw(aoi, aa)
    if es_conservacion:
        defor = base_img.eq(1).And(actual_img.gte(2)).And(actual_img.lte(4))
        actual_img = actual_img.where(defor, 6)
    areas_base   = _hist_a_ha(_histograma(base_img, aoi),   area_ha)
    areas_actual = _hist_a_ha(_histograma(actual_img, aoi), area_ha)
    return areas_base, areas_actual
```

### 6. `calcular_metricas` reescrita con fallback

[scripts/03_fusion_validacion.py:232-282](../scripts/03_fusion_validacion.py#L232-L282) — ahora recibe los
diccionarios de áreas wall-to-wall. Si no se proveen (GEE no disponible), cae al método legado de
`0.01 ha/muestra` para no romper. Los conteos `puntos_perdida` / `puntos_ganancia` se siguen tomando
del cruce de muestras (son los marcadores rojos del mapa). Se añadió el campo `metodo_ha` para
trazabilidad (`"wall_to_wall"` o `"muestras_0.01ha"`).

### 7. Orquestación en `main()` (sustituye el bloque EPSG:3857 de Copilot)

[scripts/03_fusion_validacion.py:329-341](../scripts/03_fusion_validacion.py#L329-L341):

```python
areas_base = areas_actual = None
es_conservacion = any(normalizar(c) == normalizar(alc) for c in CONSERVACION)
if inicializar_ee():
    aoi, _nombre, area_ha = cargar_aoi_y_area(alc)
    if aoi is not None and area_ha:
        print(f"   Área oficial: {area_ha:,.1f} ha — contando píxeles wall-to-wall en GEE...")
        areas_base, areas_actual = areas_wall_to_wall(aoi, ab, aa, area_ha, es_conservacion)
metricas = calcular_metricas(comparativa, alc, ab, aa, areas_base, areas_actual)
```

### 8. Frontend — etiquetas corregidas

Las etiquetas que Copilot puso ("estimadas por muestreo; no son medición wall-to-wall") quedaron
inexactas y se actualizaron:

- [frontend/src/components/MapaAlcaldias.jsx:297](../frontend/src/components/MapaAlcaldias.jsx#L297) —
  ahora indica "hectáreas por conteo wall-to-wall (todos los píxeles, Dynamic World)".
- [frontend/src/components/MapaAlcaldias.jsx:364](../frontend/src/components/MapaAlcaldias.jsx#L364) — se
  quitó "(estimadas)" de la badge delta.
- [frontend/src/components/ComparativaPanel.jsx:294](../frontend/src/components/ComparativaPanel.jsx#L294) —
  se quitó "(estimadas)" del resumen de descarga.

## Validación

Ejecución para Tlalpan (`area_ha` oficial = 31,425.48 ha):

| Métrica | Método viejo (0.01 ha/muestra) | Wall-to-wall |
|---|---|---|
| Bosque 2016 | 8.0 ha | **13,005.8 ha** |
| Bosque 2024 | 7.94 ha | **12,614.0 ha** |
| Delta bosque | −0.06 ha (−0.75%) | **−391.8 ha (−3.0%)** |
| Deforestado | 0.96 ha | **1,811.7 ha** |
| Suma de todas las clases | ≪ área | **= 31,425.48 ha** ✓ |

La suma de clases coincide exactamente con el área oficial en ambos años, lo que confirma la
consistencia del escalado. Se regeneró el caché de las **16 alcaldías** con:

```bash
python precargar.py --solo-cache   # reusa los CSV de muestras; solo recalcula 03 (wall-to-wall) + cache
```

Resultado coherente con la realidad territorial: alcaldías de conservación con miles de ha de bosque
(Tlalpan, Álvaro Obregón ~3,000, Magdalena Contreras ~4,160) y alcaldías urbanas con <15 ha
(Benito Juárez, Iztacalco).

## Pruebas de precisión: total de hectáreas vs INEGI

Tras el cambio, el total de hectáreas de cada alcaldía (suma de todas las clases) es, por
construcción, el `area_ha` del GeoJSON. Para validar que ese total corresponde a la superficie
**oficial**, se recalculó el área de forma **independiente** desde el shapefile municipal original
del INEGI (Marco Geoestadístico 2025), sin pasar por nuestro GeoJSON.

**Fuente oficial usada:** `data/raw/inegi/09_ciudaddemexico/conjunto_de_datos/09mun.shp`
(16 municipios, CRS nativo EPSG:6372 — Mexico ITRF2008 / LCC).

**Método:** se reproyectó a UTM 14N (EPSG:32614, el mismo que usa
[scripts/01_alcaldias_inegi.py:13](../scripts/01_alcaldias_inegi.py#L13)), se calculó
`geometry.area / 10000` y se cruzó por clave `CVEGEO` contra nuestro `area_ha`.

### Resultado (coincidencia exacta)

| Alcaldía | Total nuestro (ha) | INEGI `09mun.shp` (ha) | dif % |
|---|---:|---:|---:|
| Tlalpan | 31,425.5 | 31,425.5 | 0.00% |
| Milpa Alta | 28,884.9 | 28,884.9 | 0.00% |
| Xochimilco | 11,402.5 | 11,402.5 | 0.00% |
| Iztapalapa | 11,307.4 | 11,307.4 | 0.00% |
| Álvaro Obregón | 9,582.0 | 9,582.0 | 0.00% |
| Gustavo A. Madero | 8,783.6 | 8,783.6 | 0.00% |
| Tláhuac | 8,578.2 | 8,578.2 | 0.00% |
| Cuajimalpa de Morelos | 7,110.3 | 7,110.3 | 0.00% |
| La Magdalena Contreras | 6,336.9 | 6,336.9 | 0.00% |
| Coyoacán | 5,388.0 | 5,388.0 | 0.00% |
| Miguel Hidalgo | 4,638.8 | 4,638.8 | 0.00% |
| Venustiano Carranza | 3,383.6 | 3,383.6 | 0.00% |
| Azcapotzalco | 3,349.6 | 3,349.6 | 0.00% |
| Cuauhtémoc | 3,249.9 | 3,249.9 | 0.00% |
| Benito Juárez | 2,668.0 | 2,668.0 | 0.00% |
| Iztacalco | 2,307.7 | 2,307.7 | 0.00% |
| **TOTAL CDMX** | **148,397.0** | **148,397.0** | **0.00%** |

La coincidencia es exacta en las 16 alcaldías. Es lo esperado: nuestro `area_ha` se derivó de este
mismo shapefile oficial, por lo que el total mostrado al usuario **es** la superficie oficial del
INEGI, no una estimación. (Cifras redondeadas en km² publicadas en otras fuentes difieren ~1% por
versión del límite y redondeo; el contraste correcto es contra el shapefile fuente, hecho aquí.)

> **Importante — qué valida y qué no esta prueba:** valida que el **total** por alcaldía = superficie
> oficial INEGI. **No** valida cómo se reparte ese total entre clases (bosque/urbano/etc.): ese
> reparto depende de la exactitud de la clasificación Dynamic World, que es una fuente distinta y no
> se valida aquí (ver Limitaciones).

### Reproducir la prueba

```python
import geopandas as gpd, json
mun = gpd.read_file('data/raw/inegi/09_ciudaddemexico/conjunto_de_datos/09mun.shp').to_crs('EPSG:32614')
area_inegi = dict(zip(mun['CVEGEO'], mun.geometry.area / 10000.0))
gj = json.load(open('data/alcaldias/alcaldias_cdmx.geojson', encoding='utf-8'))
for f in gj['features']:
    p = f['properties']
    nuestro, oficial = p['area_ha'], area_inegi[p['CVEGEO']]
    print(f"{p['alcaldia']:24} {nuestro:12,.1f} vs INEGI {oficial:12,.1f}  ({(nuestro-oficial)/oficial*100:+.2f}%)")
```

## Limitaciones que persisten

- La exactitud del **total** por alcaldía es exacta vs INEGI (ver prueba anterior). Lo que sigue
  dependiendo de la clasificación Dynamic World es el **reparto por clase**; no se aplicó ajuste de
  área por matriz de confusión (estimador de Olofsson). Es una mejora futura si se requiere intervalo
  de confianza sobre el área de cada clase.
- `puntos_perdida` / `puntos_ganancia` siguen siendo conteos de muestras (indicativos de dónde ocurre
  el cambio), no medidas de área; el área de cambio la da `ha_deforestado` (wall-to-wall).
- Requiere conexión y credenciales GEE al correr el script 03; sin ellas se usa el método legado.
