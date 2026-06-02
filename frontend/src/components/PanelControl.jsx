export default function PanelControl({ lista, seleccionada, onSeleccionar, colores }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 13, fontWeight: 500, color: '#444' }}>
        Selecciona una alcaldía
      </div>

      <select
        value={seleccionada || ''}
        onChange={e => e.target.value && onSeleccionar(e.target.value)}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: 8,
          border: '1px solid #d0d0c8', fontSize: 14,
          background: '#fff', cursor: 'pointer', color: '#1a1a18'
        }}
      >
        <option value=''>— elige una alcaldía —</option>
        {lista.map(a => (
          <option key={a.alcaldia} value={a.alcaldia}>
            {a.alcaldia} ({a.area_ha.toLocaleString('es-MX', { maximumFractionDigits: 0 })} ha)
          </option>
        ))}
      </select>

      <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
        O haz clic directamente en el mapa
      </div>

      <div style={{
        borderTop: '1px solid #e0e0d8', paddingTop: 12,
        display: 'flex', flexDirection: 'column', gap: 6
      }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: '#666', marginBottom: 4 }}>
          Período de comparativa
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          background: '#f5f5f0', borderRadius: 8, padding: '8px 12px'
        }}>
          <span style={{
            fontSize: 13, fontWeight: 600, color: '#2d6a4f',
            background: '#d8f3dc', borderRadius: 4, padding: '2px 8px'
          }}>2016</span>
          <div style={{ flex: 1, height: 2, background: '#c0c0b8', borderRadius: 1 }} />
          <span style={{
            fontSize: 13, fontWeight: 600, color: '#1b4332',
            background: '#95d5b2', borderRadius: 4, padding: '2px 8px'
          }}>2024</span>
        </div>
        <div style={{ fontSize: 11, color: '#aaa', textAlign: 'center' }}>
          Sentinel-2 · ESA WorldCover · kNN
        </div>
      </div>

      {lista.length > 0 && (
        <div style={{ borderTop: '1px solid #e0e0d8', paddingTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: '#666', marginBottom: 8 }}>
            Leyenda — alcaldías
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {lista.slice(0, 8).map(a => (
              <div
                key={a.alcaldia}
                onClick={() => onSeleccionar(a.alcaldia)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  cursor: 'pointer', padding: '3px 6px', borderRadius: 6,
                  background: seleccionada === a.alcaldia ? '#d8f3dc' : 'transparent',
                }}
              >
                <span style={{
                  width: 10, height: 10, borderRadius: 2, flexShrink: 0,
                  background: colores[a.alcaldia] || '#2d6a4f'
                }} />
                <span style={{ fontSize: 12, color: '#333' }}>{a.alcaldia}</span>
              </div>
            ))}
            {lista.length > 8 && (
              <div style={{ fontSize: 11, color: '#aaa', paddingLeft: 6 }}>
                +{lista.length - 8} más en el mapa
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
