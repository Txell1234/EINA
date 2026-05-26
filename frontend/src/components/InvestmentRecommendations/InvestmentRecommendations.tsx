import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { investmentsService, prospectiveService } from '../../services/api'
import ComplementaryAnalysisForm from '../shared/ComplementaryAnalysisForm'
import AnalysisResultPanel from '../shared/AnalysisResultPanel'

export default function InvestmentRecommendations() {
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [projectId, setProjectId] = useState<number | null>(null)

  const { data: projects = [] } = useQuery({
    queryKey: ['prospective-projects'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const recommendMutation = useMutation({
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
    }) =>
      investmentsService.recommend(caseId, {
        user_direction: userDirection,
        focus_entity: focusEntity,
        focus_topic: focusTopic,
      }),
    onSuccess: (data) => {
      setResult(data)
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message || 'Error generant recomanació')
      setResult(null)
    },
  })

  return (
    <div className="card">
      <h1>Recomanacions d&apos;inversió</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Impacte estratègic i exposició geopolítica segons la teva pregunta — no recomanacions genèriques.
      </p>

      <ComplementaryAnalysisForm
        submitLabel="Generar recomanació d'inversió"
        isPending={recommendMutation.isPending}
        showFocusFields
        onSubmit={(payload) => recommendMutation.mutate(payload)}
      />

      <AnalysisResultPanel title="Recomanació" data={result} error={error} />

      <hr style={{ margin: 'var(--spacing-xl) 0', border: 'none', borderTop: '1px solid var(--color-gray-200)' }} />

      <h2 style={{ fontSize: 'var(--font-size-lg)', color: 'var(--color-primary)' }}>
        Informe prospectiu (PDF / DOCX)
      </h2>
      <div className="prospective-field" style={{ maxWidth: 420 }}>
        <label>Projecte prospectiu</label>
        <select
          className="prospective-select"
          value={projectId ?? ''}
          onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— Selecciona —</option>
          {(projects as { id: number; title: string }[]).map((p) => (
            <option key={p.id} value={p.id}>#{p.id} — {p.title}</option>
          ))}
        </select>
      </div>
      {projectId !== null && (
        <div className="prospective-actions">
          <button type="button" className="btn btn-accent" onClick={() => prospectiveService.exportPdf(projectId)}>
            PDF
          </button>
          <button type="button" className="btn btn-primary" onClick={() => prospectiveService.exportDocx(projectId)}>
            DOCX
          </button>
        </div>
      )}
    </div>
  )
}
