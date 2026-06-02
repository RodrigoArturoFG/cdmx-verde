export default function ComparativaPanel({ comparativa }) {
  if (!comparativa) return null

  const { alcaldia, base, actual, delta_ha, delta_pct, png_comparativa_url } = comparativa
  const perdida = delta_ha < 0

  return (
    <div style={{
      flex: 1, background: '#fff', borderTop: '1px solid #e0e0d8',
      display: 'flex', flexDirection: 'column'
    }}>
      <div style={{
        padding: '12px 20px', borderBottom: '1px solid #e0e0d8',
        display: 'flex', alignItems: 'center', gap: 12
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
      </div>

      <div style={{ flex: 1, display: 'flex' }}>
        {png_comparativa_url ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <img
              src={png_comparativa_url}
              alt={`Comparativa ${alcaldia} 2016 vs 2024`}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
            <div style={{
              padding: '8px 20px', fontSize: 12, color: '#888',
              display: 'flex', gap: 16, borderTop: '1px solid #e0e0d8'
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 12, height: 12, background: '#1b7837', borderRadius: 2 }} />
                Bosque 2016
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 12, height: 12, background: '#c2002f', borderRadius: 2 }} />
                Deforestación detectada
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 12, height: 12, background: '#404040', borderRadius: 2 }} />
                Urbano 2024
              </span>
            </div>
          </div>
        ) : (
          <div style={{
            flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr',
          }}>
            <AnioCard titulo="Referencia 2016" datos={base} color="#2d6a4f" />
            <AnioCard titulo="Actual 2024" datos={actual} color="#1b4332" border />
          </div>
        )}
      </div>
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
