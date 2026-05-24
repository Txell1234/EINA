import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { aiAnalysisService } from '../../services/api'

export default function AIAnalysis() {
  const { activeCase, setActiveCase } = useCase()
  const [result, setResult] = useState<unknown>(null)
  const [engine, setEngine] = useState<'taranis' | 'osintgpt' | 'ominis'>('taranis')

  const { data: cases } = useCasesList()

  const analyzeMutation = useMutation({
    mutationFn: () => {
      if (!activeCase) throw new Error('Selecciona un cas')
      if (engine === 'taranis') return aiAnalysisService.taranis(activeCase.id)
      if (engine === 'osintgpt') return aiAnalysisService.osintgpt(activeCase.id)
      return aiAnalysisService.ominis(activeCase.id)
    },
    onSuccess: (data) => setResult(data),
  })

  return (
    <div className="card">
      <h1>Anàlisi amb IA</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Motors Taranis, OSINTGPT i Ominis. Requereix OPENAI_API_KEY al backend.
      </p>

      <div className="prospective-field" style={{ maxWidth: 420 }}>
        <label>Cas actiu</label>
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

      <div className="prospective-field" style={{ maxWidth: 280 }}>
        <label>Motor</label>
        <select className="prospective-select" value={engine} onChange={(e) => setEngine(e.target.value as typeof engine)}>
          <option value="taranis">Taranis</option>
          <option value="osintgpt">OSINTGPT</option>
          <option value="ominis">Ominis</option>
        </select>
      </div>

      <div className="prospective-actions">
        <button
          type="button"
          className="btn btn-accent"
          disabled={!activeCase || analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
        >
          {analyzeMutation.isPending ? 'Analitzant...' : 'Executar anàlisi'}
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
