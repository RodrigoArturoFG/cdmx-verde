# CDMX Verde — Frontend: Estado actual de la interfaz

> Documento de auditoría técnica generado mediante navegación interactiva completa
> de las 16 alcaldías y todos los componentes de la UI.

---

## Descripción general

La aplicación es una SPA (Single Page Application) construida con **React + Vite**
que utiliza **Leaflet** para el mapa interactivo y **Recharts** para las gráficas de
barras. El frontend consume una API REST proxeada a través del servidor de Vite
(no se llama directamente a `localhost:8000`, sino que Vite actúa como proxy).

La pantalla está dividida en dos regiones principales:
- **Panel izquierdo (sidebar)** — Controles de selección, leyenda y tarjeta de resumen.
- **Panel derecho (main)** — Mapa Leaflet (superior) + Panel de comparativa (inferior).

---

## Componentes identificados

### 1. Header (`App.jsx`)
- Barra superior verde oscuro con el título **"CDMX Verde"** y el subtítulo
  *"Comparativa de cobertura vegetal 2016 vs 2024"*.
- Diseño simple y limpio. No tiene navegación adicional ni menú.

### 2. `PanelControl.jsx` (sidebar izquierdo)
Contiene los siguientes sub-elementos:

**Selector de alcaldía:**
- Dropdown `<select>` con las 16 alcaldías de la CDMX, cada opción muestra
  el nombre y su superficie en hectáreas (ej. `"Tlalpan (31,426 ha)"`).
- Texto auxiliar: *"O haz clic directamente en el mapa"*.
- La alcaldía seleccionada queda resaltada en verde en la leyenda lateral.

**Período de comparativa:**
- Indicador estático de rango temporal: `2016 ———— 2024`.
- Subtexto: *"Sentinel-2 · ESA WorldCover · kNN"*.
- El elemento visualmente parece un slider pero **no es interactivo** —
  solo muestra el rango fijo del proyecto.

**Leyenda — alcaldías:**
- Muestra las primeras 8 alcaldías con su color de polígono en el mapa.
- Texto al final: *"+8 más en el mapa"* (no es clicable, solo informativo).

**`ResultadosCard.jsx`** (aparece al seleccionar una alcaldía):
- Tarjeta de resumen con 4 métricas en grid 2×2:
  - **Bosque 2016** — Hectáreas de bosque en año base (redondeadas a entero).
  - **Bosque 2024** — Hectáreas de bosque en año actual (redondeadas a entero).
  - **Cambio** — Delta en ha (negativo = pérdida, positivo = ganancia), en rojo.
  - **Variación** — Delta porcentual, en rojo.
- Sección *"Principales coberturas (ha)"*: mini gráfica de barras agrupadas
  (2016 vs 2024) para las 3 coberturas principales (Bosque, Urbano, Pastizal).
  Renderizada con Recharts.
- Pie de tarjeta: *"Fuente: Sentinel-2 · ESA WorldCover · kNN"*.

### 3. `MapaAlcaldias.jsx` (mapa Leaflet)
- **Tiles base:** OpenStreetMap (sin capa satelital activa).
- **Polígonos de alcaldías:** Cargados desde `GET /alcaldias/` — GeoJSON con
  relleno semitransparente y color único por alcaldía.
- **Tooltip de polígonos:** Al hacer hover o clic sobre un polígono aparece
  un tooltip con el nombre y área en ha (ej. `"Milpa Alta / 28,885 ha"`).
- **Marcadores rojos (círculos):** Puntos de pérdida de bosque cargados desde
  `GET /cobertura/perdida?alcaldia=`. Al hacer clic en un círculo se muestra
  un popup con:
  - Título: *"Perdida de bosque"*
  - `2016: bosque`
  - `2024: deforestado`
  - `NDVI 2016: 0.XX`
  - `NDVI 2024: 0.XX`
