export interface GenerationMeta {
  id: string
  ticker: string
  start_date: string
  end_date: string
  max_regimes: number
  fat_tail: boolean
  switch_cost?: number // absent on generations made before switching costs existed
  created_at: string
  regimes: number[]
  current_regime: number | null
  observations: number | null
  legacy: boolean
}

export interface Generation {
  meta: GenerationMeta
  markdown: string
}

export interface GenerateRequest {
  ticker: string
  start_date: string
  end_date: string
  max_regimes: number
  fat_tail: boolean
  switch_cost: number
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const fetchPalette = () =>
  request<{ colors: string[] }>('/api/palette').then((r) => r.colors)

export const fetchGenerations = () => request<GenerationMeta[]>('/api/generations')

export const fetchGeneration = (id: string) =>
  request<Generation>(`/api/generations/${encodeURIComponent(id)}`)

export const generate = (body: GenerateRequest) =>
  request<Generation & { cached: boolean }>('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export async function deleteGeneration(id: string): Promise<void> {
  const res = await fetch(`/api/generations/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Delete failed (${res.status})`)
  }
}

export const imageUrl = (id: string, filename: string) =>
  `/api/generations/${encodeURIComponent(id)}/${encodeURIComponent(filename)}`

export const plotUrl = (id: string) => imageUrl(id, 'plot.png')
