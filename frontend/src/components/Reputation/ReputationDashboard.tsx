import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reputationService } from '../../services/api'
import './ReputationDashboard.css'

interface ReputationDashboardProps {
  caseId?: number
  entityName?: string
}

export default function ReputationDashboard({ caseId }: ReputationDashboardProps) {
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null)
  const [days, setDays] = useState<number>(30)

  // Fetch reputation profiles
  const { data: profiles, isLoading: profilesLoading } = useQuery({
    queryKey: ['reputation-profiles', caseId],
    queryFn: () => reputationService.getProfiles(caseId),
    enabled: true
  })

  // Fetch reputation score
  const { data: scoreData, isLoading: scoreLoading } = useQuery({
    queryKey: ['reputation-score', selectedEntityId],
    queryFn: () => reputationService.getScore(selectedEntityId!),
    enabled: selectedEntityId !== null
  })

  // Fetch reputation history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['reputation-history', selectedEntityId, days],
    queryFn: () => reputationService.getHistory(selectedEntityId!, days),
    enabled: selectedEntityId !== null
  })

  // Fetch crisis indicators
  const { data: crisisData, isLoading: crisisLoading } = useQuery({
    queryKey: ['crisis-indicators', selectedEntityId],
    queryFn: () => reputationService.getCrisisIndicators(selectedEntityId!),
    enabled: selectedEntityId !== null
  })

  // Fetch stakeholders
  const { data: stakeholders, isLoading: stakeholdersLoading } = useQuery({
    queryKey: ['stakeholders', caseId],
    queryFn: () => reputationService.getStakeholders(caseId),
    enabled: !!caseId
  })

  const getScoreColor = (score: number): string => {
    if (score >= 70) return '#28a745' // Green
    if (score >= 50) return '#ffc107' // Yellow
    return '#dc3545' // Red
  }

  const getCrisisLevelColor = (level: string): string => {
    switch (level) {
      case 'critical': return '#dc3545'
      case 'high': return '#fd7e14'
      case 'moderate': return '#ffc107'
      default: return '#6c757d'
    }
  }

  if (profilesLoading) {
    return <div className="reputation-dashboard-loading">Cargando datos de reputación...</div>
  }

  return (
    <div className="reputation-dashboard">
      <div className="dashboard-header">
        <h2>Dashboard de Reputación</h2>
        <div className="header-controls">
          <select 
            value={days} 
            onChange={(e) => setDays(Number(e.target.value))}
            className="time-range-select"
          >
            <option value={7}>7 días</option>
            <option value={30}>30 días</option>
            <option value={90}>90 días</option>
          </select>
        </div>
      </div>

      {/* Entity Selection */}
      <div className="entity-selection">
        <h3>Seleccionar Entidad</h3>
        <div className="profiles-grid">
          {profiles && profiles.length > 0 ? (
            profiles.map((profile: any) => (
              <div
                key={profile.id}
                className={`profile-card ${selectedEntityId === profile.id ? 'selected' : ''}`}
                onClick={() => setSelectedEntityId(profile.id)}
              >
                <div className="profile-name">{profile.entity_name}</div>
                <div className="profile-type">{profile.entity_type}</div>
                <div 
                  className="profile-score"
                  style={{ color: getScoreColor(profile.reputation_score) }}
                >
                  {profile.reputation_score.toFixed(1)}
                </div>
                <div className="profile-trend">{profile.sentiment_trend}</div>
              </div>
            ))
          ) : (
            <div className="no-profiles">No hay perfiles de reputación disponibles</div>
          )}
        </div>
      </div>

      {selectedEntityId && (
        <>
          {/* Reputation Score */}
          <div className="score-section">
            <h3>Score de Reputación</h3>
            {scoreLoading ? (
              <div className="loading">Cargando score...</div>
            ) : scoreData ? (
              <div className="score-display">
                <div 
                  className="score-circle"
                  style={{ borderColor: getScoreColor(scoreData.reputation_score) }}
                >
                  <div className="score-value">{scoreData.reputation_score.toFixed(1)}</div>
                  <div className="score-label">Score</div>
                </div>
                <div className="score-details">
                  <div className="detail-item">
                    <span className="detail-label">Tendencia:</span>
                    <span className="detail-value">{scoreData.sentiment_trend}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Última actualización:</span>
                    <span className="detail-value">
                      {new Date(scoreData.last_updated).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* Crisis Indicators */}
          <div className="crisis-section">
            <h3>Indicadores de Crisis</h3>
            {crisisLoading ? (
              <div className="loading">Cargando indicadores...</div>
            ) : crisisData ? (
              <div className="crisis-display">
                <div 
                  className="crisis-level"
                  style={{ backgroundColor: getCrisisLevelColor(crisisData.crisis_level) }}
                >
                  <span className="crisis-label">Nivel de Crisis:</span>
                  <span className="crisis-value">{crisisData.crisis_level.toUpperCase()}</span>
                </div>
                <div className="crisis-indicators">
                  <h4>Indicadores:</h4>
                  <ul>
                    {crisisData.indicators && crisisData.indicators.length > 0 ? (
                      crisisData.indicators.map((indicator: string, idx: number) => (
                        <li key={idx}>{indicator}</li>
                      ))
                    ) : (
                      <li>No hay indicadores de crisis activos</li>
                    )}
                  </ul>
                </div>
                {crisisData.recommendations && crisisData.recommendations.length > 0 && (
                  <div className="crisis-recommendations">
                    <h4>Recomendaciones:</h4>
                    <ul>
                      {crisisData.recommendations.map((rec: string, idx: number) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : null}
          </div>

          {/* Reputation History */}
          <div className="history-section">
            <h3>Histórico de Reputación</h3>
            {historyLoading ? (
              <div className="loading">Cargando histórico...</div>
            ) : history && history.length > 0 ? (
              <div className="history-chart">
                <div className="history-timeline">
                  {history.map((entry: any, idx: number) => (
                    <div key={idx} className="history-point">
                      <div className="point-value" style={{ color: getScoreColor(entry.score) }}>
                        {entry.score.toFixed(1)}
                      </div>
                      <div className="point-date">
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </div>
                      {entry.change_reason && (
                        <div className="point-reason">{entry.change_reason}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="no-history">No hay histórico disponible</div>
            )}
          </div>

          {/* Stakeholders */}
          <div className="stakeholders-section">
            <h3>Análisis de Stakeholders</h3>
            {stakeholdersLoading ? (
              <div className="loading">Cargando stakeholders...</div>
            ) : stakeholders && stakeholders.length > 0 ? (
              <div className="stakeholders-grid">
                {stakeholders.map((stakeholder: any) => (
                  <div key={stakeholder.id} className="stakeholder-card">
                    <div className="stakeholder-name">{stakeholder.stakeholder_name}</div>
                    <div className="stakeholder-type">{stakeholder.stakeholder_type}</div>
                    <div className="stakeholder-metrics">
                      <div className="metric">
                        <span className="metric-label">Influencia:</span>
                        <span className="metric-value">{stakeholder.influence_score.toFixed(1)}</span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Sentimiento:</span>
                        <span className="metric-value" style={{ 
                          color: stakeholder.sentiment > 0 ? '#28a745' : '#dc3545' 
                        }}>
                          {stakeholder.sentiment > 0 ? '+' : ''}{stakeholder.sentiment.toFixed(2)}
                        </span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Engagement:</span>
                        <span className="metric-value">{stakeholder.engagement_level}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-stakeholders">No hay stakeholders analizados</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
