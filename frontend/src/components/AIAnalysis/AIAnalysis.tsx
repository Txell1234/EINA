import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { aiAnalysisService } from '../../services/api'
import ComplementaryAnalysisForm from '../shared/ComplementaryAnalysisForm'
import AnalysisResultPanel from '../shared/AnalysisResultPanel'

export default function AIAnalysis() {
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [engine, setEngine] = useState<'taranis' | 'osintgpt' | 'ominis'>('taranis')

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
      const brief = {
        user_direction: userDirection,
        focus_entity: focusEntity,
        focus_topic: focusTopic,
      }
      if (engine === 'taranis') return aiAnalysisService.taranis(caseId, brief)
      if (engine === 'osintgpt') return aiAnalysisService.osintgpt(caseId, brief)
      return aiAnalysisService.ominis(caseId, brief)
    },
    onSuccess: (data) => {
      setResult(data)
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message || 'Error en l\'anàlisi')
      setResult(null)
    },
  })

  return (
    <div className="card">
      <h1>Anàlisi amb IA</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Motors Taranis, OSINTGPT i Ominis. Cal definir la teva direcció analítica abans d&apos;executar.
      </p>

      <ComplementaryAnalysisForm
        submitLabel="Executar anàlisi IA"
        isPending={analyzeMutation.isPending}
        showFocusFields
        extraFields={
          <div className="prospective-field" style={{ maxWidth: 280 }}>
            <label>Motor</label>
            <select
              className="prospective-select"
              value={engine}
              onChange={(e) => setEngine(e.target.value as typeof engine)}
            >
              <option value="taranis">Taranis — situacional</option>
              <option value="osintgpt">OSINTGPT — conceptes</option>
              <option value="ominis">Ominis — risc predictiu</option>
            </select>
          </div>
        }
        onSubmit={(payload) => analyzeMutation.mutate(payload)}
      />

      <AnalysisResultPanel
        title="Resultat de l'anàlisi IA"
        data={result}
        error={error}
      />
    </div>
  )
}
