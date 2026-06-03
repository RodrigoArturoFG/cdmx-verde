import { useState, useEffect } from 'react'
import MapaAlcaldias from './components/MapaAlcaldias.jsx'
import PanelControl from './components/PanelControl.jsx'
import ComparativaPanel from './components/ComparativaPanel.jsx'
import ResultadosCard from './components/ResultadosCard.jsx'
import { fetchListaAlcaldias, fetchComparativa, lanzarPipeline, pollJob, fetchPuntosPerdida, fetchAlcaldias } from './api.js'

const COLORES_ALCALDIA = {
  'Tlalpan': '#2d6a4f', 'Milpa Alta': '#40916c', 'Xochimilco': '#52b788',
  'Iztapalapa': '#e07a5f', 'Álvaro Obregón': '#f2cc8f', 'Gustavo A. Madero': '#81b29a',
  'Tláhuac': '#6d9eeb', 'Cuajimalpa de Morelos': '#c77dff', 'La Magdalena Contreras': '#9bf6ff',
  'Coyoacán': '#ffd166', 'Miguel Hidalgo': '#06d6a0', 'Venustiano Carranza': '#ef476f',
  'Azcapotzalco': '#118ab2', 'Cuauhtémoc': '#073b4c', 'Benito Juárez': '#f4a261',
  'Iztacalco': '#264653',
}

export default function App() {
  const [lista, setLista] = useState([])
  const [geojson, setGeojson] = useState(null)
  const [alcaldiaSeleccionada, setAlcaldiaSeleccionada] = useState(null)
  const [comparativa, setComparativa] = useState(null)
  const [puntosPerdida, setPuntosPerdida] = useState([])
  const [jobMsg, setJobMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchListaAlcaldias().then(setLista).catch(() => {})
    fetchAlcaldias().then(setGeojson).catch(() => {})
  }, [])

  const featureSeleccionada = geojson && alcaldiaSeleccionada
    ? geojson.features.find(f => f.properties.alcaldia === alcaldiaSeleccionada)
    : null

  const seleccionar = async (nombre) => {
    if (nombre === alcaldiaSeleccionada) return
    setAlcaldiaSeleccionada(nombre)
    setComparativa(null)
    setPuntosPerdida([])
    setError('')
    setJobMsg('')
    setLoading(true)
    try {
      const cached = await fetchComparativa(nombre)
      if (cached) {
        setComparativa(cached)
        fetchPuntosPerdida(nombre).then(setPuntosPerdida)
        setLoading(false)
        return
      }
      setJobMsg('Lanzando pipeline...')
      const job = await lanzarPipeline(nombre)
      await pollJob(job.job_id, setJobMsg)
      const resultado = await fetchComparativa(nombre)
      setComparativa(resultado)
      fetchPuntosPerdida(nombre).then(setPuntosPerdida)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setJobMsg('')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header style={{
        background: '#1b4332', color: '#fff', padding: '14px 28px',
        display: 'flex', alignItems: 'center', gap: 16
      }}>
        <span style={{ fontSize: 22, fontWeight: 600 }}>CDMX Verde</span>
        <span style={{ fontSize: 13, color: '#95d5b2', marginTop: 2 }}>
          Comparativa de cobertura vegetal 2016 vs 2024
        </span>
      </header>

      <div style={{ display: 'flex', flex: 1, gap: 0 }}>
        <aside style={{
          width: 300, background: '#fff', borderRight: '1px solid #e0e0d8',
          display: 'flex', flexDirection: 'column', padding: 20, gap: 20,
          overflowY: 'auto'
        }}>
          <PanelControl
            lista={lista}
            seleccionada={alcaldiaSeleccionada}
            onSeleccionar={seleccionar}
            colores={COLORES_ALCALDIA}
          />

          {loading && (
            <div style={{ fontSize: 13, color: '#555', lineHeight: 1.6 }}>
              <div style={{
                width: '100%', height: 4, background: '#e0e0d8',
                borderRadius: 2, overflow: 'hidden', marginBottom: 8
              }}>
                <div style={{
                  height: '100%', width: '60%', background: '#2d6a4f',
                  borderRadius: 2, animation: 'slide 1.4s ease-in-out infinite'
                }} />
              </div>
              <style>{`@keyframes slide{0%{transform:translateX(-100%)}100%{transform:translateX(200%)}}`}</style>
              {jobMsg || 'Procesando...'}
            </div>
          )}

          {error && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fca5a5',
              borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#991b1b'
            }}>
              {error}
            </div>
          )}

          {comparativa && !loading && (
            <ResultadosCard comparativa={comparativa} puntosPerdida={puntosPerdida} />
          )}
        </aside>

        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <MapaAlcaldias
            geojson={geojson}
            seleccionada={alcaldiaSeleccionada}
            onSeleccionar={seleccionar}
            colores={COLORES_ALCALDIA}
            comparativa={comparativa}
            puntosPerdida={puntosPerdida}
          />
          {comparativa && (
            <ComparativaPanel
              comparativa={comparativa}
              feature={featureSeleccionada}
            />
          )}
        </main>
      </div>
    </div>
  )
}