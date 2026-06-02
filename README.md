# CDMX Verde — Sistema de comparativa de cobertura vegetal

Visualiza la pérdida de áreas verdes en las 16 alcaldías de la CDMX
comparando imágenes Sentinel-2 de **2016 vs 2024**, clasificadas con
Dynamic World y un clasificador kNN.

---

## Estructura del proyecto

```
cdmx-verde/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # Pydantic schemas
│   ├── pipeline.py          # Orquestador de scripts
│   └── routers/
│       ├── alcaldias.py     # GET /alcaldias
│       ├── cobertura.py     # GET /cobertura · POST /cobertura/procesar
│       └── jobs.py          # GET /job/{id}/status
├── scripts/
│   ├── 01_alcaldias_inegi.py
│   ├── 02_muestras_gee.py   # Descarga Sentinel-2 via GEE (Dynamic World)
│   ├── 03_fusion_validacion.py  # Cruza 2016 vs 2024 y detecta cambios
│   └── 99_demo_final.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   │       ├── MapaAlcaldias.jsx      # Mapa Leaflet con puntos rojos
│   │       ├── PanelControl.jsx
│   │       ├── ComparativaPanel.jsx
│   │       └── ResultadosCard.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   ├── alcaldias/
│   │   └── alcaldias_cdmx.geojson
│   ├── training/            # CSVs de muestras GEE (versionado)
│   └── raw/                 # Datos crudos INEGI (NO versionado, ver .gitignore)
├── cache/                   # JSONs pre-calculados por alcaldia
├── precargar.py             # Pre-procesa todas las alcaldias de una vez
├── .env.example             # Plantilla de variables (SI versionado)
├── .env                     # Tu config local: GEE_PROJECT (NO versionado)
├── .gitignore
└── requirements.txt
```

---

## Instalación

### 1. Requisitos previos

- Python 3.11 o superior
- Node.js 18 o superior
- Cuenta gratuita en https://earthengine.google.com
- Proyecto en Google Cloud con la API de Earth Engine habilitada

### 2. Clonar y preparar el entorno

```powershell
# Crear entorno virtual
python -m venv .venv

# Activar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activar (macOS / Linux)
source .venv/bin/activate

# Instalar dependencias Python
pip install -r requirements.txt
```

### 3. Configurar tu proyecto de Google Earth Engine (`.env`)

El ID del proyecto de GEE **no está en el código**: cada persona usa el suyo y
se lee de un archivo `.env` en la raíz. Este archivo es personal y **no se
versiona** (está en `.gitignore`), así que **debes crearlo tú** a partir de la
plantilla `.env.example` (esa sí versionada):

```powershell
# Copia la plantilla (Windows)
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Luego abre `.env` y reemplaza el valor con el **Project ID** de tu proyecto de
Google Cloud / Earth Engine (el identificador en minúsculas, no el nombre para
mostrar):

```
GEE_PROJECT=mi-proyecto-123456
```

> El valor va **sin comillas** y sin espacios alrededor del `=`. Si la variable
> `GEE_PROJECT` no está definida, los scripts (`precargar.py`, `02_muestras_gee.py`)
> y el backend **abortan con un error claro** en vez de usar un proyecto ajeno.

### 4. Autenticar Google Earth Engine

Solo se hace una vez:

```powershell
earthengine authenticate
```

Se abre el navegador, inicia sesión con tu cuenta de Google y autoriza el acceso.

---

## Cómo correrlo

### Paso 1 — Pre-cargar todas las alcaldías (recomendado)

Antes de abrir el frontend, pre-procesa todas las alcaldías para que
carguen instantáneamente sin esperar el pipeline:

> Antes de este paso debes tener tu `.env` creado (ver
> *Instalación · paso 3*). El `project_id` de GEE se lee de ahí; si falta,
> el script aborta con un error claro.

```powershell
# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Pre-cargar las 16 alcaldías (tarda ~1 hora en total)
python precargar.py
```

Si ya tienes los CSVs descargados y solo quieres regenerar el caché:

```powershell
python precargar.py --solo-cache
```

Para pre-cargar solo una alcaldía específica:

```powershell
python precargar.py --alcaldia "Tlalpan"
```

### Paso 2 — Levantar el backend

En una terminal (con el entorno virtual activo):

```powershell
.\.venv\Scripts\Activate.ps1
# El proyecto GEE se toma del archivo .env (ver Paso 1)
uvicorn backend.main:app --reload --port 8000
```

El backend queda en: http://localhost:8000
Documentación interactiva: http://localhost:8000/docs

### Paso 3 — Levantar el frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

El frontend queda en: http://localhost:5173

### Paso 4 — Usar el sistema

1. Abre http://localhost:5173
2. Haz clic en una alcaldía en el mapa o selecciónala del dropdown
3. Si ya fue pre-cargada → carga instantáneamente
4. Si no fue pre-cargada → el pipeline corre automáticamente (3-5 min)
5. Verás en el mapa los **círculos rojos** donde hubo pérdida de bosque
6. El panel lateral muestra hectáreas de bosque 2016 vs 2024 y el delta

---

## Correr los scripts manualmente

Si quieres procesar una alcaldía paso a paso desde la terminal:

```powershell
# Descargar muestras 2016
python scripts/02_muestras_gee.py --alcaldia "Tlalpan" --anio 2016

