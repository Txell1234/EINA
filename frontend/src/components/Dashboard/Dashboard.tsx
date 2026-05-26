import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { casesService, geographicService, heatmapService } from '../../services/api'
import type { ActiveCase } from '../../contexts/CaseContext'
import { useCase } from '../../contexts/CaseContext'
import { toActiveCase } from '../../utils/caseUtils'
import { useCasesList } from '../../hooks/useCasesList'
import EmptyState from '../shared/EmptyState'
import WorkflowProgress from '../shared/WorkflowProgress'
import CreateCaseModal from './CreateCaseModal'
import EditCaseModal from './EditCaseModal'
import VisualizationsDashboard from '../Visualizations/VisualizationsDashboard'
import GeographicMap from '../Visualizations/GeographicMap'
import Heatmap from '../Visualizations/Heatmap'
import ExtractionCoveragePanel from '../shared/ExtractionCoveragePanel'
import './Dashboard.css'

// Dashboard Heatmap Summary Component
function DashboardHeatmapSummary() {
  const [granularity, setGranularity] = useState<'country' | 'region' | 'city' | 'municipality'>('country')
  
  const { data: heatmapData, isLoading } = useQuery({
    queryKey: ['dashboard-heatmap', granularity],
    queryFn: () => heatmapService.getDashboardSummary(granularity),
  })

  if (isLoading) {
    return <div className="heatmap-loading">Carregant mapa de calor del dashboard...</div>
  }

  if (!heatmapData || !heatmapData.points || heatmapData.points.length === 0) {
    return (
      <div className="heatmap-empty">
        No hi ha dades suficients per mostrar el mapa de calor agregat.
        Crea casos i recopila dades OSINT per veure la visualització.
      </div>
    )
  }

  // Use a special caseId of 0 to indicate dashboard summary
  return (
    <div>
      <div className="heatmap-controls-bar" style={{ marginBottom: '1rem' }}>
        <div className="control-group">
          <label>Granularitat:</label>
          <select value={granularity} onChange={(e) => setGranularity(e.target.value as any)}>
            <option value="country">Països</option>
            <option value="region">Regions</option>
            <option value="city">Ciutats</option>
            <option value="municipality">Comuns</option>
          </select>
        </div>
      </div>
      <div style={{ 
        background: 'white', 
        borderRadius: '8px', 
        padding: '1rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <Heatmap
          caseId={0} // Special ID for dashboard summary
          metricType="posts"
          granularity={granularity}
        />
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { activeCase, setActiveCase } = useCase()
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [showVisualizations, setShowVisualizations] = useState(false)
  const [editingCaseId, setEditingCaseId] = useState<number | null>(null)
  
  const { data: cases, isLoading, refetch, isRefetching, error: casesError } = useCasesList({
    refetchInterval: 10000,
    retry: 2,
    retryDelay: 2000,
  })

  // Get real metrics from backend
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => casesService.getMetrics(),
  })

  const activeCases = cases?.filter((c: any) => c.status === 'analyzing' || c.status === 'pending') || []
  const completedCases = cases?.filter((c: any) => c.status === 'completed') || []

  // Get all geographic locations from active cases
  const { data: allLocations } = useQuery({
    queryKey: ['all-case-locations', activeCases],
    queryFn: async () => {
      const locations: any[] = []
      for (const caseItem of activeCases || []) {
        try {
          const locs = await geographicService.getLocations(caseItem.id)
          if (locs?.locations) {
            locations.push(...locs.locations)
          }
        } catch (e) {
          // Ignore errors for individual cases
        }
      }
      return { locations }
    },
    enabled: activeCases.length > 0,
  })
  
  const handleViewVisualizations = (caseId: number) => {
    setSelectedCaseId(caseId)
    setShowVisualizations(true)
  }

  const handleSelectActiveCase = (caseItem: {
    id: number
    name: string
    case_type?: string
    status: string
    description?: string
  }) => {
    const next: ActiveCase = {
      ...toActiveCase(caseItem),
      osint_count: activeCase?.id === caseItem.id ? activeCase.osint_count : undefined,
      extraction_count: activeCase?.id === caseItem.id ? activeCase.extraction_count : undefined,
      has_micmac: activeCase?.id === caseItem.id ? activeCase.has_micmac : undefined,
      has_mactor: activeCase?.id === caseItem.id ? activeCase.has_mactor : undefined,
      has_scenarios: activeCase?.id === caseItem.id ? activeCase.has_scenarios : undefined,
    }
    setActiveCase(next)
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      'pending': 'Pendent',
      'analyzing': 'Analitzant',
      'completed': 'Completat',
      'failed': 'Error'
    }
    return labels[status] || status
  }

  const getStatusDescription = (status: string) => {
    const descriptions: Record<string, string> = {
      'pending': 'El cas està esperant a ser processat',
      'analyzing': 'El cas està sent analitzat amb IA i eines OSINT',
      'completed': 'L\'anàlisi del cas s\'ha completat correctament',
      'failed': 'Hi ha hagut un error processant el cas'
    }
    return descriptions[status] || ''
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Visió general de casos actius i mètriques clau</p>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={() => refetch()} 
            disabled={isRefetching}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#007bff', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: isRefetching ? 'wait' : 'pointer'
            }}
          >
            {isRefetching ? 'Actualitzant...' : '🔄 Actualitzar'}
          </button>
          <CreateCaseModal />
        </div>
      </div>

      {activeCase && (
        <WorkflowProgress
          osintCount={activeCase.osint_count}
          extractionCount={activeCase.extraction_count}
          hasMicmac={activeCase.has_micmac}
          hasMactor={activeCase.has_mactor}
          hasScenarios={activeCase.has_scenarios}
        />
      )}

      {activeCase?.id ? (
        <ExtractionCoveragePanel caseId={activeCase.id} />
      ) : null}

      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Casos Actius</h3>
          <div className="metric-value">
            {metricsLoading ? '...' : (metrics?.active_cases ?? activeCases.length)}
          </div>
        </div>
        <div className="metric-card">
          <h3>Dades Recopilades</h3>
          <div className="metric-value">
            {metricsLoading ? '...' : (metrics?.osint_data_collected ?? 0).toLocaleString()}
          </div>
        </div>
        <div className="metric-card">
          <h3>Anàlisis Completats</h3>
          <div className="metric-value">
            {metricsLoading ? '...' : (metrics?.analyses_completed ?? completedCases.length)}
          </div>
        </div>
        <div className="metric-card">
          <h3>Recomanacions Generades</h3>
          <div className="metric-value">
            {metricsLoading ? '...' : (metrics?.recommendations_generated ?? 0)}
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="cases-table-section">
          <h2>Casos Actius</h2>
          {isLoading ? (
            <p>Carregant...</p>
          ) : (
            <table className="cases-table">
              <thead>
                <tr>
                  <th>Nom del Cas</th>
                  <th>Descripció</th>
                  <th>Tipus</th>
                  <th>Estat</th>
                  <th>Data Creació</th>
                  <th>Última Actualització</th>
                  <th>Accions</th>
                </tr>
              </thead>
              <tbody>
                {cases && cases.length > 0 ? (
                  cases.slice(0, 10).map((caseItem: any) => (
                    <tr key={caseItem.id}>
                      <td>
                        <strong>{caseItem.name}</strong>
                      </td>
                      <td className="case-description">
                        {caseItem.description ? (
                          <span title={caseItem.description}>
                            {caseItem.description.length > 50 
                              ? `${caseItem.description.substring(0, 50)}...` 
                              : caseItem.description}
                          </span>
                        ) : (
                          <span className="no-description">Sense descripció</span>
                        )}
                      </td>
                      <td>
                        <span className="case-type-badge">{caseItem.case_type || 'general'}</span>
                      </td>
                      <td>
                        <span className={`status-badge status-${caseItem.status}`} title={getStatusDescription(caseItem.status)}>
                          {getStatusLabel(caseItem.status)}
                        </span>
                      </td>
                      <td>
                        <div className="date-info">
                          {new Date(caseItem.created_at).toLocaleDateString('ca-ES', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric'
                          })}
                        </div>
                      </td>
                      <td>
                        <div className="date-info">
                          {new Date(caseItem.updated_at || caseItem.created_at).toLocaleDateString('ca-ES', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </td>
                      <td>
                        <div className="case-actions">
                          <button
                            type="button"
                            className={`btn-edit ${activeCase?.id === caseItem.id ? 'btn-edit--active' : ''}`}
                            onClick={() => handleSelectActiveCase(caseItem)}
                            title="Seleccionar com a cas actiu"
                          >
                            {activeCase?.id === caseItem.id ? '✓ Cas actiu' : 'Seleccionar'}
                          </button>
                          <button
                            type="button"
                            className="btn-edit"
                            onClick={() => setEditingCaseId(caseItem.id)}
                            title="Editar cas"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="btn-view"
                            onClick={() => handleViewVisualizations(caseItem.id)}
                            title="Veure visualitzacions i anàlisi detallada"
                          >
                            Analitzar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>
                      {casesError ? (
                        <div>
                          <p style={{ color: 'red', fontWeight: 'bold', marginBottom: '1rem' }}>
                            ❌ Error de connexió amb el servidor
                          </p>
                          <p style={{ color: '#666', marginBottom: '1rem' }}>
                            {String(casesError).includes('Network Error') || String(casesError).includes('ERR_NETWORK')
                              ? 'No es pot connectar al servidor backend. Assegura\'t que estigui executant-se a http://localhost:8000'
                              : String(casesError)}
                          </p>
                          <div style={{ marginTop: '1rem' }}>
                            <button 
                              onClick={() => refetch()} 
                              style={{ 
                                marginRight: '0.5rem',
                                padding: '0.5rem 1rem',
                                backgroundColor: '#007bff',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                              }}
                            >
                              🔄 Reintentar
                            </button>
                            <button 
                              onClick={() => window.open('http://localhost:8000/docs', '_blank')}
                              style={{ 
                                padding: '0.5rem 1rem',
                                backgroundColor: '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                              }}
                            >
                              🔍 Verificar Backend
                            </button>
                          </div>
                          <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#999' }}>
                            Si el problema persisteix, executa el backend manualment:<br/>
                            <code style={{ backgroundColor: '#f5f5f5', padding: '0.2rem 0.5rem', borderRadius: '3px' }}>
                              cd backend && python -m uvicorn app.main:app --reload --port 8000
                            </code>
                          </p>
                        </div>
                      ) : (
                        <EmptyState
                          icon="◈"
                          title="No hi ha casos actius"
                          description="Crea el teu primer cas per començar a recopilar dades OSINT i generar anàlisis prospectives."
                        />
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        <div className="recent-activity">
          <h2>Recent Activity</h2>
          <div className="activity-list">
            {cases && cases.length > 0 ? (
              cases.slice(0, 5).map((caseItem: any) => (
                <div key={caseItem.id} className="activity-item">
                  <div className="activity-date">
                    {new Date(caseItem.updated_at || caseItem.created_at).toLocaleDateString('ca-ES', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                  <div className="activity-text">
                    Cas '{caseItem.name}' - Estat: {caseItem.status}
                  </div>
                </div>
              ))
            ) : (
              <p>No hi ha activitat recent</p>
            )}
          </div>
        </div>
      </div>

      {allLocations?.locations && allLocations.locations.length > 0 ? (
        <div className="geographic-section">
          <h2>Mapa Mundial - Casos Actius</h2>
          <GeographicMap 
            locations={allLocations.locations}
            title="Ubicacions de tots els casos actius"
          />
        </div>
      ) : activeCase ? (
        <div className="geographic-section">
          <h2>Mapa Mundial</h2>
          <GeographicMap
            locations={[]}
            title={`Mapa — ${activeCase.name}`}
            caseId={activeCase.id}
            initialZoom={2}
          />
        </div>
      ) : null}

      {/* Dashboard Heatmap Summary */}
      <div className="dashboard-heatmap-section">
        <h2>🔥 Mapa de Calor - Resum General</h2>
        <p className="section-description">
          Visualització agregada de l'opinió pública i activitat per ubicació de tots els casos.
          Colors indiquen temàtiques principals, fletxes mostren relacions entre ubicacions.
        </p>
        <DashboardHeatmapSummary />
      </div>

      {showVisualizations && selectedCaseId && (
        <div className="modal-overlay" onClick={() => setShowVisualizations(false)}>
          <div className="modal-content large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Visualitzacions del Cas</h2>
              <button className="close-modal" onClick={() => setShowVisualizations(false)}>
                &times;
              </button>
            </div>
            <div className="modal-body">
              <VisualizationsDashboard caseId={selectedCaseId} />
            </div>
          </div>
        </div>
      )}

      {editingCaseId && (
        <EditCaseModal
          caseId={editingCaseId}
          isOpen={!!editingCaseId}
          onClose={() => setEditingCaseId(null)}
          onSuccess={() => {
            setEditingCaseId(null)
            refetch()
          }}
        />
      )}
    </div>
  )
}

