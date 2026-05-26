/** Render structured analysis output instead of raw JSON dump. */
import type { ReactNode } from 'react'

type AnalysisResultPanelProps = {
  title?: string
  data: unknown
  error?: string | null
}

function renderValue(value: unknown, depth = 0): ReactNode {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    if (value.every((v) => typeof v === 'string' || typeof v === 'number')) {
      return (
        <ul className="analysis-result-list">
          {value.map((item, i) => (
            <li key={i}>{String(item)}</li>
          ))}
        </ul>
      )
    }
    return (
      <div className="analysis-result-nested">
        {value.map((item, i) => (
          <div key={i} className="analysis-result-card">
            {renderValue(item, depth + 1)}
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, v]) => v !== null && v !== undefined && v !== '',
    )
    if (entries.length === 0) return '—'
    return (
      <dl className="analysis-result-dl">
        {entries.map(([key, val]) => (
          <div key={key} className="analysis-result-row">
            <dt>{key.replace(/_/g, ' ')}</dt>
            <dd>{renderValue(val, depth + 1)}</dd>
          </div>
        ))}
      </dl>
    )
  }
  return String(value)
}

export default function AnalysisResultPanel({ title = 'Resultats', data, error }: AnalysisResultPanelProps) {
  if (error) {
    return (
      <div className="prospective-alert prospective-alert--error" style={{ marginTop: 'var(--spacing-lg)' }}>
        {error}
      </div>
    )
  }
  if (data === null || data === undefined) return null

  const payload =
    typeof data === 'object' && data !== null && 'analysis_data' in (data as object)
      ? (data as { analysis_data?: unknown }).analysis_data ?? data
      : data

  return (
    <div className="analysis-result-panel card" style={{ marginTop: 'var(--spacing-lg)' }}>
      <h3 style={{ marginTop: 0, color: 'var(--color-primary)' }}>{title}</h3>
      {renderValue(payload)}
    </div>
  )
}
