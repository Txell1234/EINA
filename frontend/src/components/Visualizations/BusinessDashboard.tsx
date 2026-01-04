import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { visualizationsService } from '../../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import './BusinessDashboard.css'

interface BusinessDashboardProps {
  caseId: number
}

interface Partnership {
  name: string
  type: string
  value?: string
  date: string
  status: string
}

interface MarketShare {
  company: string
  share: number
  trend: string
}

export default function BusinessDashboard({ caseId }: BusinessDashboardProps) {
  const [activeView, setActiveView] = useState<'overview' | 'partnerships' | 'market' | 'revenue' | 'competitive'>('overview')

  const { data: trendData } = useQuery({
    queryKey: ['trendAnalysis', caseId],
    queryFn: () => visualizationsService.trendAnalysis(caseId),
    enabled: !!caseId
  })

  // Mock data (would come from expert analysis)
  const partnerships: Partnership[] = [
    { name: 'Strategic Alliance with Company X', type: 'Strategic Alliance', value: '$50M', date: '2024-11-15', status: 'Active' },
    { name: 'Joint Venture Partnership', type: 'Joint Venture', value: '$100M', date: '2024-10-01', status: 'Active' }
  ]

  const marketShare: MarketShare[] = [
    { company: 'Company A', share: 35, trend: 'up' },
    { company: 'Company B', share: 25, trend: 'stable' },
    { company: 'Company C', share: 20, trend: 'down' },
    { company: 'Others', share: 20, trend: 'stable' }
  ]

  const revenueData = trendData?.data?.map((d: any) => ({
    date: d.date,
    revenue: d.value * 1000, // Mock conversion
    profit: d.value * 200
  })) || []

  const partnershipTypes = partnerships.reduce((acc, p) => {
    acc[p.type] = (acc[p.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const partnershipPieData = Object.entries(partnershipTypes).map(([name, value]) => ({
    name,
    value
  }))

  const COLORS = ['#667eea', '#48bb78', '#ffc107', '#dc3545', '#17a2b8']

  return (
    <div className="business-dashboard">
      <div className="dashboard-header">
        <h2>💼 Business Intelligence Dashboard</h2>
        <div className="view-selector">
          <button 
            className={activeView === 'overview' ? 'active' : ''}
            onClick={() => setActiveView('overview')}
          >
            Overview
          </button>
          <button 
            className={activeView === 'partnerships' ? 'active' : ''}
            onClick={() => setActiveView('partnerships')}
          >
            Partnerships
          </button>
          <button 
            className={activeView === 'market' ? 'active' : ''}
            onClick={() => setActiveView('market')}
          >
            Market Share
          </button>
          <button 
            className={activeView === 'revenue' ? 'active' : ''}
            onClick={() => setActiveView('revenue')}
          >
            Revenue Trends
          </button>
          <button 
            className={activeView === 'competitive' ? 'active' : ''}
            onClick={() => setActiveView('competitive')}
          >
            Competitive
          </button>
        </div>
      </div>

      {activeView === 'overview' && (
        <div className="overview-section">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Active Partnerships</div>
              <div className="metric-value">{partnerships.length}</div>
              <div className="metric-change">Strategic alliances</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Market Share</div>
              <div className="metric-value">35%</div>
              <div className="metric-change">Leading position</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Revenue Growth</div>
              <div className="metric-value positive">+12.5%</div>
              <div className="metric-change">Year over year</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Customer Satisfaction</div>
              <div className="metric-value">4.2/5</div>
              <div className="metric-change">Average rating</div>
            </div>
          </div>

          {/* Partnership Network Visualization */}
          <div className="partnership-network-section">
            <h3>🤝 Partnership Network</h3>
            <div className="partnership-network">
              {partnerships.map((partnership, idx) => (
                <div key={idx} className="partnership-node">
                  <div className="partnership-type">{partnership.type}</div>
                  <div className="partnership-name">{partnership.name}</div>
                  {partnership.value && (
                    <div className="partnership-value">{partnership.value}</div>
                  )}
                  <div className="partnership-status status-active">{partnership.status}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Partnership Types Distribution */}
          <div className="partnership-types-section">
            <h3>📊 Partnership Types Distribution</h3>
            <div className="partnership-pie-chart">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={partnershipPieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {partnershipPieData.map((entry, index) => (
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

      {activeView === 'partnerships' && (
        <div className="partnerships-section">
          <h3>🤝 Partnerships & Alliances</h3>
          <div className="partnerships-list">
            {partnerships.map((partnership, idx) => (
              <div key={idx} className="partnership-card">
                <div className="partnership-header">
                  <div>
                    <h4>{partnership.name}</h4>
                    <div className="partnership-type-badge">{partnership.type}</div>
                  </div>
                  <span className="partnership-status status-active">{partnership.status}</span>
                </div>
                <div className="partnership-details">
                  {partnership.value && (
                    <div className="partnership-detail">
                      <strong>Value:</strong> {partnership.value}
                    </div>
                  )}
                  <div className="partnership-detail">
                    <strong>Date:</strong> {new Date(partnership.date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'market' && (
        <div className="market-section">
          <h3>📊 Market Share Analysis</h3>
          <div className="market-share-chart">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={marketShare}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="company" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Bar dataKey="share" fill="#667eea" name="Market Share (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="market-share-list">
            {marketShare.map((item, idx) => (
              <div key={idx} className="market-share-item">
                <div className="market-share-company">{item.company}</div>
                <div className="market-share-bar">
                  <div 
                    className="market-share-fill" 
                    style={{ width: `${item.share}%` }}
                  ></div>
                </div>
                <div className="market-share-value">{item.share}%</div>
                <div className={`market-share-trend trend-${item.trend}`}>
                  {item.trend === 'up' && '↑'}
                  {item.trend === 'down' && '↓'}
                  {item.trend === 'stable' && '→'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === 'revenue' && (
        <div className="revenue-section">
          <h3>💰 Revenue & Profit Trends</h3>
          {revenueData.length > 0 && (
            <div className="revenue-chart">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => `$${value.toLocaleString()}`} />
                  <Legend />
                  <Line type="monotone" dataKey="revenue" stroke="#667eea" strokeWidth={2} name="Revenue" />
                  <Line type="monotone" dataKey="profit" stroke="#48bb78" strokeWidth={2} name="Profit" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="revenue-metrics">
            <div className="revenue-metric-card">
              <h4>Total Revenue</h4>
              <div className="revenue-value">$2.5M</div>
              <div className="revenue-period">Last 30 days</div>
            </div>
            <div className="revenue-metric-card">
              <h4>Profit Margin</h4>
              <div className="revenue-value">20%</div>
              <div className="revenue-period">Average</div>
            </div>
            <div className="revenue-metric-card">
              <h4>Growth Rate</h4>
              <div className="revenue-value positive">+12.5%</div>
              <div className="revenue-period">YoY</div>
            </div>
          </div>
        </div>
      )}

      {activeView === 'competitive' && (
        <div className="competitive-section">
          <h3>🏆 Competitive Landscape</h3>
          <div className="competitive-positioning">
            <div className="position-card leader">
              <div className="position-rank">#1</div>
              <div className="position-company">Our Company</div>
              <div className="position-share">35% Market Share</div>
              <div className="position-status">Market Leader</div>
            </div>
            <div className="competitors-list">
              {marketShare.filter(m => m.company !== 'Our Company').map((competitor, idx) => (
                <div key={idx} className="competitor-card">
                  <div className="competitor-rank">#{idx + 2}</div>
                  <div className="competitor-name">{competitor.company}</div>
                  <div className="competitor-share">{competitor.share}%</div>
                  <div className={`competitor-trend trend-${competitor.trend}`}>
                    {competitor.trend === 'up' && '↑ Growing'}
                    {competitor.trend === 'down' && '↓ Declining'}
                    {competitor.trend === 'stable' && '→ Stable'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}



