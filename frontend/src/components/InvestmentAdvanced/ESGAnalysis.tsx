import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

interface ESGAnalysisProps {
  data: {
    esg_score: number
    environmental_score: number
    social_score: number
    governance_score: number
    factors?: {
      environmental?: string[]
      social?: string[]
      governance?: string[]
    }
    recommendations?: string[]
  }
}

const COLORS = ['#28a745', '#ffc107', '#dc3545']

export default function ESGAnalysis({ data }: ESGAnalysisProps) {
  const chartData = [
    { name: 'Environmental', score: data.environmental_score },
    { name: 'Social', score: data.social_score },
    { name: 'Governance', score: data.governance_score },
  ]

  const pieData = [
    { name: 'Environmental', value: data.environmental_score },
    { name: 'Social', value: data.social_score },
    { name: 'Governance', value: data.governance_score },
  ]

  const getScoreColor = (score: number): string => {
    if (score >= 70) return '#28a745'
    if (score >= 50) return '#ffc107'
    return '#dc3545'
  }

  return (
    <div className="esg-analysis">
      <div className="esg-overview">
        <div className="esg-score-card">
          <div className="score-label">Score ESG Agregado</div>
          <div className="score-value" style={{ color: getScoreColor(data.esg_score) }}>
            {data.esg_score.toFixed(1)}
          </div>
          <div className="score-max">/ 100</div>
        </div>
        <div className="esg-breakdown">
          <div className="esg-item">
            <div className="esg-item-label">Environmental</div>
            <div className="esg-item-score" style={{ color: getScoreColor(data.environmental_score) }}>
              {data.environmental_score.toFixed(1)}
            </div>
          </div>
          <div className="esg-item">
            <div className="esg-item-label">Social</div>
            <div className="esg-item-score" style={{ color: getScoreColor(data.social_score) }}>
              {data.social_score.toFixed(1)}
            </div>
          </div>
          <div className="esg-item">
            <div className="esg-item-label">Governance</div>
            <div className="esg-item-score" style={{ color: getScoreColor(data.governance_score) }}>
              {data.governance_score.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      <div className="esg-charts">
        <div className="chart-container">
          <h4>Comparación de Scores ESG</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="score" fill="#007bff" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h4>Distribución ESG</h4>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {data.factors && (
        <div className="esg-factors">
          <h4>Factores Identificados</h4>
          <div className="factors-grid">
            {data.factors.environmental && data.factors.environmental.length > 0 && (
              <div className="factor-category">
                <h5>Environmental</h5>
                <ul>
                  {data.factors.environmental.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.factors.social && data.factors.social.length > 0 && (
              <div className="factor-category">
                <h5>Social</h5>
                <ul>
                  {data.factors.social.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.factors.governance && data.factors.governance.length > 0 && (
              <div className="factor-category">
                <h5>Governance</h5>
                <ul>
                  {data.factors.governance.map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {data.recommendations && data.recommendations.length > 0 && (
        <div className="esg-recommendations">
          <h4>Recomendaciones</h4>
          <ul>
            {data.recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}



