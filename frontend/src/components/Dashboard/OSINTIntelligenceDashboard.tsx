import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { casesService, dashboardService, geographicService, reportsService } from '../../services/api'
import GeographicMap from '../Visualizations/GeographicMap'
import WorkflowProgress from '../shared/WorkflowProgress'
import { useCase } from '../../contexts/CaseContext'
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
  const { activeCase } = useCase()

  const { data: cases, isLoading: casesLoading } = useQuery({
    queryKey: ['dashboard-cases'],
    queryFn: () => casesService.list(),
  })

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

  return (
    <div className="osint-intelligence-dashboard">
      <div className="dashboard-header-section">
        <div className="header-left">
          <h1 className="dashboard-title">{t('dashboard.title')}</h1>
          <div className="status-indicator">
            <span className="status-icon">🛰️</span>
            <span className="status-badge live">{t('dashboard.statusLive')}</span>
          </div>
          <p className="dashboard-description">
            {t('dashboard.description')}
          </p>
          {activeCase && (
            <WorkflowProgress
              osintCount={activeCase.osint_count}
              extractionCount={activeCase.extraction_count}
              hasMicmac={activeCase.has_micmac}
              hasMactor={activeCase.has_mactor}
              hasScenarios={activeCase.has_scenarios}
            />
          )}
          <div style={{ marginTop: '1rem' }}>
            <select
              value={selectedCaseId ?? ''}
              onChange={(event) =>
                setSelectedCaseId(event.target.value ? Number(event.target.value) : null)
              }
              style={{
                padding: '0.5rem 0.75rem',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.3)',
                background: 'rgba(255,255,255,0.2)',
                color: 'white',
                minWidth: '220px'
              }}
            >
              <option value="">{t('dashboard.allCases')}</option>
              {cases?.map((caseItem: any) => (
                <option key={caseItem.id} value={caseItem.id}>
                  {caseItem.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="header-right">
          <div className="time-filters">
            {TIME_FILTERS.map((filter) => (
              <button
                key={filter.label}
                className={`time-filter-btn ${selectedDays === filter.days ? 'active' : ''}`}
                onClick={() => setSelectedDays(filter.days)}
              >
                {t(filter.label as any)}
              </button>
            ))}
          </div>
          <div className="action-buttons">
            <button className="action-btn" onClick={() => refetchMetrics()}>
              🔄 {t('dashboard.update')}
            </button>
            <button
              className="action-btn"
              onClick={handleExport}
              disabled={!selectedCaseId || isExporting}
            >
              ⬇️ {t('dashboard.export')}
            </button>
          </div>
          {exportStatus && (
            <div style={{ fontSize: '0.875rem', color: 'white' }}>
              {exportStatus}
            </div>
          )}
        </div>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon">💬</div>
          <div className="metric-content">
            <div className="metric-value">{totalMentions.toLocaleString()}</div>
            <div className="metric-change">
              {metrics?.total_mentions?.change_percent ?? 0}% {t('metrics.previousPeriod')}
            </div>
            <div className="metric-label">{t('metrics.totalMentions')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">📈</div>
          <div className="metric-content">
            <div className="metric-value">{sentimentScore}%</div>
            <div className="metric-change">
              {metrics?.sentiment_score?.change_points ?? 0} pts
            </div>
            <div className="metric-label">{t('metrics.sentimentScore')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">👥</div>
          <div className="metric-content">
            <div className="metric-value">{estimatedReach}</div>
            <div className="metric-change">
              {metrics?.estimated_reach?.change_percent ?? 0}% {t('metrics.estimatedReachChange')}
            </div>
            <div className="metric-label">{t('metrics.estimatedReach')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">🎯</div>
          <div className="metric-content">
            <div className="metric-value">{engagementRate}%</div>
            <div className="metric-change">{t('metrics.engagementRate')}</div>
            <div className="metric-label">{t('metrics.engagement')}</div>
          </div>
        </div>
        <div className="metric-card critical">
          <div className="metric-icon">⚠️</div>
          <div className="metric-content">
            <div className="metric-value">{criticalAlerts}</div>
            <div className="metric-change">
              {metrics?.critical_alerts?.change ?? 0} alertes noves
            </div>
            <div className="metric-label">{t('metrics.criticalAlerts')}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">#️⃣</div>
          <div className="metric-content">
            <div className="metric-value">{trendingTopicsCount}</div>
            <div className="metric-change">{t('metrics.trendingTopicsNote')}</div>
            <div className="metric-label">{t('metrics.trendingTopics')}</div>
          </div>
        </div>
      </div>

      <div className="panels-grid">
        <div className="panel-card">
          <h3 className="panel-title">📡 {t('panels.dataSources')}</h3>
          <div className="panel-status-indicators">
            <div className="status-dot active">Activo</div>
            <div className="status-dot inactive">Inactivo</div>
          </div>
          <div className="sources-list">
            {dataSources?.length ? (
              dataSources.map((source: any) => (
                <div key={source.name} className="source-item">
                  <div className="source-icon">🔗</div>
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
          <h3 className="panel-title">🔥 {t('panels.trendingTopics')}</h3>
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
          <h3 className="panel-title">🚨 {t('panels.alerts')}</h3>
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
        <div className="panel-card" style={{ marginBottom: '2rem' }}>
          <h3 className="panel-title">🗺️ {t('panels.geographic')}</h3>
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
          <a className="quick-access-btn" href="/integration">🔌 {t('quickAccess.integrations')}</a>
          <a className="quick-access-btn" href="/reputation">🛡️ {t('quickAccess.reputation')}</a>
          <a className="quick-access-btn" href="/public-affairs">🏛️ {t('quickAccess.publicAffairs')}</a>
        </div>
      </div>
    </div>
  )
}
