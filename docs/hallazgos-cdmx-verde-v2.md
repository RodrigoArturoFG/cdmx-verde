# CDMX Verde — Hallazgos de Auditoría v2

**Fecha:** 10 de junio de 2026
**Versión auditada:** 2.0 (actualización respecto al documento previo)
**URL:** http://localhost:5173
**Referencia previa:** [Frontend: Estado actual de la interfaz](https://gist.github.com/RodrigoArturoFG/d2e02b5b144f703c4534f840d82869e6)

---

## Resumen ejecutivo

Esta versión introduce cambios significativos respecto a la auditoría anterior. Se incorporaron funcionalidades nuevas importantes (panel de capas con control de vistas, tab de imágenes satelitales comparativas, tab de descarga de datos), se actualizó la fuente de datos de clasificación (de ESA WorldCover a Dynamic World) y se mejoró el mapa base por defecto (de OpenStreetMap a Esri Satellite). Sin embargo, persisten varios bugs de la versión anterior y aparecen bugs nuevos asociados a las funcionalidades recién agregadas.

---

## Nuevas funcionalidades detectadas

### 1. Panel de Capas (CAPAS) — Nuevo

Se agregó un panel flotante en el mapa accesible por un botón hamburger (☰). Contiene:

**Sección VISTA:** Tres botones para cambiar el tile base del mapa:
- **Satélite** (activo por defecto) — tiles de Esri WorldImagery. Completamente funcional.
- **Calles** — tiles de OpenStreetMap. Completamente funcional. Al activarlo, el overlay "Etiquetas de lugares" desaparece del panel (comportamiento esperado ya que OSM incluye sus propias etiquetas).
- **Topográfico** — tiles de Esri. Funcional, aunque visualmente similar a "Calles" a nivel de ciudad. No se observan diferencias de topografía evidentes en el nivel de zoom de la CDMX.

**Sección OVERLAYS:** Dos checkboxes:
- **Polígonos de alcaldías** — toggle funcional. Al desactivar, los polígonos coloreados desaparecen del mapa correctamente.
- **Etiquetas de lugares** — toggle funcional. Solo visible en vista Satélite.

**Sección PÉRDIDA DE BOSQUE → CLASE 2024:** Filtros por categoría de pérdida:
- Botones **Todas / Ninguna** — funcionan correctamente para activar/desactivar todos los marcadores.
- Checkboxes individuales por clase: Deforestado, Urbano, Pastizal, Agua, Tierra sin cobertura vegetal, Cultivo — funcionan correctamente. Cada checkbox muestra el conteo de puntos de la alcaldía activa para esa clase (ej. "Deforestado 96", "Urbano 0", etc.).
- Footer con texto contextual: "{Alcaldía} · Sentinel-2 · Dynamic World · kNN".

### 2. Marcadores de pérdida multicolor — Nuevo

Los marcadores de pérdida de bosque ahora tienen **colores diferentes según la clase de destino** (antes todos eran rojo). Cada categoría tiene un color específico (rojo para Deforestado, gris para Urbano, verde claro para Pastizal, azul para Agua, naranja para Cultivo, etc.). Esto mejora significativamente la lectura visual del mapa.

### 3. Tab "Imágenes" en ComparativaPanel — Nuevo ✅

Se agregó un tab "Imágenes" en el panel inferior que muestra dos mapas Leaflet interactivos lado a lado:
- **Sentinel-2 · 2016** (temporada lluvias jul–oct)
- **Sentinel-2 · 2024** (temporada lluvias jul–oct)

Cada mapa tiene controles de zoom propios (+/−), muestra el contorno de la alcaldía en amarillo y es interactivo (arrastra/zoom). El pie de página indica: *"Composites Sentinel-2 (Copernicus vía Google Earth Engine), temporada de lluvias jul–oct, mismos meses en ambos años."*

**Estado:** Funcionando correctamente. Los tiles de imágenes satelitales reales cargan para todas las alcaldías probadas. El tiempo de carga puede tomar unos segundos dependiendo del tamaño de la alcaldía, lo cual es normal para tiles de Google Earth Engine.

### 4. Tab "Descargar" en ComparativaPanel — Nuevo

Se agregó un tab "Descargar" que permite exportar datos de la alcaldía activa:

- **↓ Puntos de pérdida (CSV)** — enlace directo a `/cobertura/perdida.csv?alcaldia={nombre}`. Descarga los puntos crudos con columnas: `lon, lat, clase_base, clase_actual, NDVI_base, NDVI_actual`.
- **↓ Métricas (JSON)** — genera un data-URI con el JSON de comparativa. Incluye todos los campos de la API (ha por cobertura, delta_ha, delta_pct, png_url, png_comparativa_url).
- Vista previa de columnas del CSV y resumen de la descarga.

**Estado:** Funcional en estructura. Ver bug de resumen en sección de errores.

### 5. Cambio de mapa base por defecto — Nuevo

La versión anterior usaba **OpenStreetMap** como mapa base. La nueva versión usa **Esri WorldImagery (Satélite)** por defecto. Esto mejora el contexto visual al mostrar la cobertura forestal real visible desde el satélite.

### 6. Nueva categoría "Cultivo" en clasificación — Nuevo

Se agregó la categoría **Cultivo** (color salmón/melocotón) tanto en el panel CAPAS como en los datos del ComparativaPanel. En la versión anterior esta categoría no existía o no estaba visible en la UI.

---

## Bugs nuevos detectados en v2

### 🔴 Bug: Total de puntos no se renderiza en tarjeta KPI flotante

**Descripción:** La tarjeta KPI en la esquina superior derecha del mapa debería mostrar el total agregado de puntos de pérdida, pero el número no aparece. El DOM revela que la línea está compuesta por tres nodos de texto separados: `"0.1"` + `" ha · "` + `" puntos"`. El valor numérico del total (ej. `96`) no se inserta entre `" ha · "` y `" puntos"`.

**Ejemplo observado (Tlalpan):**
```
▼ 0.8% bosque
pérdida 2016->2024
0.1 ha · puntos          ← debería decir "0.1 ha · 96 puntos"
```

**Aclaración:** El conteo de puntos **sí es visible** en el panel CAPAS, pero desglosado por clase individual (ej. "Deforestado 96", "Urbano 0", etc.). Lo que falta en la tarjeta KPI es el **total agregado** de todos los puntos de pérdida de la alcaldía.

**Impacto:** El usuario no puede ver el total de puntos de pérdida de un vistazo en la tarjeta KPI; debe abrir el panel CAPAS y sumar manualmente los conteos por clase.

**Severidad:** 🟡 Media

---

### 🟡 Bug: Resumen del tab Descargar sin valores numéricos de puntos

**Descripción:** El resumen en el tab "Descargar" muestra:
```
puntos de pérdida · puntos de ganancia · delta -0.1 ha (-0.8%)
```
Los conteos de "puntos de pérdida" y "puntos de ganancia" están vacíos.

**Severidad:** 🟡 Baja-Media (estética pero genera confusión)

---

### 🟠 Inconsistencia: "ESA WorldCover" vs "Dynamic World" en la misma pantalla

**Descripción:** El sidebar del panel izquierdo muestra "Sentinel-2 · **ESA WorldCover** · kNN", mientras que el footer del panel CAPAS muestra "Sentinel-2 · **Dynamic World** · kNN". Son dos fuentes de clasificación distintas referenciadas en la misma pantalla.

**Ubicaciones del texto inconsistente:**
- Sidebar (Período de comparativa): "Sentinel-2 · ESA WorldCover · kNN"
- Footer en tarjeta de resumen: "Fuente: Sentinel-2 · ESA WorldCover · kNN"
- Footer del panel CAPAS: "{Alcaldía} · Sentinel-2 · Dynamic World · kNN"

**Impacto:** Confusión sobre qué fuente de datos se está usando realmente.

**Severidad:** 🟠 Alta (credibilidad del dato)

---

## Bugs persistentes de la versión anterior

### ✅ (RESUELTO 2026-06-16) Hectáreas de cobertura inconsistentes con la realidad territorial

**Descripción original:** Los valores de ha reportados representaban muestras kNN, no la cobertura total. Ejemplo: Tlalpan tiene 31,426 ha totales pero el total de ha en todos los campos de cobertura sumaba ~30 ha. Datos de la API para Tlalpan **antes**:
```json
{
  "ha_bosque": 8,
  "ha_deforestado": 0,
  "ha_urbano": 7.48,
  "ha_pastizal": 7.89,
  "ha_agua": 3.64,
  "ha_suelo_desnudo": 3.65,
  "total_ha": 30.66,
  "png_url": null
}
```

**Solución aplicada (Claude / Opus 4.8):** Se reemplazó la suma de muestras (cada muestra = 0.01 ha) por un **conteo wall-to-wall en Google Earth Engine**: se clasifica todo el polígono con Dynamic World (mismo remapeo que el muestreo), se cuentan todos los píxeles por clase con `frequencyHistogram` y las fracciones se escalan por el `area_ha` oficial del INEGI presente en el GeoJSON. Detalle completo, justificación y track por archivo/línea en [ha_estimation_fix.md](ha_estimation_fix.md).

> Nota de causa raíz: el escalado por proporción de muestras (parche intermedio) **no** servía porque el muestreo es estratificado con asignación igual (~800 puntos por clase), por lo que la proporción de muestras no representa el área. El wall-to-wall sí, porque evalúa cada píxel.

Datos de la API para Tlalpan **ahora** (suman el área oficial, 31,425 ha):
```json
{
  "ha_bosque": 12613.98,
  "ha_deforestado": 1811.7,
  "ha_urbano": 8918.77,
  "ha_pastizal": 7567.32,
  "ha_agua": 3.49,
  "ha_suelo_desnudo": 510.22,
  "total_ha": 31425.48,
  "png_url": null
}
```

**Validación:** el total por alcaldía coincide al 0.00% con la superficie oficial del shapefile municipal del INEGI (Marco Geoestadístico 2025) en las 16 alcaldías. También se corrigieron las etiquetas del frontend que decían "(estimadas)".

**Severidad:** 🔴 Crítica → ✅ Resuelto

---

### 🔴 (Persiste) png_url y png_comparativa_url siempre son null

**Descripción:** Confirmado en el JSON del tab Descargar: tanto `png_url` (en los objetos base y actual) como `png_comparativa_url` siguen siendo null para todas las alcaldías.

**Severidad:** 🔴 Alta (funcionalidad sin implementar)

---

### 🟡 (Persiste) Reset del dropdown no limpia la vista

**Descripción:** Al seleccionar la opción vacía ("— elige una alcaldía —") del dropdown, la UI no regresa al estado inicial. El dropdown vuelve a mostrar la última alcaldía seleccionada, el mapa permanece en esa vista y los paneles siguen mostrando datos.

**Pasos para reproducir:**
1. Seleccionar "Milpa Alta" en el dropdown
2. Seleccionar "— elige una alcaldía —"
3. Observar que la UI no cambia

**Severidad:** 🟡 Media

---

### 🟡 (Persiste) Zoom automático inconsistente al seleccionar alcaldías

**Descripción:** Al seleccionar una alcaldía por dropdown, el mapa no hace zoom al polígono de esa alcaldía de manera consistente. Se observaron dos comportamientos:

- Al seleccionar **Iztacalco** (2,308 ha): inicialmente hace zoom out a toda la CDMX, luego al hacer scroll la vista se estabiliza en el polígono correcto.
- Al seleccionar **Tlalpan** (31,426 ha): muestra toda la CDMX sin centrar en Tlalpan.
- Al seleccionar **Milpa Alta**: hace zoom correcto al polígono.

El comportamiento del zoom es inconsistente entre alcaldías.

**Severidad:** 🟡 Media

---

### 🟡 (Persiste) Discrepancia entre ha en dropdown y tooltip del mapa

**Descripción:** El dropdown muestra "Tlalpan (31,426 ha)" pero el tooltip del polígono en el mapa muestra "Tlalpan / 31,425 ha" (diferencia de 1 ha).

**Severidad:** 🟢 Baja

---

### 🟡 (Persiste) Leyenda lateral muestra solo 8 de 16 alcaldías

**Descripción:** La leyenda del sidebar sigue mostrando solo las primeras 8 alcaldías. El texto "+8 más en el mapa" no es interactivo.

**Severidad:** 🟡 Baja-Media

---

### 🟡 (Persiste) Slider del período parece interactivo pero no lo es

**Descripción:** El control "2016 ——— 2024" tiene apariencia de range input pero no tiene funcionalidad.

**Severidad:** 🟢 Baja

---

## Comportamientos resueltos o mejorados

| Aspecto | v1 (anterior) | v2 (actual) |
|---------|--------------|------------|
| Mapa base por defecto | OpenStreetMap (calles) | Esri Satellite ✅ |
| Selección de vista del mapa | No existía | Panel CAPAS con 3 opciones ✅ |
| Toggle de overlays | No existía | Polígonos y etiquetas toggleables ✅ |
| Filtro de marcadores por clase | No existía | Checkboxes por categoría con conteo ✅ |
| Color de marcadores | Todos rojo | Multicolor por clase ✅ |
| Exportación de datos | No existía | CSV + JSON descargables ✅ |
| Comparativa satelital Sentinel-2 | No existía | Mapas Leaflet duales interactivos ✅ |
| Categoría "Cultivo" | No visible | Incluida en UI ✅ |
| Hectáreas de cobertura | Suma de muestras (~30 ha en Tlalpan) | Conteo wall-to-wall escalado al área oficial INEGI (= 31,425 ha) ✅ |
| Unidades en UI | "ha" ambiguo / "(estimadas)" | Coherentes con el área real; etiqueta wall-to-wall ✅ |

---

## Datos observados en esta auditoría

Valores observados durante la auditoría del **2026-06-10** (método de muestras, ya obsoleto):

| Alcaldía | Bosque 2016 | Bosque 2024 | Δ% | Puntos (CAPAS) |
|----------|------------|------------|-----|----------------|
| Tlalpan | 8 ha | 7.9 ha | ▼ 0.8% | 96 pts (Deforestado) |
| Milpa Alta | 6.7 ha | 7.6 ha | ▲ 13.7% | Multicolor visible |
| Iztacalco | 4 ha | 3 ha | ▼ 24.4% | Multicolor visible |
| Miguel Hidalgo | 8.3 ha | 7.2 ha | ▼ 13.8% | Multicolor visible |

Valores **tras la corrección wall-to-wall (2026-06-16)** — bosque en hectáreas reales:

| Alcaldía | Bosque 2016 | Bosque 2024 | Δ% |
|----------|------------|------------|-----|
| Tlalpan | 13,005.8 ha | 12,614.0 ha | ▼ 3.0% |
| Milpa Alta | 9,645.0 ha | 11,633.9 ha | ▲ 20.6% |
| Iztacalco | 10.7 ha | 2.9 ha | ▼ 72.7% |
| Miguel Hidalgo | 524.0 ha | 367.3 ha | ▼ 29.9% |

> Los conteos de puntos (panel CAPAS) no cambian: siguen siendo muestras que marcan *dónde* ocurre el cambio, no área.

---

## Estado general actualizado

| Aspecto | Estado |
|---------|--------|
| Funcionalidad core (selección + datos) | ✅ Funcionando |
| Interacción mapa (clic en polígonos) | ✅ Funcionando |
| Popups en puntos de pérdida | ✅ Funcionando |
| Datos numéricos en paneles | ✅ Funcionando |
| Panel CAPAS (Capas/Overlays/Filtros) | ✅ Nuevo — Funcionando |
| Marcadores multicolor por clase | ✅ Nuevo — Funcionando |
| Tab Descargar (CSV + JSON) | ✅ Nuevo — Funcionando (con bug de resumen) |
| Tab Imágenes (Sentinel-2 comparativo) | ✅ Nuevo — Funcionando |
| Total de puntos en tarjeta KPI | 🐛 Bug nuevo — Valor no renderizado |
| Reset de selección dropdown | ⚠️ Persiste sin corregir |
| Zoom automático al seleccionar | ⚠️ Persiste sin corregir |
| Consistencia de fuente de datos en UI | ⚠️ Nueva inconsistencia ("ESA WorldCover" vs "Dynamic World") |
| png_url (imágenes satelitales API) | ❌ Persiste null |
| Hectáreas de cobertura reales | ✅ Resuelto (wall-to-wall = área oficial INEGI, 2026-06-16) |
| Claridad de unidades (ha reales vs muestras) | ✅ Resuelto — ha reales; etiquetas "(estimadas)" eliminadas |
| Estado de carga/error explícito | ⚠️ Persiste ausente |
| Leyenda completa de 16 alcaldías | ⚠️ Persiste — Solo muestra 8 |

---

## Cosas por agregar / Mejoras futuras

### Estimador de área de Olofsson (ajuste por exactitud de la clasificación)

El conteo wall-to-wall ya da el total exacto por alcaldía (= área oficial INEGI), pero el **reparto
entre clases** (bosque/urbano/pastizal/etc.) depende de la exactitud de la clasificación Dynamic
World, que no está validada. La mejora recomendada es aplicar el **estimador de Olofsson**
(*Olofsson et al., 2014, "Good practices for estimating area and assessing accuracy of land change",
Remote Sensing of Environment 148:42-57*):

- Construir una **matriz de confusión** con puntos de referencia (foto-interpretación o muestreo de
  validación independiente del de entrenamiento).
- Ajustar el área de cada clase con el **estimador estratificado** y reportar su **intervalo de
  confianza**, en lugar del conteo crudo de píxeles.

**Beneficio:** áreas por clase insesgadas y con margen de error declarado, no solo el conteo directo
del mapa. **Costo:** requiere un set de puntos de referencia y trabajo de validación.

> Queda como pendiente; no bloquea el uso actual, ya que el total por alcaldía sí es exacto y el
> reparto por clase es indicativo. Contexto en [ha_estimation_fix.md](ha_estimation_fix.md)
> (sección "Limitaciones que persisten").

---

## Stack tecnológico (actualizado)

| Tecnología | Uso |
|-----------|-----|
| React 18.x | Framework UI |
| Vite 5.4.x | Dev server + bundler + proxy |
| react-leaflet v4 | Mapa interactivo + mapas de imágenes duales |
| Leaflet 1.9.x | Motor de mapas |
| Recharts | Gráficas de barras en ResultadosCard |
| Esri WorldImagery | Tiles satélite (nuevo, reemplaza OSM por defecto) |
| OpenStreetMap | Tiles calles (opción secundaria) |
| Esri Topographic | Tiles topográficos (opción terciaria) |
| Google Earth Engine | Fuente de composites Sentinel-2 para tab Imágenes |

**Endpoints consumidos (confirmados):**
- `GET /alcaldias/` — GeoJSON de polígonos
- `GET /alcaldias/lista` — Lista para dropdown
- `GET /cobertura/comparativa?alcaldia={nombre}` — Datos de cobertura
- `GET /cobertura/perdida?alcaldia={nombre}` — Puntos de pérdida (JSON)
- `GET /cobertura/perdida.csv?alcaldia={nombre}` — Puntos de pérdida (CSV, nuevo)

---

*Documento generado por auditoría interactiva — CDMX Verde v2 — 2026-06-10*
