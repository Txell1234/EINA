/**
 * SourceProvenance — cadena OSINT → article → declaració / alerta
 */
import { useQuery } from '@tanstack/react-query'
import { extractService, prospectiveService } from '../../services/api'
import './Traceability.css'

export type ProvenanceChainStep = {
  step: string
  label: string
  detail: string
  meta?: Record<string, unknown>
}

type SourceProvenanceProps = {
  statementId?: number
  matchId?: number
  compact?: boolean
}

export default function SourceProvenance({ statementId, matchId, compact }: SourceProvenanceProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['provenance', statementId, matchId],
    queryFn: async () => {
      if (statementId) return extractService.getStatementProvenance(statementId)
      if (matchId) return prospectiveService.getMatchProvenance(matchId)
      return null
    },
    enabled: !!(statementId || matchId),
  })

  if (isLoading) {
    return <p className="source-provenance__loading">Carregant traçabilitat…</p>
  }

  const chain = (data?.chain ?? []) as ProvenanceChainStep[]
  if (!chain.length) return null

  return (
    <div className={`source-provenance${compact ? ' source-provenance--compact' : ''}`}>
      <strong className="source-provenance__title">Traçabilitat</strong>
      <ol className="source-provenance__chain">
        {chain.map((step, i) => (
          <li key={i} className="source-provenance__step">
            <span className="source-provenance__label">{step.label}</span>
            {': '}
            {step.step === 'article' && step.meta?.url ? (
              <a
                href={String(step.meta.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="source-provenance__link"
              >
                {(step.detail || String(step.meta.url)).slice(0, compact ? 60 : 100)}
              </a>
            ) : (
              <span className="source-provenance__detail">{step.detail}</span>
            )}
            {step.meta?.matched_keywords ? (
              <span className="source-provenance__meta">
                {' '}
                · keywords: {(step.meta.matched_keywords as string[]).join(', ')}
              </span>
            ) : null}
            {step.meta?.date ? (
              <span className="source-provenance__meta"> · {String(step.meta.date).slice(0, 10)}</span>
            ) : null}
            {step.meta?.query_type ? (
              <span className="source-provenance__meta"> · {String(step.meta.query_type)}</span>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  )
}
