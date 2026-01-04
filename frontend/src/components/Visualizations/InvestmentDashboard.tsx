import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { visualizationsService } from '../../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, ZAxis, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import './InvestmentDashboard.css'

interface InvestmentDashboardProps {
  caseId: number
}

interface Opportunity {
  title: string
  roi_projection: string
  confidence: number
  time_horizon: string
  risk_level: string
}

interface RiskAssessment {
  geopolitical_risk: { score: number; factors: string[] }
  market_risk: { score: number; factors: string[] }
  operational_risk: { score: number; factors: string[] }
  overall_risk: string
}

export default function InvestmentDashboard({ caseId }: InvestmentDashboardProps) {
  const [activeView, setActiveView] = useState<'overview' | 'opportunities' | 'risks' | 'market' | 'performance'>('overview')

  const { data: trendData } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: !!caseId
  })

  // Mock data (would come from expert analysis endpoint)
  const opportunities: Opportunity[] = [
    { title: 'Technology Sector Investment', roi_projection: '15-20%', confidence: 85, time_horizon: '12 months', risk_level: 'medium' },
    { title: 'Infrastructure Development', roi_projection: '10-15%', confidence: 75, time_horizon: '24 months', risk_level: 'low' }
  ]

  const riskAssessment: RiskAssessment = {
    geopolitical_risk: { score: 35, factors: ['Regional stability', 'Trade relations'] },
    market_risk: { score: 45, factors: ['Market volatility', 'Currency fluctuations'] },
    operational_risk: { score: 30, factors: ['Regulatory changes', 'Operational efficiency'] },
    overall_risk: 'medium'
  }

  const marketTrends = trendData?.data?.map((d: any) => ({
    date: d.date,
    value: d.value,
    prediction: d.category === 'prediction' ? d.value : null
  })) || []

  const riskRadarData = [
    { category: 'Geopolitical', value: riskAssessment.geopolitical_risk.score, fullMark: 100 },
    { category: 'Market', value: riskAssessment.market_risk.score, fullMark: 100 },
    { category: 'Operational', value: riskAssessment.operational_risk.score, fullMark: 100 }
  ]

  const opportunityScatterData = opportunities.map((opp, idx) => ({
    name: opp.title,
    risk: opp.risk_level === 'low' ? 25 : opp.risk_level === 'medium' ? 50 : 75,
    return: parseInt(opp.roi_projection.split('-')[0]),
    confidence: opp.confidence,
    size: opp.confidence
  }))

  return (
    <div className="investment-dashboard">
      <div className="dashboard-header">
        <h2>💰 Investment Intelligence Dashboard</h2>
        <div className="view-selector">
          <button 
            className={activeView === 'overview' ? 'active' : ''}
            onClick={() => setActiveView('overview')}
          >
            Overview
          </button>
          <button 
            className={activeView === 'opportunities' ? 'active' : ''}
            onClick={() => setActiveView('opportunities')}
          >
            Opportunities
          </button>
          <button 
            className={activeView === 'risks' ? 'active' : ''}
            onClick={() => setActiveView('risks')}
          >
            Risk Analysis
          </button>
          <button 
            className={activeView === 'market' ? 'active' : ''}
            onClick={() => setActiveView('market')}
          >
            Market Trends
          </button>
          <button 
            className={activeView === 'performance' ? 'active' : ''}
            onClick={() => setActiveView('performance')}
          >
            Performance
          </button>
        </div>
      </div>

      {activeView === 'overview' && (
        <div className="overview-section">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Investment Opportunities</div>
              <div className="metric-value">{opportunities.length}</div>
              <div className="metric-change">Identified</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Overall Risk</div>
              <div className="metric-value risk-medium">{riskAssessment.overall_risk.toUpperCase()}</div>
              <div className="metric-change">Risk Level</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Avg ROI Projection</div>
              <div className="metric-value">12-18%</div>
              <div className="metric-change">Expected return</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Confidence Level</div>
              <div className="metric-value">
                {Math.round(opportunities.reduce((sum, o) => sum + o.confidence, 0) / opportunities.length)}%
              </div>
              <div className="metric-change">Average confidence</div>
            </div>
          </div>

          {/* Risk-Return Matrix */}
          <div className="risk-return-section">
            <h3>📊 Risk-Return Matrix</h3>
            <div className="risk-return-chart">
              <ResponsiveContainer width="100%" height={400}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    type="number" 
                    dataKey="risk" 
                    name="Risk Level" 
                    domain={[0, 100]}
                    label={{ value: 'Risk Level', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="return" 
                    name="ROI %" 
                    label={{ value: 'Expected ROI (%)', angle: -90, position: 'insideLeft' }}
                  />
                  <ZAxis type="number" dataKey="confidence" range={[50, 400]} name="Confidence" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Legend />
                  <Scatter name="Opportunities" data={opportunityScatterData} fill="#667eea" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Risk Radar */}
          <div className="risk-radar-section">
            <h3>⚠️ Risk Assessment by Category</h3>
            <div className="risk-radar-chart">
              <ResponsiveContainer width="100%" height={400}>
                <RadarChart data={riskRadarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="category" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} />
                  <Radar name="Risk Score" dataKey="value" stroke="#dc3545" fill="#dc3545" fillOpacity={0.6} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeView === 'opportunities' && (
        <div className="opportunities-section">
          <h3>🎯 Investment Opportunities</h3>
          <div className="opportunities-list">
            {opportunities.map((opp, idx) => (
              <div key={idx} className="opportunity-card">
                <div className="opportunity-header">
                  <h4>{opp.title}</h4>
                  <span className={`risk-badge risk-${opp.risk_level}`}>{opp.risk_level.toUpperCase()}</span>
                </div>
                <div className="opportunity-metrics">
                  <div className="opportunity-metric">
                    <strong>ROI Projection:</strong> {opp.roi_projection}
                  </div>
                  <div className="opportunity-metric">
                    <strong>Confidence:</strong> {opp.confidence}%
                  </div>
                  <div className="opportunity-metric">
                    <strong>Time Horizon:</strong> {opp.time_horizon}
                  </div>
                </div>
                <div className="confidence-bar">
                  <div 
                    className="confidence-fill" 
                    style={{ width: `${opp.confidence}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'risks' && (
        <div className="risks-section">
          <h3>⚠️ Risk Analysis</h3>
          <div className="risks-grid">
            <div className="risk-card">
              <div className="risk-header">
                <h4>Geopolitical Risk</h4>
                <span className="risk-score">{riskAssessment.geopolitical_risk.score}/100</span>
              </div>
              <div className="risk-factors">
                <strong>Key Factors:</strong>
                <ul>
                  {riskAssessment.geopolitical_risk.factors.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="risk-card">
              <div className="risk-header">
                <h4>Market Risk</h4>
                <span className="risk-score">{riskAssessment.market_risk.score}/100</span>
              </div>
              <div className="risk-factors">
                <strong>Key Factors:</strong>
                <ul>
                  {riskAssessment.market_risk.factors.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="risk-card">
              <div className="risk-header">
                <h4>Operational Risk</h4>
                <span className="risk-score">{riskAssessment.operational_risk.score}/100</span>
              </div>
              <div className="risk-factors">
                <strong>Key Factors:</strong>
                <ul>
                  {riskAssessment.operational_risk.factors.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeView === 'market' && (
        <div className="market-section">
          <h3>📈 Market Trend Analysis</h3>
          {marketTrends.length > 0 && (
            <div className="market-chart">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={marketTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#667eea" strokeWidth={2} name="Market Value" />
                  {marketTrends.some((d: any) => d.prediction) && (
                    <Line type="monotone" dataKey="prediction" stroke="#82ca9d" strokeDasharray="5 5" name="Prediction" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="market-insights">
            <h4>Market Insights</h4>
            <ul>
              <li>Market volatility: Moderate</li>
              <li>Trend: {trendData?.metadata?.interpretation?.trend_up ? 'Upward' : 'Stable'}</li>
              <li>Key indicators: Positive sentiment, stable growth</li>
            </ul>
          </div>
        </div>
      )}

      {activeView === 'performance' && (
        <div className="performance-section">
          <h3>📊 Performance Analysis</h3>
          <div className="performance-metrics">
            <div className="performance-card">
              <h4>Portfolio Performance</h4>
              <div className="performance-value">+12.5%</div>
              <div className="performance-period">Last 12 months</div>
            </div>
            <div className="performance-card">
              <h4>Volatility</h4>
              <div className="performance-value">15.2%</div>
              <div className="performance-period">Annualized</div>
            </div>
            <div className="performance-card">
              <h4>Sharpe Ratio</h4>
              <div className="performance-value">1.8</div>
              <div className="performance-period">Risk-adjusted return</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}



