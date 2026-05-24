import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { prospectiveService, reputationService } from '../../services/api'
import './ReputationDashboard.css'

interface ReputationProfile {
  id: number
  entity_name: string
  entity_type: string
  reputation_score: number
  sentiment_trend: string
}

interface ReputationDashboardProps {
  caseId?: number
  entityName?: string
}

export default function ReputationDashboard({ caseId: caseIdProp }: ReputationDashboardProps) {
  const [selectedEntityId, setSelectedEntityId] = useState<string | number | null>(null)
  const [days, setDays] = useState<number>(30)
  const { activeCase, setActiveCase } = useCase()

  const effectiveCaseId = activeCase?.id ?? caseIdProp

  const { data: cases } = useCasesList()

  const { data: projects = [] } = useQuery({
    queryKey: ['prospective-projects-for-reputation', effectiveCaseId],
    queryFn: () => prospectiveService.listProjects(effectiveCaseId),
    enabled: effectiveCaseId !== undefined,
  })

  const { data: profiles, isLoading: profilesLoading } = useQuery({
    queryKey: ['reputation-profiles', effectiveCaseId],
    queryFn: () => reputationService.getProfiles(effectiveCaseId),
    enabled: true,
  })

  const { data: scoreData, isLoading: scoreLoading } = useQuery({
    queryKey: ['reputation-score', selectedEntityId],
    queryFn: () => reputationService.getScore(selectedEntityId!),
    enabled: selectedEntityId !== null,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['reputation-history', selectedEntityId, days],
    queryFn: () => reputationService.getHistory(selectedEntityId!, days),
    enabled: selectedEntityId !== null,
  })

  const { data: crisisData, isLoading: crisisLoading } = useQuery({
    queryKey: ['crisis-indicators', selectedEntityId],
    queryFn: () => reputationService.getCrisisIndicators(selectedEntityId!, effectiveCaseId),
    enabled: selectedEntityId !== null,
  })

  const { data: stakeholders, isLoading: stakeholdersLoading } = useQuery({
    queryKey: ['stakeholders', effectiveCaseId],
    queryFn: () => reputationService.getStakeholders(effectiveCaseId),
    enabled: effectiveCaseId !== undefined,
  })

  const getScoreColor = (score: number): string => {
    if (score >= 70) return '#28a745'
    if (score >= 50) return '#ffc107'
    return '#dc3545'
  }

  const getCrisisLevelColor = (level: string): string => {
    switch (level) {
      case 'critical': return '#dc3545'
      case 'high': return '#fd7e14'
      case 'moderate': return '#ffc107'
      default: return '#6c757d'
    }
  }

  const mactorActors = (
    projects as { id: number; title: string; actors?: { code: string; name: string }[] }[]
  )
    .flatMap((p) => p.actors ?? [])
    .filter((a, i, arr) => arr.findIndex((x) => x.name === a.name) === i)

  if (profilesLoading) {
    return <div className="reputation-dashboard-loading">Cargando datos de reputación...</div>
  }

  return (
    <div className="reputation-dashboard">
      <div style={{
        background: 'var(--color-gray-50)',
        border: '1px solid var(--color-gray-200)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--spacing-md) var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-md)',
        flexWrap: 'wrap',
      }}>
        <label style={{
          fontSize: 'var(--font-size-sm)', fontWeight: 600,
          color: 'var(--color-gray-600)', flexShrink: 0,
        }}>
          Cas actiu:
        </label>
        <select
          style={{
            padding: '6px 12px', border: '1px solid var(--color-gray-300)',
            borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)',
            minWidth: 220,
          }}
          value={activeCase?.id ?? ''}
          onChange={(e) => {
            const id = Number(e.target.value)
            const c = (cases as { id: number; name: string }[] | undefined)
              ?.find((x) => x.id === id)
            if (c) setActiveCase({ id: c.id, name: c.name, case_type: '', status: 'actiu' })
          }}
        >
          <option value="">— Selecciona un cas —</option>
          {((cases as { id: number; name: string }[]) ?? []).map((c) => (
            <option key={c.id} value={c.id}>#{c.id} — {c.name}</option>
          ))}
        </select>
        {activeCase && (
          <span style={{
            fontSize: 'var(--font-size-xs)', color: 'var(--color-primary)',
            fontWeight: 500,
          }}>
            {activeCase.name}
          </span>
        )}
      </div>

      {effectiveCaseId !== undefined && mactorActors.length > 0 && (
        <div style={{
          background: 'rgba(30,58,95,0.04)',
          border: '1px solid rgba(30,58,95,0.15)',
          borderLeft: '3px solid var(--color-primary)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-md) var(--spacing-lg)',
          marginBottom: 'var(--spacing-lg)',
        }}>
          <p style={{
            fontSize: 'var(--font-size-xs)', fontWeight: 600,
            color: 'var(--color-primary)', marginBottom: 'var(--spacing-sm)',
            textTransform: 'uppercase', letterSpacing: '0.5px',
          }}>
            Actors del MACTOR — fes clic per veure el seu perfil de reputació
          </p>
          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
            {mactorActors.map((actor) => {
              const selected = String(selectedEntityId) === actor.name
              return (
                <button
                  key={actor.code}
                  type="button"
                  style={{
                    padding: '4px 12px',
                    borderRadius: '999px',
                    border: '1px solid var(--color-primary)',
                    background: selected ? 'var(--color-primary)' : 'transparent',
                    color: selected ? 'white' : 'var(--color-primary)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all .15s',
                  }}
                  onClick={() => setSelectedEntityId(actor.name)}
                >
                  {actor.code} — {actor.name}
                </button>
              )
            })}
          </div>
        </div>
      )}

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

      <div className="entity-selection">
        <h3>Seleccionar Entidad</h3>
        <div className="profiles-grid">
          {profiles && (profiles as ReputationProfile[]).length > 0 ? (
            (profiles as ReputationProfile[]).map((profile) => (
              <div
                key={profile.id}
                className={`profile-card ${selectedEntityId === profile.id ? 'selected' : ''}`}
                onClick={() => setSelectedEntityId(profile.id)}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedEntityId(profile.id)}
                role="button"
                tabIndex={0}
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

      {selectedEntityId !== null && (
        <>
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

          <div className="history-section">
            <h3>Histórico de Reputación</h3>
            {historyLoading ? (
              <div className="loading">Cargando histórico...</div>
            ) : history && history.length > 0 ? (
              <div className="history-chart">
                <div className="history-timeline">
                  {history.map((entry: { score: number; timestamp: string; change_reason?: string }, idx: number) => (
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

          <div className="stakeholders-section">
            <h3>Análisis de Stakeholders</h3>
            {stakeholdersLoading ? (
              <div className="loading">Cargando stakeholders...</div>
            ) : stakeholders && stakeholders.length > 0 ? (
              <div className="stakeholders-grid">
                {stakeholders.map((stakeholder: {
                  id: number
                  stakeholder_name: string
                  stakeholder_type: string
                  influence_score: number
                  sentiment: number
                  engagement_level: string
                }) => (
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
                          color: stakeholder.sentiment > 0 ? '#28a745' : '#dc3545',
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
