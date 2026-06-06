import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Brain, CheckCircle2, Circle, RefreshCw, Search, Zap } from 'lucide-react'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { useI18n } from '../../contexts/I18nContext'
import { useCasesList } from '../../hooks/useCasesList'
import { countPromptLines, toActiveCase } from '../../utils/caseUtils'
import { casesService, dashboardService, intelligenceService, prospectiveService } from '../../services/api'
import VisualizationsDashboard from '../Visualizations/VisualizationsDashboard'
import CreateCaseModal from '../Dashboard/CreateCaseModal'
import AnalysisScopeBar from '../shared/AnalysisScopeBar'
import { useAnalysisScope } from '../../hooks/useAnalysisScope'
import { useCaseScopeProfile } from '../../hooks/useCaseScopeProfile'
import ActorNetworkPanel from './ActorNetworkPanel'
import PolicyIndustryPanel from './PolicyIndustryPanel'
import FinancialCrossoverPanel from './FinancialCrossoverPanel'
import ProspectiveInquiryPanel from './ProspectiveInquiryPanel'
import './IntelligenceCenter.css'

type StepKey = 'osint' | 'extraction' | 'events' | 'risks' | 'actor_impact' | 'investment'

interface IntelStep {
  label: string
  ready: boolean
  count: number
  detail: string
}

interface IntelStatus {
  case_name?: string
  case_type?: string
  llm_configured?: boolean
  pipeline_ready?: boolean
  blocker?: 'no_osint' | 'no_llm' | null
  steps?: Record<StepKey, IntelStep>
  ready_steps?: number
  total_steps?: number
}

const STEP_ORDER: StepKey[] = ['osint', 'extraction', 'events', 'risks', 'actor_impact', 'investment']