- **Leyenda flotante (mapa):** Caja en la esquina inferior izquierda del mapa con
  los colores de cobertura (Bosque, Deforestado, Pastizal, Urbano, Agua,
  Suelo desnudo) y el total de puntos de pérdida.
- **Tarjeta KPI flotante (mapa):** Esquina superior derecha del mapa, muestra
  el resumen de pérdida/ganancia: `▼ X.X% bosque / perdida 2016→2024 / Y.Y ha · puntos`.
  En verde cuando es ganancia (▲), en rojo cuando es pérdida (▼).
- **Controles de zoom:** Botones `+` y `−` estándar de Leaflet.
- **Créditos:** *"Leaflet | © OpenStreetMap contributors"*.

### 4. `ComparativaPanel.jsx` (debajo del mapa)
- Encabezado: `"[Alcaldía] — comparativa satelital"` + badge del porcentaje de cambio.
- Dos columnas: **Referencia 2016** y **Actual 2024**.
- Por cada categoría de cobertura (Bosque, Deforestado, Pastizal, Urbano,
  Agua, Tierra sin cobertura vegetal): indicador de color + barra de progreso
  proporcional + valor en ha con un decimal.

---

## Flujo de interacción (navegación completa)

### Selección por dropdown
Al elegir una alcaldía del selector:
1. El mapa hace zoom automático y centra la vista en el polígono de la alcaldía.
2. Se renderiza la leyenda de cobertura sobre el mapa (esquina inferior izquierda).
3. Aparece la tarjeta KPI (esquina superior derecha del mapa).
4. El sidebar muestra la `ResultadosCard` con métricas de resumen.
5. Debajo del mapa aparece el `ComparativaPanel` con el detalle por cobertura.
6. El nombre de la alcaldía en la leyenda lateral queda resaltado.

### Selección por clic en el mapa
- Funciona correctamente: al hacer clic sobre un polígono, se selecciona la
  alcaldía y se actualizan todos los paneles, igual que al usar el dropdown.
- El dropdown también se actualiza para reflejar la alcaldía seleccionada vía mapa.

### Clic en marcadores rojos
- Los círculos rojos (puntos de pérdida) muestran un popup con datos
  detallados del punto: clasificación 2016/2024 y valores de NDVI.

---

## Datos observados — resumen por alcaldía

| Alcaldía | Bosque 2016 | Bosque 2024 | Δ% | Puntos pérdida |
|---|---|---|---|---|
| Tlalpan | 8 ha | 8 ha | ▼ 0.8% | 96 pts |
| Milpa Alta | 7 ha | 8 ha | ▲ 13.7% | 55 pts |
| Xochimilco | 7 ha | 7 ha | ▼ 3.0% | 105 pts |
| Cuauhtémoc | 8 ha | 8 ha | ▼ 0.3% | 3 pts |
| Benito Juárez | 8 ha | 8 ha | ▼ 0.1% | 1 pt |
| Iztapalapa | 7 ha | 7 ha | ▲ 3.5% | 127 pts |
| Gustavo A. Madero | 4 ha | 7 ha | ▲ 59.0% | 29 pts |
| Venustiano Carranza | 8 ha | 8 ha | ▲ 0.1% | 78 pts |
| Coyoacán | 6 ha | 8 ha | ▲ 23.0% | 117 pts |
| La Magdalena Contreras | 8 ha | 8 ha | ▼ 2.3% | 43 pts |
| Álvaro Obregón | 8 ha | 8 ha | ▼ 1.7% | 61 pts |
| Tláhuac | 5 ha | 6 ha | ▲ 14.8% | 3 pts |
| Iztacalco | 4 ha | 3 ha | ▼ 24.4% | 129 pts |
| Azcapotzalco | 9 ha | 8 ha | ▼ 15.5% | 158 pts |
| Cuajimalpa de Morelos | 9 ha | 8 ha | ▼ 9.8% | 123 pts |
| Miguel Hidalgo | 8 ha | 7 ha | ▼ 13.8% | 169 pts |

