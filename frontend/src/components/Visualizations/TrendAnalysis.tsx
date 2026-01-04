import { useState, useMemo } from 'react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import KPIConfigurationModal from './KPIConfigurationModal'
import PostsViewer from '../Posts/PostsViewer'

interface TrendDataPoint {
  date: string
  value: number
  category?: string
}

interface TrendDataPoint {
  date: string
  value: number
  category?: string
  source?: string
  metric_type?: string
  description?: string
}

interface TrendAnalysisProps {
  data: TrendDataPoint[]
  title?: string
  type?: 'line' | 'area' | 'bar'
  showPrediction?: boolean
  predictionData?: TrendDataPoint[]
  metadata?: {
    case_name?: string
    case_type?: string
    data_sources?: string[]
    tools_used?: string[]
    metric_type?: string
    metric_description?: string
    value_meaning?: string
    interpretation?: {
      high_value?: string
      low_value?: string
      trend_up?: string
      trend_down?: string
    }
    total_data_points?: number
    date_range?: {
      start?: string
      end?: string
    }
    data_quality?: string
    collection_timeline?: {
      first_collection?: string
      last_collection?: string
    }
    results_by_tool?: Record<string, number>
  }
  dataSourcesBreakdown?: Array<{
    tool: string
    tool_type: string
    total_results: number
    has_data: boolean
    results_by_date: Record<string, number>
  }>
  queriesExecuted?: Array<{
    id: number
    tool: string
    tool_type: string
    params: Record<string, any>
    status: string
    created_at: string
    case_linked: boolean
  }>
  totalResultsBySource?: Record<string, number>
  metrics?: Array<{
    kpi_name: string
    value: number
    previous_value?: number
    change_percent?: number
    trend: string
    details?: Record<string, any>
    measurement_unit?: string
  }>
  insights?: string[]
  comments_by_social_network?: Record<string, { positive: number; negative: number; neutral: number }>
  concepts?: Array<{
    name: string
    category?: string
    relevance?: number
    confidence?: number
  }>
  caseId?: number
}

