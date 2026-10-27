import { Children, isValidElement, cloneElement, useMemo, type ReactNode, type ReactElement } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { imageUrl, plotUrl, type Generation } from '../api'
import { RegimeChip } from '../palette'

const REGIME_RE = /(Regime \d+)/g

// Replaces every "Regime N" inside text nodes with a colored chip
function chipify(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child === 'string') {
      const parts = child.split(REGIME_RE)
      if (parts.length === 1) return child
      return parts.map((part, i) => {
        const match = /^Regime (\d+)$/.exec(part)
        return match ? <RegimeChip key={i} regime={Number(match[1])} /> : part
      })
    }
    return child
  })
}

const withChips = (Tag: 'p' | 'li' | 'td' | 'th' | 'strong') =>
  ({ children, node: _node, ...props }: { children?: ReactNode; node?: unknown }) => (
    <Tag {...props}>{chipify(children)}</Tag>
  )

const components: Components = {
  p: withChips('p'),
  li: withChips('li'),
  td: withChips('td'),
  th: withChips('th'),
  // A bold "Regime N" becomes just the chip, without the bold wrapper
  strong: ({ children }) => {
    const chips = chipify(children)
    const only = Children.toArray(chips)
    if (only.length === 1 && isValidElement(only[0]) && only[0].type === RegimeChip) {
      return cloneElement(only[0] as ReactElement)
    }
    return <strong>{chips}</strong>
  },
  table: ({ children }) => (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  ),
}

function prepareMarkdown(markdown: string): string {
  return markdown
    // The regime plot is shown above the report, so drop its embedded copy
    .replace(/!\[[^\]]*\]\(plot\.png\)\n?/g, '')
    .replace(/\$\\rightarrow\$/g, '→')
}

export default function GenerationView({ generation, cached }: { generation: Generation; cached?: boolean }) {
  const { meta } = generation
  // Report images use paths relative to the generation folder; resolve them against the API
  const reportComponents = useMemo<Components>(() => ({
    ...components,
    img: ({ src, alt }) => {
      const url = typeof src === 'string' ? imageUrl(meta.id, src) : undefined
      return (
        <a className="report-image" href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={alt ?? ''} />
        </a>
      )
    },
  }), [meta.id])
  return (
    <div className="generation">
      <div className="generation-header">
        <h2>{meta.ticker}</h2>
        <span className="muted">
          {meta.start_date} → {meta.end_date} · {meta.fat_tail ? "Student's t (PyMC)" : 'Gaussian DPGMM'} · max {meta.max_regimes} regimes
        </span>
        {cached && <span className="badge">Loaded from cache</span>}
        {meta.legacy && <span className="badge badge-muted">Legacy</span>}
      </div>
      <a className="plot" href={plotUrl(meta.id)} target="_blank" rel="noreferrer">
        <img src={plotUrl(meta.id)} alt={`${meta.ticker} market regimes`} />
      </a>
      <article className="report">
        <Markdown remarkPlugins={[remarkGfm]} components={reportComponents}>
          {prepareMarkdown(generation.markdown)}
        </Markdown>
      </article>
    </div>
  )
}
