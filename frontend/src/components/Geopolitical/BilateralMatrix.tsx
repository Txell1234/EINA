import { useQuery } from '@tanstack/react-query'
import { geopoliticalService } from '../../services/api'
import './BilateralMatrix.css'

interface BilateralMatrixProps {
  caseId?: number
}

export default function BilateralMatrix({ caseId }: BilateralMatrixProps) {
  const { data: matrixData, isLoading } = useQuery({
    queryKey: ['bilateral-matrix', caseId],
    queryFn: () => geopoliticalService.getBilateralMatrix(caseId),
    enabled: true
  })

  if (isLoading) {
    return <div className="matrix-loading">Carregant matriu de relacions...</div>
  }

  if (!matrixData || matrixData.error) {
    return (
      <div className="matrix-error">
        <p>No s'han trobat relacions bilaterals</p>
        <p className="error-hint">Intenta extreure relacions des de dades OSINT primer</p>
      </div>
    )
  }

  const { countries, matrix, total_relations } = matrixData

  if (countries.length === 0) {
    return (
      <div className="matrix-empty">
        No hi ha països amb relacions detectades
      </div>
    )
  }

  const getScoreColor = (score: number | null): string => {
    if (score === null) return '#e5e7eb' // Gray for unknown
    if (score >= 70) return '#28a745' // Green for good relations
    if (score >= 50) return '#ffc107' // Yellow for neutral
    if (score >= 30) return '#fd7e14' // Orange for poor
    return '#dc3545' // Red for very poor
  }

  const getScoreLabel = (score: number | null, status: string): string => {
    if (score === null) return '?'
    if (status === 'self') return '—'
    return score.toFixed(0)
  }

  return (
    <div className="bilateral-matrix">
      <div className="matrix-header">
        <h3>Matriu de Relacions Bilaterals</h3>
        <div className="matrix-stats">
          <span>{countries.length} països</span>
          <span>•</span>
          <span>{total_relations} relacions</span>
        </div>
      </div>

      <div className="matrix-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#28a745' }}></div>
          <span>Bona (70-100)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#ffc107' }}></div>
          <span>Neutral (50-69)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#fd7e14' }}></div>
          <span>Dèbil (30-49)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#dc3545' }}></div>
          <span>Crítica (0-29)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#e5e7eb' }}></div>
          <span>Desconeguda</span>
        </div>
      </div>

      <div className="matrix-container">
        <div className="matrix-table-wrapper">
          <table className="matrix-table">
            <thead>
              <tr>
                <th className="matrix-corner"></th>
                {countries.map((country: string) => (
                  <th key={country} className="matrix-header-cell">
                    {country}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {countries.map((country1: string) => (
                <tr key={country1}>
                  <td className="matrix-row-header">{country1}</td>
                  {countries.map((country2: string) => {
                    const cellData = matrix[country1]?.[country2] || { score: null, status: 'unknown' }
                    const score = cellData.score
                    const status = cellData.status
                    
                    return (
                      <td
                        key={`${country1}-${country2}`}
                        className="matrix-cell"
                        style={{ backgroundColor: getScoreColor(score) }}
                        title={
                          status === 'self'
                            ? 'Mateix país'
                            : score !== null
                            ? `Score: ${score.toFixed(1)}, Estat: ${cellData.status || 'unknown'}`
                            : 'Relació desconeguda'
                        }
                      >
                        {getScoreLabel(score, status)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="matrix-footer">
        <p className="matrix-note">
          La matriu mostra el score de relació entre cada parella de països (0-100).
          Valors alts indiquen millors relacions.
        </p>
      </div>
    </div>
  )
}