// Clickable count component that opens PostsViewer
function ClickableCount({ 
  caseId, 
  count, 
  label, 
  color, 
  filters 
}: { 
  caseId?: number
  count: number
  label: string
  color: string
  filters?: { sentiment?: string; category?: string; concept?: string; content_type?: string }
}) {
  const [showPosts, setShowPosts] = useState(false)

  if (!caseId || count === 0) {
    return <div style={{ color }}>{label}: {count}</div>
  }

  return (
    <>
      <div 
        style={{ 
          color, 
          cursor: 'pointer', 
          textDecoration: 'underline',
          display: 'inline-block'
        }}
        onClick={() => setShowPosts(true)}
        title="Clicar per veure els posts"
      >
        {label}: {count}
      </div>
      {showPosts && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 2000,
          background: 'white',
          padding: '2rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h2>Posts: {label} ({count})</h2>
            <button onClick={() => setShowPosts(false)} style={{ padding: '0.5rem 1rem', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              ✕ Tancar
            </button>
          </div>
          <PostsViewer caseId={caseId} initialFilters={filters} />
        </div>
      )}
    </>
  )
}

export default function TrendAnalysis({ 
  data, 
  title = "Trend Analysis", 
  type = 'line',
  showPrediction = false,
  predictionData = [],
  metadata,
  dataSourcesBreakdown = [],
  queriesExecuted = [],
  totalResultsBySource = {},
  metrics = [],
  insights = [],
  comments_by_social_network = {},
  concepts = [],
  caseId
}: TrendAnalysisProps) {
  const [showKpiConfig, setShowKpiConfig] = useState(false)
  const chartData = useMemo(() => {
    const processed = data.map(d => ({
      date: d.date,
      value: d.value,
      category: d.category || 'main'
    }))
    
    if (showPrediction && predictionData.length > 0) {
      return [...processed, ...predictionData.map(d => ({
        date: d.date,
        value: d.value,
        category: 'prediction'
      }))]
    }
    
    return processed
  }, [data, predictionData, showPrediction])

  const stats = useMemo(() => {
    if (data.length === 0) return { avg: 0, max: 0, min: 0, trend: 'stable' }
    
    const values = data.map(d => d.value)
    const avg = values.reduce((a, b) => a + b, 0) / values.length
    const max = Math.max(...values)
    const min = Math.min(...values)
    
    // Calculate trend
    const firstHalf = values.slice(0, Math.floor(values.length / 2))
    const secondHalf = values.slice(Math.floor(values.length / 2))
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length
    const trend = secondAvg > firstAvg * 1.1 ? 'up' : secondAvg < firstAvg * 0.9 ? 'down' : 'stable'
    
    return { avg, max, min, trend }
  }, [data])

  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    }

    switch (type) {
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis 
              label={{ 
                value: metadata?.value_meaning || 'Valor', 
                angle: -90, 
                position: 'insideLeft',
                style: { textAnchor: 'middle' }
              }}
            />
            <Tooltip 
              formatter={(value: any, name: any, props: any) => {
                const dataPoint = props.payload
                const description = dataPoint?.description || dataPoint?.metric_type || ''
                return [
                  `${metadata?.value_meaning || 'Valor'}: ${value}`,
                  description ? `\n${description}` : ''
                ]
              }}
              labelFormatter={(label) => `📅 Data: ${label}`}
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
                padding: '10px'
              }}
            />
            <Legend 
              formatter={(value) => value === 'value' ? 'Dades Reals' : 'Prediccions'}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              name="Dades Reals"
              stroke="#8884d8" 
              fill="#8884d8" 
              fillOpacity={0.6}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            {showPrediction && (
              <Area 
                type="monotone" 
                dataKey="value" 
                name="Prediccions"
                stroke="#82ca9d" 
                fill="#82ca9d" 
                fillOpacity={0.3} 
                strokeDasharray="5 5"
                dot={{ r: 3 }}
              />
            )}
          </AreaChart>
        )
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis 
              label={{ 
                value: metadata?.value_meaning || 'Valor', 
                angle: -90, 
                position: 'insideLeft',
                style: { textAnchor: 'middle' }
              }}
            />
            <Tooltip 
              formatter={(value: any, name: any, props: any) => {
                const dataPoint = props.payload
                const description = dataPoint?.description || dataPoint?.metric_type || ''
                return [
                  `${metadata?.value_meaning || 'Valor'}: ${value}`,
                  description ? `\n${description}` : ''
                ]
              }}
              labelFormatter={(label) => `📅 Data: ${label}`}
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
                padding: '10px'
              }}
            />
            <Legend formatter={() => 'Dades Reals'} />
            <Bar 
              dataKey="value" 
              name="Dades Reals"
              fill="#8884d8"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        )
      default:
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip 
              formatter={(value: any) => [`Valor: ${value}`, '']}
              labelFormatter={(label) => `Data: ${label}`}
            />
            <Legend 
              formatter={(value) => value === 'value' ? 'Dades Reals' : 'Prediccions'}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              name="Dades Reals"
              stroke="#8884d8" 
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            {showPrediction && (
              <Line 
                type="monotone" 
                dataKey="value" 
                name="Prediccions"
                stroke="#82ca9d" 
                strokeWidth={2} 
                strokeDasharray="5 5"
                dot={{ r: 3 }}
              />
            )}
          </LineChart>
        )
    }
  }

  return (
    <div className="trend-analysis-container">
      <div className="trend-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>{title}</h3>
          {caseId && (
            <button 
              onClick={() => setShowKpiConfig(true)}
              style={{ 
                padding: '0.5rem 1rem', 
                background: '#007bff', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: 'pointer' 
              }}
            >
              ⚙️ Configurar KPIs
            </button>
          )}
        </div>
        <div className="trend-description">
          {metadata ? (
            <>
              <div className="metadata-section">
                <p>
                  <strong>📊 Què s'està analitzant:</strong> {metadata.metric_description || 
                    "Aquest gràfic mostra l'evolució temporal de les dades recopilades per aquest cas."}
                </p>
                <div className="metadata-details">
                  <div className="metadata-item">
                    <strong>Eines OSINT utilitzades:</strong> {metadata.tools_used?.join(", ") || metadata.data_sources?.join(", ") || "Cap eina"}
                  </div>
                  <div className="metadata-item">
                    <strong>Font de dades:</strong> {metadata.data_sources?.join(", ") || "Dades OSINT"}
                  </div>
                  <div className="metadata-item">
                    <strong>Tipus de mètrica:</strong> {metadata.metric_type || "Volum de dades"}
                  </div>
                  {metadata.data_quality && (
                    <div className="metadata-item">
                      <strong>Qualitat de dades:</strong> 
                      <span className={`data-quality ${metadata.data_quality}`}>
                        {metadata.data_quality === 'good' ? '✅ Bona' : 
                         metadata.data_quality === 'medium' ? '⚠️ Mitjana' : 
                         metadata.data_quality === 'low' ? '⚠️ Baixa' : 
                         metadata.data_quality === 'empty' ? '❌ Sense dades' : metadata.data_quality}
                      </span>
                    </div>
                  )}
                  <div className="metadata-item">
                    <strong>Què significa el valor:</strong> {metadata.value_meaning || 
                      "Nombre de resultats o intensitat de la tendència"}
                  </div>
                  {metadata.total_data_points !== undefined && (
                    <div className="metadata-item">
                      <strong>Total de punts de dades:</strong> {metadata.total_data_points}
                    </div>
                  )}
                </div>
              </div>
              {metadata.interpretation && (
                <div className="interpretation-section">
                  <strong>💡 Com interpretar el gràfic:</strong>
                  <ul>
                    {metadata.interpretation.high_value && (
                      <li><strong>Valors alts:</strong> {metadata.interpretation.high_value}</li>
                    )}
                    {metadata.interpretation.low_value && (
                      <li><strong>Valors baixos:</strong> {metadata.interpretation.low_value}</li>
                    )}
                    {metadata.interpretation.trend_up && (
                      <li><strong>Tendència creixent (↑):</strong> {metadata.interpretation.trend_up}</li>
                    )}
                    {metadata.interpretation.trend_down && (
                      <li><strong>Tendència decreixent (↓):</strong> {metadata.interpretation.trend_down}</li>
                    )}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p>
              <strong>Què s'està analitzant:</strong> Aquest gràfic mostra l'evolució temporal de les dades recopilades 
              per aquest cas. La línia blava representa les dades històriques i reals, mentre que la línia verda puntejada 
              mostra les prediccions futures generades per IA.
            </p>
          )}
          {showPrediction && predictionData.length > 0 && (
            <p className="prediction-note">
              <strong>🔮 Prediccions:</strong> Les prediccions es basen en patrons identificats en les dades històriques 
              i anàlisis de tendències amb intel·ligència artificial.
            </p>
          )}
        </div>
      </div>
      
      <div className="trend-stats">
        <div className="stat-item">
          <span className="stat-label">Mitjana</span>
          <span className="stat-value">{stats.avg.toFixed(2)}</span>
          <span className="stat-description">Valor mitjà del període analitzat</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Màxim</span>
          <span className="stat-value">{stats.max.toFixed(2)}</span>
          <span className="stat-description">Pic més alt registrat</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Mínim</span>
          <span className="stat-value">{stats.min.toFixed(2)}</span>
          <span className="stat-description">Valor més baix registrat</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Tendència</span>
          <span className={`stat-value trend-${stats.trend}`}>
            {stats.trend === 'up' ? '↑ Creixent' : stats.trend === 'down' ? '↓ Decreixent' : '→ Estable'}
          </span>
          <span className="stat-description">
            {stats.trend === 'up' 
              ? 'Les dades mostren una tendència creixent' 
              : stats.trend === 'down' 
              ? 'Les dades mostren una tendència decreixent'
              : 'Les dades es mantenen estables'}
          </span>
        </div>
      </div>
      
      {/* Desglose de fuentes de datos */}
      {(dataSourcesBreakdown.length > 0 || Object.keys(totalResultsBySource).length > 0) && (
        <div className="data-sources-breakdown">
          <h4>🔍 Eines OSINT Utilitzades</h4>
          <div className="sources-grid">
            {dataSourcesBreakdown.map((source, idx) => (
              <div key={idx} className={`source-card ${source.has_data ? 'has-data' : 'no-data'}`}>
                <div className="source-header">
                  <strong>{source.tool}</strong>
                  <span className={`source-status ${source.has_data ? 'active' : 'inactive'}`}>
                    {source.has_data ? '✅' : '⚠️'}
                  </span>
                </div>
                <div className="source-stats">
                  <div className="stat">
                    <span className="stat-label">Resultats totals:</span>
                    <span className="stat-value">{source.total_results}</span>
                  </div>
                </div>
              </div>
            ))}
            {dataSourcesBreakdown.length === 0 && Object.keys(totalResultsBySource).length > 0 && (
              Object.entries(totalResultsBySource).map(([tool, count]) => (
                <div key={tool} className={`source-card ${count > 0 ? 'has-data' : 'no-data'}`}>
                  <div className="source-header">
                    <strong>{tool}</strong>
                    <span className={`source-status ${count > 0 ? 'active' : 'inactive'}`}>
                      {count > 0 ? '✅' : '⚠️'}
                    </span>
                  </div>
                  <div className="source-stats">
                    <div className="stat">
                      <span className="stat-label">Resultats totals:</span>
                      <span className="stat-value">{count}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {queriesExecuted.length > 0 && (
            <div className="queries-executed-section">
              <h5>📋 Consultes Executades ({queriesExecuted.length})</h5>
              <div className="queries-list">
                {queriesExecuted.slice(0, 5).map((query) => (
                  <div key={query.id} className="query-item">
                    <div className="query-header">
                      <span className="query-tool">{query.tool}</span>
                      <span className={`query-status ${query.status === 'completed' ? 'success' : query.status === 'failed' ? 'failed' : 'pending'}`}>
                        {query.status}
                      </span>
                    </div>
                    <div className="query-details">
                      <div className="query-param">
                        <strong>Paràmetres:</strong> {Object.entries(query.params || {}).map(([k, v]) => `${k}: ${v}`).join(', ') || 'Cap'}
                      </div>
                      <div className="query-date">
                        {query.created_at ? new Date(query.created_at).toLocaleString('ca-ES') : 'Data desconeguda'}
                      </div>
                      {query.case_linked && (
                        <span className="case-linked-badge">Vinculat al cas</span>
                      )}
                    </div>
                  </div>
                ))}
                {queriesExecuted.length > 5 && (
                  <div className="queries-more">
                    <em>... i {queriesExecuted.length - 5} consultes més</em>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Concrete Metrics Section */}
      {metrics && metrics.length > 0 && (
        <div className="concrete-metrics-section" style={{ margin: '2rem 0', padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <h4 style={{ marginTop: 0 }}>📊 Mètriques Concretes</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {metrics.map((metric, idx) => (
              <div key={idx} style={{ padding: '1rem', background: 'white', borderRadius: '6px', border: '1px solid #e0e0e0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <strong>{metric.kpi_name}</strong>
                  <span style={{ 
                    fontSize: '1.2rem', 
                    fontWeight: 'bold',
                    color: metric.trend === 'increasing' ? '#dc3545' : metric.trend === 'decreasing' ? '#28a745' : '#6c757d'
                  }}>
                    {metric.value.toFixed(1)}
                    {metric.measurement_unit && ` ${metric.measurement_unit}`}
                  </span>
                </div>
                {metric.previous_value !== undefined && metric.change_percent !== undefined && (
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>
                    Anterior: {metric.previous_value.toFixed(1)}
                    {metric.change_percent !== 0 && (
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: metric.change_percent > 0 ? '#dc3545' : '#28a745'
                      }}>
                        ({metric.change_percent > 0 ? '↑' : '↓'} {Math.abs(metric.change_percent).toFixed(1)}%)
                      </span>
                    )}
                  </div>
                )}
                {metric.details && (
                  <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '0.5rem' }}>
                    {metric.details.social_network && `Xarxa: ${metric.details.social_network}`}
                    {metric.details.date_range && ` | Període: ${metric.details.date_range}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* AI Insights Section */}
      {insights && insights.length > 0 && (
        <div className="insights-section" style={{ margin: '2rem 0', padding: '1.5rem', background: '#e7f3ff', borderRadius: '8px', border: '1px solid #b3d9ff' }}>
          <h4 style={{ marginTop: 0 }}>💡 Insights Generats per IA</h4>
          <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
            {insights.map((insight, idx) => (
              <li key={idx} style={{ marginBottom: '0.5rem' }}>{insight}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Social Network Breakdown */}
      {comments_by_social_network && Object.keys(comments_by_social_network).length > 0 && (
        <div className="social-network-breakdown" style={{ margin: '2rem 0', padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <h4 style={{ marginTop: 0 }}>💬 Comentaris per Xarxa Social</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
            {Object.entries(comments_by_social_network).map(([network, counts]) => (
              <div key={network} style={{ padding: '1rem', background: 'white', borderRadius: '6px', border: '1px solid #e0e0e0' }}>
                <strong>{network}</strong>
                <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  <ClickableCount
                    caseId={caseId}
                    count={counts.positive}
                    label="✅ Positius"
                    color="#28a745"
                    filters={{ sentiment: 'positive', content_type: network.toLowerCase().includes('instagram') ? 'instagram_post' : network.toLowerCase().includes('tiktok') ? 'tiktok_video' : undefined }}
                  />
                  <ClickableCount
                    caseId={caseId}
                    count={counts.negative}
                    label="❌ Negatius"
                    color="#dc3545"
                    filters={{ sentiment: 'negative', content_type: network.toLowerCase().includes('instagram') ? 'instagram_post' : network.toLowerCase().includes('tiktok') ? 'tiktok_video' : undefined }}
                  />
                  <ClickableCount
                    caseId={caseId}
                    count={counts.neutral}
                    label="⚪ Neutrals"
                    color="#6c757d"
                    filters={{ sentiment: 'neutral', content_type: network.toLowerCase().includes('instagram') ? 'instagram_post' : network.toLowerCase().includes('tiktok') ? 'tiktok_video' : undefined }}
                  />
                  <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>
                    Total: {counts.positive + counts.negative + counts.neutral}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="chart-container">
        <div className="chart-legend">
          <div className="legend-item">
            <span className="legend-color" style={{backgroundColor: '#8884d8'}}></span>
            <span>Dades Reals (Històriques)</span>
          </div>
          {showPrediction && predictionData.length > 0 && (
            <div className="legend-item">
              <span className="legend-color" style={{backgroundColor: '#82ca9d'}}></span>
              <span>Prediccions IA (Futures)</span>
            </div>
          )}
        </div>
        <ResponsiveContainer width="100%" height={350}>
          {renderChart()}
        </ResponsiveContainer>
        <div className="chart-footer">
          <p className="data-source">
            <strong>Font de dades:</strong> Dades recopilades mitjançant eines OSINT i processades amb intel·ligència artificial.
            Les prediccions es generen utilitzant models de machine learning i anàlisi de patrons.
          </p>
        </div>
      </div>
      
      {caseId && (
        <KPIConfigurationModal
          caseId={caseId}
          isOpen={showKpiConfig}
          onClose={() => setShowKpiConfig(false)}
          onSave={(kpiIds) => {
            console.log('KPIs configured:', kpiIds)
            setShowKpiConfig(false)
          }}
        />
      )}
    </div>
  )
}