# Descargar muestras 2024
python scripts/02_muestras_gee.py --alcaldia "Tlalpan" --anio 2024

# Cruzar ambos años y detectar cambios
python scripts/03_fusion_validacion.py --alcaldia "Tlalpan" --anio-base 2016 --anio-actual 2024
```

---

## Endpoints del API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/alcaldias/` | GeoJSON de las 16 alcaldías |
| GET | `/alcaldias/lista` | Lista con nombre y área |
| GET | `/cobertura/comparativa?alcaldia=` | Comparativa 2016 vs 2024 |
| GET | `/cobertura/perdida?alcaldia=` | Puntos de pérdida de bosque |
| POST | `/cobertura/procesar?alcaldia=` | Lanza el pipeline en background |
| GET | `/job/{job_id}/status` | Estado del job |

---

## Fuentes de datos

| Fuente | Uso |
|--------|-----|
| INEGI Marco Geoestadístico 2025 | Polígonos de las 16 alcaldías |
| Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED) | Imágenes satelitales multiespectrales |
| Google Dynamic World V1 | Clasificación de cobertura del suelo 2016 y 2024 |
| EPSG:4326 + EPSG:32614 (UTM zona 14N) | Sistemas de referencia utilizados |

Dynamic World se usa para **ambos años** (2016 y 2024) para garantizar
comparabilidad real. Usar fuentes distintas generaría diferencias
artificiales que no reflejan cambio real.

### Datos crudos de INEGI (no versionados)

La carpeta `data/raw/` **no está en git** (pesa ~388 MB e incluye archivos que
superan el límite de 100 MB de GitHub). **No hace falta para desplegar**: el
geojson ya generado (`data/alcaldias/alcaldias_cdmx.geojson`) sí está versionado
y es lo único que consumen el backend y los scripts `02`, `03` y `99`.

Solo necesitas el raw si quieres **regenerar el geojson** o **extenderlo a otros
estados/municipios**. En ese caso:

1. Descarga el **Marco Geoestadístico Nacional** de INEGI:
   https://www.inegi.org.mx/temas/mg/
2. Descomprime el paquete dentro de `data/raw/inegi/`. El script
   [`01_alcaldias_inegi.py`](scripts/01_alcaldias_inegi.py) busca el shapefile de
   municipios en estas rutas (la primera que exista):
   - `data/raw/inegi/09_ciudaddemexico/conjunto_de_datos/09mun.shp`
   - `data/raw/inegi/09mun.shp`
   - `data/raw/inegi/00mun.shp`
   - `data/raw/inegi/mg2024_integrado/conjunto_de_datos/00mun.shp`

   > Solo se usa la capa de **municipios** (`*mun.shp` + sus archivos hermanos
   > `.shx`, `.dbf`, `.prj`). Las demás capas del paquete (frentes de manzana,
   > ejes de vialidad, etc.) no las usa el código; puedes omitirlas.

3. Genera los archivos de alcaldías:
   ```powershell
   python scripts/01_alcaldias_inegi.py
   ```
   Esto produce `alcaldias_cdmx.geojson`, `alcaldias_cdmx.shp` y
   `alcaldias_cdmx_utm14n.shp` en `data/alcaldias/`.

**Para otros estados:** el script filtra la CDMX con la clave de entidad
`CVE_ENT == "09"`. Cambia esa constante (`CVE_CDMX`) en
[`01_alcaldias_inegi.py`](scripts/01_alcaldias_inegi.py) por la clave del estado
que quieras (p. ej. `"15"` para el Estado de México) usando el archivo nacional
`00mun.shp`.

---

## Dependencias con otros roles del proyecto

| Rol | Lo que consume |
|-----|---------------|
| Rol 4 (kNN) | `data/training/training_samples_{slug}.csv` |
| Rol 8 (GIS) | `data/alcaldias/alcaldias_cdmx.geojson` |
| Rol 2 (Sentinel-2) | Comparte CRS EPSG:32614 (UTM zona 14N) |

---

## Notas

- Los CSVs de muestras en `data/training/` persisten en disco.
  Una vez descargados no se vuelven a bajar de GEE.
- El caché en `cache/` se puede regenerar en segundos con
  `python precargar.py --solo-cache` sin llamar a GEE.
- Las alcaldías con más suelo de conservación (Tlalpan, Milpa Alta,
  Xochimilco) son las más interesantes para la comparativa.
