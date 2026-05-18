import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Zap,
} from 'lucide-react'
import { useI18n } from '../../contexts/I18nContext'
import { prospectiveService } from '../../services/api'
import EmptyState from '../shared/EmptyState'
import './AlertMonitors.css'

interface Monitor {
  id: number
  indicator: string
  keywords: string[]
  osint_sources: string[]
  is_active: boolean
  match_count: number
  last_checked: string | null
  last_match: string | null
}

interface Project {
  id: number
  title: string
  case_id?: number | null
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ca-ES', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const SOURCE_LABELS: Record<string, string> = {
  gdelt: 'GDELT',
  google_news: 'News',
  reddit: 'Reddit',
  rss_feed: 'RSS',
  rss_all: 'RSS All',
}

export default function AlertMonitors() {
  const { t } = useI18n()
  const qc = useQueryClient()

  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [checkingId, setCheckingId] = useState<number | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newIndicator, setNewIndicator] = useState('')
  const [newKeywords, setNewKeywords] = useState('')
  const [newSources, setNewSources] = useState<string[]>(['gdelt', 'google_news', 'reddit'])

  const { data: projects, isLoading: loadingProjects } = useQuery<Project[]>({
    queryKey: ['prospective-projects-list'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const {
    data: monitors,
    isLoading: loadingMonitors,
    refetch: refetchMonitors,
  } = useQuery<Monitor[]>({
    queryKey: ['project-monitors', selectedProjectId],
    queryFn: () => prospectiveService.listMonitors(selectedProjectId!),
    enabled: selectedProjectId !== null,
    refetchInterval: 5 * 60 * 1000,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      prospectiveService.toggleMonitor(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] }),
  })

  const checkMutation = useMutation({
    mutationFn: async (monitorId: number) => {
      setCheckingId(monitorId)
      return prospectiveService.checkMonitor(monitorId)
    },
    onSettled: () => {
      setCheckingId(null)
      qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] })
    },
  })

  const addMutation = useMutation({
    mutationFn: () =>
      prospectiveService.addManualMonitor(selectedProjectId!, {
        indicator: newIndicator,
        keywords: newKeywords
          .split(',')
          .map((k) => k.trim())
          .filter(Boolean),
        osint_sources: newSources,
      }),
    onSuccess: () => {
      setNewIndicator('')
      setNewKeywords('')
      setShowAddForm(false)
      qc.invalidateQueries({ queryKey: ['project-monitors', selectedProjectId] })
    },
  })

  const activeCount = monitors?.filter((m) => m.is_active).length ?? 0
  const triggeredCount = monitors?.filter((m) => m.match_count > 0).length ?? 0
  const totalMatches = monitors?.reduce((s, m) => s + (m.match_count || 0), 0) ?? 0

  return (
    <div className="am-page">
      <div className="am-header">
        <div className="am-header-left">
          <h1 className="am-title">
            <Activity size={22} />
            {t('alerts.title')}
          </h1>
          {selectedProjectId && monitors && (
            <div className="am-stats">
              <span className="am-stat am-stat--active">
                <Zap size={12} /> {activeCount} actius
              </span>
              {triggeredCount > 0 && (
                <span className="am-stat am-stat--triggered">
                  <AlertTriangle size={12} /> {triggeredCount} disparats
                </span>
              )}
              {totalMatches > 0 && (
                <span className="am-stat am-stat--matches">
                  {totalMatches} coincidències totals
                </span>
              )}
            </div>
          )}
        </div>
        <div className="am-header-actions">
          {selectedProjectId && (
            <>
              <button
                type="button"
                className="btn"
                onClick={() => refetchMonitors()}
                title="Refresca"
              >
                <RefreshCw size={15} />
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowAddForm((v) => !v)}
              >
                <Plus size={15} />
                Afegir monitor
              </button>
            </>
          )}
        </div>
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
              setShowAddForm(false)
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

      {showAddForm && selectedProjectId && (
        <div className="card am-add-form">
          <h3 className="am-add-title">
            <Plus size={16} /> Nou monitor manual
          </h3>
          <div className="am-field">
            <label className="am-field-label" htmlFor="am-indicator">
              {t('alerts.indicator')}
            </label>
            <input
              id="am-indicator"
              className="am-input"
              placeholder="Ex.: Augment de presència naval xinesa al Mar de la Xina Meridional"
              value={newIndicator}
              onChange={(e) => setNewIndicator(e.target.value)}
            />
          </div>
          <div className="am-field">
            <label className="am-field-label" htmlFor="am-keywords">
              {t('alerts.keywords')}
              <span className="am-field-hint"> (separades per comes)</span>
            </label>
            <input
              id="am-keywords"
              className="am-input"
              placeholder="Ex.: China, naval, South China Sea"
              value={newKeywords}
              onChange={(e) => setNewKeywords(e.target.value)}
            />
          </div>
          <div className="am-field">
            <span className="am-field-label">{t('alerts.sources')}</span>
            <div className="am-source-checks">
              {Object.entries(SOURCE_LABELS).map(([val, label]) => (
                <label key={val} className="am-check-label">
                  <input
                    type="checkbox"
                    checked={newSources.includes(val)}
                    onChange={(e) =>
                      setNewSources((prev) =>
                        e.target.checked ? [...prev, val] : prev.filter((s) => s !== val),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
          <div className="am-form-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={!newIndicator.trim() || addMutation.isPending}
              onClick={() => addMutation.mutate()}
            >
              {addMutation.isPending ? 'Afegint...' : 'Afegir monitor'}
            </button>
            <button type="button" className="btn" onClick={() => setShowAddForm(false)}>
              Cancel·lar
            </button>
          </div>
        </div>
      )}

      {!selectedProjectId && (
        <div className="card">
          <EmptyState
            icon="◎"
            title={t('alerts.noProject')}
            description="Els monitors s'activen des del pas Escenaris del wizard prospectiu."
          />
        </div>
      )}

      {selectedProjectId && loadingMonitors && (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          <div className="spinner" style={{ margin: '0 auto' }} />
        </div>
      )}

      {selectedProjectId && !loadingMonitors && monitors?.length === 0 && (
        <div className="card">
          <EmptyState
            icon="△"
            title={t('alerts.noMonitors')}
            description="Genera escenaris al wizard prospectiu i fes clic a 'Activar monitoratge d'alertes' per a cada escenari."
          />
        </div>
      )}

      {(monitors ?? []).length > 0 && (
        <div className="am-list">
          {(monitors ?? []).map((monitor) => {
            const isTriggered = monitor.match_count > 0
            const isChecking = checkingId === monitor.id

            return (
              <div
                key={monitor.id}
                className={`card am-card ${isTriggered ? 'am-card--triggered' : ''} ${!monitor.is_active ? 'am-card--paused' : ''}`}
              >
                <div className="am-card-status">
                  {isTriggered ? (
                    <AlertTriangle size={20} className="am-icon--triggered" />
                  ) : monitor.is_active ? (
                    <CheckCircle size={20} className="am-icon--active" />
                  ) : (
                    <Pause size={20} className="am-icon--paused" />
                  )}
                </div>

                <div className="am-card-content">
                  <p className="am-card-indicator">{monitor.indicator}</p>

                  <div className="am-card-meta">
                    <span className="am-meta-item">
                      <Search size={11} />
                      <span className="am-meta-label">{t('alerts.keywords')}:</span>
                      {(monitor.keywords ?? []).map((k) => (
                        <span key={k} className="am-keyword">
                          {k}
                        </span>
                      ))}
                    </span>

                    <span className="am-meta-item">
                      <Activity size={11} />
                      <span className="am-meta-label">{t('alerts.sources')}:</span>
                      {(monitor.osint_sources ?? []).map((s) => (
                        <span key={s} className="am-source-tag">
                          {SOURCE_LABELS[s] ?? s}
                        </span>
                      ))}
                    </span>

                    <span className="am-meta-item">
                      <Clock size={11} />
                      <span className="am-meta-label">{t('alerts.lastCheck')}:</span>
                      {formatDate(monitor.last_checked)}
                    </span>

                    {isTriggered && (
                      <span className="am-meta-item am-meta-item--match">
                        <Zap size={11} />
                        <span className="am-meta-label">{t('alerts.matches')}:</span>
                        <strong>{monitor.match_count}</strong>
                        {monitor.last_match && (
                          <span className="am-last-match">
                            · {t('alerts.lastMatch')}: {formatDate(monitor.last_match)}
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                </div>

                <div className="am-card-actions">
                  {isTriggered && (
                    <span className="am-badge am-badge--triggered">
                      <AlertTriangle size={10} /> {t('alerts.triggered')}
                    </span>
                  )}
                  {!isTriggered && monitor.is_active && (
                    <span className="am-badge am-badge--monitoring">
                      <Activity size={10} /> {t('alerts.monitoring')}
                    </span>
                  )}

                  <button
                    type="button"
                    className="btn am-btn-sm"
                    disabled={isChecking || !monitor.is_active}
                    onClick={() => checkMutation.mutate(monitor.id)}
                    title={t('alerts.checkNow')}
                  >
                    {isChecking ? (
                      <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} />
                    ) : (
                      <RefreshCw size={13} />
                    )}
                    {!isChecking && t('alerts.checkNow')}
                  </button>

                  <button
                    type="button"
                    className={`btn am-btn-sm ${monitor.is_active ? 'am-btn-pause' : 'am-btn-activate'}`}
                    disabled={toggleMutation.isPending}
                    onClick={() =>
                      toggleMutation.mutate({ id: monitor.id, active: !monitor.is_active })
                    }
                    title={monitor.is_active ? t('alerts.deactivate') : t('alerts.activate')}
                  >
                    {monitor.is_active ? (
                      <>
                        <Pause size={13} /> {t('alerts.deactivate')}
                      </>
                    ) : (
                      <>
                        <Play size={13} /> {t('alerts.activate')}
                      </>
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
