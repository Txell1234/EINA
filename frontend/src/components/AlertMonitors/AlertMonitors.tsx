import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  Archive,
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  ExternalLink,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react'
import { useI18n } from '../../contexts/I18nContext'
import api, { prospectiveService } from '../../services/api'
import EmptyState from '../shared/EmptyState'
import SourceProvenance from '../shared/SourceProvenance'
import AnalysisScopeBar from '../shared/AnalysisScopeBar'
import { useAnalysisScope } from '../../hooks/useAnalysisScope'
import { useCaseScopeProfile } from '../../hooks/useCaseScopeProfile'
import '../shared/Traceability.css'
import '../shared/ExtractionCoverage.css'
import './AlertMonitors.css'

interface Monitor {
  id: number
  indicator: string
  keywords: string[]
  is_active: boolean
  match_count: number
  unread_count?: number
  last_checked: string | null
  lookback_days?: number | null
  horizon_label?: string | null
  min_match_score?: number | null
  min_keywords_matched?: number | null
}

interface AlertMatch {
  id: number
  title: string
  url: string
  excerpt: string
  source_type: string
  published_at: string
  matched_keywords: string[]
  match_score: number
  status: string
  analysis_summary?: string
}

interface Project {
  id: number
  title: string
  case_id?: number
}

