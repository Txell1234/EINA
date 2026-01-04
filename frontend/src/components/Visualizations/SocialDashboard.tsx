import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { visualizationsService } from '../../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import Heatmap from './Heatmap'
import './SocialDashboard.css'

interface SocialDashboardProps {
  caseId: number
}

interface ViralContent {
  platform: string
  engagement: number
  reach: number
  impact: string
  url?: string
}

interface Influencer {
  name: string
  platform: string
  reach: number
  sentiment: number
  engagement_rate: number
}

export default function SocialDashboard({ caseId }: SocialDashboardProps) {
  const [activeView, setActiveView] = useState<'overview' | 'sentiment' | 'viral' | 'influencers' | 'engagement' | 'heatmap'>('overview')

  const { data: trendData } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: !!caseId
  })

  // Extract sentiment by platform from trend data
  const commentsByNetwork = trendData?.comments_by_social_network || {}
  
  // Prepare sentiment evolution data
  const sentimentEvolutionData = Object.entries(commentsByNetwork).map(([platform, data]: [string, any]) => ({
    platform,
    positive: data.positive || 0,
    negative: data.negative || 0,
    neutral: data.neutral || 0,
    total: (data.positive || 0) + (data.negative || 0) + (data.neutral || 0)
  }))

  // Mock viral content (would come from expert analysis)
  const viralContent: ViralContent[] = [
    { platform: 'Instagram', engagement: 50000, reach: 200000, impact: 'High', url: '#' },
    { platform: 'TikTok', engagement: 35000, reach: 150000, impact: 'Medium', url: '#' }
  ]

  // Mock influencers (would come from expert analysis)
  const influencers: Influencer[] = [
    { name: '@influencer1', platform: 'Instagram', reach: 500000, sentiment: 0.8, engagement_rate: 5.2 },
    { name: '@influencer2', platform: 'TikTok', reach: 300000, sentiment: 0.7, engagement_rate: 4.8 }
  ]

  // Sentiment pie chart data
  const totalSentiment = sentimentEvolutionData.reduce((sum, d) => sum + d.total, 0)
  const sentimentPieData = [
    { name: 'Positive', value: sentimentEvolutionData.reduce((sum, d) => sum + d.positive, 0) },
    { name: 'Negative', value: sentimentEvolutionData.reduce((sum, d) => sum + d.negative, 0) },
    { name: 'Neutral', value: sentimentEvolutionData.reduce((sum, d) => sum + d.neutral, 0) }
  ]

  const COLORS = ['#28a745', '#dc3545', '#6c757d']

  return (
    <div className="social-dashboard">
      <div className="dashboard-header">
        <h2>💬 Social Public Affairs Dashboard</h2>
        <div className="view-selector">
          <button 
            className={activeView === 'overview' ? 'active' : ''}
            onClick={() => setActiveView('overview')}
          >
            Overview
          </button>
          <button 
            className={activeView === 'sentiment' ? 'active' : ''}
            onClick={() => setActiveView('sentiment')}
          >
            Sentiment Analysis
          </button>
          <button 
            className={activeView === 'viral' ? 'active' : ''}
            onClick={() => setActiveView('viral')}
          >
            Viral Content
          </button>
          <button 
            className={activeView === 'influencers' ? 'active' : ''}
            onClick={() => setActiveView('influencers')}
          >
            Influencers
          </button>
          <button 
            className={activeView === 'engagement' ? 'active' : ''}
            onClick={() => setActiveView('engagement')}
          >
            Engagement
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
              <div className="metric-label">Total Mentions</div>
              <div className="metric-value">{totalSentiment}</div>
              <div className="metric-change">Across all platforms</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Positive Sentiment</div>
              <div className="metric-value positive">
                {totalSentiment > 0 ? Math.round((sentimentPieData[0].value / totalSentiment) * 100) : 0}%
              </div>
              <div className="metric-change">Overall positive</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Viral Posts</div>
              <div className="metric-value">{viralContent.length}</div>
              <div className="metric-change">High engagement content</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Key Influencers</div>
              <div className="metric-value">{influencers.length}</div>
              <div className="metric-change">Tracked</div>
            </div>
          </div>

          {/* Sentiment by Platform */}
          <div className="sentiment-platform-section">
            <h3>📊 Sentiment by Platform</h3>
            <div className="sentiment-platform-chart">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={sentimentEvolutionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="platform" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="positive" stackId="a" fill="#28a745" name="Positive" />
                  <Bar dataKey="negative" stackId="a" fill="#dc3545" name="Negative" />
                  <Bar dataKey="neutral" stackId="a" fill="#6c757d" name="Neutral" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Overall Sentiment Distribution */}
          <div className="sentiment-distribution-section">
            <h3>📈 Overall Sentiment Distribution</h3>
            <div className="sentiment-pie-chart">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={sentimentPieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {sentimentPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeView === 'sentiment' && (
        <div className="sentiment-section">
          <h3>📊 Sentiment Evolution by Platform</h3>
          {trendData?.data && (
            <div className="sentiment-evolution-chart">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={trendData.data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#667eea" strokeWidth={2} name="Mentions" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          
          <div className="platform-sentiment-breakdown">
            <h4>Platform Breakdown</h4>
            <div className="platform-cards">
              {Object.entries(commentsByNetwork).map(([platform, data]: [string, any]) => (
                <div key={platform} className="platform-card">
                  <h5>{platform}</h5>
                  <div className="platform-metrics">
                    <div className="platform-metric positive">
                      ✅ Positive: {data.positive || 0}
                    </div>
                    <div className="platform-metric negative">
                      ❌ Negative: {data.negative || 0}
                    </div>
                    <div className="platform-metric neutral">
                      ⚪ Neutral: {data.neutral || 0}
                    </div>
                    <div className="platform-metric total">
                      📊 Total: {(data.positive || 0) + (data.negative || 0) + (data.neutral || 0)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeView === 'viral' && (
        <div className="viral-section">
          <h3>🔥 Viral Content Tracker</h3>
          <div className="viral-content-list">
            {viralContent.map((content, idx) => (
              <div key={idx} className="viral-content-card">
                <div className="viral-header">
                  <div className="viral-platform">{content.platform}</div>
                  <span className={`impact-badge impact-${content.impact.toLowerCase()}`}>
                    {content.impact} Impact
                  </span>
                </div>
                <div className="viral-metrics">
                  <div className="viral-metric">
                    <strong>Engagement:</strong> {content.engagement.toLocaleString()}
                  </div>
                  <div className="viral-metric">
                    <strong>Reach:</strong> {content.reach.toLocaleString()}
                  </div>
                  <div className="viral-metric">
                    <strong>Engagement Rate:</strong> {((content.engagement / content.reach) * 100).toFixed(2)}%
                  </div>
                </div>
                {content.url && (
                  <a href={content.url} target="_blank" rel="noopener noreferrer" className="viral-link">
                    View Content →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'influencers' && (
        <div className="influencers-section">
          <h3>👥 Influencer Network Analysis</h3>
          <div className="influencers-list">
            {influencers.map((influencer, idx) => (
              <div key={idx} className="influencer-card">
                <div className="influencer-header">
                  <div>
                    <h4>{influencer.name}</h4>
                    <div className="influencer-platform">{influencer.platform}</div>
                  </div>
                  <div className="influencer-sentiment">
                    <span className={`sentiment-badge ${influencer.sentiment > 0.6 ? 'positive' : influencer.sentiment > 0.4 ? 'neutral' : 'negative'}`}>
                      {Math.round(influencer.sentiment * 100)}% Positive
                    </span>
                  </div>
                </div>
                <div className="influencer-metrics">
                  <div className="influencer-metric">
                    <strong>Reach:</strong> {influencer.reach.toLocaleString()}
                  </div>
                  <div className="influencer-metric">
                    <strong>Engagement Rate:</strong> {influencer.engagement_rate}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'engagement' && (
        <div className="engagement-section">
          <h3>📈 Engagement Funnel Analysis</h3>
          <div className="engagement-funnel">
            <div className="funnel-stage">
              <div className="stage-label">Views</div>
              <div className="stage-value">1,000,000</div>
            </div>
            <div className="funnel-arrow">↓</div>
            <div className="funnel-stage">
              <div className="stage-label">Likes</div>
              <div className="stage-value">50,000</div>
              <div className="stage-conversion">5%</div>
            </div>
            <div className="funnel-arrow">↓</div>
            <div className="funnel-stage">
              <div className="stage-label">Comments</div>
              <div className="stage-value">5,000</div>
              <div className="stage-conversion">10%</div>
            </div>
            <div className="funnel-arrow">↓</div>
            <div className="funnel-stage">
              <div className="stage-label">Shares</div>
              <div className="stage-value">1,000</div>
              <div className="stage-conversion">20%</div>
            </div>
          </div>
          
          <div className="engagement-metrics">
            <div className="engagement-metric-card">
              <h4>Overall Engagement Rate</h4>
              <div className="engagement-value">5.6%</div>
            </div>
            <div className="engagement-metric-card">
              <h4>Viral Coefficient</h4>
              <div className="engagement-value">1.2</div>
            </div>
            <div className="engagement-metric-card">
              <h4>Community Growth</h4>
              <div className="engagement-value">+12%</div>
            </div>
          </div>
        </div>
      )}

      {activeView === 'heatmap' && (
        <div className="heatmap-section">
          <h3>🔥 Mapa de Calor de Posts per Ubicació</h3>
          <div className="heatmap-controls">
            <label>
              Mètrica:
              <select defaultValue="posts">
                <option value="posts">Posts</option>
                <option value="sentiment">Sentiment</option>
                <option value="engagement">Engagement</option>
              </select>
            </label>
            <label>
              Granularitat:
              <select defaultValue="municipality">
                <option value="municipality">Comuns (Andorra)</option>
                <option value="city">Ciutats</option>
                <option value="region">Regions</option>
                <option value="country">Països</option>
              </select>
            </label>
          </div>
          <Heatmap
            caseId={caseId}
            metricType="posts"
            granularity="municipality"
          />
        </div>
      )}
    </div>
  )
}

