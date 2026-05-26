/**
 * FinancialIntelWidget — Real-time financial intelligence
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { financialService, geopoliticalService, investmentsService } from '../../services/api'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts'

interface FinancialIntelWidgetProps {
  caseId?: number
  watchlist?: string[]
}

interface InvestmentRisk {
  risk_type?: string
  risk_percentage?: number
  risk_level?: string
  description?: string
  country?: string
  source?: 'investment' | 'geopolitical'
}

interface GeoRisk {
  country: string
  overall_risk_score?: number
  political_stability_risk?: number
  conflict_risk?: number
  economic_risk?: number
}

const DEFAULT_WATCHLIST = ['EUR', 'CNY', 'JPY', 'GBP']

export default function FinancialIntelWidget({
  caseId,
  watchlist = DEFAULT_WATCHLIST,
}: FinancialIntelWidgetProps) {
  const [activeTab, setActiveTab] = useState<'risk' | 'forex' | 'radar' | 'sanctions'>('risk')
  const [sanctionQuery, setSanctionQuery] = useState('')

  const { data: invRisks, isLoading: invRisksLoading } = useQuery({
    queryKey: ['inv-risks', caseId],
    queryFn: () => investmentsService.getRisks(caseId),
    refetchInterval: 120_000,
    enabled: !!caseId,
  })

  const { data: geoRisks, isLoading: geoRisksLoading } = useQuery({
    queryKey: ['geo-risks-financial', caseId],
    queryFn: () => geopoliticalService.getRisks(caseId),
    enabled: !!caseId,
  })

  const risksLoading = invRisksLoading || geoRisksLoading

  const { data: fxData, isLoading: fxLoading } = useQuery({
    queryKey: ['currency-rates'],
    queryFn: () => financialService.getCurrencyRates('USD'),
    refetchInterval: 60_000,
    enabled: activeTab === 'forex',
  })

  const { data: sanctionsData, isFetching: sanctionsFetching } = useQuery({
    queryKey: ['sanctions', sanctionQuery],
    queryFn: () => financialService.getSanctionedEntities(sanctionQuery),
    enabled: sanctionQuery.length >= 3,
  })

  const riskList: InvestmentRisk[] = (() => {
    const inv = Array.isArray(invRisks) ? invRisks : []
    if (inv.length > 0) {
      return inv.map((r: InvestmentRisk) => ({ ...r, source: 'investment' as const }))
    }
    const geo = (Array.isArray(geoRisks) ? geoRisks : []) as GeoRisk[]
    return geo.map((r) => ({
      risk_type: r.country,
      risk_percentage: Math.round(r.overall_risk_score ?? 0),
      risk_level:
        (r.overall_risk_score ?? 0) > 70 ? 'critical' : (r.overall_risk_score ?? 0) > 40 ? 'high' : 'medium',
      description: `Polític ${Math.round(r.political_stability_risk ?? 0)} · Conflicte ${Math.round(r.conflict_risk ?? 0)} · Econòmic ${Math.round(r.economic_risk ?? 0)}`,
      country: r.country,
      source: 'geopolitical' as const,
    }))
  })()

  const radarData = ['political', 'economic', 'security', 'regulatory', 'social'].map((cat) => ({
    category: cat.charAt(0).toUpperCase() + cat.slice(1),
    value:
      Math.round(
        riskList
          .filter((r) => r.risk_type?.toLowerCase().includes(cat))
          .reduce((acc, r) => acc + (r.risk_percentage ?? 0), 0) /
          Math.max(riskList.filter((r) => r.risk_type?.toLowerCase().includes(cat)).length, 1),
      ) || 0,
  }))

  const fxRates = (fxData?.rates ?? {}) as Record<string, number>
  const fxRows = watchlist.map((curr) => ({
    currency: curr,
    rate: fxRates[curr] ? (1 / fxRates[curr]).toFixed(4) : '—',
  }))

  const TABS = [
    { id: 'risk' as const, label: 'Riscos' },
    { id: 'forex' as const, label: 'Divises' },
    { id: 'radar' as const, label: 'Radar' },
    { id: 'sanctions' as const, label: 'Sancions' },
  ]

  const sanctionsResults = (sanctionsData as { results?: Array<{ name?: string; schema?: string; datasets?: string[] }> })
    ?.results

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <h3
          style={{
            margin: 0,
            fontSize: 'var(--font-size-base)',
            fontWeight: 600,
            color: 'var(--color-primary)',
          }}
        >
          Intel·ligència financera
        </h3>
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '4px 12px',
                borderRadius: 4,
                cursor: 'pointer',
                border: '1px solid var(--color-gray-200)',
                background: activeTab === t.id ? 'var(--color-primary)' : 'transparent',
                color: activeTab === t.id ? 'white' : 'var(--color-gray-600)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 500,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'risk' && (
        <>
          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
            {[
              { label: 'Riscos totals', val: riskList.length, color: 'var(--color-primary)' },
              {
                label: 'Crítics',
                val: riskList.filter((r) => r.risk_level === 'critical').length,
                color: 'var(--color-danger)',
              },
              {
                label: 'Alts',
                val: riskList.filter((r) => r.risk_level === 'high').length,
                color: 'var(--color-warning)',
              },
              {
                label: 'Score mig',
                val:
                  riskList.length > 0
                    ? Math.round(
                        riskList.reduce((a, r) => a + (r.risk_percentage ?? 0), 0) / riskList.length,
                      )
                    : 0,
                color: 'var(--color-gray-600)',
              },
            ].map(({ label, val, color }) => (
              <div
                key={label}
                style={{
                  flex: 1,
                  minWidth: 100,
                  textAlign: 'center',
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-sm)',
                  padding: 'var(--spacing-sm)',
                }}
              >
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color }}>{val}</div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>{label}</div>
              </div>
            ))}
          </div>

          {risksLoading ? (
            <div className="spinner" style={{ margin: '1rem auto' }} />
          ) : riskList.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <h3 className="empty-state-title">Sense riscos calculats</h3>
              <p className="empty-state-desc">
                Executa el pipeline des de Intelligence Unit (riscos geopolítics o recomanació d&apos;inversió).
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[...riskList]
                .sort((a, b) => (b.risk_percentage ?? 0) - (a.risk_percentage ?? 0))
                .slice(0, 8)
                .map((risk, i) => {
                  const score = risk.risk_percentage ?? 0
                  const barColor =
                    score > 70 ? 'var(--color-danger)' : score > 40 ? 'var(--color-warning)' : 'var(--color-success)'
                  return (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-sm)',
                        padding: '6px 0',
                        borderBottom: '1px solid var(--color-gray-100)',
                        fontSize: 'var(--font-size-xs)',
                      }}
                    >
                      <span
                        style={{
                          flex: 1,
                          color: 'var(--color-gray-800)',
                          fontWeight: 500,
                          textTransform: 'capitalize',
                        }}
                      >
                        {risk.risk_type?.replace(/_/g, ' ') ?? 'Risc'}
                      </span>
                      <div
                        style={{
                          width: 100,
                          height: 8,
                          background: 'var(--color-gray-200)',
                          borderRadius: 4,
                          overflow: 'hidden',
                        }}
                      >
                        <div style={{ width: `${score}%`, height: '100%', background: barColor, borderRadius: 4 }} />
                      </div>
                      <span style={{ width: 30, textAlign: 'right', fontWeight: 700, color: barColor }}>{score}</span>
                    </div>
                  )
                })}
            </div>
          )}
        </>
      )}

      {activeTab === 'forex' && (
        <div>
          {fxLoading ? (
            <div className="spinner" style={{ margin: '1rem auto' }} />
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
              <thead>
                <tr style={{ background: 'var(--color-primary)', color: 'white' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left' }}>Divisa</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right' }}>USD/divisa</th>
                </tr>
              </thead>
              <tbody>
                {fxRows.map((row, i) => (
                  <tr
                    key={row.currency}
                    style={{
                      background: i % 2 === 0 ? 'transparent' : 'var(--color-gray-50)',
                      borderBottom: '1px solid var(--color-gray-100)',
                    }}
                  >
                    <td style={{ padding: '6px 12px', fontWeight: 600, color: 'var(--color-primary)' }}>
                      {row.currency}
                    </td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace' }}>{row.rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ fontSize: 10, color: 'var(--color-gray-400)', marginTop: 6, textAlign: 'right' }}>
            Font: Open Exchange Rates · Actualitza cada 60 s
          </p>
        </div>
      )}

      {activeTab === 'radar' && (
        <div style={{ height: 280 }}>
          {riskList.length === 0 ? (
            <div className="empty-state" style={{ height: '100%', justifyContent: 'center' }}>
              <p className="empty-state-desc">Calcula els riscos primer.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--color-gray-200)" />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: 'var(--color-gray-600)' }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9, fill: 'var(--color-gray-400)' }} />
                <Radar name="Risc" dataKey="value" stroke="#dc3545" fill="#dc3545" fillOpacity={0.25} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {activeTab === 'sanctions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
          <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
            <input
              value={sanctionQuery}
              onChange={(e) => setSanctionQuery(e.target.value)}
              placeholder="Cerca persona, empresa o entitat..."
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid var(--color-gray-300)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
            {sanctionsFetching && <div className="spinner" style={{ alignSelf: 'center' }} />}
          </div>
          {sanctionQuery.length >= 3 && !sanctionsFetching && (
            <div>
              {!sanctionsResults || sanctionsResults.length === 0 ? (
                <div
                  style={{
                    padding: 'var(--spacing-md)',
                    background: 'rgba(40,167,69,0.08)',
                    border: '1px solid rgba(40,167,69,0.3)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-success)',
                  }}
                >
                  ✓ Sense coincidències a OpenSanctions per &quot;{sanctionQuery}&quot;
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {sanctionsResults.slice(0, 5).map((r, i) => (
                    <div
                      key={i}
                      style={{
                        padding: 'var(--spacing-sm) var(--spacing-md)',
                        border: '1px solid rgba(220,53,69,0.3)',
                        borderLeft: '3px solid var(--color-danger)',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(220,53,69,0.05)',
                      }}
                    >
                      <p
                        style={{
                          margin: 0,
                          fontWeight: 600,
                          fontSize: 'var(--font-size-sm)',
                          color: 'var(--color-danger)',
                        }}
                      >
                        ⚠ {r.name ?? 'Entitat sancionada'}
                      </p>
                      <p style={{ margin: '2px 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-600)' }}>
                        {r.schema} · {(r.datasets ?? []).join(', ')}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {sanctionQuery.length < 3 && (
            <p
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-gray-500)',
                textAlign: 'center',
                padding: 'var(--spacing-lg)',
              }}
            >
              Escriu almenys 3 caràcters per consultar OpenSanctions
            </p>
          )}
        </div>
      )}
    </div>
  )
}
