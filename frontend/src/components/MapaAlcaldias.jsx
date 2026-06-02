import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchAlcaldias } from '../api.js'

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

export default function MapaAlcaldias({ seleccionada, onSeleccionar, colores, comparativa, puntosPerdida = [] }) {
  const [geojson, setGeojson] = useState(null)

  useEffect(() => {
    fetchAlcaldias().then(setGeojson).catch(console.error)
  }, [])

  const estilo = (feature) => {
    const nombre = feature.properties.alcaldia
    const isSelected = nombre === seleccionada
    return {
      color: '#ffffff',
      weight: isSelected ? 3 : 1,
      fillColor: colores[nombre] || '#2d6a4f',
      fillOpacity: isSelected ? 0.6 : 0.3,
    }
  }

  const onCadaFeature = (feature, layer) => {
    const nombre = feature.properties.alcaldia
    const ha = feature.properties.area_ha?.toLocaleString('es-MX', { maximumFractionDigits: 0 })
    layer.bindTooltip(`<strong>${nombre}</strong><br/>${ha} ha`, { sticky: true })
    layer.on('click', () => onSeleccionar(nombre))
    layer.on('mouseover', () => { if (nombre !== seleccionada) layer.setStyle({ fillOpacity: 0.55 }) })
    layer.on('mouseout',  () => { if (nombre !== seleccionada) layer.setStyle({ fillOpacity: 0.30 }) })
  }

  const leyendaClases = [
    { color: '#1b7837', label: 'Bosque' },
    { color: '#c2002f', label: 'Deforestado' },
    { color: '#a6dba0', label: 'Pastizal' },
    { color: '#404040', label: 'Urbano' },
    { color: '#2166ac', label: 'Agua' },
    { color: '#d8b365', label: 'Suelo desnudo' },
  ]

  return (
    <div style={{ width: '100%', height: '450px', position: 'relative' }}>
      <MapContainer
        center={[19.35, -99.13]}
        zoom={10}
        style={{ width: '100%', height: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='© OpenStreetMap contributors'
          url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        />

        {geojson && (
          <GeoJSON
            key={seleccionada}
            data={geojson}
            style={estilo}
            onEachFeature={onCadaFeature}
          />
        )}

        {/* Puntos rojos de perdida de bosque */}
        {puntosPerdida.map((p, i) => (
          <CircleMarker
            key={i}
            center={[p.lat, p.lon]}
            radius={5}
            pathOptions={{
              color: '#991b1b',
              fillColor: '#ef4444',
              fillOpacity: 0.85,
              weight: 1.5,
            }}
          >
            <Tooltip>
              <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                <strong>Perdida de bosque</strong><br />
                2016: {p.clase_base}<br />
                2024: {p.clase_actual}<br />
                NDVI 2016: {Number(p.NDVI_base).toFixed(2)}<br />
                NDVI 2024: {Number(p.NDVI_actual).toFixed(2)}
              </div>
            </Tooltip>
          </CircleMarker>
        ))}

        {geojson && seleccionada && (
          <FlyTo geojson={geojson} seleccionada={seleccionada} />
        )}
      </MapContainer>

      {/* Leyenda flotante */}
      {seleccionada && (
        <div style={{
          position: 'absolute', bottom: 24, left: 12, zIndex: 1000,
          background: 'rgba(255,255,255,0.95)', borderRadius: 10,
          padding: '10px 14px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          fontSize: 12, display: 'flex', flexDirection: 'column', gap: 5
        }}>
          <div style={{ fontWeight: 600, fontSize: 11, color: '#555', marginBottom: 3 }}>
            COBERTURA — {seleccionada.toUpperCase()}
          </div>
          {leyendaClases.map(c => (
            <div key={c.label} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ width: 10, height: 10, background: c.color, borderRadius: 2, flexShrink: 0 }} />
              <span>{c.label}</span>
            </div>
          ))}
          {puntosPerdida.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, borderTop: '1px solid #eee', paddingTop: 5, marginTop: 2 }}>
              <span style={{ width: 10, height: 10, background: '#ef4444', borderRadius: '50%', flexShrink: 0 }} />
              <span style={{ color: '#c2002f', fontWeight: 500 }}>
                Perdida bosque ({puntosPerdida.length} pts)
              </span>
            </div>
          )}
          <div style={{ fontSize: 10, color: '#aaa', borderTop: '1px solid #eee', paddingTop: 4, marginTop: 2 }}>
            Sentinel-2 · Dynamic World · kNN
          </div>
        </div>
      )}

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
            {comparativa.delta_ha < 0 ? 'perdida' : 'ganancia'} 2016-&gt;2024
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