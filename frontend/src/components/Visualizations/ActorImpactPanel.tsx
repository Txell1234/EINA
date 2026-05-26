/**
 * ActorImpactPanel — actors affected per scenario with evidence-backed claims
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { intelligenceService } from '../../services/api'
import SourceProvenance from '../shared/SourceProvenance'

interface ActorImpactPanelProps {
  caseId: number
}

type ClaimEvidence = {
  statement_id?: number
  source_url?: string
  source_date?: string
  excerpt?: string
}

type Claim = {
  claim?: string
  confidence?: number
  scenario_name?: string
  method?: string
  evidence?: ClaimEvidence[]
  has_cited_evidence?: boolean
}

type ScenarioJustification = {
  scenario_name?: string
  base_probability_pct?: number
  estimated_probability_pct?: number
  adjustment_points?: number
  rationale?: string
}

type ScenarioRow = {
  name?: string
  scenario_type?: string
  possibility?: string
  possibility_rationale?: string
  probability?: string
  probability_label?: string
  estimated_probability_pct?: number
  base_probability_pct?: number
  adjustment_points?: number
  rationale?: string
}

type ActorRow = {
  name?: string
  motivation?: string
  motivation_sources?: string[]
  avg_posture?: number
  statement_count?: number
  topics?: string[]
}

type DataFreshness = {
  stale?: boolean
  reasons?: string[]
  saved_at?: string | null
}

type OsintSignals = {
  total_statements?: number
  hostile_statements?: number
  cooperative_statements?: number
  conflict_events?: number
  avg_geopolitical_risk?: number | string
}

type Validation = {
  export_ready?: boolean
  claims_without_citation?: number
}

function claimHasCitation(c: Claim): boolean {
  if (c.has_cited_evidence !== undefined) return c.has_cited_evidence
  return (c.evidence ?? []).some((ev) => Boolean(ev.source_url?.trim()))
}

export default function ActorImpactPanel({ caseId }: ActorImpactPanelProps) {
  const queryClient = useQueryClient()
  const [expandedClaim, setExpandedClaim] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['actor-impact', caseId],
    queryFn: () => intelligenceService.getActorImpact(caseId),
    enabled: !!caseId,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => intelligenceService.analyzeActorImpact(caseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actor-impact', caseId] })
    },
  })

  if (isLoading) {
    return <div className="spinner" style={{ margin: '1rem auto' }} />
  }

  const hasData = data?.has_data
  const validation = (data?.validation ?? {}) as Validation
  const signals = (data?.osint_signals ?? {}) as OsintSignals
  const justifications = (data?.scenario_justifications ?? []) as ScenarioJustification[]
  const scenarioRows = (data?.scenarios ?? []) as ScenarioRow[]
  const actors = (data?.actors ?? []) as ActorRow[]
  const freshness = (data?.data_freshness ?? {}) as DataFreshness
  const claims = (data?.claims ?? []) as Claim[]
  const matrix = (data?.impact_matrix ?? []) as Array<{
    actor?: string
    scenario_name?: string
    impact_score?: number
    confidence?: number
  }>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 600, color: 'var(--color-primary)' }}>
          Impacte sobre actors i escenaris
        </h3>
        <button
          type="button"
          className="btn btn-primary"
          style={{ fontSize: 'var(--font-size-xs)', padding: '6px 12px' }}
          disabled={analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
        >
          {analyzeMutation.isPending ? 'Analitzant…' : 'Recalcular impacte'}
        </button>
      </div>

      {!hasData ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎯</div>
          <h3 className="empty-state-title">Sense dades d&apos;impacte</h3>
          <p className="empty-state-desc">
            Cal extracció OSINT i, idealment, escenaris prospectius. Executa el pipeline d&apos;intel·ligència.
          </p>
        </div>
      ) : (
        <>
          {freshness.stale && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: '#e7f1ff',
                color: '#0c5460',
                fontSize: 'var(--font-size-sm)',
                border: '1px solid #bee5eb',
              }}
            >
              <strong>Dades noves disponibles</strong> — l&apos;avaluació guardada pot estar desactualitzada
              {freshness.saved_at ? ` (última: ${freshness.saved_at})` : ''}. Prem «Recalcular impacte» per
              incorporar alertes, extracció i Tavily Research.
            </div>
          )}

          {validation.export_ready === false && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: '#fff3cd',
                color: '#856404',
                fontSize: 'var(--font-size-sm)',
                border: '1px solid #ffeeba',
              }}
            >
              <strong>Avís de traçabilitat:</strong> {validation.claims_without_citation ?? 0}{' '}
              conclusió(ns) sense citació verificable. Revisa l&apos;extracció OSINT abans d&apos;exportar
              l&apos;informe.
            </div>
          )}

          {data?.summary ? (
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)', margin: 0 }}>
              {data.summary.actor_count} actors · {data.summary.scenario_count} escenaris ·{' '}
              {data.summary.claim_count} conclusions · confiança {data.summary.overall_confidence}%
              {data.summary.most_likely_scenario
                ? ` · escenari més probable: ${data.summary.most_likely_scenario}`
                : ''}
            </p>
          ) : null}

          {Object.keys(signals).length > 0 && (
            <div
              style={{
                padding: '10px 12px',
                background: 'var(--color-gray-50)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              <strong style={{ display: 'block', marginBottom: 4, color: 'var(--color-primary)' }}>
                Senyals OSINT
              </strong>
              {signals.total_statements ?? 0} declaracions · {signals.hostile_statements ?? 0} hostils ·{' '}
              {signals.cooperative_statements ?? 0} cooperatives · {signals.conflict_events ?? 0} esdeveniments
              de conflicte · risc geo mitjà {signals.avg_geopolitical_risk ?? '—'}/100
            </div>
          )}

          {(scenarioRows.length > 0 || justifications.length > 0) && (
            <div>
              <h4 style={{ fontSize: 'var(--font-size-sm)', margin: '0 0 8px', color: 'var(--color-primary)' }}>
                Justificació d&apos;escenaris · possibilitat i probabilitat
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-xs)' }}>
                  <thead>
                    <tr style={{ background: 'var(--color-primary)', color: 'white' }}>
                      <th style={{ padding: 6, textAlign: 'left' }}>Escenari</th>
                      <th style={{ padding: 6 }}>Possibilitat</th>
                      <th style={{ padding: 6 }}>Base</th>
                      <th style={{ padding: 6 }}>Estimada</th>
                      <th style={{ padding: 6 }}>Ajust</th>
                      <th style={{ padding: 6, textAlign: 'left' }}>Raonament</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(scenarioRows.length > 0 ? scenarioRows : justifications).map((row, i) => {
                      const name =
                        'name' in row && row.name
                          ? row.name
                          : (row as ScenarioJustification).scenario_name
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--color-gray-100)' }}>
                          <td style={{ padding: 6 }}>{name}</td>
                          <td style={{ padding: 6, textAlign: 'center' }}>
                            {'possibility' in row ? row.possibility : '—'}
                          </td>
                          <td style={{ padding: 6, textAlign: 'center' }}>
                            {row.base_probability_pct ?? '—'}%
                          </td>
                          <td style={{ padding: 6, textAlign: 'center', fontWeight: 700 }}>
                            {row.estimated_probability_pct ?? '—'}%
                          </td>
                          <td style={{ padding: 6, textAlign: 'center' }}>
                            {(row.adjustment_points ?? 0) >= 0 ? '+' : ''}
                            {row.adjustment_points ?? 0}
                          </td>
                          <td style={{ padding: 6 }}>{row.rationale}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {actors.filter((a) => a.motivation).length > 0 && (
            <div>
              <h4 style={{ fontSize: 'var(--font-size-sm)', margin: '0 0 8px', color: 'var(--color-primary)' }}>
                Motivació d&apos;actors
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {actors
                  .filter((a) => a.motivation)
                  .slice(0, 8)
                  .map((a, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '8px 12px',
                        background: 'var(--color-gray-50)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--font-size-xs)',
                      }}
                    >
                      <strong>{a.name}</strong>
                      {(a.motivation_sources?.length ?? 0) > 0 && (
                        <span style={{ color: 'var(--color-gray-500)', marginLeft: 6 }}>
                          [{a.motivation_sources?.join(', ')}]
                        </span>
                      )}
                      <p style={{ margin: '4px 0 0' }}>{a.motivation}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {claims.length > 0 && (
            <div>
              <h4 style={{ fontSize: 'var(--font-size-sm)', margin: '0 0 8px', color: 'var(--color-primary)' }}>
                Conclusions justificades
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {claims.slice(0, 8).map((c, i) => {
                  const cited = claimHasCitation(c)
                  const primaryStatementId = (c.evidence ?? []).find((ev) => ev.statement_id)?.statement_id
                  const isExpanded = expandedClaim === i
                  return (
                    <div
                      key={i}
                      style={{
                        borderLeft: `3px solid ${cited ? 'var(--color-primary)' : '#dc3545'}`,
                        padding: '8px 12px',
                        background: cited ? 'var(--color-gray-50)' : '#fff5f5',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {!cited && (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: '#dc3545',
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                          }}
                        >
                          Sense citació
                        </span>
                      )}
                      <p style={{ margin: '0 0 4px', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                        {c.claim}
                      </p>
                      <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>
                        {c.confidence}% · {c.scenario_name} · {c.method}
                      </p>
                      {(c.evidence ?? []).slice(0, 2).map((ev, j) => (
                        <p key={j} style={{ margin: '4px 0 0', fontSize: 10, color: 'var(--color-gray-600)' }}>
                          {ev.source_date ? `${ev.source_date} · ` : ''}
                          {ev.source_url ? (
                            <a href={ev.source_url} target="_blank" rel="noopener noreferrer">
                              Font
                            </a>
                          ) : (
                            'Sense URL'
                          )}
                          {ev.excerpt ? ` · «${ev.excerpt.slice(0, 100)}…»` : ''}
                        </p>
                      ))}
                      {primaryStatementId ? (
                        <button
                          type="button"
                          className="btn"
                          style={{ fontSize: 10, padding: '4px 8px', marginTop: 6 }}
                          onClick={() => setExpandedClaim(isExpanded ? null : i)}
                        >
                          {isExpanded ? 'Amagar traçabilitat' : 'Veure traçabilitat'}
                        </button>
                      ) : null}
                      {isExpanded && primaryStatementId ? (
                        <div style={{ marginTop: 8 }}>
                          <SourceProvenance statementId={primaryStatementId} compact />
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {matrix.length > 0 && (
            <div>
              <h4 style={{ fontSize: 'var(--font-size-sm)', margin: '0 0 8px' }}>Matriu actor × escenari</h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-xs)' }}>
                  <thead>
                    <tr style={{ background: 'var(--color-primary)', color: 'white' }}>
                      <th style={{ padding: 6, textAlign: 'left' }}>Actor</th>
                      <th style={{ padding: 6 }}>Escenari</th>
                      <th style={{ padding: 6 }}>Impacte</th>
                      <th style={{ padding: 6 }}>Conf.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...matrix]
                      .sort((a, b) => (a.impact_score ?? 0) - (b.impact_score ?? 0))
                      .slice(0, 15)
                      .map((row, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--color-gray-100)' }}>
                          <td style={{ padding: 6 }}>{row.actor}</td>
                          <td style={{ padding: 6 }}>{row.scenario_name}</td>
                          <td style={{ padding: 6, textAlign: 'center', fontWeight: 700 }}>{row.impact_score}</td>
                          <td style={{ padding: 6, textAlign: 'center' }}>{row.confidence}%</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
