import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { visualizationsService, geographicService } from '../../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, ScatterChart, Scatter, ZAxis } from 'recharts'
import Heatmap from './Heatmap'
import './GeopoliticalDashboard.css'

interface GeopoliticalDashboardProps {
  caseId: number
}

interface BilateralRelation {
  country1: string
  country2: string
  strength: number
  recent_agreements: number
  sentiment: number
}

interface Treaty {
  name: string
  date: string
  status: string
  countries: string[]
}

interface DiplomaticEvent {
  event: string
  date: string
  significance: string
  sentiment: number
}

export default function GeopoliticalDashboard({ caseId }: GeopoliticalDashboardProps) {
  const [activeView, setActiveView] = useState<'overview' | 'relations' | 'treaties' | 'events' | 'trade' | 'heatmap'>('overview')

  // Get trend analysis data
  const { data: trendData } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: !!caseId
  })

  // Get geographic data
  const { data: geographicData } = useQuery({
    queryKey: ['geographicLocations', caseId],
    queryFn: () => geographicService.getLocations(caseId),
    enabled: !!caseId
  })

  // Get expert analysis (would need new endpoint)
  const { data: expertAnalysis } = useQuery({
    queryKey: ['expertAnalysis', caseId, 'geopolitical'],
    queryFn: async () => {
      // This would call a new endpoint: GET /api/visualizations/expert/{case_id}
      // For now, extract from trend data metadata
      return null
    },
    enabled: !!caseId
  })

  // Extract geopolitical data from trend analysis metadata
  const geopoliticalInsights = trendData?.metadata?.predictions?.filter((p: any) => 
    p.type === 'geopolitical' || p.text?.toLowerCase().includes('bilateral') || 
    p.text?.toLowerCase().includes('treaty') || p.text?.toLowerCase().includes('diplomatic')
  ) || []

  // Mock data structure (would come from expert analysis endpoint)
  const bilateralRelations: BilateralRelation[] = [
    { country1: 'India', country2: 'UAE', strength: 85, recent_agreements: 3, sentiment: 0.7 },
    { country1: 'Spain', country2: 'Andorra', strength: 90, recent_agreements: 1, sentiment: 0.8 }
  ]

  const treaties: Treaty[] = [
    { name: 'India-UAE Comprehensive Economic Partnership Agreement', date: '2024-02-18', status: 'Active', countries: ['India', 'UAE'] },
    { name: 'Bilateral Investment Treaty', date: '2023-06-15', status: 'Active', countries: ['India', 'UAE'] }
  ]

  const diplomaticEvents: DiplomaticEvent[] = [
    { event: 'Bilateral Summit', date: '2024-12-01', significance: 'High', sentiment: 0.75 },
    { event: 'Trade Agreement Signing', date: '2024-11-15', significance: 'High', sentiment: 0.8 }
  ]

  return (
    <div className="geopolitical-dashboard">
      <div className="dashboard-header">
        <h2>🌍 Geopolitical Intelligence Dashboard</h2>
        <div className="view-selector">
          <button 
            className={activeView === 'overview' ? 'active' : ''}
            onClick={() => setActiveView('overview')}
          >
            Overview
          </button>
          <button 
            className={activeView === 'relations' ? 'active' : ''}
            onClick={() => setActiveView('relations')}
          >
            Bilateral Relations
          </button>
          <button 
            className={activeView === 'treaties' ? 'active' : ''}
            onClick={() => setActiveView('treaties')}
          >
            Treaties & Agreements
          </button>
          <button 
            className={activeView === 'events' ? 'active' : ''}
            onClick={() => setActiveView('events')}
          >
            Diplomatic Events
          </button>
          <button 
            className={activeView === 'trade' ? 'active' : ''}
            onClick={() => setActiveView('trade')}
          >
            Trade Analysis
          </button>
          <button 
            className={activeView === 'heatmap' ? 'active' : ''}
            onClick={() => setActiveView('heatmap')}
          >
            Heatmap
          </button>
        </div>
      </div>

      {activeView === 'overview' && (
        <div className="overview-section">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Bilateral Accords</div>
              <div className="metric-value">{treaties.length}</div>
              <div className="metric-change">Active treaties</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Diplomatic Events</div>
              <div className="metric-value">{diplomaticEvents.length}</div>
              <div className="metric-change">Last 30 days</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Relations Strength</div>
              <div className="metric-value">
                {Math.round(bilateralRelations.reduce((sum, r) => sum + r.strength, 0) / bilateralRelations.length)}%
              </div>
              <div className="metric-change">Average</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Regional Sentiment</div>
              <div className="metric-value">
                {Math.round(bilateralRelations.reduce((sum, r) => sum + r.sentiment, 0) / bilateralRelations.length * 100)}%
              </div>
              <div className="metric-change">Positive</div>
            </div>
          </div>

          {/* Bilateral Relations Map */}
          <div className="relations-map-section">
            <h3>🗺️ Bilateral Relations Map</h3>
            <div className="relations-map">
              {bilateralRelations.map((relation, idx) => (
                <div key={idx} className="relation-item">
                  <div className="relation-countries">
                    <span className="country">{relation.country1}</span>
                    <span className="relation-strength" style={{
                      width: `${relation.strength}%`,
                      backgroundColor: relation.strength > 70 ? '#28a745' : relation.strength > 50 ? '#ffc107' : '#dc3545'
                    }}></span>
                    <span className="country">{relation.country2}</span>
                  </div>
                  <div className="relation-details">
                    <span>Strength: {relation.strength}%</span>
                    <span>Agreements: {relation.recent_agreements}</span>
                    <span>Sentiment: {Math.round(relation.sentiment * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Key Insights */}
          {geopoliticalInsights.length > 0 && (
            <div className="insights-section">
              <h3>💡 Key Geopolitical Insights</h3>
              <ul>
                {geopoliticalInsights.map((insight: any, idx: number) => (
                  <li key={idx}>{insight.text}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {activeView === 'relations' && (
        <div className="relations-section">
          <h3>🤝 Bilateral Relations Analysis</h3>
          <div className="relations-chart">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={bilateralRelations}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="country1" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="strength" fill="#667eea" name="Relation Strength (%)" />
                <Bar dataKey="recent_agreements" fill="#48bb78" name="Recent Agreements" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeView === 'treaties' && (
        <div className="treaties-section">
          <h3>📜 Treaties & Agreements Timeline</h3>
          <div className="treaties-timeline">
            {treaties.map((treaty, idx) => (
              <div key={idx} className="treaty-item">
                <div className="treaty-date">{new Date(treaty.date).toLocaleDateString()}</div>
                <div className="treaty-content">
                  <div className="treaty-name">{treaty.name}</div>
                  <div className="treaty-details">
                    <span className="treaty-status status-active">{treaty.status}</span>
                    <span className="treaty-countries">{treaty.countries.join(' ↔ ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'events' && (
        <div className="events-section">
          <h3>🏛️ Diplomatic Events Calendar</h3>
          <div className="events-list">
            {diplomaticEvents.map((event, idx) => (
              <div key={idx} className="event-item">
                <div className="event-date">{new Date(event.date).toLocaleDateString()}</div>
                <div className="event-content">
                  <div className="event-name">{event.event}</div>
                  <div className="event-details">
                    <span className={`event-significance significance-${event.significance.toLowerCase()}`}>
                      {event.significance}
                    </span>
                    <span className="event-sentiment">
                      Sentiment: {Math.round(event.sentiment * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'trade' && (
        <div className="trade-section">
          <h3>📊 Trade Flow Analysis</h3>
          {trendData?.data && (
            <div className="trade-chart">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={trendData.data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#667eea" strokeWidth={2} name="Trade Volume" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="trade-metrics">
            <div className="trade-metric">
              <strong>Trade Volume Trend:</strong> {trendData?.metadata?.interpretation?.trend_up || 'Stable'}
            </div>
            <div className="trade-metric">
              <strong>Key Commodities:</strong> Extracted from OSINT data
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

