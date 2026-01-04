import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { visualizationsService, geographicService, casesService } from '../../services/api'
import NetworkGraph from './NetworkGraph'
import TrendAnalysis from './TrendAnalysis'
import RelationshipMap from './RelationshipMap'
import GeographicMap from './GeographicMap'
import GeopoliticalDashboard from './GeopoliticalDashboard'
import InvestmentDashboard from './InvestmentDashboard'
import SocialDashboard from './SocialDashboard'
import BusinessDashboard from './BusinessDashboard'
import Heatmap from './Heatmap'
import PostsViewer from '../Posts/PostsViewer'
import './Visualizations.css'

// Heatmap Selector Component
function HeatmapSelector({ caseId }: { caseId: number }) {
  const [metricType, setMetricType] = useState<'posts' | 'sentiment' | 'engagement'>('posts')
  const [granularity, setGranularity] = useState<'country' | 'region' | 'city' | 'municipality'>('city')

  return (
    <div>
      <div className="heatmap-controls-bar">
        <div className="control-group">
          <label>Mètrica:</label>
          <select value={metricType} onChange={(e) => setMetricType(e.target.value as any)}>
            <option value="posts">Posts</option>
            <option value="sentiment">Sentiment</option>
            <option value="engagement">Engagement</option>
          </select>
        </div>
        <div className="control-group">
          <label>Granularitat:</label>
          <select value={granularity} onChange={(e) => setGranularity(e.target.value as any)}>
            <option value="municipality">Comuns (Andorra)</option>
            <option value="city">Ciutats</option>
            <option value="region">Regions</option>
            <option value="country">Països</option>
          </select>
        </div>
      </div>
      <Heatmap
        caseId={caseId}
        metricType={metricType}
        granularity={granularity}
      />
    </div>
  )
}

interface VisualizationsDashboardProps {
  caseId: number
}

export default function VisualizationsDashboard({ caseId }: VisualizationsDashboardProps) {
  const [activeTab, setActiveTab] = useState<'network' | 'trends' | 'relationships' | 'geographic' | 'heatmap' | 'posts'>('network')
  
  // Get case data to determine case type
  const { data: caseData } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesService.get(caseId),
    enabled: !!caseId
  })
  
  const caseType = caseData?.case_type?.toLowerCase() || 'general'

  const { data: networkData, isLoading: networkLoading } = useQuery({
    queryKey: ['networkGraph', caseId],
    queryFn: () => visualizationsService.networkGraph(caseId),
    enabled: activeTab === 'network'
  })

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: activeTab === 'trends'
  })

  const { data: relationshipData, isLoading: relationshipLoading } = useQuery({
    queryKey: ['relationshipMap', caseId],
    queryFn: () => visualizationsService.relationshipMap(caseId),
    enabled: activeTab === 'relationships'
  })

  const { data: geographicData, isLoading: geographicLoading } = useQuery({
    queryKey: ['geographicLocations', caseId],
    queryFn: () => geographicService.getLocations(caseId),
    enabled: activeTab === 'geographic'
  })

  // Route to expert dashboard based on case type
  const getExpertDashboard = () => {
    switch (caseType) {
      case 'geopolitical':
        return <GeopoliticalDashboard caseId={caseId} />
      case 'business':
      case 'investment':
        return <InvestmentDashboard caseId={caseId} />
      case 'social':
      case 'political':
        return <SocialDashboard caseId={caseId} />
      default:
        // For general cases or when type is not recognized, show BusinessDashboard
        return <BusinessDashboard caseId={caseId} />
    }
  }

  // Show expert dashboard if case type matches
  if (['geopolitical', 'business', 'investment', 'social', 'political'].includes(caseType)) {
    return (
      <div className="visualizations-dashboard">
        {getExpertDashboard()}
      </div>
    )
  }

  // Otherwise show standard visualizations
  return (
    <div className="visualizations-dashboard">
      <div className="visualizations-header">
        <h2>Visualizaciones - Economic Intelligence Unit</h2>
        <div className="visualization-tabs">
          <button
            className={activeTab === 'network' ? 'active' : ''}
            onClick={() => setActiveTab('network')}
          >
            Network Graph
          </button>
          <button
            className={activeTab === 'trends' ? 'active' : ''}
            onClick={() => setActiveTab('trends')}
          >
            Trend Analysis
          </button>
          <button
            className={activeTab === 'relationships' ? 'active' : ''}
            onClick={() => setActiveTab('relationships')}
          >
            Relationship Map
          </button>
          <button
            className={activeTab === 'geographic' ? 'active' : ''}
            onClick={() => setActiveTab('geographic')}
          >
            Geographic Map
          </button>
          <button
            className={activeTab === 'heatmap' ? 'active' : ''}
            onClick={() => setActiveTab('heatmap')}
          >
            Heatmap
          </button>
        </div>
      </div>

      <div className="visualization-content">
        {activeTab === 'network' && (
          <div>
            {networkLoading ? (
              <div className="loading">Cargando network graph...</div>
            ) : networkData ? (
              <NetworkGraph
                nodes={networkData.nodes}
                edges={networkData.edges}
                title="Network Graph - Case Analysis"
              />
            ) : (
              <div className="no-data">No hay datos de red disponibles</div>
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <div>
            {trendLoading ? (
              <div className="loading">Cargando análisis de tendencias...</div>
            ) : trendData ? (
              <TrendAnalysis
                data={trendData.data || []}
                predictionData={trendData.prediction || []}
                showPrediction={!!trendData.prediction}
                title="Trend Analysis - Case Evolution"
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
              <div className="no-data">No hay datos de tendencias disponibles</div>
            )}
          </div>
        )}

        {activeTab === 'relationships' && (
          <div>
            {relationshipLoading ? (
              <div className="loading">Cargando mapa de relaciones...</div>
            ) : relationshipData ? (
              <RelationshipMap
                relationships={relationshipData.relationships.map(r => ({
                  from: r.from_entity,
                  to: r.to_entity,
                  type: r.type,
                  strength: r.strength
                }))}
                title="Relationship Map - Entity Connections"
              />
            ) : (
              <div className="no-data">No hay datos de relaciones disponibles</div>
            )}
          </div>
        )}

        {activeTab === 'geographic' && (
          <div>
            {geographicLoading ? (
              <div className="loading">Cargando mapa geográfico...</div>
            ) : geographicData && geographicData.locations && geographicData.locations.length > 0 ? (
              <GeographicMap
                locations={geographicData.locations.map(loc => ({
                  id: loc.id,
                  name: loc.name,
                  latitude: loc.latitude,
                  longitude: loc.longitude,
                  type: loc.type as 'country' | 'region' | 'city' | 'neighborhood' | 'point',
                  data: loc.data,
                  count: loc.count
                }))}
                title="Geographic Map - Case Locations"
                caseId={caseId}
                showHeatmap={true}
              />
            ) : (
              <div className="no-data">No hay datos geográficos disponibles para este caso</div>
            )}
          </div>
        )}

        {activeTab === 'heatmap' && (
          <div>
            <HeatmapSelector caseId={caseId} />
          </div>
        )}

        {activeTab === 'posts' && (
          <div>
            <PostsViewer caseId={caseId} />
          </div>
        )}
      </div>
    </div>
  )
}

