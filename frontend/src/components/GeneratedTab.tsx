import { useEffect, useState } from 'react'
import { deleteGeneration, fetchGeneration, fetchGenerations, type Generation, type GenerationMeta } from '../api'
import { RegimeChip } from '../palette'
import GenerationView from './GenerationView'

export default function GeneratedTab({ refreshKey }: { refreshKey: number }) {
  const [items, setItems] = useState<GenerationMeta[]>([])
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<Generation | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchGenerations().then(setItems).catch((err) => setError(String(err.message ?? err)))
  }, [refreshKey])

  async function open(id: string) {
    setError(null)
    try {
      setSelected(await fetchGeneration(id))
      window.scrollTo({ top: 0 })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function remove(meta: GenerationMeta) {
    if (!window.confirm(`Delete the ${meta.ticker} report (${meta.start_date} → ${meta.end_date})? This cannot be undone.`)) return
    setError(null)
    try {
      await deleteGeneration(meta.id)
      setItems((prev) => prev.filter((m) => m.id !== meta.id))
      if (selected?.meta.id === meta.id) setSelected(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  if (selected) {
    return (
      <div>
        <div className="detail-toolbar">
          <button className="secondary" onClick={() => setSelected(null)}>← All generations</button>
          <button className="danger" onClick={() => remove(selected.meta)}>Delete report</button>
        </div>
        {error && <div className="panel error">{error}</div>}
        <GenerationView generation={selected} />
      </div>
    )
  }

  const query = filter.trim().toUpperCase()
  const visible = query ? items.filter((m) => m.ticker.includes(query)) : items

  return (
    <div>
      <div className="panel toolbar">
        <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter by ticker…" />
        <span className="muted">{visible.length} of {items.length} generations</span>
      </div>
      {error && <div className="panel error">{error}</div>}
      <div className="cards">
        {visible.map((m) => (
          <div key={m.id} className="card" role="button" tabIndex={0} onClick={() => open(m.id)}
            onKeyDown={(e) => { if (e.key === 'Enter') open(m.id) }}>
            <div className="card-title">
              <strong>{m.ticker}</strong>
              <span className="card-actions">
                {m.legacy && <span className="badge badge-muted">Legacy</span>}
                <button
                  className="icon-button"
                  title="Delete report"
                  aria-label={`Delete ${m.ticker} report`}
                  onClick={(e) => { e.stopPropagation(); remove(m) }}
                >
                  ✕
                </button>
              </span>
            </div>
            <div className="muted">{m.start_date} → {m.end_date}</div>
            <div className="muted">
              {m.fat_tail ? "Student's t" : 'Gaussian'} · max {m.max_regimes}{m.switch_cost ? ` · switch ${m.switch_cost}` : ''} · {m.regimes.length} active
            </div>
            {m.current_regime !== null && (
              <div className="card-current">
                Current: <RegimeChip regime={m.current_regime} />
              </div>
            )}
            <div className="muted small">Generated {new Date(m.created_at).toLocaleString()}</div>
          </div>
        ))}
        {visible.length === 0 && !error && <div className="muted">No generations yet.</div>}
      </div>
    </div>
  )
}
