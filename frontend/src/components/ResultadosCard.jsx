import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function ResultadosCard({ comparativa }) {
  if (!comparativa) return null

  const { alcaldia, base, actual, delta_ha, delta_pct } = comparativa
  const perdida = delta_ha < 0

  const chartData = [
    { name: 'Bosque', v2016: base.ha_bosque, v2024: actual.ha_bosque },
    { name: 'Urbano', v2016: base.ha_urbano, v2024: actual.ha_urbano },
    { name: 'Pastizal', v2016: base.ha_pastizal, v2024: actual.ha_pastizal },
  ]

  return (
    <div style={{
      background: '#f9f9f5', border: '1px solid #e0e0d8',
      borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 14
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1b4332' }}>
        Resumen · {alcaldia}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <MetricBox
          label="Bosque 2016"
          value={`${base.ha_bosque.toLocaleString('es-MX', { maximumFractionDigits: 0 })} ha`}
          color="#2d6a4f"
        />
        <MetricBox
          label="Bosque 2024"
          value={`${actual.ha_bosque.toLocaleString('es-MX', { maximumFractionDigits: 0 })} ha`}
          color="#1b4332"
        />
        <MetricBox
          label="Cambio"
          value={`${perdida ? '' : '+'}${delta_ha.toLocaleString('es-MX', { maximumFractionDigits: 1 })} ha`}
          color={perdida ? '#991b1b' : '#166534'}
          bg={perdida ? '#fef2f2' : '#f0fdf4'}
        />
        <MetricBox
          label="Variación"
          value={`${perdida ? '' : '+'}${delta_pct.toFixed(1)}%`}
          color={perdida ? '#991b1b' : '#166534'}
          bg={perdida ? '#fef2f2' : '#f0fdf4'}
        />
      </div>

      <div style={{ height: 120 }}>
        <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
          Principales coberturas (ha)
        </div>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={chartData} barGap={2} barSize={10}>
            <XAxis dataKey="name" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #e0e0d8' }}
              formatter={(v) => [`${v.toLocaleString('es-MX', { maximumFractionDigits: 0 })} ha`]}
            />
            <Bar dataKey="v2016" name="2016" fill="#52b788" radius={[2, 2, 0, 0]} />
            <Bar dataKey="v2024" name="2024" fill="#1b4332" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ fontSize: 11, color: '#aaa', textAlign: 'center' }}>
        Fuente: Sentinel-2 · ESA WorldCover · kNN
      </div>
    </div>
  )
}

function MetricBox({ label, value, color, bg = '#fff' }) {
  return (
    <div style={{
      background: bg, border: '1px solid #e0e0d8', borderRadius: 8,
      padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 2
    }}>
      <div style={{ fontSize: 10, color: '#888' }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 600, color }}>{value}</div>
    </div>
  )
}
