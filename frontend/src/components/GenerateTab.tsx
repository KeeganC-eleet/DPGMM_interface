import { useEffect, useState, type FormEvent } from 'react'
import { generate, type Generation } from '../api'
import GenerationView from './GenerationView'

// Yahoo Finance only serves 1h bars for roughly the last 730 days (mirrors the backend limit)
const MAX_LOOKBACK_DAYS = 729

const isoDate = (d: Date) => {
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 10)
}
const daysAgo = (n: number) => isoDate(new Date(Date.now() - n * 86400000))

export default function GenerateTab({ onGenerated }: { onGenerated: () => void }) {
  const today = isoDate(new Date())
  const minDate = daysAgo(MAX_LOOKBACK_DAYS)

  const [ticker, setTicker] = useState('')
  const [startDate, setStartDate] = useState(daysAgo(365))
  const [endDate, setEndDate] = useState(today)
  const [maxRegimes, setMaxRegimes] = useState(3)
  const [fatTail, setFatTail] = useState(false)

  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<(Generation & { cached: boolean }) | null>(null)

  useEffect(() => {
    if (!loading) return
    const started = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [loading])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setElapsed(0)
    setError(null)
    setResult(null)
    try {
      const res = await generate({
        ticker: ticker.trim().toUpperCase(),
        start_date: startDate,
        end_date: endDate,
        max_regimes: maxRegimes,
        fat_tail: fatTail,
      })
      setResult(res)
      if (!res.cached) onGenerated()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <form className="panel generate-form" onSubmit={onSubmit}>
        <label>
          Ticker
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="AMD"
            required
            autoFocus
          />
        </label>
        <label>
          Start date
          <input type="date" value={startDate} min={minDate} max={endDate} onChange={(e) => setStartDate(e.target.value)} required />
        </label>
        <label>
          End date
          <input type="date" value={endDate} min={startDate} max={today} onChange={(e) => setEndDate(e.target.value)} required />
        </label>
        <label>
          Max regimes
          <input type="number" min={1} max={10} value={maxRegimes} onChange={(e) => setMaxRegimes(Number(e.target.value))} required />
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={fatTail} onChange={(e) => setFatTail(e.target.checked)} />
          Fat-tail (PyMC Student's t)
        </label>
        <button type="submit" disabled={loading || !ticker.trim()}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </form>

      {loading && (
        <div className="panel status">
          <span className="spinner" /> Running regime model for {ticker.toUpperCase()}… {elapsed}s
          {fatTail && <span className="muted"> (PyMC runs can take several minutes)</span>}
        </div>
      )}
      {error && <div className="panel error">{error}</div>}
      {result && <GenerationView generation={result} cached={result.cached} />}
    </div>
  )
}
