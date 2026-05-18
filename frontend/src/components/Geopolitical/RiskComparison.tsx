import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { geopoliticalService } from '../../services/api'
import './RiskComparison.css'

interface RiskComparisonProps {
  countries: string[]
  caseId?: number
}

interface RiskData {
  country: string
  overall_risk: number
  political: number
  conflict: number
  economic: number
  security: number
  trend_7d: number
  trend_30d: number
}

export default function RiskComparison({ countries, caseId }: RiskComparisonProps) {
  const [selectedCountries, setSelectedCountries] = useState<string[]>(countries)

  const { data: comparisonData, isLoading } = useQuery({
    queryKey: ['risk-comparison', selectedCountries.join(','), caseId],
    queryFn: () => geopoliticalService.compareRisks(selectedCountries),
    enabled: selectedCountries.length > 0
  })

  if (isLoading) {
    return <div className="risk-comparison-loading">Carregant comparació de riscos...</div>
  }

  if (!comparisonData || comparisonData.error) {
    return (
      <div className="risk-comparison-error">
        <p>Error carregant comparació de riscos</p>
      </div>
    )
  }

  const risks: RiskData[] = comparisonData.risks || []

  if (risks.length === 0) {
    return (
      <div className="risk-comparison-empty">
        No hi ha dades de risc disponibles per als països seleccionats
      </div>
    )
  }

  const getRiskColor = (score: number): string => {
    if (score >= 70) return '#dc3545' // High risk
    if (score >= 50) return '#fd7e14' // Medium-high
    if (score >= 30) return '#ffc107' // Medium
    return '#28a745' // Low risk
  }

  const getRiskLabel = (score: number): string => {
    if (score >= 70) return 'Alt'
    if (score >= 50) return 'Mitjà-Alt'
    if (score >= 30) return 'Mitjà'
    return 'Baix'
  }

  const getTrendColor = (trend: number): string => {
    if (trend > 5) return '#dc3545' // Increasing
    if (trend < -5) return '#28a745' // Decreasing
    return '#6c757d' // Stable
  }

  const getTrendIcon = (trend: number): string => {
    if (trend > 5) return '↗️'
    if (trend < -5) return '↘️'
    return '→'
  }

  return (
    <div className="risk-comparison">
      <div className="comparison-header">
        <h3>Comparació de Riscos Geopolítics</h3>
        <div className="comparison-meta">
          <span>{risks.length} països comparats</span>
          {comparisonData.highest_risk && (
            <span className="highest-risk-badge">
              Risc més alt: {comparisonData.highest_risk.country} ({comparisonData.highest_risk.overall_risk.toFixed(1)})
            </span>
          )}
        </div>
      </div>

      <div className="comparison-table-container">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>País</th>
              <th>Risc General</th>
              <th>Estabilitat Política</th>
              <th>Risc de Conflicte</th>
              <th>Risc Econòmic</th>
              <th>Risc de Seguretat</th>
              <th>Tendència 7d</th>
              <th>Tendència 30d</th>
            </tr>
          </thead>
          <tbody>
            {risks.map((risk, index) => (
              <tr key={risk.country} className={index % 2 === 0 ? 'even-row' : 'odd-row'}>
                <td className="country-cell">
                  <strong>{risk.country}</strong>
                </td>
                <td className="risk-cell overall">
                  <div className="risk-bar-container">
                    <div
                      className="risk-bar"
                      style={{
                        width: `${risk.overall_risk}%`,
                        backgroundColor: getRiskColor(risk.overall_risk)
                      }}
                    >
                      <span className="risk-value">{risk.overall_risk.toFixed(1)}</span>
                    </div>
                  </div>
                  <span className="risk-label">{getRiskLabel(risk.overall_risk)}</span>
                </td>
                <td className="risk-cell">
                  <div className="risk-indicator">
                    <div
                      className="risk-dot"
                      style={{ backgroundColor: getRiskColor(risk.political) }}
                    />
                    <span>{risk.political.toFixed(0)}</span>
                  </div>
                </td>
                <td className="risk-cell">
                  <div className="risk-indicator">
                    <div
                      className="risk-dot"
                      style={{ backgroundColor: getRiskColor(risk.conflict) }}
                    />
                    <span>{risk.conflict.toFixed(0)}</span>
                  </div>
                </td>
                <td className="risk-cell">
                  <div className="risk-indicator">
                    <div
                      className="risk-dot"
                      style={{ backgroundColor: getRiskColor(risk.economic) }}
                    />
                    <span>{risk.economic.toFixed(0)}</span>
                  </div>
                </td>
                <td className="risk-cell">
                  <div className="risk-indicator">
                    <div
                      className="risk-dot"
                      style={{ backgroundColor: getRiskColor(risk.security) }}
                    />
                    <span>{risk.security.toFixed(0)}</span>
                  </div>
                </td>
                <td className="trend-cell">
                  <span
                    className="trend-value"
                    style={{ color: getTrendColor(risk.trend_7d) }}
                  >
                    {getTrendIcon(risk.trend_7d)} {risk.trend_7d > 0 ? '+' : ''}{risk.trend_7d.toFixed(1)}
                  </span>
                </td>
                <td className="trend-cell">
                  <span
                    className="trend-value"
                    style={{ color: getTrendColor(risk.trend_30d) }}
                  >
                    {getTrendIcon(risk.trend_30d)} {risk.trend_30d > 0 ? '+' : ''}{risk.trend_30d.toFixed(1)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="comparison-legend">
        <div className="legend-section">
          <h4>Riscos:</h4>
          <div className="legend-items">
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#28a745' }}></div>
              <span>Baix (0-29)</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#ffc107' }}></div>
              <span>Mitjà (30-49)</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#fd7e14' }}></div>
              <span>Mitjà-Alt (50-69)</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#dc3545' }}></div>
              <span>Alt (70-100)</span>
            </div>
          </div>
        </div>
        <div className="legend-section">
          <h4>Tendències:</h4>
          <div className="legend-items">
            <div className="legend-item">
              <span className="trend-icon">↗️</span>
              <span>Augmentant ({'>'}5)</span>
            </div>
            <div className="legend-item">
              <span className="trend-icon">→</span>
              <span>Estable (-5 a 5)</span>
            </div>
            <div className="legend-item">
              <span className="trend-icon">↘️</span>
              <span>Disminuint ({'<'}-5)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

