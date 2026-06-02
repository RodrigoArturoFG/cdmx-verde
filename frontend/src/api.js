const BASE = ''  // proxied via Vite

export async function fetchAlcaldias() {
  const res = await fetch(`${BASE}/alcaldias/`)
  if (!res.ok) throw new Error('No se pudo cargar el GeoJSON de alcaldías')
  return res.json()
}

export async function fetchListaAlcaldias() {
  const res = await fetch(`${BASE}/alcaldias/lista`)
  if (!res.ok) throw new Error('No se pudo cargar la lista de alcaldías')
  return res.json()
}

export async function fetchComparativa(alcaldia) {
  const res = await fetch(`${BASE}/cobertura/comparativa?alcaldia=${encodeURIComponent(alcaldia)}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error('Error al obtener comparativa')
  return res.json()
}

export async function lanzarPipeline(alcaldia) {
  const res = await fetch(
    `${BASE}/cobertura/procesar?alcaldia=${encodeURIComponent(alcaldia)}`,
    { method: 'POST' }
  )
  if (!res.ok) throw new Error('Error al lanzar el pipeline')
  return res.json()   // { job_id, status }
}

export async function fetchJobStatus(jobId) {
  const res = await fetch(`${BASE}/job/${jobId}/status`)
  if (!res.ok) throw new Error('Error al consultar el job')
  return res.json()
}

/** Polling hasta que el job termine (done | error) */
export async function pollJob(jobId, onProgress, intervalMs = 3000) {
  return new Promise((resolve, reject) => {
    const id = setInterval(async () => {
      try {
        const job = await fetchJobStatus(jobId)
        onProgress(job.message)
        if (job.status === 'done') {
          clearInterval(id)
          resolve(job)
        } else if (job.status === 'error') {
          clearInterval(id)
          reject(new Error(job.message))
        }
      } catch (e) {
        clearInterval(id)
        reject(e)
      }
    }, intervalMs)
  })
}


export async function fetchPuntosPerdida(alcaldia) {
  const res = await fetch(`/cobertura/perdida?alcaldia=${encodeURIComponent(alcaldia)}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.puntos || []
}