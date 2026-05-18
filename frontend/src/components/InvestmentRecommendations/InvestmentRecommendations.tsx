import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { casesService, investmentsService, prospectiveService } from '../../services/api'

export default function InvestmentRecommendations() {
  const { activeCase, setActiveCase } = useCase()
  const [result, setResult] = useState<unknown>(null)
  const [projectId, setProjectId] = useState<number | null>(null)

  const { data: cases } = useQuery({
    queryKey: ['cases-list'],
    queryFn: () => casesService.list(),
  })

  const { data: projects = [] } = useQuery({
    queryKey: ['prospective-projects'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const recommendMutation = useMutation({
    mutationFn: () => {
      if (!activeCase) throw new Error('Selecciona un cas')
      return investmentsService.recommend(activeCase.id)
    },
    onSuccess: (data) => setResult(data),
  })

  return (
    <div className="card">
      <h1>Exportar informe</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Recomanacions d&apos;inversió per cas i exportació d&apos;informe prospectiu complet.
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

      <div className="prospective-actions">
        <button
          type="button"
          className="btn btn-accent"
          disabled={!activeCase || recommendMutation.isPending}
          onClick={() => recommendMutation.mutate()}
        >
          {recommendMutation.isPending ? 'Generant...' : 'Generar recomanació d\'inversió'}
        </button>
      </div>

      {result !== null && (
        <pre style={{ marginTop: 'var(--spacing-lg)', fontSize: 11, overflow: 'auto', maxHeight: 300 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}

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
