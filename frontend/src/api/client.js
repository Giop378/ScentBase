const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function buildUrl(path, params) {
  const url = new URL(`${API_BASE_URL}${path}`)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) url.searchParams.set(key, value)
  })
  return url.toString()
}

export async function apiRequest(path, options = {}) {
  const { params, ...fetchOptions } = options
  let response
  try {
    response = await fetch(buildUrl(path, params), {
      headers: { 'Content-Type': 'application/json', ...(fetchOptions.headers || {}) },
      ...fetchOptions,
    })
  } catch {
    throw new ApiError('Impossibile raggiungere il backend. Verifica che FastAPI sia avviato.', 0)
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : detail?.message || `Errore HTTP ${response.status}`
    throw new ApiError(message, response.status, detail)
  }
  return data
}

export const api = {
  counts: () => apiRequest('/collections/counts'),
  perfumes: (params) => apiRequest('/perfumes', { params }),
  perfume: (id) => apiRequest(`/perfumes/${encodeURIComponent(id)}`),
  details: (id) => apiRequest(`/perfumes/${encodeURIComponent(id)}/details`),
  similar: (id, limit = 6) => apiRequest(`/perfumes/${encodeURIComponent(id)}/similar`, { params: { limit } }),
  topPerfumes: (limit = 6, minVotes = 100) => apiRequest('/statistics/top-perfumes', { params: { limit, min_votes: minVotes } }),
  brandStats: (limit = 8) => apiRequest('/statistics/brands', { params: { limit } }),
  noteStats: (limit = 10) => apiRequest('/statistics/notes', { params: { limit } }),
  createPerfume: (payload) => apiRequest('/perfumes', { method: 'POST', body: JSON.stringify(payload) }),
  updatePerfume: (id, payload) => apiRequest(`/perfumes/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deletePerfume: (id) => apiRequest(`/perfumes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