const SOURCE_LABELS: Record<string, string> = {
  gdelt: 'GDELT',
  google_news: 'News',
  reddit: 'Reddit',
  tavily: 'Tavily',
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ca-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function downloadExport(url: string, filename: string) {
  const response = await api.get(url, { responseType: 'blob' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([response.data]))
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

function MonitorAdvancedSettings({
  monitor,
  onSaved,
}: {
  monitor: Monitor
  onSaved: () => void
}) {
  const [horizon, setHorizon] = useState(monitor.horizon_label ?? '')
  const [lookback, setLookback] = useState(
    monitor.lookback_days != null ? String(monitor.lookback_days) : '',
  )
  const [minScore, setMinScore] = useState(
    monitor.min_match_score != null ? String(monitor.min_match_score) : '',
  )
  const [minKw, setMinKw] = useState(
    monitor.min_keywords_matched != null ? String(monitor.min_keywords_matched) : '',
  )
  const [busy, setBusy] = useState(false)

  const save = async () => {
    setBusy(true)
    try {
      await prospectiveService.updateMonitorSettings(monitor.id, {
        horizon_label: horizon || null,
        lookback_days: lookback ? Number(lookback) : null,
        min_match_score: minScore ? Number(minScore) : null,
        min_keywords_matched: minKw ? Number(minKw) : null,
      })
      onSaved()
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setBusy(true)
    try {
      await prospectiveService.updateMonitorSettings(monitor.id, { clear_thresholds: true })
      setHorizon('')
      setLookback('')
      setMinScore('')
      setMinKw('')
      onSaved()
    } finally {
      setBusy(false)
    }
  }

  return (
    <details className="am-monitor-advanced">
      <summary>Horitzó i llindars (opcional)</summary>
      <div className="am-monitor-advanced-grid">
        <label>
          Horitzó
          <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
            <option value="">Per defecte (7 dies GDELT)</option>
            <option value="3m">3 mesos (sector públic)</option>
            <option value="6m">6 mesos</option>
            <option value="12m">12 mesos</option>
            <option value="18m">18 mesos (sector privat)</option>
          </select>
        </label>
        <label>
          Dies enrere (GDELT)
          <input
            type="number"
            min={1}
            max={365}
            placeholder="7"
            value={lookback}
            onChange={(e) => setLookback(e.target.value)}
          />
        </label>
        <label>
          Mín. score coincidència (0–1)
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            placeholder="cap"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
          />
        </label>
        <label>
          Mín. paraules clau coincidents
          <input
            type="number"
            min={1}
            max={10}
            placeholder="1"
            value={minKw}
            onChange={(e) => setMinKw(e.target.value)}
          />
        </label>
      </div>
      <div className="am-form-actions">
        <button type="button" className="btn btn-accent am-btn-sm" disabled={busy} onClick={save}>
          Desar
        </button>
        <button type="button" className="btn am-btn-sm" disabled={busy} onClick={reset}>
          Restaurar per defecte
        </button>
      </div>
    </details>
  )
}

function MatchCard({ match, onRefresh }: { match: AlertMatch; onRefresh: () => void }) {
  const [localAnalysis, setLocalAnalysis] = useState(match.analysis_summary || '')
  const [showAnalysis, setShowAnalysis] = useState(Boolean(match.analysis_summary))
  const [showProvenance, setShowProvenance] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const run = async (action: 'extract' | 'analyze' | 'archive' | 'review') => {
    setBusy(action)
    try {
      if (action === 'extract') await prospectiveService.extractMatch(match.id)
      if (action === 'analyze') {
        const res = await prospectiveService.analyzeMatch(match.id)
        setLocalAnalysis(res.analysis_summary || res.analysis?.summary || '')
        setShowAnalysis(true)
      }
      if (action === 'archive') await prospectiveService.archiveMatch(match.id)
      if (action === 'review') await prospectiveService.updateMatchStatus(match.id, 'reviewed', 'reviewed')
      onRefresh()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className={`am-match-card ${match.status === 'new' ? 'am-match-card--new' : ''}`}>
      <MatchHeader match={match} />
      <p className="am-match-title">{match.title || 'Sense titular'}</p>
      {match.excerpt ? <p className="am-match-excerpt">{match.excerpt}</p> : null}
      {match.excerpt && match.excerpt.length < 200 ? (
        <p className="excerpt-short-warn">
          <AlertTriangle size={12} />
          Excerpt curt ({match.excerpt.length} chars) — s&apos;enriqueix automàticament en extreure.
        </p>
      ) : null}
      <p className="am-match-meta">
        <span className="am-match-keywords">
          {(match.matched_keywords ?? []).map((kw) => (
            <span key={kw} className="am-match-keyword">
              {kw}
            </span>
          ))}
        </span>
        {match.match_score != null ? `${Math.round(match.match_score * 100)}% coincidència` : null}
      </p>
      {showAnalysis && localAnalysis ? (
        <div className="am-match-analysis">
          <strong>Anàlisi IA</strong>
          <p>{localAnalysis}</p>
        </div>
      ) : null}
      {showProvenance ? (
        <div className="am-provenance-wrap">
          <SourceProvenance matchId={match.id} compact />
        </div>
      ) : null}
      <div className="am-match-actions">
        {match.url ? (
          <a href={match.url} target="_blank" rel="noopener noreferrer" className="btn am-btn-sm">
            <ExternalLink size={12} /> Font
          </a>
        ) : null}
        <button
          type="button"
          className={`btn am-btn-sm am-btn-trace${showProvenance ? ' am-btn-trace--active' : ''}`}
          onClick={() => setShowProvenance((v) => !v)}
        >
          {showProvenance ? 'Amagar traçabilitat' : 'Traçabilitat'}
        </button>
        <button type="button" className="btn am-btn-sm" disabled={!!busy} onClick={() => run('extract')}>
          Extreure
        </button>
        <button type="button" className="btn am-btn-sm" disabled={!!busy} onClick={() => run('analyze')}>
          <Brain size={12} /> Analitzar
        </button>
        {match.status === 'new' ? (
          <button type="button" className="btn am-btn-sm" disabled={!!busy} onClick={() => run('review')}>
            Revisada
          </button>
        ) : null}
        {match.status !== 'archived' ? (
          <button type="button" className="btn am-btn-sm" disabled={!!busy} onClick={() => run('archive')}>
            <Archive size={12} />
          </button>
        ) : null}
      </div>
    </div>
  )
}

function MatchHeader({ match }: { match: AlertMatch }) {
  return (
    <div className="am-match-header">
      <span className={`am-match-badge ${match.status === 'new' ? 'am-match-badge--new' : ''}`}>
        {match.status === 'new' ? 'NOVA' : match.status.toUpperCase()}
      </span>
      <span>{SOURCE_LABELS[match.source_type] ?? match.source_type}</span>
      {match.published_at ? <span>{match.published_at.slice(0, 10)}</span> : null}
    </div>
  )
}

export default function AlertMonitors() {
  const { t } = useI18n()
  const qc = useQueryClient()
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [checkingId, setCheckingId] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newIndicator, setNewIndicator] = useState('')
  const [newKeywords, setNewKeywords] = useState('')
  const [bulkExtractBusy, setBulkExtractBusy] = useState(false)

  const { data: projects, isLoading: loadingProjects } = useQuery<Project[]>({
    queryKey: ['prospective-projects-list'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const selectedProject = projects?.find((p) => p.id === selectedProjectId)

  const scopeCaseId = selectedProject?.case_id ?? null
  const { scope, setScope, setPeriodPreset, timeRange } = useAnalysisScope(scopeCaseId)
  const { data: scopeProfile } = useCaseScopeProfile(scopeCaseId)

  const { data: monitors, isLoading: loadingMonitors, refetch: refetchMonitors } = useQuery<Monitor[]>({
    queryKey: ['project-monitors', selectedProjectId],
    queryFn: () => prospectiveService.listMonitors(selectedProjectId!),
    enabled: selectedProjectId !== null,
  })

  const {
    data: matchesData,
    refetch: refetchMatches,
    isLoading: matchesLoading,
    isError: matchesError,
    error: matchesQueryError,
  } = useQuery({
    queryKey: ['monitor-matches', expandedId, includeArchived, timeRange?.start, timeRange?.end],
    queryFn: () =>
      prospectiveService.getMonitorMatches(expandedId!, {
        includeArchived,
        limit: 500,
        dateFrom: timeRange?.start,
        dateTo: timeRange?.end,
      }),
    enabled: expandedId !== null,
  })

  const checkMutation = useMutation({
    mutationFn: (monitorId: number) => {
      setCheckingId(monitorId)
      return prospectiveService.checkMonitor(monitorId)
    },
    onSuccess: (_r, monitorId) => {
      setExpandedId(monitorId)
      qc.invalidateQueries({ queryKey: ['project-monitors'] })
      qc.invalidateQueries({ queryKey: ['monitor-matches'] })
    },
    onSettled: () => setCheckingId(null),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      prospectiveService.toggleMonitor(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] }),
  })

  const addMutation = useMutation({
    mutationFn: () =>
      prospectiveService.addManualMonitor(selectedProjectId!, {
        indicator: newIndicator,
        keywords: newKeywords.split(',').map((k) => k.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      setNewIndicator('')
      setNewKeywords('')
      setShowAddForm(false)
      qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] })
    },
  })

  const matches = (matchesData?.items ?? []) as AlertMatch[]
  const matchesTotal = (matchesData?.total as number | undefined) ?? matches.length
  const expandedMonitor = (monitors ?? []).find((m) => m.id === expandedId)

  return (
    <div className="am-page">
      <div className="am-header">
        <div className="am-header-left">
          <h1 className="am-title">
            <Activity size={22} />
            {t('alerts.title')}
          </h1>
        </div>
        {selectedProjectId ? (
          <div className="am-header-actions">
            <button
              type="button"
              className="btn"
              disabled={bulkExtractBusy}
              onClick={async () => {
                setBulkExtractBusy(true)
                try {
                  await prospectiveService.bulkExtractMatches({
                    caseId: selectedProject?.case_id,
                    monitorId: expandedId ?? undefined,
                    limit: 25,
                  })
                  qc.invalidateQueries({ queryKey: ['monitor-matches'] })
                } finally {
                  setBulkExtractBusy(false)
                }
              }}
            >
              {bulkExtractBusy ? 'Extraint…' : 'Extreure alertes pendents'}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() =>
                downloadExport(
                  prospectiveService.exportProjectMatchesUrl(selectedProjectId, 'csv'),
                  `alertes_${selectedProjectId}.csv`,
                )
              }
            >
              <Download size={15} /> Exportar
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setShowAddForm((v) => !v)}>
              <Plus size={15} /> Afegir
            </button>
          </div>
        ) : null}
      </div>

      <div className="card am-project-selector">
        <label className="am-field-label" htmlFor="am-project-select">
          <Search size={13} /> {t('alerts.selectProject')}
        </label>
        {loadingProjects ? (
          <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
        ) : (
          <select
            id="am-project-select"
            className="am-select"
            value={selectedProjectId ?? ''}
            onChange={(e) => {
              setSelectedProjectId(e.target.value ? Number(e.target.value) : null)
              setExpandedId(null)
            }}
          >
            <option value="">— {t('alerts.selectProject')} —</option>
            {(projects ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} — {p.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {scopeCaseId ? (
        <AnalysisScopeBar
          scope={scope}
          onChange={(patch) => setScope(patch)}
          onPeriodPreset={setPeriodPreset}
          focusLabel={scopeProfile?.focus_label}
          suggestedQuery={scopeProfile?.suggested_query}
          showSource={false}
        />
      ) : selectedProjectId ? (
        <p className="am-field-label" style={{ margin: '0 0 1rem' }}>
          Aquest projecte no té cas EINA vinculat — la delimitació per dates no s&apos;aplicarà als monitors.
        </p>
      ) : null}

      {showAddForm && selectedProjectId ? (
        <div className="card am-add-form">
          <h3 className="am-add-title">
            <Plus size={16} /> Nou monitor
          </h3>
          <div className="am-field">
            <label className="am-field-label" htmlFor="am-indicator">
              {t('alerts.indicator')}
            </label>
            <input id="am-indicator" className="am-input" value={newIndicator} onChange={(e) => setNewIndicator(e.target.value)} />
          </div>
          <div className="am-field">
            <label className="am-field-label" htmlFor="am-keywords">
              {t('alerts.keywords')}
            </label>
            <input id="am-keywords" className="am-input" value={newKeywords} onChange={(e) => setNewKeywords(e.target.value)} />
          </div>
          <div className="am-form-actions">
            <button type="button" className="btn btn-accent" disabled={!newIndicator.trim() || addMutation.isPending} onClick={() => addMutation.mutate()}>
              Afegir
            </button>
            <button type="button" className="btn" onClick={() => setShowAddForm(false)}>
              Cancel·lar
            </button>
          </div>
        </div>
      ) : null}

      {!selectedProjectId ? (
        <div className="card">
          <EmptyState icon="◎" title={t('alerts.noProject')} description="Selecciona un projecte." />
        </div>
      ) : null}

      {selectedProjectId && loadingMonitors ? (
        <div className="card">
          <SpinnerDiv />
        </div>
      ) : null}

      {selectedProjectId && !loadingMonitors && !monitors?.length ? (
        <div className="card">
          <EmptyState icon="△" title={t('alerts.noMonitors')} description="Activa monitors des d'escenaris." />
        </div>
      ) : null}

      <div className="am-list">
        {(monitors ?? []).map((monitor) => {
          const isExpanded = expandedId === monitor.id
          const isChecking = checkingId === monitor.id
          return (
            <div key={monitor.id} className={`card am-card am-card--full ${monitor.match_count > 0 ? 'am-card--triggered' : ''}`}>
              <div className="am-card-row">
                <div className="am-card-status">
                  {monitor.match_count > 0 ? (
                    <AlertTriangle size={20} className="am-icon--triggered" />
                  ) : (
                    <CheckCircle size={20} className="am-icon--active" />
                  )}
                </div>
                <div className="am-card-content">
                  <p className="am-card-indicator">{monitor.indicator}</p>
                  <div className="am-card-meta">
                    <span className="am-meta-item">
                      <Search size={11} />
                      {(monitor.keywords ?? []).map((k) => (
                        <span key={k} className="am-keyword">
                          {k}
                        </span>
                      ))}
                    </span>
                    <span className="am-meta-item">
                      <Clock size={11} /> {formatDate(monitor.last_checked)}
                    </span>
                  </div>
                </div>
                <div className="am-card-actions">
                  {(monitor.unread_count ?? 0) > 0 ? (
                    <span className="am-badge am-badge--triggered">{monitor.unread_count} noves</span>
                  ) : null}
                  <button type="button" className="btn am-btn-sm" onClick={() => setExpandedId(isExpanded ? null : monitor.id)}>
                    {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />} Evidència ({monitor.match_count})
                  </button>
                  <button type="button" className="btn am-btn-sm" disabled={isChecking || !monitor.is_active} onClick={() => checkMutation.mutate(monitor.id)}>
                    {isChecking ? '…' : <RefreshCw size={13} />}
                  </button>
                  <button type="button" className="btn am-btn-sm" onClick={() => toggleMutation.mutate({ id: monitor.id, active: !monitor.is_active })}>
                    {monitor.is_active ? <Pause size={13} /> : <Play size={13} />}
                  </button>
                </div>
              </div>
              {isExpanded ? (
                <div className="am-matches-panel">
                  <MonitorAdvancedSettings
                    monitor={monitor}
                    onSaved={() => qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] })}
                  />
                  <div className="am-matches-toolbar">
                    <label className="am-check-label">
                      <input type="checkbox" checked={includeArchived} onChange={(e) => setIncludeArchived(e.target.checked)} />
                      Arxivades
                    </label>
                    <button
                      type="button"
                      className="btn am-btn-sm"
                      onClick={() => downloadExport(prospectiveService.exportMonitorMatchesUrl(monitor.id, 'csv'), `monitor_${monitor.id}.csv`)}
                    >
                      <Download size={12} /> CSV
                    </button>
                  </div>
                  {matchesLoading ? (
                    <SpinnerDiv />
                  ) : matchesError ? (
                    <p className="am-match-empty">
                      Error carregant evidències:{' '}
                      {(matchesQueryError as Error)?.message ?? 'error desconegut'}
                    </p>
                  ) : matches.length === 0 ? (
                    <div className="am-match-empty">
                      <p>Sense coincidències guardades a la base de dades.</p>
                      {(expandedMonitor?.match_count ?? 0) > 0 ? (
                        <p style={{ marginTop: 8, fontSize: '0.85rem' }}>
                          El comptador del monitor estava desactualitzat. Prem{' '}
                          <RefreshCw size={12} style={{ verticalAlign: 'middle' }} /> per tornar a cercar
                          fonts OSINT i generar evidència verificable.
                        </p>
                      ) : (
                        <p style={{ marginTop: 8, fontSize: '0.85rem' }}>
                          Prem actualitzar per executar GDELT/News i detectar articles que coincideixin amb les
                          paraules clau.
                        </p>
                      )}
                    </div>
                  ) : (
                    <>
                      {matchesTotal > matches.length ? (
                        <p className="am-match-meta" style={{ marginBottom: 8 }}>
                          Mostrant {matches.length} de {matchesTotal} coincidències
                        </p>
                      ) : null}
                      {matches.map((m) => (
                        <MatchCard
                          key={m.id}
                          match={m}
                          onRefresh={() => {
                            refetchMatches()
                            refetchMonitors()
                          }}
                        />
                      ))}
                    </>
                  )}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SpinnerDiv() {
  return <div className="spinner" style={{ margin: '1rem auto' }} />
}
