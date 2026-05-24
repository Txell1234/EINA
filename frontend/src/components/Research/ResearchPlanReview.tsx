import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import './ResearchPlanReview.css'

interface ResearchPlanReviewProps {
  caseId: number
  isOpen: boolean
  onClose: () => void
  onApprove: (plan: any) => void
  researchPlan?: any
  osintOnly?: boolean
}

interface ResearchPhase {
  phase: string
  phase_name: string
  queries: Array<{
    type: string
    params: Record<string, any>
    rationale?: string
  }>
}

export default function ResearchPlanReview({
  caseId,
  isOpen,
  onClose,
  onApprove,
  researchPlan,
  osintOnly = false,
}: ResearchPlanReviewProps) {
  const [plan, setPlan] = useState<any>(researchPlan)
  const [editingQuery, setEditingQuery] = useState<number | null>(null)
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  const { data: integrationStatus } = useQuery({
    queryKey: ['integration-status'],
    queryFn: async () => {
      const response = await api.get('/api/integration/status')
      return response.data
    },
    enabled: isOpen,
    staleTime: 60_000,
  })

  const newsApiConfigured =
    plan?.news_api_configured ??
    integrationStatus?.osint_apis?.news_api?.configured ??
    true

  useEffect(() => {
    if (researchPlan) {
      setPlan(researchPlan)
      // Expand all phases by default
      const phases = new Set<string>(
        researchPlan.research_phases?.map((p: ResearchPhase) => p.phase) || [],
      )
      setExpandedPhases(phases)
    }
  }, [researchPlan])

  const approveMutation = useMutation({
    mutationFn: async (approvedPlan: any) => {
      const response = await api.post(`/api/research/plan/${caseId}/approve`, approvedPlan)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['researchPlan', caseId] })
      queryClient.invalidateQueries({ queryKey: ['researchStatus', caseId] })
      onApprove(plan)
      onClose()
    }
  })

  const handleApprove = () => {
    approveMutation.mutate(plan)
  }

  const handleTogglePhase = (phase: string) => {
    const newExpanded = new Set(expandedPhases)
    if (newExpanded.has(phase)) {
      newExpanded.delete(phase)
    } else {
      newExpanded.add(phase)
    }
    setExpandedPhases(newExpanded)
  }

  const handleRemoveQuery = (phaseIndex: number, queryIndex: number) => {
    const newPlan = { ...plan }
    newPlan.research_phases[phaseIndex].queries.splice(queryIndex, 1)
    setPlan(newPlan)
  }

  const handleEditQuery = (phaseIndex: number, queryIndex: number) => {
    setEditingQuery(phaseIndex * 1000 + queryIndex)
  }

  const getQueryTypeName = (type: string): string => {
    const typeNames: Record<string, string> = {
      'google_news': 'Google News',
      'gdelt': 'GDELT',
      'rss_feed': 'RSS (think-tank)',
      'rss_url': 'RSS/Substack (URL curada)',
      'ensembledata_twitter_keyword_posts': 'Twitter/X (EnsembleData)',
      'ensembledata_instagram_hashtag_posts': 'Instagram (EnsembleData)',
      'ensembledata_tiktok_keyword_posts': 'TikTok (EnsembleData)',
      'ensembledata_youtube_keyword_posts': 'YouTube (EnsembleData)',
      'ensembledata_threads_keyword_posts': 'Threads (EnsembleData)',
      'ensembledata_reddit_subreddit_posts': 'Reddit (EnsembleData)',
      'reddit': 'Reddit',
      'github': 'GitHub',
      'sherlock': 'Sherlock',
      'recon-ng': 'Recon-ng',
      'theharvester': 'theHarvester'
    }
    return typeNames[type] || type
  }

  if (!isOpen || !plan) return null

  const totalQueries = plan.research_phases?.reduce((sum: number, phase: ResearchPhase) => 
    sum + (phase.queries?.length || 0), 0) || 0

  return (
    <div className="research-plan-overlay" onClick={onClose}>
      <div className="research-plan-modal" onClick={(e) => e.stopPropagation()}>
        <div className="research-plan-header">
          <h2>
            {osintOnly
              ? '📡 Recollida OSINT — Revisió i aprovació'
              : '📋 Pla de recerca IA — Revisió i aprovació'}
          </h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="research-plan-content">
          {!osintOnly && (
            <p className="plan-permission-notice">
              Revisa les cerques OSINT proposades i les variables/factors abans d&apos;executar.
              Res es recollirà sense la teva aprovació.
            </p>
          )}
          {osintOnly && (
            <p className="plan-permission-notice">
              Mode manual: només s&apos;executarà la recollida OSINT. Les variables les defines tu
              al mòdul prospectiu.
            </p>
          )}
          {!newsApiConfigured && (
            <p className="plan-permission-notice" style={{ borderColor: '#f59e0b' }}>
              NEWS_API_KEY no configurada: les cerques <strong>google_news</strong> usaran Google
              News RSS (gratuït). GDELT i RSS no requereixen clau API.
            </p>
          )}
          {/* Plan Summary */}
          <div className="plan-summary">
            <div className="summary-item">
              <strong>Tipus de Cas:</strong> {plan.case_type || 'General'}
            </div>
            <div className="summary-item">
              <strong>Fases de Recerca:</strong> {plan.research_phases?.length || 0}
            </div>
            <div className="summary-item">
              <strong>Total Consultes:</strong> {totalQueries}
            </div>
            <div className="summary-item">
              <strong>Durada Estimada:</strong> {plan.estimated_duration || 'N/A'}
            </div>
            <div className="summary-item">
              <strong>Fonts de Dades:</strong> {plan.data_sources?.join(', ') || 'N/A'}
            </div>
            {plan.research_strategy && (
              <div className="summary-item full-width">
                <strong>Estratègia de Recerca:</strong> {plan.research_strategy}
              </div>
            )}
            {plan.curated_feeds && plan.curated_feeds.length > 0 && (
              <div className="summary-item full-width">
                <strong>Fonts curades (RSS/Substack):</strong>{' '}
                {(plan.curated_feeds as string[]).join(', ')}
              </div>
            )}
          </div>

          {/* Key Entities */}
          {plan.key_entities && plan.key_entities.length > 0 && (
            <div className="key-entities">
              <h3>🔑 Entitats Clau a Rastrejar</h3>
              <div className="entities-list">
                {plan.key_entities.map((entity: string, idx: number) => (
                  <span key={idx} className="entity-tag">{entity}</span>
                ))}
              </div>
            </div>
          )}

          {!osintOnly && plan.suggested_variables?.length > 0 && (
            <div className="suggested-variables">
              <h3>📊 Variables proposades (MIC-MAC)</h3>
              <ul className="suggestion-list">
                {plan.suggested_variables.map((v: any, idx: number) => (
                  <li key={idx}>
                    <strong>{v.code ? `${v.code} — ` : ''}{v.name}</strong>
                    {v.var_type && <span className="suggestion-meta"> ({v.var_type})</span>}
                    {v.description && <p className="suggestion-desc">{v.description}</p>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!osintOnly && plan.suggested_actors?.length > 0 && (
            <div className="suggested-actors">
              <h3>👥 Actors proposats (MACTOR)</h3>
              <ul className="suggestion-list">
                {plan.suggested_actors.map((a: any, idx: number) => (
                  <li key={idx}>
                    <strong>{a.code ? `${a.code} — ` : ''}{a.name}</strong>
                    {a.strategic_goals?.length > 0 && (
                      <p className="suggestion-desc">{a.strategic_goals.join(' · ')}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Temporal Scope */}
          {plan.temporal_scope && (
            <div className="temporal-scope">
              <h3>⏱️ Abast Temporal</h3>
              <div className="scope-details">
                <div><strong>Històric:</strong> {plan.temporal_scope.historical || 'N/A'}</div>
                <div><strong>Actual:</strong> {plan.temporal_scope.current || 'N/A'}</div>
                <div><strong>Monitorització:</strong> {plan.temporal_scope.monitoring || 'N/A'}</div>
              </div>
            </div>
          )}

          {/* Research Phases */}
          <div className="research-phases">
            <h3>📊 Fases de Recerca</h3>
            {plan.research_phases?.map((phase: ResearchPhase, phaseIndex: number) => (
              <div key={phaseIndex} className="phase-card">
                <div 
                  className="phase-header"
                  onClick={() => handleTogglePhase(phase.phase)}
                >
                  <div className="phase-title">
                    <span className="phase-icon">
                      {phase.phase === 'initial' && '🚀'}
                      {phase.phase === 'deep_dive' && '🔍'}
                      {phase.phase === 'monitoring' && '👁️'}
                      {!['initial', 'deep_dive', 'monitoring'].includes(phase.phase) && '📋'}
                    </span>
                    <span className="phase-name">{phase.phase_name || phase.phase}</span>
                    <span className="phase-badge">{phase.queries?.length || 0} consultes</span>
                  </div>
                  <span className="expand-icon">
                    {expandedPhases.has(phase.phase) ? '▼' : '▶'}
                  </span>
                </div>

                {expandedPhases.has(phase.phase) && (
                  <div className="phase-queries">
                    {phase.queries?.map((query, queryIndex: number) => (
                      <div key={queryIndex} className="query-item">
                        <div className="query-header">
                          <div className="query-type">
                            <strong>{getQueryTypeName(query.type)}</strong>
                            {query.rationale && (
                              <span className="query-rationale">💡 {query.rationale}</span>
                            )}
                          </div>
                          <div className="query-actions">
                            <button 
                              className="btn-edit"
                              onClick={() => handleEditQuery(phaseIndex, queryIndex)}
                            >
                              ✏️ Editar
                            </button>
                            <button 
                              className="btn-remove"
                              onClick={() => handleRemoveQuery(phaseIndex, queryIndex)}
                            >
                              🗑️ Eliminar
                            </button>
                          </div>
                        </div>
                        <div className="query-params">
                          <strong>Paràmetres:</strong>
                          <pre>{JSON.stringify(query.params, null, 2)}</pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="research-plan-footer">
          <button className="btn-cancel" onClick={onClose}>
            Cancel·lar
          </button>
          <button
            className="btn-approve"
            onClick={handleApprove}
            disabled={approveMutation.isPending || totalQueries === 0}
          >
            {approveMutation.isPending
              ? 'Executant…'
              : osintOnly
                ? `✅ Aprovar recollida OSINT (${totalQueries} consultes)`
                : `✅ Aprovar pla complet (${totalQueries} OSINT + extracció)`}
          </button>
        </div>
      </div>
    </div>
  )
}



