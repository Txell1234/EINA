import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { qualitativeService } from '../../services/api'

export default function QualitativeAnalysis() {
  const { activeCase, setActiveCase } = useCase()
  const [frameworkId, setFrameworkId] = useState<number | ''>('')
  const [result, setResult] = useState<unknown>(null)

  const { data: cases } = useCasesList()

  const { data: frameworks = [] } = useQuery({
    queryKey: ['qualitative-frameworks'],
    queryFn: () => qualitativeService.getFrameworks(),
  })

  const analyzeMutation = useMutation({
    mutationFn: () => {
      if (!activeCase || !frameworkId) throw new Error('Cas i marc requerits')
      return qualitativeService.runAnalysis({
        case_id: activeCase.id,
        framework_id: frameworkId,
      })
    },
    onSuccess: (data) => setResult(data),
  })

  return (
    <div className="card">
      <h1>Anàlisi qualitativa</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Marc de raonament i conclusions estructurades per cas.
      </p>

      <div className="prospective-field" style={{ maxWidth: 420 }}>
        <label>Cas</label>
        <select
          className="prospective-select"
          value={activeCase?.id ?? ''}
          onChange={(e) => {
            const id = Number(e.target.value)
            const c = (cases as { id: number; name: string }[])?.find((x) => x.id === id)
            if (c) setActiveCase({ id: c.id, name: c.name, case_type: '', status: 'actiu' })
          }}
        >
          <option value="">— Sense cas —</option>
          {((cases as { id: number; name: string }[]) ?? []).map((c) => (
            <option key={c.id} value={c.id}>#{c.id} — {c.name}</option>
          ))}
        </select>
      </div>

      <div className="prospective-field" style={{ maxWidth: 420 }}>
        <label>Marc de raonament</label>
        <select
          className="prospective-select"
          value={frameworkId}
          onChange={(e) => setFrameworkId(e.target.value ? Number(e.target.value) : '')}
        >
          <option value="">— Selecciona —</option>
          {(frameworks as { id: number; name: string }[]).map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
      </div>

      <div className="prospective-actions">
        <button
          type="button"
          className="btn btn-accent"
          disabled={!activeCase || !frameworkId || analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
        >
          {analyzeMutation.isPending ? 'Analitzant...' : 'Executar anàlisi qualitativa'}
        </button>
      </div>

      {result !== null && (
        <pre style={{ marginTop: 'var(--spacing-lg)', fontSize: 11, overflow: 'auto', maxHeight: 400 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  )
}
