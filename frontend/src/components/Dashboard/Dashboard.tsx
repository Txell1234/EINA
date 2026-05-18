import { useQuery } from '@tanstack/react-query'
import { FolderKanban } from 'lucide-react'
import { useState } from 'react'
import { casesService, extractService } from '../../services/api'
import type { ActiveCase } from '../../contexts/CaseContext'
import { useCase } from '../../contexts/CaseContext'
import EmptyState from '../shared/EmptyState'
import WorkflowProgress from '../shared/WorkflowProgress'
import './Dashboard.css'

export default function Dashboard() {
  const { activeCase, setActiveCase } = useCase()
  const [showCreateHint, setShowCreateHint] = useState(false)

  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['cases-list'],
    queryFn: () => casesService.list() as Promise<{ id: number; name: string }[]>,
  })

  const { data: extractionRows = [] } = useQuery({
    queryKey: ['extract-statements', activeCase?.id],
    queryFn: () => extractService.getStatements(activeCase!.id),
    enabled: Boolean(activeCase?.id),
  })

  const extractionCount =
    activeCase?.extraction_count ?? (Array.isArray(extractionRows) ? extractionRows.length : 0)

  const handleSelectCase = (c: { id: number; name: string }) => {
    const next: ActiveCase = {
      id: c.id,
      name: c.name,
      type: 'investigació',
      status: 'actiu',
      osint_count: activeCase?.id === c.id ? activeCase.osint_count : undefined,
      extraction_count: activeCase?.id === c.id ? activeCase.extraction_count : undefined,
    }
    setActiveCase(next)
  }

  return (
    <div className="dashboard-page">
      <div className="section-header">
        <h2>Dashboard</h2>
      </div>

      <p style={{ color: 'var(--color-gray-600)', marginTop: 0 }}>
        Plataforma d&apos;intel·ligència estratègica i OSINT — selecciona un cas actiu al panell
        esquerre des de la llista següent.
      </p>

      {activeCase && (
        <WorkflowProgress
          osintCount={activeCase.osint_count ?? 0}
          extractionCount={extractionCount}
          hasMicmac={false}
          hasMactor={false}
          hasScenarios={false}
        />
      )}

      {isLoading && (
        <div className="loading-inline">
          <div className="spinner" />
          <span>Carregant casos…</span>
        </div>
      )}

      {!isLoading && (!cases || cases.length === 0) && (
        <EmptyState
          icon={<FolderKanban aria-hidden />}
          title="No hi ha casos registrats"
          description="Crea casos des del backend o base de dades (taula cases) per començar a vincular OSINT i anàlisi prospectiva."
          actionLabel="Com crear el primer cas"
          onAction={() => setShowCreateHint(true)}
        />
      )}

      {showCreateHint && (
        <div className="card" style={{ marginTop: 'var(--spacing-md)', background: 'var(--color-gray-50)' }}>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-700)' }}>
            Inseriu una fila a la taula <code>cases</code> (API futura) o useu el cas per defecte si el
            servidor el crea a l&apos;arrencada.
          </p>
        </div>
      )}

      {!isLoading && cases.length > 0 && (
        <div className="dashboard-case-grid">
          {cases.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`dashboard-case-card ${activeCase?.id === c.id ? 'dashboard-case-card--active' : ''}`}
              onClick={() => handleSelectCase(c)}
            >
              <span className="dashboard-case-id">#{c.id}</span>
              <span className="dashboard-case-name">{c.name}</span>
              {activeCase?.id === c.id && (
                <span className="status-badge success">Actiu</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
