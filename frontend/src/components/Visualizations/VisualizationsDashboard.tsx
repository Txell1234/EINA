import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  visualizationsService,
  geographicService,
} from '../../services/api'
import NetworkGraph from './NetworkGraph'
import TrendAnalysis from './TrendAnalysis'
import GeographicMap from './GeographicMap'
import Heatmap from './Heatmap'
import EventTimeline from './EventTimeline'
import FinancialIntelWidget from './FinancialIntelWidget'
import IntelMetricsPanel from './IntelMetricsPanel'
import PostsViewer from '../Posts/PostsViewer'
import './Visualizations.css'

function HeatmapSelector({ caseId }: { caseId: number }) {
  const [metricType, setMetricType] = useState<'posts' | 'sentiment' | 'engagement'>('posts')
  const [granularity, setGranularity] = useState<'country' | 'region' | 'city' | 'municipality'>('city')
  return (
    <div>
      <div className="heatmap-controls-bar">
        <div className="control-group">
          <label>Mètrica:</label>
          <select
            value={metricType}
            onChange={(e) => setMetricType(e.target.value as 'posts' | 'sentiment' | 'engagement')}
          >
            <option value="posts">Posts</option>
            <option value="sentiment">Sentiment</option>
            <option value="engagement">Engagement</option>
          </select>
        </div>
        <div className="control-group">
          <label>Granularitat:</label>
          <select
            value={granularity}
            onChange={(e) =>
              setGranularity(e.target.value as 'country' | 'region' | 'city' | 'municipality')
            }
          >
            <option value="municipality">Comuns (Andorra)</option>
            <option value="city">Ciutats</option>
            <option value="region">Regions</option>
            <option value="country">Països</option>
          </select>
        </div>
      </div>
      <Heatmap caseId={caseId} metricType={metricType} granularity={granularity} />
    </div>
  )
}

type TabId = 'overview' | 'map' | 'timeline' | 'network' | 'financial' | 'intel' | 'trends' | 'heatmap' | 'posts'

const TABS: Array<{ id: TabId; label: string; icon: string }> = [
  { id: 'overview', label: 'Visió general', icon: '◈' },
  { id: 'map', label: 'Mapa', icon: '🗺️' },
  { id: 'timeline', label: 'Timeline', icon: '⏱️' },
  { id: 'network', label: 'Xarxa', icon: '🕸️' },
  { id: 'financial', label: 'Financer', icon: '📊' },
  { id: 'intel', label: 'Intel', icon: '🎯' },
  { id: 'trends', label: 'Tendències', icon: '📈' },
  { id: 'heatmap', label: 'Heatmap', icon: '🔥' },
  { id: 'posts', label: 'Publicacions', icon: '📋' },
]

interface VisualizationsDashboardProps {
  caseId: number
}

function TabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: TabId
  onTabChange: (t: TabId) => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 0,
        overflowX: 'auto',
        borderBottom: '1px solid var(--color-gray-200)',
        scrollbarWidth: 'none',
      }}
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onTabChange(tab.id)}
          style={{
            padding: '10px 16px',
            border: 'none',
            cursor: 'pointer',
            background: 'none',
            borderBottom: activeTab === tab.id ? '2px solid var(--color-primary)' : '2px solid transparent',
            color: activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-gray-500)',
            fontWeight: activeTab === tab.id ? 600 : 400,
            fontSize: 'var(--font-size-sm)',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'all .15s',
          }}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export default function VisualizationsDashboard({ caseId }: VisualizationsDashboardProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const { data: networkData, isLoading: networkLoading } = useQuery({
    queryKey: ['networkGraph', caseId],
    queryFn: () => visualizationsService.networkGraph(caseId),
    enabled: !!caseId,
  })

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: !!caseId,
  })

  const { data: geographicData, isLoading: geographicLoading } = useQuery({
    queryKey: ['geographicLocations', caseId],
    queryFn: () => geographicService.getLocations(caseId),
    enabled: !!caseId,
  })

  const mapLocations =
    geographicData?.locations?.map(
      (loc: {
        id: string
        name: string
        latitude: number
        longitude: number
        type: string
        data?: unknown
        count?: number
      }) => ({
        id: loc.id,
        name: loc.name,
        latitude: loc.latitude,
        longitude: loc.longitude,
        type: loc.type as 'country' | 'region' | 'city' | 'neighborhood' | 'point',
        data: loc.data,
        count: loc.count,
      }),
    ) ?? []

  return (
    <div className="visualizations-dashboard">
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="visualization-content" style={{ marginTop: 'var(--spacing-lg)' }}>
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-lg)' }}>
            <div className="card">
              <h3
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 600,
                  color: 'var(--color-primary)',
                  margin: '0 0 var(--spacing-sm)',
                }}
              >
                🗺️ Mapa geoespacial
              </h3>
              {geographicLoading ? (
                <div className="spinner" style={{ margin: '1rem auto' }} />
              ) : mapLocations.length > 0 ? (
                <GeographicMap locations={mapLocations} caseId={caseId} initialZoom={2} showHeatmap={false} />
              ) : (
                <div
                  style={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-gray-400)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  Sense dades geogràfiques
                </div>
              )}
            </div>

            <div className="card">
              <h3
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 600,
                  color: 'var(--color-primary)',
                  margin: '0 0 var(--spacing-sm)',
                }}
              >
                🕸️ Xarxa de relacions
              </h3>
              {networkLoading ? (
                <div className="spinner" style={{ margin: '1rem auto' }} />
              ) : networkData ? (
                <NetworkGraph
                  nodes={networkData.nodes ?? []}
                  edges={networkData.edges ?? []}
                  width={380}
                  height={280}
                />
              ) : (
                <div
                  style={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-gray-400)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  Sense dades de xarxa
                </div>
              )}
            </div>

            <div className="card">
              <FinancialIntelWidget caseId={caseId} />
            </div>

            <div className="card">
              <IntelMetricsPanel caseId={caseId} />
            </div>
          </div>
        )}

        {activeTab === 'map' && (
          <div className="card">
            {geographicLoading ? (
              <div className="spinner" style={{ margin: '2rem auto' }} />
            ) : mapLocations.length > 0 ? (
              <GeographicMap
                locations={mapLocations}
                title="Mapa geopolític — capes superposables"
                caseId={caseId}
                showHeatmap={true}
                initialZoom={2}
              />
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🗺️</div>
                <h3 className="empty-state-title">Sense dades geogràfiques</h3>
                <p className="empty-state-desc">Recull dades OSINT amb ubicació per veure el mapa.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'timeline' && (
          <div className="card">
            <h3
              style={{
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                color: 'var(--color-primary)',
                margin: '0 0 var(--spacing-lg)',
              }}
            >
              ⏱️ Timeline d&apos;esdeveniments geopolítics
            </h3>
            <EventTimeline caseId={caseId} />
          </div>
        )}

        {activeTab === 'network' && (
          <div className="card">
            {networkLoading ? (
              <div className="spinner" style={{ margin: '2rem auto' }} />
            ) : networkData ? (
              <NetworkGraph
                nodes={networkData.nodes ?? []}
                edges={networkData.edges ?? []}
                title="Actors i connexions"
                width={900}
                height={600}
              />
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🕸️</div>
                <h3 className="empty-state-title">Xarxa buida</h3>
              </div>
            )}
          </div>
        )}

        {activeTab === 'financial' && (
          <div className="card">
            <FinancialIntelWidget caseId={caseId} watchlist={['EUR', 'CNY', 'JPY', 'GBP', 'CHF', 'AED', 'INR']} />
          </div>
        )}

        {activeTab === 'intel' && (
          <div className="card">
            <IntelMetricsPanel caseId={caseId} />
          </div>
        )}

        {activeTab === 'trends' && (
          <div>
            {trendLoading ? (
              <div className="spinner" style={{ margin: '2rem auto' }} />
            ) : trendData ? (
              <TrendAnalysis
                data={trendData.data || []}
                predictionData={trendData.prediction || []}
                showPrediction={!!trendData.prediction}
                title="Anàlisi de tendències"
                type="area"
                metadata={trendData.metadata}
                dataSourcesBreakdown={trendData.data_sources_breakdown}
                queriesExecuted={trendData.queries_executed}
                totalResultsBySource={trendData.total_results_by_source}
                metrics={trendData.metrics}
                insights={trendData.insights}
                comments_by_social_network={trendData.comments_by_social_network}
                concepts={trendData.concepts}
                caseId={caseId}
              />
            ) : (
              <div className="card">
                <div className="empty-state">
                  <div className="empty-state-icon">📈</div>
                  <h3 className="empty-state-title">Sense dades de tendències</h3>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'heatmap' && (
          <div className="card">
            <HeatmapSelector caseId={caseId} />
          </div>
        )}

        {activeTab === 'posts' && (
          <div className="card">
            <PostsViewer caseId={caseId} />
          </div>
        )}
      </div>
    </div>
  )
}


