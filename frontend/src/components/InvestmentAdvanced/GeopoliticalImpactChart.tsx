import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface GeopoliticalImpactChartProps {
  data: {
    impacts: Array<{
      country: string
      impact_score: number
      impact_level: string
      factors: {
        political_stability: number
        conflict_risk: number
        economic_risk: number
        regulatory_risk: number
      }
      recommendation: string
    }>
    overall_assessment?: {
      average_impact: number
      overall_level: string
      countries_analyzed: number
    }
    investment_type: string
  }
}

export default function GeopoliticalImpactChart({ data }: GeopoliticalImpactChartProps) {
  const impactChartData = data.impacts.map(impact => ({
    country: impact.country,
    impact: impact.impact_score
  }))

  const factorsChartData = data.impacts.map(impact => ({
    country: impact.country,
    political_stability: impact.factors.political_stability,
    conflict_risk: impact.factors.conflict_risk,
    economic_risk: impact.factors.economic_risk,
    regulatory_risk: impact.factors.regulatory_risk
  }))

  const getImpactLevelColor = (level: string): string => {
    switch (level.toLowerCase()) {
      case 'high':
        return '#dc3545'
      case 'medium':
        return '#ffc107'
      case 'low':
        return '#28a745'
      default:
        return '#6c757d'
    }
  }

  return (
    <div className="geopolitical-impact-chart">
      {data.overall_assessment && (
        <div className="overall-assessment">
          <h4>Evaluación General</h4>
          <div className="assessment-metrics">
            <div className="metric">
              <div className="metric-label">Impacto Promedio</div>
              <div
                className="metric-value"
                style={{ color: getImpactLevelColor(data.overall_assessment.overall_level) }}
              >
                {data.overall_assessment.average_impact.toFixed(1)}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Nivel General</div>
              <div
                className="metric-value"
                style={{ color: getImpactLevelColor(data.overall_assessment.overall_level) }}
              >
                {data.overall_assessment.overall_level.toUpperCase()}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Países Analizados</div>
              <div className="metric-value">{data.overall_assessment.countries_analyzed}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Tipo de Inversión</div>
              <div className="metric-value">{data.investment_type}</div>
            </div>
          </div>
        </div>
      )}

      <div className="impact-chart">
        <h4>Impacto Geopolítico por País</h4>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={impactChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="country" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="impact" name="Impacto" fill="#dc3545" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="factors-chart">
        <h4>Factores de Impacto por País</h4>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={factorsChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="country" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="political_stability" name="Estabilidad Política" fill="#28a745" stackId="a" />
            <Bar dataKey="conflict_risk" name="Riesgo de Conflicto" fill="#dc3545" stackId="a" />
            <Bar dataKey="economic_risk" name="Riesgo Económico" fill="#ffc107" stackId="a" />
            <Bar dataKey="regulatory_risk" name="Riesgo Regulatorio" fill="#17a2b8" stackId="a" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="impact-details">
        <h4>Detalles por País</h4>
        <div className="impact-cards">
          {data.impacts.map((impact, idx) => (
            <div key={idx} className="impact-card">
              <div className="impact-card-header">
                <h5>{impact.country}</h5>
                <div
                  className="impact-level-badge"
                  style={{ backgroundColor: getImpactLevelColor(impact.impact_level) }}
                >
                  {impact.impact_level.toUpperCase()}
                </div>
              </div>
              <div className="impact-score">
                Score: {impact.impact_score.toFixed(1)}
              </div>
              <div className="impact-factors">
                <div className="factor">
                  <span>Estabilidad Política:</span>
                  <span>{impact.factors.political_stability.toFixed(1)}</span>
                </div>
                <div className="factor">
                  <span>Riesgo de Conflicto:</span>
                  <span>{impact.factors.conflict_risk.toFixed(1)}</span>
                </div>
                <div className="factor">
                  <span>Riesgo Económico:</span>
                  <span>{impact.factors.economic_risk.toFixed(1)}</span>
                </div>
                <div className="factor">
                  <span>Riesgo Regulatorio:</span>
                  <span>{impact.factors.regulatory_risk.toFixed(1)}</span>
                </div>
              </div>
              <div className="impact-recommendation">
                <strong>Recomendación:</strong> {impact.recommendation}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
