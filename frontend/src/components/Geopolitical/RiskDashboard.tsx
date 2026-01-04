import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { geopoliticalService } from '../../services/api'
import RiskComparison from './RiskComparison'
import './RiskDashboard.css'

interface RiskDashboardProps {
  caseId?: number
}

export default function RiskDashboard({ caseId }: RiskDashboardProps) {
  const [selectedCountries, setSelectedCountries] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<'overview' | 'comparison'>('overview')

  const { data: risksData, isLoading } = useQuery({
    queryKey: ['geopolitical-risks', caseId],
    queryFn: () => geopoliticalService.getRisks(caseId),
    enabled: true
  })

  const handleCalculateRisks = async () => {
    try {
      await geopoliticalService.calculateRisks(caseId)
      // Refetch after calculation
      window.location.reload()
    } catch (error) {
      console.error('Error calculating risks:', error)
    }
  }

  if (isLoading) {
    return <div className="risk-dashboard-loading">Carregant riscos geopolítics...</div>
  }

  const risks = risksData || []

  return (
    <div className="risk-dashboard">
      <div className="dashboard-header">
        <h2>Dashboard de Riscos Geopolítics</h2>
        <div className="header-actions">
          <button className="btn-calculate" onClick={handleCalculateRisks}>
            🔄 Calcular Riscos des de OSINT
          </button>
          <div className="view-mode-toggle">
            <button
              className={`mode-btn ${viewMode === 'overview' ? 'active' : ''}`}
              onClick={() => setViewMode('overview')}
            >
              Resum
            </button>
            <button
              className={`mode-btn ${viewMode === 'comparison' ? 'active' : ''}`}
              onClick={() => setViewMode('comparison')}
            >
              Comparació
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'overview' ? (
        <div className="risks-overview">
          {risks.length === 0 ? (
            <div className="no-risks">
              <p>No hi ha riscos geopolítics calculats</p>
              <button className="btn-primary" onClick={handleCalculateRisks}>
                Calcular Riscos
              </button>
            </div>
          ) : (
            <div className="risks-grid">
              {risks.map((risk: any) => (
                <div key={risk.id} className="risk-card">
                  <div className="risk-card-header">
                    <h3>{risk.country}</h3>
                    {risk.alert_triggered && (
                      <span className="alert-badge">⚠️ Alerta</span>
                    )}
                  </div>
                  <div className="risk-score-main">
                    <div className="score-value">{risk.overall_risk_score.toFixed(1)}</div>
                    <div className="score-label">Risc General</div>
                  </div>
                  <div className="risk-factors">
                    <div className="factor-item">
                      <span className="factor-label">Estabilitat Política</span>
                      <div className="factor-bar">
                        <div
                          className="factor-fill"
                          style={{
                            width: `${risk.political_stability_risk}%`,
                            backgroundColor: risk.political_stability_risk >= 50 ? '#dc3545' : '#6c757d'
                          }}
                        />
                        <span className="factor-value">{risk.political_stability_risk.toFixed(0)}</span>
                      </div>
                    </div>
                    <div className="factor-item">
                      <span className="factor-label">Risc de Conflicte</span>
                      <div className="factor-bar">
                        <div
                          className="factor-fill"
                          style={{
                            width: `${risk.conflict_risk}%`,
                            backgroundColor: risk.conflict_risk >= 50 ? '#dc3545' : '#6c757d'
                          }}
                        />
                        <span className="factor-value">{risk.conflict_risk.toFixed(0)}</span>
                      </div>
                    </div>
                    <div className="factor-item">
                      <span className="factor-label">Risc Econòmic</span>
                      <div className="factor-bar">
                        <div
                          className="factor-fill"
                          style={{
                            width: `${risk.economic_risk}%`,
                            backgroundColor: risk.economic_risk >= 50 ? '#dc3545' : '#6c757d'
                          }}
                        />
                        <span className="factor-value">{risk.economic_risk.toFixed(0)}</span>
                      </div>
                    </div>
                    <div className="factor-item">
                      <span className="factor-label">Risc de Seguretat</span>
                      <div className="factor-bar">
                        <div
                          className="factor-fill"
                          style={{
                            width: `${risk.security_risk}%`,
                            backgroundColor: risk.security_risk >= 50 ? '#dc3545' : '#6c757d'
                          }}
                        />
                        <span className="factor-value">{risk.security_risk.toFixed(0)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="risk-trends">
                    <div className="trend-item">
                      <span className="trend-label">Canvi 7 dies:</span>
                      <span
                        className="trend-value"
                        style={{
                          color: risk.risk_change_7d > 5 ? '#dc3545' : risk.risk_change_7d < -5 ? '#28a745' : '#6c757d'
                        }}
                      >
                        {risk.risk_change_7d > 0 ? '+' : ''}{risk.risk_change_7d.toFixed(1)}
                      </span>
                    </div>
                    <div className="trend-item">
                      <span className="trend-label">Canvi 30 dies:</span>
                      <span
                        className="trend-value"
                        style={{
                          color: risk.risk_change_30d > 5 ? '#dc3545' : risk.risk_change_30d < -5 ? '#28a745' : '#6c757d'
                        }}
                      >
                        {risk.risk_change_30d > 0 ? '+' : ''}{risk.risk_change_30d.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  {risk.alert_reason && (
                    <div className="alert-reason">
                      <strong>Alerta:</strong> {risk.alert_reason}
                    </div>
                  )}
                  {(risk.risk_3_months || risk.risk_6_months || risk.risk_12_months) && (
                    <div className="risk-predictions">
                      <h4>Prediccions:</h4>
                      <div className="predictions-list">
                        {risk.risk_3_months && (
                          <div className="prediction-item">
                            <span>3 mesos:</span>
                            <span className="prediction-value">{risk.risk_3_months.toFixed(1)}</span>
                          </div>
                        )}
                        {risk.risk_6_months && (
                          <div className="prediction-item">
                            <span>6 mesos:</span>
                            <span className="prediction-value">{risk.risk_6_months.toFixed(1)}</span>
                          </div>
                        )}
                        {risk.risk_12_months && (
                          <div className="prediction-item">
                            <span>12 mesos:</span>
                            <span className="prediction-value">{risk.risk_12_months.toFixed(1)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="comparison-view">
          {selectedCountries.length === 0 ? (
            <div className="select-countries">
              <p>Selecciona països per comparar:</p>
              <div className="countries-list">
                {risks.map((risk: any) => (
                  <label key={risk.id} className="country-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedCountries.includes(risk.country)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCountries([...selectedCountries, risk.country])
                        } else {
                          setSelectedCountries(selectedCountries.filter(c => c !== risk.country))
                        }
                      }}
                    />
                    {risk.country}
                  </label>
                ))}
              </div>
            </div>
          ) : (
            <RiskComparison countries={selectedCountries} caseId={caseId} />
          )}
        </div>
      )}
    </div>
  )
}

