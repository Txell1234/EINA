import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'

interface MarketOpportunityComparisonProps {
  data: {
    opportunities: Array<{
      country: string
      opportunity_score: number
      geopolitical_risk: number
      industry_analysis?: Record<string, {
        supply_chain_risk: number
        opportunity: number
      }>
    }>
    best_opportunity?: {
      country: string
      opportunity_score: number
    }
    comparison_date: string
  }
}

const COLORS = ['#28a745', '#ffc107', '#17a2b8', '#6c757d', '#dc3545']

export default function MarketOpportunityComparison({ data }: MarketOpportunityComparisonProps) {
  const chartData = data.opportunities.map(opp => ({
    country: opp.country,
    opportunity: opp.opportunity_score,
    risk: opp.geopolitical_risk
  }))

  const getScoreColor = (score: number): string => {
    if (score >= 70) return '#28a745'
    if (score >= 50) return '#ffc107'
    return '#dc3545'
  }

  return (
    <div className="market-opportunity-comparison">
      {data.best_opportunity && (
        <div className="best-opportunity-card">
          <h4>Mejor Oportunidad</h4>
          <div className="best-opportunity-content">
            <div className="country-name">{data.best_opportunity.country}</div>
            <div
              className="opportunity-score"
              style={{ color: getScoreColor(data.best_opportunity.opportunity_score) }}
            >
              {data.best_opportunity.opportunity_score.toFixed(1)}
            </div>
            <div className="score-label">Score de Oportunidad</div>
          </div>
        </div>
      )}

      <div className="comparison-chart">
        <h4>Comparación de Oportunidades por País</h4>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="country" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="opportunity" name="Oportunidad" fill="#28a745" />
            <Bar dataKey="risk" name="Riesgo Geopolítico" fill="#dc3545" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="opportunities-table">
        <h4>Detalles por País</h4>
        <table>
          <thead>
            <tr>
              <th>País</th>
              <th>Score de Oportunidad</th>
              <th>Riesgo Geopolítico</th>
              <th>Análisis por Industria</th>
            </tr>
          </thead>
          <tbody>
            {data.opportunities.map((opp, idx) => (
              <tr key={idx}>
                <td>{opp.country}</td>
                <td style={{ color: getScoreColor(opp.opportunity_score) }}>
                  {opp.opportunity_score.toFixed(1)}
                </td>
                <td style={{ color: opp.geopolitical_risk > 60 ? '#dc3545' : opp.geopolitical_risk > 40 ? '#ffc107' : '#28a745' }}>
                  {opp.geopolitical_risk.toFixed(1)}
                </td>
                <td>
                  {opp.industry_analysis ? (
                    <div className="industry-details">
                      {Object.entries(opp.industry_analysis).map(([industry, analysis]) => (
                        <div key={industry} className="industry-item">
                          <strong>{industry}:</strong> Oportunidad: {analysis.opportunity.toFixed(1)}, 
                          Riesgo Cadena Suministro: {analysis.supply_chain_risk.toFixed(1)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    'N/A'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="comparison-date">
        <small>Fecha de comparación: {new Date(data.comparison_date).toLocaleDateString()}</small>
      </div>
    </div>
  )
}



