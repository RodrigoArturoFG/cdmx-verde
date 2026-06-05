# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CDMX Verde** is a full-stack geospatial application that visualizes vegetation coverage loss across Mexico City's 16 boroughs by comparing Sentinel-2 satellite imagery from 2016 vs 2024. It uses Google Earth Engine (GEE) for data processing, a FastAPI backend, and a React/Vite frontend.

## Development Commands

### Backend
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Dev server on :5173 (proxies /alcaldias, /cobertura, /job, /cache to :8000)
npm run build
npm run preview
```

### Data Preprocessing
```bash
python precargar.py                     # All 16 boroughs via GEE (~1 hour)
python precargar.py --solo-cache        # Regenerate cache/ from existing CSVs (~10s)
python precargar.py --alcaldia "Tlalpan"  # Single borough

# Individual pipeline steps
python scripts/02_muestras_gee.py --alcaldia "Tlalpan" --anio 2016
python scripts/03_fusion_validacion.py --alcaldia "Tlalpan" --anio-base 2016 --anio-actual 2024
```

## Environment Setup

Copy `.env.example` to `.env` and set your GEE project ID:
```
GEE_PROJECT=tu-proyecto-gee-id
```

GEE authentication is OAuth-based (one-time): `earthengine authenticate`

## Architecture

### Data Flow
```
GEE (Dynamic World v1) → scripts/02_muestras_gee.py → data/training/muestras_{slug}_{anio}.csv
                       → scripts/03_fusion_validacion.py → data/training/metricas_{slug}_2016vs2024.json
                                                         → data/training/perdida_{slug}_2016vs2024.csv
                       → precargar.py / backend pipeline → cache/comparativa_{slug}.json
                       → FastAPI backend → React frontend
```

### Backend (`backend/`)
- **main.py** — FastAPI app; CORS allows `localhost:5173`; mounts static `/cache` directory
- **routers/alcaldias.py** — `GET /alcaldias/` (full GeoJSON), `GET /alcaldias/lista`
- **routers/cobertura.py** — `GET /cobertura/comparativa?alcaldia=`, `GET /cobertura/perdida?alcaldia=`, `POST /cobertura/procesar?alcaldia=` (launches background pipeline)
- **routers/jobs.py** — `GET /job/{job_id}/status` (poll pipeline state)
- **pipeline.py** — Orchestrates the two Python scripts as subprocesses; reads/writes `cache/` JSON
- **models.py** — Pydantic schemas: `ComparativaResult`, `CoberturaResult`, `JobStatus`

### Frontend (`frontend/src/`)
- **App.jsx** — Root state: selected borough, comparativa data, loss points, job polling
- **api.js** — All HTTP calls; `lanzarPipeline()` + `pollJob()` poll every 3s until `done|error`
- **components/MapaAlcaldias.jsx** — Leaflet map with borough polygons, red loss-point markers, floating KPI overlay
- **components/PanelControl.jsx** — Borough `<select>` + legend
- **components/ResultadosCard.jsx** — 2×2 KPI grid + Recharts bar chart
- **components/ComparativaPanel.jsx** — Side-by-side 2016 vs 2024 coverage breakdown

### Scripts (`scripts/`)
- **02_muestras_gee.py** — Downloads 800 sample points/class/year from GEE Dynamic World v1; outputs CSV
- **03_fusion_validacion.py** — Spatial cross-join via KDTree; detects coverage changes; outputs metrics JSON + loss CSV
- **01_alcaldias_inegi.py** — One-time GeoJSON generation from INEGI shapefile (raw data not versioned)

### Versioned Data
- `data/alcaldias/` — Borough polygons (GeoJSON + shapefiles, EPSG:4326)
- `data/training/` — Training CSVs and metrics JSON (kept to avoid re-running GEE)
- `cache/` — Pre-computed `comparativa_{slug}.json` served directly to frontend

`data/raw/` (~388 MB INEGI source files) is **not versioned**.

## Key Implementation Details

- **Slug normalization:** Used consistently across scripts, backend, and cache filenames to handle accents/spaces in borough names
- **Background jobs:** FastAPI `BackgroundTasks` + frontend polling every 3s; job state held in-memory (not persistent across restarts)
- **Cache-first strategy:** Backend checks `cache/comparativa_{slug}.json` before launching the pipeline
- **Hectare values:** Sample-based estimates, not full polygon area calculations
- **`png_url` field:** Exists in Pydantic schema but always returns `null` — satellite image generation is not implemented
- **Vite proxy:** All frontend API calls use a relative base URL; proxy routes to `localhost:8000`
