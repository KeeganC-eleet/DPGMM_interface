import { createContext, useContext, type ReactNode } from 'react'

// Mirrors backend/src/regime_hmm/palette.py; replaced by /api/palette on load
export const DEFAULT_PALETTE = [
  '#00E5FF', '#FF2E63', '#7CFF4F', '#FFD400', '#B266FF',
  '#FF8A00', '#FF4FD8', '#3D7BFF', '#00FFA3', '#F5F5F5',
]

export const PaletteContext = createContext<string[]>(DEFAULT_PALETTE)

export function RegimeChip({ regime, label }: { regime: number; label?: ReactNode }) {
  const palette = useContext(PaletteContext)
  const color = palette[regime % palette.length]
  return (
    <span className="regime-chip" style={{ background: color, boxShadow: `0 0 10px ${color}66` }}>
      {label ?? `Regime ${regime}`}
    </span>
  )
}