---

## Errores y problemas detectados

### 🔴 Error crítico: Hectáreas de cobertura inconsistentes con la realidad
**Descripción:** Los valores de ha reportados en el panel (ej. `8 ha` de bosque para Tlalpan)
son estadísticas de **muestras de entrenamiento kNN**, no la cobertura total real de
la alcaldía. Tlalpan tiene 31,426 ha totales, y la suma de todas sus coberturas en la
API solo da **30.66 ha** en total. Esto significa que los datos representan ~30 puntos
de muestra, no el territorio completo.

**Impacto:** Un usuario interpretará "8 ha de bosque" como el total real, cuando en
realidad es el área representada por las muestras. Esto puede causar confusión grave.

**Evidencia API:**
```json
{
  "ha_bosque": 8,
  "ha_pastizal": 7.89,
  "ha_urbano": 7.48,
  "total_ha": 30.66
}
```

### 🔴 Error: `png_url` siempre es `null`
**Descripción:** El campo `png_url` en la respuesta de `/cobertura/comparativa`
retorna `null` para todas las alcaldías. Existe un placeholder en el diseño para
mostrar imágenes satelitales de comparación, pero nunca se renderiza.
El componente `ComparativaPanel` maneja el `null` sin errores pero la funcionalidad
de visualización de imágenes satelitales está completamente inactiva.

### 🟡 Problema: Reset del dropdown no limpia la vista
**Descripción:** Al usar `form_input` para deseleccionar la opción del dropdown
(valor vacío), el mapa y los paneles no se limpian — permanece la última alcaldía
visible. El comportamiento esperado sería volver al estado inicial con la vista
general de CDMX y sin datos en el panel.

### 🟡 Problema: El período de comparativa parece un slider interactivo pero no lo es
**Descripción:** El elemento visual `2016 ——— 2024` tiene apariencia de slider/range
input, lo que puede llevar al usuario a intentar arrastrarlo. No tiene funcionalidad
interactiva, solo es decorativo. Falta un estado de cursor o indicador que deje claro
que es estático.

### 🟡 Problema: Zoom del mapa no se reajusta al regresar al estado inicial
**Descripción:** Al hacer scroll en el panel lateral con una alcaldía seleccionada
y luego regresar al scroll inicial, el mapa puede quedar fuera de la vista centrada
de CDMX (se ha observado que el mapa queda muy alejado). El zoom no es persistente
al cambiar de alcaldía en ciertos estados de scroll.

### 🟡 Problema: Marcadores de otras alcaldías visibles en el mapa
**Descripción:** Al seleccionar una alcaldía, los triángulos/marcadores naranjas de
otras alcaldías vecinas (datos de pérdida previamente cargados) pueden permanecer
visibles en el mapa fuera del polígono activo. Esto genera confusión visual al no
quedar claro si pertenecen a la alcaldía seleccionada o no.

### 🟡 Problema: Leyenda muestra solo 8 de 16 alcaldías
**Descripción:** La leyenda lateral muestra solo las primeras 8 alcaldías en el DOM
y el texto *"+8 más en el mapa"* no es clicable ni expandible. El usuario no puede
ver los colores del resto de alcaldías sin interactuar con el mapa.

### 🟢 Sin errores de consola
No se detectaron errores JavaScript en la consola del navegador durante toda la
sesión de navegación. La app es estable en ese sentido.

---

## Áreas de mejora sugeridas

### Datos y claridad
- **Aclarar las unidades:** Agregar una nota o tooltip que explique que los valores
  en ha representan el área de las muestras de clasificación kNN, no la cobertura
  total de la alcaldía. O bien, escalar los datos al territorio completo.
- **Porcentaje de cambio vs absolutos:** Para alcaldías densamente urbanas como
  Benito Juárez (▼ 0.1%) y Cuauhtémoc (▼ 0.3%), los datos son casi irrelevantes
  en términos de bosque real. Considerar mostrar un estado "Sin cobertura forestal
  significativa" para estas alcaldías en lugar de datos casi idénticos.