export default function IntelligenceCenter() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { activeCase, setActiveCase } = useCase()
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(activeCase?.id ?? null)
  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null)
  const [pipelineApplyScope, setPipelineApplyScope] = useState(true)
  const [pipelineAutoCleanup, setPipelineAutoCleanup] = useState(false)

  const { data: cases, isLoading: casesLoading } = useCasesList()

  useEffect(() => {
    if (activeCase?.id) {
      setSelectedCaseId((prev) => prev ?? activeCase.id)
    }
  }, [activeCase?.id])

  const selectedCase = cases?.find((c) => c.id === selectedCaseId) ?? null

  const { scope, setScope, setPeriodPreset, timeRange } = useAnalysisScope(selectedCaseId)
  const { data: scopeProfile } = useCaseScopeProfile(selectedCaseId)

  const { data: intelStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['intel-status', selectedCaseId],
    queryFn: () => intelligenceService.getStatus(selectedCaseId!),
    enabled: selectedCaseId !== null,
    refetchInterval: 30_000,
  })

  const { data: metrics } = useQuery({
    queryKey: ['intel-dashboard-metrics', selectedCaseId],
    queryFn: () => dashboardService.getMetrics(30, selectedCaseId),
    enabled: selectedCaseId !== null,
  })

  const { data: alertMatches } = useQuery({
    queryKey: ['case-alert-matches', selectedCaseId, timeRange?.start, timeRange?.end],
    queryFn: () =>
      prospectiveService.getCaseAlertMatches(selectedCaseId!, {
        dateFrom: timeRange?.start,
        dateTo: timeRange?.end,
      }),
    enabled: selectedCaseId !== null,
  })

  const {
    data: intsum,
    isLoading: intsumLoading,
    isError: intsumError,
    refetch: refetchIntsum,
  } = useQuery({
    queryKey: ['case-intsum', selectedCaseId],
    queryFn: () => casesService.getIntsum(selectedCaseId!, 7),
    enabled: selectedCaseId !== null,
    refetchInterval: 120_000,
    retry: 1,
  })

  const status = intelStatus as IntelStatus | undefined

  const handleCaseChange = (caseId: number | null) => {
    setSelectedCaseId(caseId)
    if (!caseId) return
    const c = cases?.find((x) => x.id === caseId)
    if (c) setActiveCase(toActiveCase(c))
  }

  const handleCaseCreated = (created: ActiveCase) => {
    setSelectedCaseId(created.id)
    setActiveCase(created)
    queryClient.invalidateQueries({ queryKey: ['cases-list'] })
  }

  const pipelineMutation = useMutation({
    mutationFn: () =>
      intelligenceService.runPipeline(selectedCaseId!, true, {
        applyScope: pipelineApplyScope,
        autoCleanup: pipelineAutoCleanup,
      }),
    onMutate: () => setPipelineMsg(t('intel.pipeline.running')),
    onSuccess: (result) => {
      const steps = (result?.steps ?? []) as Array<{ label: string; ok: boolean; error?: string }>
      const failed = steps.filter((s) => !s.ok)
      setPipelineMsg(
        failed.length === 0
          ? t('intel.pipeline.success')
          : t('intel.pipeline.partialError', { count: failed.length }),
      )
      queryClient.invalidateQueries({ queryKey: ['intel-status'] })
      queryClient.invalidateQueries({ queryKey: ['geo-events-timeline'] })
      queryClient.invalidateQueries({ queryKey: ['geo-risks-pred'] })
      queryClient.invalidateQueries({ queryKey: ['geo-risks-predictions'] })
      queryClient.invalidateQueries({ queryKey: ['inv-risks'] })
      queryClient.invalidateQueries({ queryKey: ['source-reliability'] })
      queryClient.invalidateQueries({ queryKey: ['networkGraph'] })
      queryClient.invalidateQueries({ queryKey: ['trendAnalysis'] })
      queryClient.invalidateQueries({ queryKey: ['geographicLocations'] })
      queryClient.invalidateQueries({ queryKey: ['intel-dashboard-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['actor-impact'] })
      queryClient.invalidateQueries({ queryKey: ['statements-sentiment'] })
      queryClient.invalidateQueries({ queryKey: ['case-intsum'] })
      setTimeout(() => setPipelineMsg(null), 6000)
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : t('intel.pipeline.error')
      setPipelineMsg(msg)
    },
  })

  const caseDescription = selectedCase?.description ?? activeCase?.description ?? null
  const totalMentions = metrics?.total_mentions?.total_mentions ?? 0
  const sentimentScore = metrics?.sentiment_score?.sentiment_score ?? 0
  const criticalAlerts = metrics?.critical_alerts?.critical_alerts ?? 0

  const blockerMessage = useMemo(() => {
    if (!status) return null
    if (status.blocker === 'no_osint') {
      return t('intel.blocker.noOsint')
    }
    if (status.blocker === 'no_llm') {
      return t('intel.blocker.noLlm')
    }
    return null
  }, [status, t])

  const canRunPipeline = Boolean(status?.pipeline_ready && selectedCaseId && !pipelineMutation.isPending)

  return (
    <div className="intelligence-center">
      <header className="intel-center-header">
        <p className="intel-center-kicker">{t('intel.kicker')}</p>
        <h1 className="intel-center-title">{t('intel.title')}</h1>
        <p className="intel-center-desc">{t('intel.subtitle')}</p>

        <div className="intel-center-toolbar">
          <select
            className="intel-case-select"
            value={selectedCaseId ?? ''}
            onChange={(e) => handleCaseChange(e.target.value ? Number(e.target.value) : null)}
            disabled={casesLoading}
          >
            <option value="">
              {casesLoading ? t('intel.case.loading') : t('intel.case.select')}
            </option>
            {cases?.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>

          <CreateCaseModal onCaseCreated={handleCaseCreated} />

          <button
            type="button"
            className="intel-action-btn primary"
            disabled={!canRunPipeline}
            onClick={() => pipelineMutation.mutate()}
            title={blockerMessage ?? t('intel.pipeline.runTitle')}
          >
            <Zap size={15} />
            {pipelineMutation.isPending ? t('intel.pipeline.runPending') : t('intel.pipeline.run')}
          </button>

          <button
            type="button"
            className="intel-action-btn"
            disabled={!selectedCaseId}
            onClick={() => {
              refetchStatus()
              queryClient.invalidateQueries()
              setPipelineMsg(t('intel.refresh.done'))
              setTimeout(() => setPipelineMsg(null), 2500)
            }}
          >
            <RefreshCw size={15} />
            {t('intel.refresh')}
          </button>

          {selectedCaseId ? (
            <Link to="/osint-collection" className="intel-action-btn">
              <Search size={15} />
              {t('intel.osintCollection')}
            </Link>
          ) : null}
        </div>

        {pipelineMsg ? <p className="intel-analyze-msg">{pipelineMsg}</p> : null}

        {selectedCaseId ? (
          <div className="intel-pipeline-options">
            <label className="intel-pipeline-opt">
              <input
                type="checkbox"
                checked={pipelineApplyScope}
                onChange={(e) => setPipelineApplyScope(e.target.checked)}
              />
              {t('intel.pipeline.applyScope')}
            </label>
            <label className="intel-pipeline-opt">
              <input
                type="checkbox"
                checked={pipelineAutoCleanup}
                onChange={(e) => setPipelineAutoCleanup(e.target.checked)}
              />
              {t('intel.pipeline.autoCleanup')}
            </label>
          </div>
        ) : null}

        {selectedCaseId ? (
          <AnalysisScopeBar
            scope={scope}
            onChange={(patch) => setScope(patch)}
            onPeriodPreset={setPeriodPreset}
            focusLabel={scopeProfile?.focus_label}
            suggestedQuery={scopeProfile?.suggested_query}
            themes={scopeProfile?.themes}
            analyticalProfile={scopeProfile?.analytical_profile}
          />
        ) : null}

        {selectedCaseId && status ? (
          <>
            <div className="intel-status-bar">
              <span className="intel-status-pill">
                {t('intel.status.case')}{' '}
                <strong>{status.case_name ?? selectedCase?.name ?? `#${selectedCaseId}`}</strong>
              </span>
              <span className="intel-status-pill">
                {t('intel.status.pipeline', {
                  ready: status.ready_steps ?? 0,
                  total: status.total_steps ?? 6,
                })}
              </span>
              {!status.llm_configured ? (
                <span className="intel-status-pill warn">
                  <AlertTriangle size={12} /> {t('intel.status.llmMissing')}
                </span>
              ) : null}
            </div>

            {blockerMessage ? (
              <div className="intel-blocker">
                <AlertTriangle size={16} />
                <span>{blockerMessage}</span>
                {status.blocker === 'no_osint' ? (
                  <Link to="/osint-collection" className="intel-blocker-link">
                    {t('intel.blocker.goOsint')}
                  </Link>
                ) : null}
              </div>
            ) : null}

            <div className="intel-pipeline-steps">
              {STEP_ORDER.map((key) => {
                const step = status.steps?.[key]
                if (!step) return null
                const Icon = step.ready ? CheckCircle2 : key === 'osint' && !step.ready ? AlertTriangle : Circle
                return (
                  <div key={key} className={`intel-pipeline-step ${step.ready ? 'done' : 'pending'}`}>
                    <Icon size={16} className="intel-step-icon" />
                    <div className="intel-step-body">
                      <span className="intel-step-label">{step.label}</span>
                      <span className="intel-step-detail">{step.detail}</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {caseDescription ? (
              <details className="intel-case-briefing">
                <summary>
                  {t('intel.briefing.summary', {
                    lines: countPromptLines(caseDescription),
                    chars: caseDescription.length,
                  })}
                </summary>
                <pre className="intel-case-briefing-text">{caseDescription}</pre>
              </details>
            ) : null}

            {selectedCaseId ? (
              <section className="intel-intsum" aria-label="Resum setmanal INTSUM">
                <div className="intel-intsum-head">
                  <h2 className="intel-intsum-title">
                    {t('intel.intsum.title', { days: intsum?.days ?? 7 })}
                    {intsum?.case_name ? (
                      <span className="intel-intsum-case"> — {intsum.case_name}</span>
                    ) : null}
                  </h2>
                  <button
                    type="button"
                    className="intel-intsum-refresh"
                    onClick={() => refetchIntsum()}
                    disabled={intsumLoading}
                    title={t('intel.intsum.refreshTitle')}
                  >
                    <RefreshCw size={14} className={intsumLoading ? 'spin' : ''} />
                  </button>
                </div>

                {intsumLoading && !intsum ? (
                  <p className="intel-intsum-muted">{t('intel.intsum.loading')}</p>
                ) : null}

                {intsumError ? (
                  <p className="intel-intsum-error">
                    {t('intel.intsum.error')}{' '}
                    <button type="button" className="intel-intsum-link" onClick={() => refetchIntsum()}>
                      {t('intel.intsum.retry')}
                    </button>
                  </p>
                ) : null}

                {intsum?.summary ? (
                  <>
                    <div className="intel-intsum-stats">
                      <span>{intsum.summary.alert_matches} alertes (finestra)</span>
                      <span>{intsum.summary.new_statements} declaracions noves</span>
                      <span>{intsum.summary.posture_highlights} actors destacats</span>
                      {intsum.summary.milestone_count > 0 ? (
                        <span>{intsum.summary.milestone_count} milestones</span>
                      ) : null}
                    </div>

                    {!intsum.has_activity ? (
                      <p className="intel-intsum-muted">
                        {t('intel.intsum.noActivity', { days: intsum.days })}
                      </p>
                    ) : null}

                    {intsum.summary.alerts_fallback || intsum.summary.statements_fallback ? (
                      <p className="intel-intsum-muted intel-intsum-fallback">
                        {t('intel.intsum.fallback')}
                      </p>
                    ) : null}

                    {intsum.signal_breakdown &&
                    Object.keys(intsum.signal_breakdown).length > 0 ? (
                      <div className="intel-intsum-signals">
                        {Object.entries(intsum.signal_breakdown).map(([k, v]) =>
                          v > 0 ? (
                            <span key={k} className="intel-intsum-chip">
                              {k}: {v}
                            </span>
                          ) : null,
                        )}
                      </div>
                    ) : null}

                    {intsum.posture_highlights?.length ? (
                      <div className="intel-intsum-block">
                        <h3 className="intel-intsum-sub">Actors</h3>
                        <ul className="intel-intsum-list">
                          {intsum.posture_highlights.slice(0, 5).map((p) => (
                            <li key={p.actor}>
                              <strong>{p.actor}</strong>
                              {p.highlight_type === 'top_activity' ? (
                                <> — {p.statement_count} declaracions</>
                              ) : (
                                <>
                                  {' '}
                                  — postura {p.avg_posture} ({p.statement_count} decl.)
                                </>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {intsum.statements?.length ? (
                      <details className="intel-intsum-details" open={intsum.summary.new_statements > 0}>
                        <summary>
                          Declaracions ({intsum.statements.length}
                          {intsum.summary.statements_fallback ? ', historial recent' : ''})
                        </summary>
                        <ul className="intel-intsum-list">
                          {intsum.statements.slice(0, 6).map((s) => (
                            <li key={s.id}>
                              <strong>{s.actor}</strong>
                              {s.posture_value != null ? ` [${s.posture_value}]` : ''}: {s.statement}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : null}

                    {intsum.alerts?.length ? (
                      <details className="intel-intsum-details">
                        <summary>
                          Alertes ({intsum.alerts.length}
                          {intsum.summary.alerts_fallback ? ', historial recent' : ''})
                        </summary>
                        <ul className="intel-intsum-list">
                          {intsum.alerts.slice(0, 6).map((a) => (
                            <li key={a.id}>
                              {a.url ? (
                                <a href={a.url} target="_blank" rel="noreferrer">
                                  {a.title || a.monitor}
                                </a>
                              ) : (
                                a.title || a.monitor
                              )}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </>
                ) : null}
              </section>
            ) : null}

            {metrics ? (
              <div className="intel-kpi-row">
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{totalMentions.toLocaleString()}</div>
                  <div className="intel-kpi-label">{t('intel.kpi.mentions')}</div>
                </div>
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{sentimentScore}%</div>
                  <div className="intel-kpi-label">{t('intel.kpi.sentiment')}</div>
                </div>
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{criticalAlerts}</div>
                  <div className="intel-kpi-label">{t('intel.kpi.alerts')}</div>
                </div>
              </div>
            ) : null}

            {(alertMatches?.items?.length ?? 0) > 0 ? (
              <div className="intel-alert-evidence card" style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-md)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: 'var(--font-size-sm)', color: 'var(--color-primary)' }}>
                  Alertes OSINT amb evidència
                </h4>
                {(alertMatches.items as Array<{ id: number; title: string; excerpt?: string; url?: string }>)
                  .slice(0, 5)
                  .map((m) => (
                    <div key={m.id} style={{ marginBottom: 8, fontSize: 'var(--font-size-xs)', borderLeft: '2px solid var(--color-primary)', paddingLeft: 8 }}>
                      <strong>{m.title?.slice(0, 80)}</strong>
                      {m.excerpt ? <p style={{ margin: '2px 0', color: 'var(--color-gray-600)' }}>{m.excerpt.slice(0, 100)}…</p> : null}
                      {m.url ? <a href={m.url} target="_blank" rel="noopener noreferrer">Font →</a> : null}
                    </div>
                  ))}
                <Link to="/alert-monitors" style={{ fontSize: 'var(--font-size-xs)' }}>Veure monitors →</Link>
              </div>
            ) : null}
          </>
        ) : selectedCaseId && statusLoading ? (
          <p className="intel-analyze-msg">Carregant estat del pipeline…</p>
        ) : null}
      </header>

      {!selectedCaseId ? (
        <div className="card intel-empty-panel">
          <h2 className="intel-empty-title">{t('intel.empty.selectCase.title')}</h2>
          <p className="intel-empty-desc">{t('intel.empty.selectCase.desc')}</p>
          <div className="intel-empty-actions">
            <CreateCaseModal onCaseCreated={handleCaseCreated} />
            <Link to="/" className="btn btn-primary">
              {t('intel.empty.goDashboard')}
            </Link>
          </div>
        </div>
      ) : status?.steps?.osint?.ready ? (
        <div data-testid="intel-panels-ready">
          <ActorNetworkPanel caseId={selectedCaseId} />
          <PolicyIndustryPanel caseId={selectedCaseId} />
          <ProspectiveInquiryPanel caseId={selectedCaseId} />
          <FinancialCrossoverPanel caseId={selectedCaseId} />
          <VisualizationsDashboard caseId={selectedCaseId} hideScopeBar key={selectedCaseId} />
        </div>
      ) : (
        <div className="card intel-empty-panel">
          <Brain size={32} className="intel-empty-icon" />
          <h2 className="intel-empty-title">{t('intel.empty.pipelinePending.title')}</h2>
          <p className="intel-empty-desc">{t('intel.empty.pipelinePending.desc')}</p>
          <div className="intel-empty-actions">
            <Link to="/osint-collection" className="btn btn-primary">
              <Search size={14} /> {t('intel.osintCollection')}
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
