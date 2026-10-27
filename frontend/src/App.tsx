import { useEffect, useState } from 'react'
import { fetchPalette } from './api'
import { DEFAULT_PALETTE, PaletteContext } from './palette'
import GenerateTab from './components/GenerateTab'
import GeneratedTab from './components/GeneratedTab'

type Tab = 'generate' | 'generated'

export default function App() {
  const [tab, setTab] = useState<Tab>('generate')
  const [palette, setPalette] = useState(DEFAULT_PALETTE)
  // Bumped after a new generation so the history tab refetches
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    fetchPalette().then(setPalette).catch(() => {})
  }, [])

  return (
    <PaletteContext.Provider value={palette}>
      <header className="app-header">
        <h1>Market Regimes <span className="muted">DPGMM</span></h1>
        <nav className="tabs">
          <button className={tab === 'generate' ? 'active' : ''} onClick={() => setTab('generate')}>Generate</button>
          <button className={tab === 'generated' ? 'active' : ''} onClick={() => setTab('generated')}>Generated</button>
        </nav>
      </header>
      <main>
        {/* Both tabs stay mounted so switching doesn't lose an in-flight generation */}
        <div hidden={tab !== 'generate'}>
          <GenerateTab onGenerated={() => setRefreshKey((k) => k + 1)} />
        </div>
        <div hidden={tab !== 'generated'}>
          <GeneratedTab refreshKey={refreshKey} />
        </div>
      </main>
    </PaletteContext.Provider>
  )
}
