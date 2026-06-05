import { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const TABS = [
  { id: 'datos', label: 'Datos' },
  { id: 'imagenes', label: 'Imágenes' },
  { id: 'descargar', label: 'Descargar' },
]

export default function ComparativaPanel({ comparativa, feature }) {
  const [tab, setTab] = useState('datos')
  if (!comparativa) return null

  const { alcaldia, base, actual, delta_ha, delta_pct } = comparativa
  const perdida = delta_ha < 0

  return (
    <div style={{
      flex: 1, background: '#fff', borderTop: '1px solid #e0e0d8',
      display: 'flex', flexDirection: 'column'
    }}>
      <div style={{
        padding: '12px 20px 0', borderBottom: '1px solid #e0e0d8',
        display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap'
      }}>
        <span style={{ fontWeight: 600, fontSize: 15 }}>
          {alcaldia} — comparativa satelital
        </span>
        <span style={{
          fontSize: 12, padding: '2px 10px', borderRadius: 20,
          background: perdida ? '#fef2f2' : '#f0fdf4',
          color: perdida ? '#991b1b' : '#166534', fontWeight: 500
        }}>
          {perdida ? '▼' : '▲'} {Math.abs(delta_pct).toFixed(1)}% bosque
        </span>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '8px 14px', fontSize: 13,
                color: tab === t.id ? '#1b4332' : '#888',
                fontWeight: tab === t.id ? 600 : 400,
                borderBottom: tab === t.id ? '2px solid #1b4332' : '2px solid transparent',
                marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', minHeight: 280 }}>
        {tab === 'datos' && <DatosTab base={base} actual={actual} />}
        {tab === 'imagenes' && <ImagenesTab alcaldia={alcaldia} feature={feature} />}
        {tab === 'descargar' && <DescargarTab alcaldia={alcaldia} comparativa={comparativa} />}
      </div>
    </div>
  )
}

// ── Tab: Datos ───────────────────────────────────────────────────────────────

function DatosTab({ base, actual }) {
  return (
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
      <AnioCard titulo="Referencia 2016" datos={base} color="#2d6a4f" />
      <AnioCard titulo="Actual 2024" datos={actual} color="#1b4332" border />
    </div>
  )
}

function AnioCard({ titulo, datos, color, border }) {
  const clases = [
    { key: 'ha_bosque', label: 'Bosque', color: '#1b7837' },
    { key: 'ha_deforestado', label: 'Deforestado', color: '#c2002f' },
    { key: 'ha_pastizal', label: 'Pastizal', color: '#a6dba0' },
    { key: 'ha_urbano', label: 'Urbano', color: '#404040' },
    { key: 'ha_agua', label: 'Agua', color: '#2166ac' },
    { key: 'ha_suelo_desnudo', label: 'Tierra sin cobertura vegetal', color: '#d8b365' },
  ]

  return (
    <div style={{
      padding: 20, borderLeft: border ? '1px solid #e0e0d8' : 'none',
      display: 'flex', flexDirection: 'column', gap: 12
    }}>
      <div style={{
        fontSize: 13, fontWeight: 600, color,
        borderBottom: `2px solid ${color}`, paddingBottom: 6
      }}>
        {titulo}
      </div>
      {clases.map(c => {
        const ha = datos[c.key] || 0
        const pct = datos.total_ha > 0 ? (ha / datos.total_ha * 100) : 0
        return (
          <div key={c.key} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 8, height: 8, background: c.color, borderRadius: 1 }} />
                {c.label}
              </span>
              <span style={{ fontWeight: 500 }}>
                {ha.toLocaleString('es-MX', { maximumFractionDigits: 1 })} ha
              </span>
            </div>
            <div style={{ background: '#f0f0ea', borderRadius: 2, height: 4 }}>
              <div style={{
                height: '100%', width: `${Math.min(pct, 100)}%`,
                background: c.color, borderRadius: 2,
                transition: 'width 0.6s ease'
              }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Tab: Imágenes (Sentinel-2 EOX cloudless 2016 vs 2024) ────────────────────

function FitToFeature({ feature }) {
  const map = useMap()
  useEffect(() => {
    if (!feature) return
    import('leaflet').then(({ default: L }) => {
      const layer = L.geoJSON(feature)
      map.fitBounds(layer.getBounds(), { padding: [10, 10] })
    })
  }, [feature])
  return null
}

function MiniMapaSentinel({ feature, anio }) {
  // Composite Sentinel-2 generado por Google Earth Engine para la temporada de
  // lluvias (jul-oct) del año dado. Usar los mismos meses en 2016 y 2024 hace que
  // la comparación sea justa (misma estación = pasto verde en ambos).
  const [url, setUrl] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let activo = true
    setUrl(null)
    setError(null)
    fetch(`/imagenes/mosaico?anio=${anio}`)
      .then(async r => {
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`)
        return r.json()
      })
      .then(d => { if (activo) setUrl(d.url) })
      .catch(e => { if (activo) setError(e.message) })
    return () => { activo = false }
  }, [anio])

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{
        padding: '8px 14px', fontSize: 12, fontWeight: 600,
        color: '#1b4332', background: '#f7f7f2',
        borderBottom: '1px solid #e0e0d8',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
        <span>Sentinel-2 · {anio}</span>
        <span style={{ fontSize: 10, fontWeight: 400, color: '#888' }}>
          temporada lluvias (jul–oct)
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 260, position: 'relative' }}>
        {error && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 500, padding: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            textAlign: 'center', fontSize: 12, color: '#991b1b', background: '#fef2f2'
          }}>
            No se pudo generar el mosaico GEE: {error}
          </div>
        )}
        <MapContainer
          center={[19.35, -99.13]}
          zoom={11}
          style={{ width: '100%', height: '100%' }}
          scrollWheelZoom={false}
          attributionControl={false}
        >
          {url && (
            <TileLayer
              attribution='Sentinel-2 (Copernicus) vía Google Earth Engine'
              url={url}
              maxZoom={16}
            />
          )}
          {feature && (
            <GeoJSON
              data={feature}
              style={{ color: '#ffeb3b', weight: 2, fillOpacity: 0 }}
            />
          )}
          {feature && <FitToFeature feature={feature} />}
        </MapContainer>
      </div>
    </div>
  )
}

function ImagenesTab({ alcaldia, feature }) {
  if (!feature) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888', fontSize: 13 }}>
        Cargando polígono de {alcaldia}...
      </div>
    )
  }
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, display: 'flex', borderBottom: '1px solid #e0e0d8' }}>
        <MiniMapaSentinel feature={feature} anio={2016} />
        <div style={{ width: 1, background: '#e0e0d8' }} />
        <MiniMapaSentinel feature={feature} anio={2024} />
      </div>
      <div style={{
        padding: '8px 20px', fontSize: 11, color: '#888',
        display: 'flex', justifyContent: 'space-between', gap: 12
      }}>
        <span>Composites Sentinel-2 (Copernicus vía Google Earth Engine), temporada de lluvias jul–oct, mismos meses en ambos años. El polígono amarillo marca los límites de {alcaldia}.</span>
        <span>Arrastra/zoom para explorar.</span>
      </div>
    </div>
  )
}

// ── Tab: Descargar ───────────────────────────────────────────────────────────

function DescargarTab({ alcaldia, comparativa }) {
  const csvUrl = `/cobertura/perdida.csv?alcaldia=${encodeURIComponent(alcaldia)}`
  const jsonHref = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(comparativa, null, 2))}`
  const slug = alcaldia.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '_').replace(/\./g, '')

  return (
    <div style={{ flex: 1, padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ fontSize: 13, color: '#555', lineHeight: 1.6, maxWidth: 720 }}>
        Descarga los datos crudos del análisis para <strong>{alcaldia}</strong>.
        El CSV contiene cada punto de pérdida de bosque detectado entre 2016 y 2024
        (lon, lat, clase original/actual y NDVI).
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <a
          href={csvUrl}
          download
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#1b4332', color: '#fff', textDecoration: 'none',
            padding: '10px 18px', borderRadius: 8, fontSize: 13, fontWeight: 500,
          }}
        >
          ⬇ Puntos de pérdida (CSV)
        </a>
        <a
          href={jsonHref}
          download={`comparativa_${slug}.json`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#fff', color: '#1b4332',
            border: '1px solid #1b4332', textDecoration: 'none',
            padding: '10px 18px', borderRadius: 8, fontSize: 13, fontWeight: 500,
          }}
        >
          ⬇ Métricas (JSON)
        </a>
      </div>

      <div style={{
        marginTop: 8, padding: 14, background: '#f7f7f2',
        borderRadius: 8, fontSize: 12, color: '#666', lineHeight: 1.6
      }}>
        <div style={{ fontWeight: 600, color: '#1b4332', marginBottom: 4 }}>
          Columnas del CSV
        </div>
        <code style={{ fontSize: 11 }}>
          lon, lat, clase_base, clase_actual, NDVI_base, NDVI_actual
        </code>
        <div style={{ marginTop: 8, fontWeight: 600, color: '#1b4332' }}>
          Resumen
        </div>
        <div>
          {comparativa.puntos_perdida} puntos de pérdida · {comparativa.puntos_ganancia} puntos de ganancia ·
          delta {comparativa.delta_ha.toFixed(1)} ha ({comparativa.delta_pct.toFixed(1)}%)
        </div>
      </div>
    </div>
  )
}
