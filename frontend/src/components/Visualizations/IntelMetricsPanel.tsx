/**
 * IntelMetricsPanel — Source reliability, sentiment trends, predictive scores
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { extractService, geopoliticalService } from '../../services/api'
import ExtractStatementsTable from '../shared/ExtractStatementsTable'
import '../shared/Traceability.css'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'

interface IntelMetricsPanelProps {
  caseId: number
}

interface GeoRisk {
  country: string
  risk_3_months?: number
  risk_6_months?: number
  risk_12_months?: number
}

export default function IntelMetricsPanel({ caseId }: IntelMetricsPanelProps) {
  const [tab, setTab] = useState<'sources' | 'sentiment' | 'predictions'>('sources')
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)

  const { data: sourceData, isLoading: srcLoading } = useQuery({
    queryKey: ['source-reliability', caseId],
    queryFn: () => extractService.getSourceReliability(caseId),
    enabled: !!caseId,
  })

  const { data: statements, isLoading: stmtLoading } = useQuery({
    queryKey: ['statements-sentiment', caseId],
    queryFn: () => extractService.getStatements(caseId, 'KEEP', 0, 200),
    enabled: !!caseId && tab === 'sentiment',
  })

  const { data: domainStatements, isLoading: domainLoading } = useQuery({
    queryKey: ['statements-by-domain', caseId, selectedDomain],
    queryFn: () => extractService.getStatements(caseId, 'KEEP', 0, 100, selectedDomain!),
    enabled: !!caseId && !!selectedDomain,
  })

  const { data: risks } = useQuery({
    queryKey: ['geo-risks-pred', caseId],
    queryFn: () => geopoliticalService.getRisks(caseId),
    enabled: !!caseId,
  })

  const sentimentTimeline = (() => {
    if (!statements?.items) return []
    const byDate: Record<string, number[]> = {}
    for (const s of statements.items as Array<{ source_date?: string; posture_value?: number }>) {
      if (!s.source_date) continue
      const d = s.source_date.slice(0, 7)
      if (!byDate[d]) byDate[d] = []
      byDate[d].push(s.posture_value ?? 0)
    }
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({
        date,
        sentiment: +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2),
        n: vals.length,
      }))
  })()

  const predictionData = ((Array.isArray(risks) ? risks : []) as GeoRisk[])
    .filter((r) => r.risk_3_months || r.risk_6_months || r.risk_12_months)
    .slice(0, 6)
    .map((r) => ({
      country: r.country,
      '3 mesos': Math.round(r.risk_3_months ?? 0),
      '6 mesos': Math.round(r.risk_6_months ?? 0),
      '12 mesos': Math.round(r.risk_12_months ?? 0),
    }))

  const sources =
    (
      sourceData as {
        sources: Array<{
          domain: string
          n_statements: number
          avg_grounding: number
          hallucination_rate: number
          reliability_label: string
          main_topics: string[]
        }>
      } | null
    )?.sources ?? []

  const TABS = [
    { id: 'sources' as const, label: '🏅 Fonts' },
    { id: 'sentiment' as const, label: '📈 Sentiment' },
    { id: 'predictions' as const, label: '🔮 Prediccions' },
  ]

  return (
    <div>
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--color-gray-200)',
          marginBottom: 'var(--spacing-md)',
          gap: 0,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              setTab(t.id)
              if (t.id !== 'sources') setSelectedDomain(null)
            }}
            style={{
              padding: '8px 16px',
              border: 'none',
              cursor: 'pointer',
              background: 'none',
              borderBottom: tab === t.id ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: tab === t.id ? 'var(--color-primary)' : 'var(--color-gray-500)',
              fontWeight: tab === t.id ? 600 : 400,
              fontSize: 'var(--font-size-sm)',
              transition: 'all .15s',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'sources' &&
        (srcLoading ? (
          <div className="spinner" style={{ margin: '1rem auto' }} />
        ) : sources.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📰</div>
            <h3 className="empty-state-title">Sense fonts</h3>
            <p className="empty-state-desc">Executa l&apos;extracció OSINT per veure la fiabilitat per font.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sources.slice(0, 10).map((src, i) => {
              const isSelected = selectedDomain === src.domain
              return (
                <button
                  key={i}
                  type="button"
                  className={`intel-domain-btn${isSelected ? ' intel-domain-btn--selected' : ''}`}
                  onClick={() => setSelectedDomain(isSelected ? null : src.domain)}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      flexShrink: 0,
                      background:
                        src.avg_grounding > 0.6
                          ? 'var(--color-success)'
                          : src.avg_grounding > 0.3
                            ? 'var(--color-warning)'
                            : 'var(--color-danger)',
                    }}
                  />
                  <span
                    style={{
                      flex: 1,
                      fontWeight: 500,
                      color: 'var(--color-gray-800)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {src.domain}
                  </span>
                  <span style={{ color: 'var(--color-gray-400)', minWidth: 50 }}>{src.n_statements} decl.</span>
                  <div
                    style={{
                      width: 80,
                      height: 6,
                      background: 'var(--color-gray-200)',
                      borderRadius: 3,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${src.avg_grounding * 100}%`,
                        height: '100%',
                        background:
                          src.avg_grounding > 0.6
                            ? 'var(--color-success)'
                            : src.avg_grounding > 0.3
                              ? 'var(--color-warning)'
                              : 'var(--color-danger)',
                        borderRadius: 3,
                      }}
                    />
                  </div>
                  <span
                    style={{
                      fontWeight: 700,
                      minWidth: 30,
                      textAlign: 'right',
                      color:
                        src.avg_grounding > 0.6
                          ? 'var(--color-success)'
                          : src.avg_grounding > 0.3
                            ? '#856404'
                            : 'var(--color-danger)',
                    }}
                  >
                    {Math.round(src.avg_grounding * 100)}%
                  </span>
                </button>
              )
            })}

            {selectedDomain ? (
              <div className="intel-domain-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <h4 style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-primary)' }}>
                    Declaracions de {selectedDomain}
                  </h4>
                  <button type="button" className="btn" style={{ fontSize: 10, padding: '4px 8px' }} onClick={() => setSelectedDomain(null)}>
                    Tancar
                  </button>
                </div>
                {domainLoading ? (
                  <div className="spinner" style={{ margin: '1rem auto' }} />
                ) : (
                  <ExtractStatementsTable statements={domainStatements?.items ?? []} />
                )}
              </div>
            ) : (
              <p style={{ fontSize: 10, color: 'var(--color-gray-400)', margin: '4px 0 0' }}>
                Clica un domini per veure les declaracions d&apos;aquesta font.
              </p>
            )}
          </div>
        ))}

      {tab === 'sentiment' &&
        (stmtLoading ? (
          <div className="spinner" style={{ margin: '1rem auto' }} />
        ) : sentimentTimeline.length < 2 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📈</div>
            <h3 className="empty-state-title">Dades insuficients</h3>
            <p className="empty-state-desc">
              Cal almenys 2 mesos amb declaracions datades per construir la tendència.
            </p>
          </div>
        ) : (
          <>
            <div
              style={{
                display: 'flex',
                gap: 'var(--spacing-md)',
                marginBottom: 'var(--spacing-md)',
                flexWrap: 'wrap',
              }}
            >
              {[
                { label: 'Mesos', val: sentimentTimeline.length },
                {
                  label: 'Sentiment actual',
                  val: sentimentTimeline[sentimentTimeline.length - 1]?.sentiment?.toFixed(2) ?? '—',
                },
                {
                  label: 'Tendència',
                  val:
                    sentimentTimeline.length >= 2
                      ? sentimentTimeline[sentimentTimeline.length - 1].sentiment >
                        sentimentTimeline[sentimentTimeline.length - 2].sentiment
                        ? '↑ Millora'
                        : '↓ Deteriora'
                      : '—',
                },
              ].map(({ label, val }) => (
                <div
                  key={label}
                  style={{
                    flex: 1,
                    textAlign: 'center',
                    minWidth: 80,
                    padding: 'var(--spacing-sm)',
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <div style={{ fontWeight: 700, color: 'var(--color-primary)', fontSize: 'var(--font-size-sm)' }}>
                    {val}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>{label}</div>
                </div>
              ))}
            </div>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sentimentTimeline}>
                  <defs>
                    <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1e3a5f" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#1e3a5f" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-100)" />
                  <XAxis dataKey="date" tick={{ fontSize: 9 }} />
                  <YAxis domain={[-2, 2]} tick={{ fontSize: 9 }} />
                  <Tooltip formatter={(v: number) => [v.toFixed(2), 'Sentiment mig']} />
                  <Area type="monotone" dataKey="sentiment" stroke="#1e3a5f" fill="url(#sentGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <p style={{ fontSize: 10, color: 'var(--color-gray-400)', marginTop: 4 }}>
              Basat en posture_value (–2..+2) de les declaracions extretes per l&apos;IA.
            </p>
          </>
        ))}

      {tab === 'predictions' &&
        (predictionData.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔮</div>
            <h3 className="empty-state-title">Sense prediccions</h3>
            <p className="empty-state-desc">
              Calcula els riscos geopolítics per obtenir prediccions a 3, 6 i 12 mesos.
            </p>
          </div>
        ) : (
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={predictionData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 9 }} />
                <YAxis type="category" dataKey="country" tick={{ fontSize: 10 }} width={80} />
                <Tooltip />
                <Bar dataKey="3 mesos" fill="#1e3a5f" opacity={0.9} />
                <Bar dataKey="6 mesos" fill="#ff6b35" opacity={0.8} />
                <Bar dataKey="12 mesos" fill="#dc3545" opacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
    </div>
  )
}
