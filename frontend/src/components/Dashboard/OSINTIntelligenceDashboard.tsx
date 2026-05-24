import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  Download,
  Globe2,
  Hash,
  Landmark,
  Link2,
  MessageSquare,
  Plug,
  Radio,
  RefreshCw,
  Satellite,
  Shield,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import { dashboardService, geographicService, prospectiveService, reportsService } from '../../services/api'
import GeographicMap from '../Visualizations/GeographicMap'
import WorkflowProgress from '../shared/WorkflowProgress'
import CreateCaseModal from './CreateCaseModal'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import './OSINTIntelligenceDashboard.css'
import { useI18n } from '../../contexts/I18nContext'

type TimeFilter = {
  label: string
  days: number
}

const TIME_FILTERS: TimeFilter[] = [
  { label: 'time.24h', days: 1 },
  { label: 'time.7days', days: 7 },
  { label: 'time.30days', days: 30 },
  { label: 'time.90days', days: 90 },
]

export default function OSINTIntelligenceDashboard() {
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [selectedDays, setSelectedDays] = useState<number>(7)
  const [isExporting, setIsExporting] = useState(false)
  const [exportStatus, setExportStatus] = useState<string | null>(null)
  const { t } = useI18n()
  const { activeCase, setActiveCase } = useCase()

  useEffect(() => {
    if (activeCase?.id && selectedCaseId === null) {
      setSelectedCaseId(activeCase.id)
    }
  }, [activeCase?.id, selectedCaseId])

  const handleCaseCreated = (created: ActiveCase) => {
    setSelectedCaseId(created.id)
  }

  const { data: cases, isLoading: casesLoading } = useCasesList()

  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['osint-dashboard-metrics', selectedDays, selectedCaseId],
    queryFn: () => dashboardService.getMetrics(selectedDays, selectedCaseId),
  })

  const { data: alertsFeed } = useQuery({
    queryKey: ['osint-dashboard-alerts-feed', selectedDays, selectedCaseId],
    queryFn: () => dashboardService.getAlertsFeed(selectedDays, selectedCaseId, 5),
  })

  const { data: trendingTopics } = useQuery({
    queryKey: ['osint-dashboard-trending-topics', selectedDays, selectedCaseId],
    queryFn: () => dashboardService.getTrendingTopicsList(selectedDays, selectedCaseId, 5),
  })

  const { data: dataSources } = useQuery({
    queryKey: ['osint-dashboard-sources', selectedCaseId],
    queryFn: () => dashboardService.getSources(selectedCaseId),
  })

  const { data: geographicData } = useQuery({
    queryKey: ['osint-dashboard-locations', selectedCaseId],
    queryFn: () => geographicService.getLocations(selectedCaseId as number),
    enabled: !!selectedCaseId,
  })

  const monitorCaseId = selectedCaseId ?? activeCase?.id
  const { data: monitorSummary } = useQuery({
    queryKey: ['monitor-summary-dashboard', monitorCaseId],
    queryFn: () => prospectiveService.getMonitorSummary(monitorCaseId),
    refetchInterval: 60_000,
  })

  const selectedCase = useMemo(
    () => cases?.find((caseItem: any) => caseItem.id === selectedCaseId) ?? null,
    [cases, selectedCaseId]
  )

  const handleExport = async () => {
    if (!selectedCaseId || isExporting) return
    setIsExporting(true)
    setExportStatus(t('dashboard.exportGenerating'))
    try {
      const report = await reportsService.generate({
        case_id: selectedCaseId,
        title: `Informe OSINT - ${selectedCase?.name || 'Caso'}`
      })

      const reportId = report?.id
      if (!reportId) {
        throw new Error('No se pudo generar el informe')
      }

      let attempts = 0
      const maxAttempts = 10
      while (attempts < maxAttempts) {
        const reportStatus = await reportsService.get(reportId)
        if (reportStatus?.status === 'completed' && reportStatus?.file_path) {
          setExportStatus(t('dashboard.exportDownloading'))
          const blob = await reportsService.export(reportId)
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `report_${reportId}.pdf`
          document.body.appendChild(link)
          link.click()
          link.remove()
          window.URL.revokeObjectURL(url)
          setExportStatus('Informe descargado')
          break
        }
        attempts += 1
        await new Promise(resolve => setTimeout(resolve, 1500))
      }
      if (attempts >= maxAttempts) {
        setExportStatus(t('dashboard.exportQueued'))
      }
    } catch (error) {
      setExportStatus(t('dashboard.exportError'))
    } finally {
      setIsExporting(false)
      setTimeout(() => setExportStatus(null), 4000)
    }
  }

  if (casesLoading && metricsLoading) {
    return (
      <div className="osint-dashboard-loading">
        <div className="loading-spinner" />
        <p>{t('dashboard.title')}</p>
      </div>
    )
  }

  const totalMentions = metrics?.total_mentions?.total_mentions ?? 0
  const sentimentScore = metrics?.sentiment_score?.sentiment_score ?? 0
  const estimatedReach = metrics?.estimated_reach?.formatted_reach ?? '0'
  const engagementRate = metrics?.engagement_rate?.engagement_rate ?? 0
  const criticalAlerts = metrics?.critical_alerts?.critical_alerts ?? 0
  const trendingTopicsCount = metrics?.trending_topics?.trending_topics ?? 0
  const triggeredMonitors = monitorSummary?.triggered_count ?? 0
  const totalMonitorMatches = monitorSummary?.total_matches ?? 0

  return (
    <div className="osint-intelligence-dashboard">
      <div className="dashboard-header-section">
        <div className="header-left">
          <p className="dashboard-kicker">{t('layout.intelligenceUnit')}</p>
          <h1 className="dashboard-title">{t('dashboard.title')}</h1>
          <div className="status-indicator">
            <span className="status-icon" aria-hidden>
              <Satellite size={16} />
            </span>
            <span className="status-badge live">{t('dashboard.statusLive')}</span>
          </div>
          <p className="dashboard-description">{t('dashboard.description')}</p>
          {activeCase && (
            <WorkflowProgress
              osintCount={activeCase.osint_count}
              extractionCount={activeCase.extraction_count}
              hasMicmac={activeCase.has_micmac}
              hasMactor={activeCase.has_mactor}
              hasScenarios={activeCase.has_scenarios}
            />
          )}
          <div className="case-toolbar">
            <select
              className="case-select"
              value={selectedCaseId ?? ''}
              onChange={(event) => {
                const value = event.target.value
                if (!value) {
                  setSelectedCaseId(null)
                  return
                }
                const id = Number(value)
                setSelectedCaseId(id)
                const c = cases?.find((x) => x.id === id)
                if (c) {
                  setActiveCase({
                    id: c.id,
                    name: c.name,
                    case_type: c.case_type ?? 'general',
                    status: c.status ?? 'pending',
                  })
                }
              }}
            >
              <option value="">{t('dashboard.allCases')}</option>
              {cases?.map((caseItem) => (
                <option key={caseItem.id} value={caseItem.id}>
                  #{caseItem.id} — {caseItem.name}
                </option>
              ))}
            </select>
            <CreateCaseModal className="btn-create-case-dashboard" onCaseCreated={handleCaseCreated} />
            {activeCase && (
              <Link to="/osint-collection" className="case-osint-link">
                Recollida OSINT →
              </Link>
            )}
          </div>
        </div>
        <div className="header-right">
          <div className="time-filters">
            {TIME_FILTERS.map((filter) => (
              <button
                key={filter.label}
                type="button"
                className={`time-filter-btn ${selectedDays === filter.days ? 'active' : ''}`}
                onClick={() => setSelectedDays(filter.days)}
              >
                {t(filter.label as 'time.24h')}
              </button>
            ))}
          </div>
          <div className="action-buttons">
            <button type="button" className="action-btn" onClick={() => refetchMetrics()}>
              <RefreshCw size={14} />
              {t('dashboard.update')}
            </button>
            <button
              type="button"
              className="action-btn"
              onClick={handleExport}
              disabled={!selectedCaseId || isExporting}
            >
              <Download size={14} />
              {t('dashboard.export')}
            </button>
          </div>
          {exportStatus && <div className="export-status">{exportStatus}</div>}
        </div>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon"><MessageSquare size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{totalMentions.toLocaleString()}</div>
            <div className="metric-change">
              {metrics?.total_mentions?.change_percent ?? 0}% {t('metrics.previousPeriod')}
            </div>
            <div className="metric-label">{t('metrics.totalMentions')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon"><TrendingUp size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{sentimentScore}%</div>
            <div className="metric-change">{metrics?.sentiment_score?.change_points ?? 0} pts</div>
            <div className="metric-label">{t('metrics.sentimentScore')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon"><Users size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{estimatedReach}</div>
            <div className="metric-change">
              {metrics?.estimated_reach?.change_percent ?? 0}% {t('metrics.estimatedReachChange')}
            </div>
            <div className="metric-label">{t('metrics.estimatedReach')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon"><Target size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{engagementRate}%</div>
            <div className="metric-change">{t('metrics.engagementRate')}</div>
            <div className="metric-label">{t('metrics.engagement')}</div>
          </div>
        </div>
        <div className="metric-card critical">
          <div className="metric-icon"><Bell size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{criticalAlerts}</div>
            <div className="metric-change">{metrics?.critical_alerts?.change ?? 0} alertes noves</div>
            <div className="metric-label">{t('metrics.criticalAlerts')}</div>
          </div>
        </div>
        <div className={`metric-card ${triggeredMonitors > 0 ? 'critical' : ''}`}>
          <div className="metric-icon"><Radio size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{triggeredMonitors}</div>
            <div className="metric-change">
              {totalMonitorMatches > 0
                ? `${totalMonitorMatches} coincidències OSINT`
                : t('metrics.triggeredMonitorsNote')}
            </div>
            <div className="metric-label">
              <Link to="/alert-monitors">{t('metrics.triggeredMonitors')}</Link>
            </div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon"><Hash size={18} /></div>
          <div className="metric-content">
            <div className="metric-value">{trendingTopicsCount}</div>
            <div className="metric-change">{t('metrics.trendingTopicsNote')}</div>
            <div className="metric-label">{t('metrics.trendingTopics')}</div>
          </div>
        </div>
      </div>

      <div className="panels-grid">
        <div className="panel-card">
          <h3 className="panel-title">
            <span className="panel-title-icon"><Radio size={18} /></span>
            {t('panels.dataSources')}
          </h3>
          <div className="panel-status-indicators">
            <div className="status-dot active">Actiu</div>
            <div className="status-dot inactive">Inactiu</div>
          </div>
          <div className="sources-list">
            {dataSources?.length ? (
              dataSources.map((source: { name: string; mentions: number }) => (
                <div key={source.name} className="source-item">
                  <div className="source-icon"><Link2 size={16} /></div>
                  <div className="source-info">
                    <div className="source-name">{source.name}</div>
                    <div className="source-mentions">{source.mentions} {t('panels.mentionsLabel')}</div>
                  </div>
                  <div className="source-status-dot active" />
                </div>
              ))
            ) : (
              <div className="no-data">{t('panels.dataSourcesNoData')}</div>
            )}
          </div>
        </div>

        <div className="panel-card">
          <h3 className="panel-title">
            <span className="panel-title-icon"><TrendingUp size={18} /></span>
            {t('panels.trendingTopics')}
          </h3>
          <div className="topic-filters">
            <button className="topic-filter-btn active">Todo</button>
          </div>
          <div className="topics-list">
            {trendingTopics?.length ? (
              trendingTopics.map((topic: any) => (
                <div key={topic.topic} className="topic-item">
                  <div className="topic-name"># {topic.topic}</div>
                  <div className="topic-mentions">{topic.mentions} {t('panels.mentionsLabel')}</div>
                  <div className="topic-stats">
                    <span className="topic-change">
                      {topic.change_percent >= 0 ? '+' : ''}
                      {topic.change_percent}%
                    </span>
                    <div className="topic-sentiment-bar" />
                  </div>
                </div>
              ))
            ) : (
              <div className="no-data">{t('panels.trendingTopicsNoData')}</div>
            )}
          </div>
        </div>

        <div className="panel-card">
          <h3 className="panel-title">
            <span className="panel-title-icon"><Bell size={18} /></span>
            {t('panels.alerts')}
          </h3>
          <div className="alerts-list">
            {alertsFeed?.length ? (
              alertsFeed.map((alert: any) => (
                <div key={alert.id} className="alert-item">
                  <div className={`alert-bar ${alert.level}`} />
                  <div className="alert-content">
                    <div className="alert-title">{alert.title}</div>
                    <div className="alert-details">
                      {alert.prediction_type} · {alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}
                    </div>
                  </div>
                  <div className="alert-percentage">{Math.round(alert.confidence)}%</div>
                </div>
              ))
            ) : (
              <div className="no-data">{t('panels.alertsNoData')}</div>
            )}
          </div>
        </div>
      </div>

      {selectedCaseId && geographicData?.locations?.length ? (
        <div className="panel-card">
          <h3 className="panel-title">
            <span className="panel-title-icon"><Globe2 size={18} /></span>
            {t('panels.geographic')}
          </h3>
          <GeographicMap
            locations={geographicData.locations.map((loc: any) => ({
              id: loc.id,
              name: loc.name,
              latitude: loc.latitude,
              longitude: loc.longitude,
              type: loc.type as 'country' | 'region' | 'city' | 'neighborhood' | 'point',
              count: loc.count,
              data: loc.data
            }))}
            title={selectedCase?.name ? `Ubicacions - ${selectedCase.name}` : 'Ubicacions'}
            initialZoom={2}
            showHeatmap={true}
            caseId={selectedCaseId}
          />
        </div>
      ) : null}

      <div className="quick-access-section">
        <h3>{t('quickAccess.title')}</h3>
        <div className="quick-access-buttons">
          <Link className="quick-access-btn accent" to="/intelligence">
            <Globe2 size={16} />
            Intelligence Unit
          </Link>
          <Link className="quick-access-btn" to="/integration">
            <Plug size={16} />
            {t('quickAccess.integrations')}
          </Link>
          <Link className="quick-access-btn" to="/reputation">
            <Shield size={16} />
            {t('quickAccess.reputation')}
          </Link>
          <Link className="quick-access-btn" to="/public-affairs">
            <Landmark size={16} />
            {t('quickAccess.publicAffairs')}
          </Link>
        </div>
      </div>
    </div>
  )
}
