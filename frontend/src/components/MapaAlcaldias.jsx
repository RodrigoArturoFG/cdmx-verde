import { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const BASEMAPS = {
  satelite: {
    label: 'Satélite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics',
  },
  calles: {
    label: 'Calles',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
  },
  topo: {
    label: 'Topográfico',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
  },
}

function FlyTo({ geojson, seleccionada }) {
  const map = useMap()
  useEffect(() => {
    if (!geojson || !seleccionada) return
    const feature = geojson.features.find(f => f.properties.alcaldia === seleccionada)
    if (!feature) return
    import('leaflet').then(({ default: L }) => {
      map.flyToBounds(L.geoJSON(feature).getBounds(), { duration: 0.8, padding: [40, 40] })
    })
  }, [seleccionada])
  return null
}

// Colores por clase de destino (lo que era bosque en 2016 y se convirtió en X en 2024).
const COLOR_CLASE = {
  deforestado: '#c2002f',
  urbano: '#404040',
  pastizal: '#a6dba0',
  agua: '#2166ac',
  suelo_desnudo: '#d8b365',
  suelo: '#d8b365',
  cultivo: '#f4a261',
  otro: '#9ca3af',
}

const LABEL_CLASE = {
  deforestado: 'Deforestado',
  urbano: 'Urbano',
  pastizal: 'Pastizal',
  agua: 'Agua',
  suelo_desnudo: 'Tierra sin cobertura vegetal',
  suelo: 'Tierra sin cobertura vegetal',
  cultivo: 'Cultivo',
  otro: 'Otro',
}

function colorPunto(claseActual) {
  const k = (claseActual || '').toString().toLowerCase().trim()
  return COLOR_CLASE[k] || '#ef4444'
}

function labelPunto(claseActual) {
  const k = (claseActual || '').toString().toLowerCase().trim()
  return LABEL_CLASE[k] || (claseActual || 'Pérdida')
}

// Clases estándar de destino que pueden aparecer en los puntos de pérdida.
const CLASES_ESTANDAR = ['deforestado', 'urbano', 'pastizal', 'agua', 'suelo_desnudo', 'cultivo']

export default function MapaAlcaldias({ geojson, seleccionada, onSeleccionar, colores, comparativa, puntosPerdida = [] }) {
  // Conteo por clase (presente o no).
  const conteoPorClase = useMemo(() => {
    const m = new Map()
    for (const c of CLASES_ESTANDAR) m.set(c, 0)
    let otros = 0
    for (const p of puntosPerdida) {
      const k = (p.clase_actual || 'otro').toString().toLowerCase().trim()
      if (m.has(k)) m.set(k, m.get(k) + 1)
      else if (k === 'suelo') m.set('suelo_desnudo', m.get('suelo_desnudo') + 1)
      else otros++
    }
    if (otros > 0) m.set('otro', otros)
    return m
  }, [puntosPerdida])

  // Filtros activos: por defecto todas las clases con puntos.
  const [clasesActivas, setClasesActivas] = useState(new Set())
  useEffect(() => {
    const activas = new Set()
    for (const [k, n] of conteoPorClase) if (n > 0) activas.add(k)
    setClasesActivas(activas)
  }, [conteoPorClase])

  // Toggle alcaldías visibles.
  const [mostrarAlcaldias, setMostrarAlcaldias] = useState(true)
  const [mostrarEtiquetas, setMostrarEtiquetas] = useState(true)
  const [baseMapKey, setBaseMapKey] = useState('satelite')
  const [panelAbierto, setPanelAbierto] = useState(true)
  const base = BASEMAPS[baseMapKey]

  const toggleClase = (k) => {
    setClasesActivas(prev => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }

  const puntosFiltrados = useMemo(() => {
    if (clasesActivas.size === 0) return []
    return puntosPerdida.filter(p => {
      const k = (p.clase_actual || 'otro').toString().toLowerCase().trim()
      return clasesActivas.has(k)
    })
  }, [puntosPerdida, clasesActivas])

  const estilo = (feature) => {
    const nombre = feature.properties.alcaldia
    const isSelected = nombre === seleccionada
    return {
      color: '#ffffff',
      weight: isSelected ? 3 : 1,
      fillColor: colores[nombre] || '#2d6a4f',
      fillOpacity: isSelected ? 0.55 : 0.25,
    }
  }

  const onCadaFeature = (feature, layer) => {
    const nombre = feature.properties.alcaldia
    const ha = feature.properties.area_ha?.toLocaleString('es-MX', { maximumFractionDigits: 0 })
    layer.bindTooltip(`<strong>${nombre}</strong><br/>${ha} ha`, { sticky: true })
    layer.on('click', () => onSeleccionar(nombre))
    layer.on('mouseover', () => { if (nombre !== seleccionada) layer.setStyle({ fillOpacity: 0.5 }) })
    layer.on('mouseout',  () => { if (nombre !== seleccionada) layer.setStyle({ fillOpacity: 0.25 }) })
  }

  return (
    <div style={{ width: '100%', height: '450px', position: 'relative' }}>
      <MapContainer
        center={[19.35, -99.13]}
        zoom={10}
        style={{ width: '100%', height: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          key={baseMapKey}
          attribution={base.attribution}
          url={base.url}
          maxZoom={19}
        />
        {mostrarEtiquetas && baseMapKey === 'satelite' && (
          <TileLayer
            attribution='&copy; Esri'
            url='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'
            maxZoom={19}
          />
        )}

        {geojson && mostrarAlcaldias && (
          <GeoJSON
            key={seleccionada}
            data={geojson}
            style={estilo}
            onEachFeature={onCadaFeature}
          />
        )}

        {puntosFiltrados.map((p, i) => {
          const col = colorPunto(p.clase_actual)
          return (
            <CircleMarker
              key={i}
              center={[p.lat, p.lon]}
              radius={5}
              pathOptions={{
                color: col,
                fillColor: col,
                fillOpacity: 0.85,
                weight: 1.5,
              }}
            >
              <Tooltip>
                <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                  <strong>Pérdida de bosque</strong><br />
                  2016: {p.clase_base}<br />
                  2024: {p.clase_actual}<br />
                  NDVI 2016: {Number(p.NDVI_base).toFixed(2)}<br />
                  NDVI 2024: {Number(p.NDVI_actual).toFixed(2)}
                </div>
              </Tooltip>
            </CircleMarker>
          )
        })}

        {geojson && seleccionada && (
          <FlyTo geojson={geojson} seleccionada={seleccionada} />
        )}
      </MapContainer>

      {/* Panel de capas / filtros */}
      <div
        onMouseDown={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
        style={{
        position: 'absolute', bottom: 24, left: 12, zIndex: 1000,
        background: 'rgba(255,255,255,0.96)', borderRadius: 10,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        fontSize: 12,
        minWidth: panelAbierto ? 200 : 0, maxWidth: 260,
        maxHeight: 'calc(100% - 100px)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        }}
      >
        <button
          onClick={() => setPanelAbierto(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '8px 14px', fontSize: 11, fontWeight: 600,
            color: '#555', letterSpacing: 0.3, width: '100%',
            borderBottom: panelAbierto ? '1px solid #eee' : 'none',
          }}
        >
          <span>{panelAbierto ? 'CAPAS' : '☰'}</span>
          {panelAbierto && <span style={{ fontSize: 14, lineHeight: 1 }}>×</span>}
        </button>

        {panelAbierto && (
        <>
        {/* Cabecera fija con VISTA (basemap) */}
        <div style={{ padding: '8px 14px 8px', borderBottom: '1px solid #eee' }}>
          <div style={{ fontWeight: 600, fontSize: 11, color: '#555', letterSpacing: 0.3, marginBottom: 6 }}>
            VISTA
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {Object.entries(BASEMAPS).map(([k, b]) => (
              <button
                key={k}
                onClick={() => setBaseMapKey(k)}
                style={{
                  flex: 1, padding: '5px 6px', fontSize: 11, cursor: 'pointer',
                  border: '1px solid',
                  borderColor: baseMapKey === k ? '#1b4332' : '#ddd',
                  background: baseMapKey === k ? '#1b4332' : '#fff',
                  color: baseMapKey === k ? '#fff' : '#555',
                  borderRadius: 5,
                  fontWeight: baseMapKey === k ? 600 : 400,
                }}
              >
                {b.label}
              </button>
            ))}
          </div>
        </div>

        {/* Resto con scroll si hace falta */}
        <div style={{
          padding: '8px 14px 10px', display: 'flex', flexDirection: 'column', gap: 6,
          overflowY: 'auto', flex: 1, minHeight: 0,
        }}>
        <div style={{
          fontWeight: 600, fontSize: 11, color: '#555', letterSpacing: 0.3,
        }}>
          OVERLAYS
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={mostrarAlcaldias}
            onChange={() => setMostrarAlcaldias(v => !v)}
          />
          <span>Polígonos de alcaldías</span>
        </label>
        {baseMapKey === 'satelite' && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={mostrarEtiquetas}
              onChange={() => setMostrarEtiquetas(v => !v)}
            />
            <span>Etiquetas de lugares</span>
          </label>
        )}

        <div style={{
          fontWeight: 600, fontSize: 11, color: '#555', letterSpacing: 0.3,
          borderTop: '1px solid #eee', paddingTop: 6, marginTop: 2,
        }}>
          PÉRDIDA DE BOSQUE → CLASE 2024
        </div>
        <div style={{ fontSize: 10, color: '#888', lineHeight: 1.4, marginTop: -2 }}>
          Puntos donde un píxel de bosque 2016 pasó a otra clase en 2024 (no son ha totales).
        </div>
        <div style={{ display: 'flex', gap: 6, fontSize: 10 }}>
          <button
            onClick={() => {
              const all = new Set()
              for (const [k, n] of conteoPorClase) if (n > 0) all.add(k)
              setClasesActivas(all)
            }}
            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', color: '#555' }}
          >Todas</button>
          <button
            onClick={() => setClasesActivas(new Set())}
            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', color: '#555' }}
          >Ninguna</button>
        </div>
        {[...conteoPorClase.entries()].map(([k, n]) => {
          const sinDatos = n === 0
          return (
            <label
              key={k}
              style={{
                display: 'flex', alignItems: 'center', gap: 7,
                cursor: 'pointer',
                opacity: sinDatos ? 0.55 : 1,
              }}
              title={sinDatos ? 'En esta alcaldía no se detectó pérdida de bosque hacia esta clase' : ''}
            >
              <input
                type="checkbox"
                checked={clasesActivas.has(k)}
                onChange={() => toggleClase(k)}
              />
              <span style={{
                width: 10, height: 10, background: colorPunto(k),
                borderRadius: '50%', flexShrink: 0
              }} />
              <span style={{ flex: 1 }}>{labelPunto(k)}</span>
              <span style={{ color: '#888', fontSize: 11 }}>{n}</span>
            </label>
          )
        })}

        <div style={{ fontSize: 10, color: '#aaa', borderTop: '1px solid #eee', paddingTop: 4, marginTop: 2 }}>
          {seleccionada ? `${seleccionada} · ` : ''}Sentinel-2 · Dynamic World · kNN
        </div>
        </div>
        </>
        )}
      </div>

      {/* Badge delta */}
      {comparativa && seleccionada && (
        <div style={{
          position: 'absolute', top: 12, right: 12, zIndex: 1000,
          background: comparativa.delta_ha < 0 ? '#fef2f2' : '#f0fdf4',
          border: `1px solid ${comparativa.delta_ha < 0 ? '#fca5a5' : '#86efac'}`,
          borderRadius: 10, padding: '8px 14px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.12)'
        }}>
          <div style={{ fontWeight: 700, color: comparativa.delta_ha < 0 ? '#991b1b' : '#166534', fontSize: 16 }}>
            {comparativa.delta_ha < 0 ? '▼' : '▲'} {Math.abs(comparativa.delta_pct).toFixed(1)}% bosque
          </div>
          <div style={{ color: '#666', fontSize: 11, marginTop: 2 }}>
            {comparativa.delta_ha < 0 ? 'pérdida' : 'ganancia'} 2016-&gt;2024
          </div>
          <div style={{ color: '#888', fontSize: 11 }}>
            {Math.abs(comparativa.delta_ha).toFixed(1)} ha · {comparativa.puntos_perdida} puntos
          </div>
        </div>
      )}

      {!geojson && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: '#f5f5f0', fontSize: 14, color: '#666'
        }}>
          Cargando mapa...
        </div>
      )}
    </div>
  )
}
