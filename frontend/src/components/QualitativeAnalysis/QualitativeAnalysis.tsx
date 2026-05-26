import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Settings2 } from 'lucide-react'
import { qualitativeService } from '../../services/api'
import ComplementaryAnalysisForm from '../shared/ComplementaryAnalysisForm'
import AnalysisResultPanel from '../shared/AnalysisResultPanel'

interface FrameworkItem {
  id: number
  name: string
  description?: string
  definition?: { application_notes?: string; doctrine?: string }
}

export default function QualitativeAnalysis() {
  const [frameworkId, setFrameworkId] = useState<number | ''>('')
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: frameworks = [] } = useQuery({
    queryKey: ['qualitative-frameworks'],
    queryFn: () => qualitativeService.getFrameworks(),
  })

  const analyzeMutation = useMutation({
    mutationFn: ({
      caseId,
      userDirection,
      focusEntity,
      focusTopic,
    }: {
      caseId: number
      userDirection: string
      focusEntity?: string
      focusTopic?: string
    }) => {
      const fw = (frameworks as { id: number; name: string }[]).find((f) => f.id === frameworkId)
      return qualitativeService.runAnalysis({
        case_id: caseId,
        premise: userDirection,
        framework: fw?.name ?? 'deductive',
        framework_id: frameworkId ? Number(frameworkId) : undefined,
        focus_entity: focusEntity,
        focus_topic: focusTopic,
      })
    },
    onSuccess: (data) => {
      setResult(data)
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message || 'Error en l\'anàlisi qualitativa')
      setResult(null)
    },
  })

  const selectedFramework = (frameworks as FrameworkItem[]).find((f) => f.id === frameworkId)

  return (
    <div className="card">
      <h1>Anàlisi qualitativa</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Marc de raonament i conclusions estructurades segons la teva pregunta analítica.{' '}
        <Link to="/reasoning-frameworks" className="inline-link">
          <Settings2 size={14} style={{ verticalAlign: 'middle' }} /> Gestionar marcs personalitzats
        </Link>
      </p>

      <ComplementaryAnalysisForm
        submitLabel="Executar anàlisi qualitativa"
        isPending={analyzeMutation.isPending}
        disabled={!frameworkId}
        showFocusFields
        extraFields={
          <div className="prospective-field" style={{ maxWidth: 420 }}>
            <label>Marc de raonament *</label>
            <select
              className="prospective-select"
              value={frameworkId}
              onChange={(e) => setFrameworkId(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">— Selecciona un marc —</option>
              {(frameworks as { id: number; name: string }[]).map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            {selectedFramework && (
              <p style={{ marginTop: 8, fontSize: '0.875rem', color: 'var(--color-gray-600)' }}>
                {selectedFramework.description}
                {selectedFramework.definition?.doctrine && (
                  <> — {selectedFramework.definition.doctrine.slice(0, 120)}…</>
                )}
              </p>
            )}
            {!frameworks.length && (
              <p style={{ marginTop: 8, fontSize: '0.875rem' }}>
                Cap marc disponible. <Link to="/reasoning-frameworks">Crea marcs</Link>.
              </p>
            )}
          </div>
        }
        onSubmit={(payload) => analyzeMutation.mutate(payload)}
      />

      <AnalysisResultPanel title="Conclusions qualitatives" data={result} error={error} />
    </div>
  )
}
