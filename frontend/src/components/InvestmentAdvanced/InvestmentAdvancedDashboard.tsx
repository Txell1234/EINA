import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { prospectiveService } from '../../services/api'
import ESGAnalysis from './ESGAnalysis'
import GeopoliticalImpactChart from './GeopoliticalImpactChart'
import MarketOpportunityComparison from './MarketOpportunityComparison'
import RegulatoryRiskAssessment from './RegulatoryRiskAssessment'
import './InvestmentAdvancedDashboard.css'

const DEMO_ESG = {
  esg_score: 68,
  environmental_score: 72,
  social_score: 65,
  governance_score: 67,
  recommendations: ['Millorar transparència de supply chain', 'Reforçar polítiques socials'],
}

interface MonitorRow {
  id: number
  indicator: string
  keywords: string[]
  osint_sources: string[]
  is_active: boolean
  match_count: number
  last_checked: string | null
  last_match: string | null
}

export default function InvestmentAdvancedDashboard() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'alerts' | 'investment'>('alerts')
  const [projectId, setProjectId] = useState<number | null>(null)
  const [investTab, setInvestTab] = useState<'esg' | 'geo' | 'market' | 'regulatory'>('esg')

  const { data: projects = [] } = useQuery({
    queryKey: ['prospective-projects'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const { data: monitors = [], isLoading: loadingMonitors } = useQuery({
    queryKey: ['alert-monitors', projectId],
    queryFn: () => prospectiveService.listMonitors(projectId!),
    enabled: projectId !== null && tab === 'alerts',
  })

  const checkMutation = useMutation({
    mutationFn: (monitorId: number) => prospectiveService.checkMonitor(monitorId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['alert-monitors', projectId] })
    },
  })

  const checkAllMutation = useMutation({
    mutationFn: async () => {
      const rows = monitors as MonitorRow[]
      for (const m of rows.filter((x) => x.is_active)) {
        await prospectiveService.checkMonitor(m.id)
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['alert-monitors', projectId] })
    },
  })

  return (
    <div className="investment-advanced-dashboard">
      <div className="tab-bar">
        <button type="button" className={tab === 'alerts' ? 'active' : ''} onClick={() => setTab('alerts')}>
          Alertes OSINT
        </button>
        <button
          type="button"
          className={tab === 'investment' ? 'active' : ''}
          onClick={() => setTab('investment')}
        >
          Inversió avançada
        </button>
      </div>

      {tab === 'alerts' && (
        <div className="card" style={{ marginTop: 'var(--spacing-md)' }}>
          <h2>Monitors d&apos;alerta primerenca</h2>
          <p style={{ color: 'var(--color-gray-600)', fontSize: 'var(--font-size-sm)' }}>
            Indicadors extrets dels escenaris prospectius. Es comproven automàticament cada 30 minuts
            contra GDELT, Google News i Reddit.
          </p>

          <div className="prospective-field" style={{ maxWidth: 420, marginBottom: 'var(--spacing-lg)' }}>
            <label htmlFor="monitor-project">Projecte prospectiu</label>
            <select
              id="monitor-project"
              className="prospective-select"
              value={projectId ?? ''}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">— Selecciona projecte —</option>
              {(projects as { id: number; title: string }[]).map((p) => (
                <option key={p.id} value={p.id}>
                  #{p.id} — {p.title}
                </option>
              ))}
            </select>
          </div>

          {projectId !== null && (
            <>
              <div className="prospective-actions" style={{ marginBottom: 'var(--spacing-md)' }}>
                <button
                  type="button"
                  className="btn btn-accent"
                  disabled={checkAllMutation.isPending || (monitors as MonitorRow[]).length === 0}
                  onClick={() => checkAllMutation.mutate()}
                >
                  {checkAllMutation.isPending ? 'Comprovant...' : 'Comprovar tots ara'}
                </button>
              </div>

              {loadingMonitors && <p>Carregant monitors...</p>}

              {!loadingMonitors && (monitors as MonitorRow[]).length === 0 && (
                <div className="empty-state">
                  <p className="empty-state-desc">
                    Cap monitor actiu. Activa monitoratge des del pas d&apos;escenaris del wizard
                    prospectiu.
                  </p>
                </div>
              )}

              <ul className="project-list">
                {(monitors as MonitorRow[]).map((m) => (
                  <li key={m.id} style={{ cursor: 'default', marginBottom: 'var(--spacing-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                      <div>
                        <strong>{m.indicator.slice(0, 120)}{m.indicator.length > 120 ? '…' : ''}</strong>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-600)', marginTop: 4 }}>
                          Keywords: {(m.keywords ?? []).join(', ') || '—'} · Fonts:{' '}
                          {(m.osint_sources ?? []).join(', ')}
                        </div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)', marginTop: 2 }}>
                          Coincidències: {m.match_count ?? 0}
                          {m.last_match && ` · Últim match: ${new Date(m.last_match).toLocaleString('ca-ES')}`}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn"
                        disabled={checkMutation.isPending || !m.is_active}
                        onClick={() => checkMutation.mutate(m.id)}
                      >
                        Comprovar
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {tab === 'investment' && (
        <>
          <div className="tab-bar" style={{ marginTop: 'var(--spacing-md)' }}>
            <button
              type="button"
              className={investTab === 'esg' ? 'active' : ''}
              onClick={() => setInvestTab('esg')}
            >
              ESG
            </button>
            <button
              type="button"
              className={investTab === 'geo' ? 'active' : ''}
              onClick={() => setInvestTab('geo')}
            >
              Impacte geopolític
            </button>
            <button
              type="button"
              className={investTab === 'market' ? 'active' : ''}
              onClick={() => setInvestTab('market')}
            >
              Mercat
            </button>
            <button
              type="button"
              className={investTab === 'regulatory' ? 'active' : ''}
              onClick={() => setInvestTab('regulatory')}
            >
              Risc regulatori
            </button>
          </div>
          {investTab === 'esg' && <ESGAnalysis data={DEMO_ESG} />}
          {investTab === 'geo' && (
            <GeopoliticalImpactChart data={{ impacts: [], investment_type: 'equity' }} />
          )}
          {investTab === 'market' && (
            <MarketOpportunityComparison
              data={{ opportunities: [], comparison_date: new Date().toISOString() }}
            />
          )}
          {investTab === 'regulatory' && (
            <RegulatoryRiskAssessment data={{}} country="Espanya" />
          )}
        </>
      )}
    </div>
  )
}
