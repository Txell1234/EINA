import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface RegulatoryRiskAssessmentProps {
  data: {
    regulatory_risk?: {
      risk_level?: string
      factors?: string[]
      recommendations?: string[]
    }
    geopolitical_risk?: {
      overall?: number
      regulatory?: number
    }
    recommendation?: string
  }
  country: string
}

export default function RegulatoryRiskAssessment({ data, country }: RegulatoryRiskAssessmentProps) {
  const getRiskLevelColor = (level?: string): string => {
    if (!level) return '#6c757d'
    switch (level.toLowerCase()) {
      case 'high':
      case 'critical':
        return '#dc3545'
      case 'medium':
        return '#ffc107'
      case 'low':
        return '#28a745'
      default:
        return '#6c757d'
    }
  }

  const riskData = []
  if (data.regulatory_risk?.risk_level) {
    riskData.push({
      name: 'Regulatory Risk',
      level: data.regulatory_risk.risk_level,
      score: data.regulatory_risk.risk_level === 'high' ? 75 : data.regulatory_risk.risk_level === 'medium' ? 50 : 25
    })
  }
  if (data.geopolitical_risk) {
    riskData.push({
      name: 'Geopolitical Overall',
      level: data.geopolitical_risk.overall! > 60 ? 'high' : data.geopolitical_risk.overall! > 40 ? 'medium' : 'low',
      score: data.geopolitical_risk.overall || 50
    })
    riskData.push({
      name: 'Geopolitical Regulatory',
      level: data.geopolitical_risk.regulatory! > 60 ? 'high' : data.geopolitical_risk.regulatory! > 40 ? 'medium' : 'low',
      score: data.geopolitical_risk.regulatory || 50
    })
  }

  return (
    <div className="regulatory-risk-assessment">
      <div className="risk-header">
        <h4>Riesgo Regulatorio - {country}</h4>
        {data.regulatory_risk?.risk_level && (
          <div
            className="risk-level-badge"
            style={{ backgroundColor: getRiskLevelColor(data.regulatory_risk.risk_level) }}
          >
            {data.regulatory_risk.risk_level.toUpperCase()}
          </div>
        )}
      </div>

      {riskData.length > 0 && (
        <div className="risk-chart">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={riskData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="score" fill="#dc3545" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.regulatory_risk?.factors && data.regulatory_risk.factors.length > 0 && (
        <div className="risk-factors">
          <h5>Factores de Riesgo</h5>
          <ul>
            {data.regulatory_risk.factors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {data.recommendation && (
        <div className="risk-recommendation">
          <h5>Recomendación</h5>
          <p>{data.recommendation}</p>
        </div>
      )}

      {data.regulatory_risk?.recommendations && data.regulatory_risk.recommendations.length > 0 && (
        <div className="risk-recommendations">
          <h5>Recomendaciones Detalladas</h5>
          <ul>
            {data.regulatory_risk.recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}



