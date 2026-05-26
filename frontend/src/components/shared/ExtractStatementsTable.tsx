/**
 * ExtractStatementsTable — declaracions amb fonts traçables i fila expandible
 */
import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import SourceProvenance from './SourceProvenance'
import './Traceability.css'

export type ExtractStatementItem = {
  id: number
  actor: string
  statement: string
  posture_value: number
  tone: string
  grounding_score: number | null
  source_url?: string
  source_date?: string
  source_text_excerpt?: string
  osint_result_id?: number | null
  cleanup_decision?: string
  source_verified?: boolean
}

function postureClass(v: number): string {
  if (v >= 1) return 'extract-posture-pos'
  if (v <= -1) return 'extract-posture-neg'
  return ''
}

function domainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url.slice(0, 24) || '—'
  }
}

function isRowVerified(s: ExtractStatementItem): boolean {
  if (s.source_verified !== undefined) return s.source_verified
  const url = (s.source_url || '').trim()
  if (!url || url.startsWith('direct-analysis:')) return false
  return (s.source_text_excerpt?.length ?? 0) >= 40
}

function groundingClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return ''
  if (score >= 0.6) return 'extract-grounding--high'
  if (score >= 0.3) return 'extract-grounding--mid'
  return 'extract-grounding--low'
}

type ExtractStatementsTableProps = {
  statements: ExtractStatementItem[]
  showExpand?: boolean
}

export default function ExtractStatementsTable({
  statements,
  showExpand = true,
}: ExtractStatementsTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  if (!statements.length) {
    return <p className="extract-empty">Sense declaracions extretes encara.</p>
  }

  return (
    <div className="extract-table-wrap">
      <table className="extract-table">
        <thead>
          <tr>
            {showExpand ? <th aria-label="Expandir" style={{ width: 36 }} /> : null}
            <th>Actor</th>
            <th>Declaració</th>
            <th>Font</th>
            <th>Data</th>
            <th>Excerpt</th>
            <th>Postura</th>
            <th>To</th>
            <th>Ground.</th>
          </tr>
        </thead>
        <tbody>
          {statements.map((s) => {
            const isOpen = expandedId === s.id
            const colSpan = showExpand ? 9 : 8
            const verified = isRowVerified(s)
            const hasSource = verified && Boolean(s.source_url?.trim())
            const displayGrounding =
              s.grounding_score !== null && s.grounding_score !== undefined && verified
                ? s.grounding_score
                : null
            return (
              <Fragment key={s.id}>
                <tr
                  className={[
                    'extract-row',
                    isOpen ? 'extract-row--expanded' : '',
                    !verified ? 'extract-row--no-source' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {showExpand ? (
                    <td>
                      <button
                        type="button"
                        className="extract-expand-btn"
                        aria-expanded={isOpen}
                        aria-label={isOpen ? 'Replegar detall de font' : 'Expandir detall de font'}
                        onClick={() => setExpandedId(isOpen ? null : s.id)}
                      >
                        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                    </td>
                  ) : null}
                  <td>{s.actor}</td>
                  <td className="extract-statement-cell">{s.statement}</td>
                  <td>
                    {hasSource ? (
                      <a
                        href={s.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="extract-source-link"
                        title={s.source_url}
                      >
                        {domainFromUrl(s.source_url!)}
                      </a>
                    ) : (
                      <span className="extract-source-missing" title={s.cleanup_decision === 'SYNTHETIC' ? 'Anàlisi directa' : 'Sense font OSINT'}>
                        {s.cleanup_decision === 'SYNTHETIC' ? 'Síntesi IA' : 'Sense URL'}
                      </span>
                    )}
                  </td>
                  <td className="extract-date">
                    {s.source_date ? s.source_date.slice(0, 10) : '—'}
                  </td>
                  <td className="extract-excerpt">
                    {(s.source_text_excerpt || '—').slice(0, 80)}
                    {(s.source_text_excerpt?.length ?? 0) > 80 ? '…' : ''}
                  </td>
                  <td className={postureClass(s.posture_value)}>{s.posture_value}</td>
                  <td>{s.tone}</td>
                  <td>
                    {displayGrounding !== null ? (
                      <span className={`extract-grounding ${groundingClass(displayGrounding)}`}>
                        {(displayGrounding * 100).toFixed(0)}%
                      </span>
                    ) : (
                      <span className="extract-source-missing" style={{ fontSize: 9 }}>
                        N/A
                      </span>
                    )}
                  </td>
                </tr>
                {showExpand && isOpen ? (
                  <tr className="extract-detail-row">
                    <td colSpan={colSpan}>
                      <div className="extract-detail-panel">
                        {s.source_text_excerpt ? (
                          <p className="extract-detail-text">
                            <strong>Text original:</strong> {s.source_text_excerpt}
                          </p>
                        ) : null}
                        <div className="extract-detail-actions">
                          {hasSource ? (
                            <a
                              href={s.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="extract-detail-link"
                            >
                              <ExternalLink size={12} />
                              Obrir font original
                            </a>
                          ) : null}
                        </div>
                        {s.osint_result_id ? (
                          <p className="extract-detail-meta">Resultat OSINT #{s.osint_result_id}</p>
                        ) : null}
                        <SourceProvenance statementId={s.id} compact />
                      </div>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
