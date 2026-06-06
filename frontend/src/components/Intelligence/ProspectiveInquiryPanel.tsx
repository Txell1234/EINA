import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { prospectiveInquiryService } from '../../services/api'
import CcaHeatmapPanel, { type CcaCell } from './CcaHeatmapPanel'
import './ProspectiveInquiryPanel.css'

type ProspectiveInquiryPanelProps = {
  caseId: number
}

type StepState = {
  step: string
  status: string
  cached?: boolean
  detail?: string
}

const SAMPLE =
  'Trump announces US blockade of Hormuz lifted by December 2026?'

export default function ProspectiveInquiryPanel({ caseId }: ProspectiveInquiryPanelProps) {
  const queryClient = useQueryClient()
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'full' | 'lite'>('full')
  const [forceRefresh, setForceRefresh] = useState(false)
  const [autoRerun, setAutoRerun] = useState(false)
  const [rerunHours, setRerunHours] = useState(24)
  const [steps, setSteps] = useState<StepState[]>([])
  const [answer, setAnswer] = useState<Record<string, unknown> | null>(null)
  const [answerDiff, setAnswerDiff] = useState<Record<string, unknown> | null>(null)
  const [awaitingGodet, setAwaitingGodet] = useState(false)
  const [lastInquiryId, setLastInquiryId] = useState<number | null>(null)
  const [morphPreview, setMorphPreview] = useState<Array<Record<string, unknown>>>([])
  const [monitorSuggestions, setMonitorSuggestions] = useState<Array<Record<string, unknown>>>([])
  const [wizardProjectId, setWizardProjectId] = useState<number | null>(null)
  const [ccaCells, setCcaCells] = useState<CcaCell[]>([])
  const [ccaParameters, setCcaParameters] = useState<
    Array<{ code: string; name: string; states: string[] }>
  >([])

  const { data: inquiries = [] } = useQuery({
    queryKey: ['prospective-inquiries', caseId],
    queryFn: () => prospectiveInquiryService.listForCase(caseId),
  })

  const handleStreamEvent = (event: Record<string, unknown>) => {
    if (event.event === 'step') {
      const detail =
        event.mode != null
          ? `mode=${String(event.mode)}`
          : event.companies != null
            ? `empreses=${String(event.companies)}`
            : event.valid_combinations != null
              ? `combinacions=${String(event.valid_combinations)}`
              : event.count != null
                ? `monitors=${String(event.count)}`
                : undefined
      setSteps((prev) => {
        const idx = prev.findIndex((s) => s.step === event.step)
        const row: StepState = {
          step: String(event.step),
          status: String(event.status),
          cached: Boolean(event.cached),
          detail,
        }
        if (idx >= 0) {
          const next = [...prev]
          next[idx] = row
          return next
        }
        return [...prev, row]
      })
      if (event.step === 'morph_bootstrap' && Array.isArray(event.godet_preview)) {
        setMorphPreview(event.godet_preview as Array<Record<string, unknown>>)
      }
      if (event.step === 'monitors' && Array.isArray(event.suggested_monitors)) {
        setMonitorSuggestions(event.suggested_monitors as Array<Record<string, unknown>>)
      }
    }
    if (event.event === 'awaiting_godet') {
      setAwaitingGodet(true)
      const mb = event.morph_bootstrap as Record<string, unknown> | undefined
      if (mb && Array.isArray(mb.godet_preview)) {
        setMorphPreview(mb.godet_preview as Array<Record<string, unknown>>)
      }
    }
    if (event.event === 'done') {
      setAnswer(event.answer as Record<string, unknown>)
      if (event.answer_diff) setAnswerDiff(event.answer_diff as Record<string, unknown>)
    }
  }

  const resetRunState = () => {
    setSteps([])
    setAnswer(null)
    setAnswerDiff(null)
    setAwaitingGodet(false)
    setMorphPreview([])
    setMonitorSuggestions([])
    setCcaCells([])
    setCcaParameters([])
  }

  const runMutation = useMutation({
    mutationFn: async () => {
      resetRunState()
      const created = await prospectiveInquiryService.create({
        case_id: caseId,
        question: question.trim(),
        mode,
      })
      setLastInquiryId(created.inquiry_id)
      await prospectiveInquiryService.runStream(created.inquiry_id, handleStreamEvent, {
        forceRefresh,
      })
      if (autoRerun) {
        await prospectiveInquiryService.setSchedule(created.inquiry_id, true, rerunHours)
      }
      return created.inquiry_id
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
    },
  })

  const rerunMutation = useMutation({
    mutationFn: async (inquiryId: number) => {
      resetRunState()
      setLastInquiryId(inquiryId)
      await prospectiveInquiryService.rerunStream(inquiryId, handleStreamEvent, { forceRefresh })
      return inquiryId
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
    },
  })

  const scheduleMutation = useMutation({
    mutationFn: ({ inquiryId, enabled }: { inquiryId: number; enabled: boolean }) =>
      prospectiveInquiryService.setSchedule(inquiryId, enabled, rerunHours),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
    },
  })

  const synthMutation = useMutation({
    mutationFn: (inquiryId: number) => prospectiveInquiryService.synthesize(inquiryId),
    onSuccess: (data) => {
      setAnswer(data.answer as Record<string, unknown>)
      if (data.answer_diff) setAnswerDiff(data.answer_diff as Record<string, unknown>)
      setAwaitingGodet(false)
      setLastInquiryId(data.inquiry_id as number)
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
    },
  })

  const morphMutation = useMutation({
    mutationFn: (inquiryId: number) => prospectiveInquiryService.morphBootstrap(inquiryId),
    onSuccess: (data) => {
      if (Array.isArray(data.godet_preview)) {
        setMorphPreview(data.godet_preview as Array<Record<string, unknown>>)
      }
    },
  })

  const wizardMutation = useMutation({
    mutationFn: (inquiryId: number) => prospectiveInquiryService.applyToWizard(inquiryId),
    onSuccess: (data) => {
      if (data.project_id) setWizardProjectId(data.project_id as number)
    },
  })

  const heatmapMutation = useMutation({
    mutationFn: (inquiryId: number) => prospectiveInquiryService.ccaHeatmap(inquiryId),
    onSuccess: (data) => {
      const heat = data.cca_heatmap as { cells?: CcaCell[]; parameters?: typeof ccaParameters }
      if (Array.isArray(heat?.cells)) setCcaCells(heat.cells)
      if (Array.isArray(heat?.parameters)) setCcaParameters(heat.parameters)
    },
  })

  const reasoning = (answer?.reasoning as Array<{ conclusion?: string; because?: string }>) ?? []
  const conclusions = (answer?.conclusions as string[]) ?? []
  const exportId =
    lastInquiryId ??
    (inquiries as Array<{ id: number; status: string }>).find(
      (i) => i.status === 'completed' || i.status === 'awaiting_godet',
    )?.id

  return (
    <section className="prospective-inquiry-panel card">
      <header>
        <h3>Pregunta analítica (Q2FS)</h3>
        <p className="prospective-inquiry-panel__sub">
          La pregunta dispara recollida OSINT filtrada, pipeline, finances, morph, monitors i síntesi
          traçable. Re-runs programats opcionals.
        </p>
        <span className="prospective-inquiry-panel__badge">
          Scope must-match · Audit trail · Scheduler
        </span>
      </header>

      <textarea
        rows={3}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={SAMPLE}
      />

      <div className="prospective-inquiry-panel__row">
        <label>
          Mode
          <select value={mode} onChange={(e) => setMode(e.target.value as 'full' | 'lite')}>
            <option value="full">Complet (espera Godet manual)</option>
            <option value="lite">Lite (OSINT + síntesi parcial)</option>
          </select>
        </label>
        <label className="prospective-inquiry-panel__check">
          <input
            type="checkbox"
            checked={forceRefresh}
            onChange={(e) => setForceRefresh(e.target.checked)}
          />
          Forçar reexecució (ignorar cache)
        </label>
        <label className="prospective-inquiry-panel__check">
          <input
            type="checkbox"
            checked={autoRerun}
            onChange={(e) => setAutoRerun(e.target.checked)}
          />
          Auto re-run
          <input
            type="number"
            min={1}
            max={168}
            value={rerunHours}
            onChange={(e) => setRerunHours(Number(e.target.value) || 24)}
            disabled={!autoRerun}
            className="prospective-inquiry-panel__hours"
          />
          h
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={question.trim().length < 15 || runMutation.isPending}
          onClick={() => runMutation.mutate()}
        >
          {runMutation.isPending ? 'Executant…' : 'Llançar inquiry'}
        </button>
      </div>

      {exportId && (
        <div className="prospective-inquiry-panel__row">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={rerunMutation.isPending}
            onClick={() => rerunMutation.mutate(exportId)}
          >
            {rerunMutation.isPending ? 'Reexecutant…' : `Re-run inquiry #${exportId}`}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={scheduleMutation.isPending}
            onClick={() => scheduleMutation.mutate({ inquiryId: exportId, enabled: true })}
          >
            Activar scheduler
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={scheduleMutation.isPending}
            onClick={() => scheduleMutation.mutate({ inquiryId: exportId, enabled: false })}
          >
            Desactivar scheduler
          </button>
        </div>
      )}

      {steps.length > 0 && (
        <div className="prospective-inquiry-panel__steps">
          <h4>Monitor de passos</h4>
          <ul>
            {steps.map((s) => (
              <li key={s.step}>
                <strong>{s.step}</strong>: {s.status}
                {s.cached ? ' (cache)' : ''}
                {s.detail ? ` — ${s.detail}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {awaitingGodet && (
        <div className="prospective-inquiry-panel__wait">
          <p>Completa Godet al wizard prospectiu i després:</p>
          {(inquiries as Array<{ id: number; status: string }>)
            .filter((i) => i.status === 'awaiting_godet')
            .map((i) => (
              <button
                key={i.id}
                type="button"
                className="btn btn-secondary"
                disabled={synthMutation.isPending}
                onClick={() => synthMutation.mutate(i.id)}
              >
                Síntesi inquiry #{i.id}
              </button>
            ))}
        </div>
      )}

      {morphPreview.length > 0 && (
        <details open className="prospective-inquiry-panel__morph">
          <summary>Suggeriments morfològics (Zwicky preview)</summary>
          <table>
            <thead>
              <tr>
                <th>Escenari</th>
                <th>Config</th>
                <th>Possibilitat</th>
              </tr>
            </thead>
            <tbody>
              {morphPreview.map((row) => (
                <tr key={String(row.name)}>
                  <td>{String(row.name ?? '')}</td>
                  <td>{String(row.config ?? '')}</td>
                  <td>{String(row.possibility ?? '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {exportId && (
            <>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={wizardMutation.isPending}
                onClick={() => wizardMutation.mutate(exportId)}
              >
                {wizardMutation.isPending ? 'Sembrant…' : 'Aplicar al wizard Godet'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={heatmapMutation.isPending}
                onClick={() => heatmapMutation.mutate(exportId)}
              >
                Carregar heatmap CCA
              </button>
            </>
          )}
          {wizardProjectId && (
            <p className="prospective-inquiry-panel__sub">
              Projecte #{wizardProjectId} — continua MIC-MAC/MACTOR a Anàlisi Prospectiva.
            </p>
          )}
        </details>
      )}

      {(ccaCells.length > 0 || ccaParameters.length > 0) && (
        <details open className="prospective-inquiry-panel__morph">
          <summary>Heatmap CCA (Zwicky)</summary>
          <CcaHeatmapPanel cells={ccaCells} parameters={ccaParameters} />
        </details>
      )}

      {monitorSuggestions.length > 0 && (
        <details open className="prospective-inquiry-panel__monitors">
          <summary>Monitors suggerits ({monitorSuggestions.length})</summary>
          <ul>
            {monitorSuggestions.map((m) => (
              <li key={String(m.indicator)}>{String(m.indicator)}</li>
            ))}
          </ul>
        </details>
      )}

      {answer && (
        <div className="prospective-inquiry-panel__answer">
          <h4>Resposta (determinista)</h4>
          <p>
            Probabilitat: {String(answer.probability_pct ?? '—')}% · Possibilitat:{' '}
            {String(answer.possibility ?? '—')}
            {answer.financial_mode != null ? ` · Financial: ${String(answer.financial_mode)}` : ''}
          </p>
          {answerDiff && answerDiff.probability_delta != null && (
            <p className="prospective-inquiry-panel__diff">
              Δ probabilitat vs run anterior: {String(answerDiff.probability_delta)} pts
              {answerDiff.possibility_changed ? ' · possibilitat canviada' : ''}
            </p>
          )}
          {reasoning.length > 0 && (
            <ul>
              {reasoning.map((r) => (
                <li key={r.conclusion}>
                  {r.conclusion}
                  {r.because ? ` — Per què: ${r.because}` : ''}
                </li>
              ))}
            </ul>
          )}
          {conclusions.length > 0 && (
            <div>
              <h5>Conclusions</h5>
              <ul>
                {conclusions.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {exportId && (
        <p className="prospective-inquiry-panel__export">
          <a
            href={prospectiveInquiryService.exportHtmlUrl(exportId)}
            target="_blank"
            rel="noreferrer"
          >
            Exportar HTML (#{exportId})
          </a>
          {' · '}
          <a
            href={prospectiveInquiryService.exportPdfUrl(exportId)}
            target="_blank"
            rel="noreferrer"
          >
            Exportar PDF
          </a>
        </p>
      )}

      {inquiries.length > 0 && (
        <details>
          <summary>Inquiries anteriors ({inquiries.length})</summary>
          <ul>
            {(inquiries as Array<{
              id: number
              question: string
              status: string
              auto_rerun_enabled?: boolean
              next_rerun_at?: string
              run_count?: number
            }>).map((i) => (
              <li key={i.id}>
                #{i.id} [{i.status}] runs={i.run_count ?? 0}
                {i.auto_rerun_enabled ? ` · scheduler ${i.next_rerun_at ?? ''}` : ''}
                {' — '}
                {i.question.slice(0, 60)}…
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