### UX / Interfaz
- **Hacer la leyenda completa o expandible:** Mostrar las 16 alcaldías o agregar
  un botón "Ver todas" que expanda la leyenda.
- **Clarificar el control de período:** Cambiar el slider decorativo por un simple
  texto o un badge que indique el rango, evitando confusión de interactividad.
- **Estado inicial vacío explícito:** Al cargar la app sin alcaldía seleccionada,
  el panel inferior y el sidebar deberían mostrar un estado de bienvenida/instrucción
  en lugar de simplemente no mostrar nada.
- **Botón "Ver toda la CDMX":** Agregar un control para hacer zoom out y ver todas
  las alcaldías a la vez con sus datos de pérdida/ganancia representados por color
  (tipo heatmap) sin necesitar seleccionar una por una.

### Mapa
- **Filtrar marcadores por alcaldía activa:** Solo mostrar los puntos de pérdida
  de la alcaldía actualmente seleccionada; limpiar los de sesiones anteriores.
- **Capa satelital como opción de base:** Ofrecer un toggle entre mapa de calles
  (OSM actual) y mapa satelital (ej. Esri WorldImagery o MapBox) para dar más
  contexto visual a los polígonos de bosque.
- **Auto-fit al seleccionar:** Cuando se selecciona una alcaldía muy pequeña como
  Iztacalco (2,308 ha) o muy grande como Milpa Alta (28,885 ha), el nivel de zoom
  debería ajustarse automáticamente al bounding box del polígono.

### Técnico
- **Activar `png_url`:** Implementar o conectar la generación de imágenes
  satelitales de comparación para poblar el campo `png_url` que actualmente
  siempre retorna `null`.
- **Cache de datos en frontend:** Al navegar entre alcaldías, la app hace una
  nueva petición a la API cada vez. Agregar un cache en memoria (ej. con `useMemo`
  o `react-query`) para no re-fetcher datos ya obtenidos.
- **Manejo de estado de carga:** No se observó ningún spinner o skeleton loader
  durante las peticiones. Si el pipeline no está precargado y tarda 3-5 min,
  la experiencia sería confusa sin indicador de progreso.

---

## Stack tecnológico del frontend (confirmado)

| Tecnología | Versión confirmada | Uso |
|---|---|---|
| React | 18.x | Framework UI |
| Vite | 5.4.21 | Dev server + bundler + proxy |
| react-leaflet | v4 | Mapa interactivo |
| Leaflet | 1.9.4 | Motor de mapas |
| Recharts | (detectada) | Gráficas de barras en ResultadosCard |

**Endpoints consumidos:**
- `GET /alcaldias/` — GeoJSON de polígonos (cargado al inicio)
- `GET /alcaldias/lista` — Lista de alcaldías para el dropdown (cargado al inicio)
- `GET /cobertura/comparativa?alcaldia={nombre}` — Datos de cobertura 2016 vs 2024
- `GET /cobertura/perdida?alcaldia={nombre}` — Puntos de pérdida de bosque

---

## Estado general

| Aspecto | Estado |
|---|---|
| Funcionalidad core (selección + datos) | ✅ Funcionando |
| Interacción mapa (clic en polígonos) | ✅ Funcionando |
| Popups en puntos de pérdida | ✅ Funcionando |
| Datos numéricos en paneles | ✅ Funcionando |
| Sincronía dropdown ↔ mapa | ✅ Funcionando |
| Imágenes satelitales de comparativa | ❌ No implementado (`png_url` = null) |
| Claridad de unidades (ha reales vs muestras) | ⚠️ Confuso |
| Estado de carga/error explícito | ⚠️ Ausente |
| Leyenda completa de 16 alcaldías | ⚠️ Solo muestra 8 |
| Reset de selección | ⚠️ No limpia la vista |