import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../../contexts/I18nContext'
import type { PanelTranslationKey } from '../../i18n/panelBundles'
import { prospectiveInquiryService } from '../../services/api'
import CcaHeatmapPanel, { type CcaCell } from './CcaHeatmapPanel'
import InquiryComparePanel, { type InquiryCompareItem } from './InquiryComparePanel'
import InquiryTracePanel, { type ScopeAuditData, type AuditTrailEntry } from './InquiryTracePanel'
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

const GODET_CHECKLIST: Array<{
  key: string
  labelKey: PanelTranslationKey
  path: string
}> = [
  { key: 'project', labelKey: 'inquiry.panel.godet.project', path: '/prospective/project' },
  { key: 'variables', labelKey: 'inquiry.panel.godet.variables', path: '/prospective/variables' },
  { key: 'micmac', labelKey: 'inquiry.panel.godet.micmac', path: '/prospective/micmac' },
  { key: 'actors', labelKey: 'inquiry.panel.godet.actors', path: '/prospective/actors' },
  { key: 'mactor', labelKey: 'inquiry.panel.godet.mactor', path: '/prospective/mactor' },
  { key: 'morph', labelKey: 'inquiry.panel.godet.morph', path: '/prospective/morph' },
  { key: 'smic', labelKey: 'inquiry.panel.godet.smic', path: '/prospective-analysis' },
  { key: 'scenarios', labelKey: 'inquiry.panel.godet.scenarios', path: '/prospective-analysis' },
]

export default function ProspectiveInquiryPanel({ caseId }: ProspectiveInquiryPanelProps) {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
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
  const [scopeAuditLive, setScopeAuditLive] = useState<ScopeAuditData | null>(null)
  const [parsePreview, setParsePreview] = useState<Record<string, unknown> | null>(null)

  const { data: inquiries = [] } = useQuery({
    queryKey: ['prospective-inquiries', caseId],
    queryFn: () => prospectiveInquiryService.listForCase(caseId),
  })

  const traceInquiryId =
    lastInquiryId ??
    (inquiries as Array<{ id: number; status: string }>).find(
      (i) =>
        i.status === 'completed' ||
        i.status === 'awaiting_godet' ||
        i.status === 'failed',
    )?.id ??
    null

  const { data: scopeAuditData } = useQuery({
    queryKey: ['prospective-inquiry-scope-audit', traceInquiryId],
    queryFn: () => prospectiveInquiryService.getScopeAudit(traceInquiryId!),
    enabled: traceInquiryId !== null,
  })

  const { data: auditData } = useQuery({
    queryKey: ['prospective-inquiry-audit', traceInquiryId],
    queryFn: () => prospectiveInquiryService.getAudit(traceInquiryId!),
    enabled: traceInquiryId !== null,
  })

  const hasAwaitingGodetInquiry = (inquiries as Array<{ status: string }>).some(
    (i) => i.status === 'awaiting_godet',
  )

  const { data: godetStatusData } = useQuery({
    queryKey: ['prospective-inquiry-godet-status', traceInquiryId],
    queryFn: () => prospectiveInquiryService.getGodetStatus(traceInquiryId!),
    enabled: traceInquiryId !== null,
    refetchInterval: awaitingGodet || hasAwaitingGodetInquiry ? 15000 : false,
  })

  const { data: compareData } = useQuery({
    queryKey: ['prospective-inquiries-compare', caseId],
    queryFn: () => prospectiveInquiryService.compareForCase(caseId),
    enabled: (inquiries as unknown[]).length >= 2,
  })

  const openWizard = async (inquiryId: number, projectId?: number | null) => {
    if (projectId) {
      navigate(prospectiveInquiryService.buildWizardUrl(projectId, inquiryId, 'morph'))
      return
    }
    const link = await prospectiveInquiryService.wizardLink(inquiryId)
    navigate(link.wizard_paths.morph)
  }

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
      if (event.step === 'osint' && event.audit && typeof event.audit === 'object') {
        setScopeAuditLive({ audit: event.audit as Record<string, number | string> })
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
    setScopeAuditLive(null)
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
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiry-godet-status'] })
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiry-audit'] })
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

  const reasoning = (answer?.reasoning as Array<{ conclusion?: string; because?: string; sources?: Array<{ origin?: string; field?: string }> }>) ?? []
  const evidence = (answer?.evidence as Array<Record<string, unknown>>) ?? []
  const conclusions = (answer?.conclusions as string[]) ?? []
  const exportId =
    lastInquiryId ??
    (inquiries as Array<{ id: number; status: string }>).find(
      (i) => i.status === 'completed' || i.status === 'awaiting_godet',
    )?.id

  useEffect(() => {
    const trimmed = question.trim()
    if (trimmed.length < 15) {
      setParsePreview(null)
      return
    }
    const timer = window.setTimeout(() => {
      void prospectiveInquiryService
        .parsePreview(trimmed, caseId)
        .then((data) => setParsePreview(data as Record<string, unknown>))
        .catch(() => setParsePreview(null))
    }, 500)
    return () => window.clearTimeout(timer)
  }, [question, caseId])

  const isRunning = runMutation.isPending || rerunMutation.isPending
  const godetStatus = godetStatusData as
    | {
        checklist?: Record<string, boolean>
        missing_steps?: string[]
        godet_ready?: boolean
        can_synthesize?: boolean
        project_id?: number | null
        status?: string
      }
    | undefined
  const showGodetGuide = awaitingGodet || godetStatus?.status === 'awaiting_godet'
  const godetReady = Boolean(godetStatus?.godet_ready)
  const canSynthesize = Boolean(godetStatus?.can_synthesize) || godetReady
  const synthTargetId =
    lastInquiryId ??
    (inquiries as Array<{ id: number; status: string }>).find((i) => i.status === 'awaiting_godet')
      ?.id

  const openGodetStep = (stepPath: string) => {
    const projectId = godetStatus?.project_id ?? wizardProjectId
    if (!projectId) {
      navigate(stepPath)
      return
    }
    const params = new URLSearchParams({ project: String(projectId) })
    if (synthTargetId) params.set('inquiry', String(synthTargetId))
    navigate(`${stepPath}?${params.toString()}`)
  }

  return (
    <section
      className={`prospective-inquiry-panel card${isRunning ? ' prospective-inquiry-panel--running' : ''}`}
      data-testid="prospective-inquiry-panel"
    >
      <header>
        <h3>{t('inquiry.panel.title')}</h3>
        <p className="prospective-inquiry-panel__sub">{t('inquiry.panel.subtitle')}</p>
        <span className="prospective-inquiry-panel__badge">{t('inquiry.panel.badge')}</span>
      </header>

      <textarea
        rows={3}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={t('inquiry.panel.questionPlaceholder')}
        data-testid="inquiry-question"
      />

      {parsePreview?.ok ? (
        <p className="prospective-inquiry-panel__parse-preview" data-testid="inquiry-parse-preview">
          <strong>{t('inquiry.panel.parse.label')}</strong>
          <span>{t('inquiry.panel.parse.confidence', { value: String(parsePreview.confidence ?? '—') })}</span>
          <span>{parsePreview.llm_used ? t('inquiry.panel.parse.llm') : t('inquiry.panel.parse.rules')}</span>
          {parsePreview.event_type ? <span>{String(parsePreview.event_type)}</span> : null}
        </p>
      ) : null}

      <div className="prospective-inquiry-panel__row prospective-inquiry-panel__actions">
        <label>
          {t('inquiry.panel.mode.label')}
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'full' | 'lite')}
            data-testid="inquiry-mode"
          >
            <option value="full">{t('inquiry.panel.mode.full')}</option>
            <option value="lite">{t('inquiry.panel.mode.lite')}</option>
          </select>
        </label>
        <label className="prospective-inquiry-panel__check">
          <input
            type="checkbox"
            checked={forceRefresh}
            onChange={(e) => setForceRefresh(e.target.checked)}
          />
          {t('inquiry.panel.forceRefresh')}
        </label>
        <label className="prospective-inquiry-panel__check">
          <input
            type="checkbox"
            checked={autoRerun}
            onChange={(e) => setAutoRerun(e.target.checked)}
          />
          {t('inquiry.panel.autoRerun')}
          <input
            type="number"
            min={1}
            max={168}
            value={rerunHours}
            onChange={(e) => setRerunHours(Number(e.target.value) || 24)}
            disabled={!autoRerun}
            className="prospective-inquiry-panel__hours"
          />
          {t('inquiry.panel.hoursSuffix')}
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={question.trim().length < 15 || runMutation.isPending}
          onClick={() => runMutation.mutate()}
          data-testid="inquiry-launch"
        >
          {runMutation.isPending ? t('inquiry.panel.launch.running') : t('inquiry.panel.launch')}
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
            {rerunMutation.isPending
              ? t('inquiry.panel.rerun.running')
              : t('inquiry.panel.rerun', { id: exportId })}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={scheduleMutation.isPending}
            onClick={() => scheduleMutation.mutate({ inquiryId: exportId, enabled: true })}
          >
            {t('inquiry.panel.scheduler.enable')}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={scheduleMutation.isPending}
            onClick={() => scheduleMutation.mutate({ inquiryId: exportId, enabled: false })}
          >
            {t('inquiry.panel.scheduler.disable')}
          </button>
        </div>
      )}

      {steps.length > 0 && (
        <div className="prospective-inquiry-panel__steps" data-testid="inquiry-steps">
          <h4>{t('inquiry.panel.steps.title')}</h4>
          <ul>
            {steps.map((s) => {
              const statusKey = (s.cached ? 'cached' : s.status || 'pending')
                .toLowerCase()
                .replace(/\s+/g, '_')
              return (
                <li
                  key={s.step}
                  className={`prospective-inquiry-panel__step prospective-inquiry-panel__step--${statusKey}`}
                >
                  <strong>{s.step}</strong>
                  <span className="prospective-inquiry-panel__step-status">{s.status}</span>
                  {s.cached ? (
                    <span className="prospective-inquiry-panel__step-status">{t('inquiry.panel.steps.cached')}</span>
                  ) : null}
                  {s.detail ? (
                    <span className="prospective-inquiry-panel__step-detail">{s.detail}</span>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {showGodetGuide && (
        <div className="prospective-inquiry-panel__godet" data-testid="inquiry-awaiting-godet">
          <h4>{t('inquiry.panel.godet.title')}</h4>
          <p className="prospective-inquiry-panel__sub">{t('inquiry.panel.godet.subtitle')}</p>
          <ul className="prospective-inquiry-panel__godet-list">
            {GODET_CHECKLIST.map((step) => {
              const done = Boolean(godetStatus?.checklist?.[step.key])
              return (
                <li
                  key={step.key}
                  className={`prospective-inquiry-panel__godet-item${done ? ' prospective-inquiry-panel__godet-item--done' : ''}`}
                >
                  <span className="prospective-inquiry-panel__godet-label">{t(step.labelKey)}</span>
                  <span className="prospective-inquiry-panel__godet-state">
                    {done ? t('inquiry.panel.godet.done') : t('inquiry.panel.godet.pending')}
                  </span>
                  {!done && (
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => openGodetStep(step.path)}
                    >
                      {t('inquiry.panel.godet.open')}
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
          {godetStatus?.missing_steps?.length ? (
            <p className="prospective-inquiry-panel__sub" data-testid="inquiry-godet-missing">
              {t('inquiry.panel.godet.missing', { steps: godetStatus.missing_steps.join(', ') })}
            </p>
          ) : null}
          <div className="prospective-inquiry-panel__godet-actions">
            {synthTargetId && (
              <button
                type="button"
                className={`btn ${canSynthesize ? 'btn-primary' : 'btn-secondary'}`}
                disabled={synthMutation.isPending || !canSynthesize}
                onClick={() => synthMutation.mutate(synthTargetId)}
                data-testid="inquiry-synthesize"
              >
                {synthMutation.isPending
                  ? t('inquiry.panel.synthesize.running')
                  : canSynthesize
                    ? t('inquiry.panel.synthesize', { id: synthTargetId })
                    : t('inquiry.panel.synthesize.waitGodet')}
              </button>
            )}
            {synthTargetId && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void openWizard(synthTargetId, godetStatus?.project_id ?? wizardProjectId)}
              >
                {t('inquiry.panel.godet.wizardMorph')}
              </button>
            )}
          </div>
        </div>
      )}

      {morphPreview.length > 0 && (
        <details open className="prospective-inquiry-panel__morph">
          <summary>{t('inquiry.panel.morph.summary')}</summary>
          <table>
            <thead>
              <tr>
                <th>{t('inquiry.panel.morph.col.scenario')}</th>
                <th>{t('inquiry.panel.morph.col.config')}</th>
                <th>{t('inquiry.panel.morph.col.possibility')}</th>
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
                {wizardMutation.isPending
                  ? t('inquiry.panel.morph.seeding')
                  : t('inquiry.panel.morph.applyWizard')}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void openWizard(exportId, wizardProjectId)}
              >
                {t('inquiry.panel.wizard.openMorph')}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={heatmapMutation.isPending}
                onClick={() => heatmapMutation.mutate(exportId)}
              >
                {t('inquiry.panel.morph.loadHeatmap')}
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
          <h4>{t('inquiry.panel.answer.title')}</h4>
          <p>
            {t('inquiry.panel.answer.probability')}: {String(answer.probability_pct ?? '—')}% ·{' '}
            {t('inquiry.panel.answer.possibility')}: {String(answer.possibility ?? '—')}
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
                  {r.because ? ` — ${t('inquiry.panel.answer.why')} ${r.because}` : ''}
                </li>
              ))}
            </ul>
          )}
          {conclusions.length > 0 && (
            <div>
              <h5>{t('inquiry.panel.answer.conclusions')}</h5>
              <ul>
                {conclusions.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {traceInquiryId && (
        <details open className="prospective-inquiry-panel__trace">
          <summary>{t('inquiry.panel.trace.title', { id: traceInquiryId })}</summary>
          <InquiryTracePanel
            scopeAudit={(scopeAuditData as ScopeAuditData | undefined) ?? scopeAuditLive ?? undefined}
            auditTrail={(auditData?.audit_trail as AuditTrailEntry[]) ?? []}
            evidence={evidence}
            reasoning={reasoning}
            godetStatus={
              (godetStatusData as {
                godet_ready?: boolean
                project_id?: number | null
                checklist?: Record<string, boolean>
                missing_steps?: string[]
                can_synthesize?: boolean
              }) ?? null
            }
            onSynthesize={() => synthMutation.mutate(traceInquiryId)}
            synthesizePending={synthMutation.isPending}
          />
        </details>
      )}

      {exportId && (
        <p className="prospective-inquiry-panel__export">
          <a
            href={prospectiveInquiryService.exportHtmlUrl(exportId)}
            target="_blank"
            rel="noreferrer"
          >
            {t('inquiry.panel.export.html', { id: exportId })}
          </a>
          {' · '}
          <a
            href={prospectiveInquiryService.exportPdfUrl(exportId)}
            target="_blank"
            rel="noreferrer"
          >
            {t('inquiry.panel.export.pdf')}
          </a>
        </p>
      )}

      {((compareData?.items as InquiryCompareItem[] | undefined)?.length ?? 0) >= 2 && (
        <details open className="prospective-inquiry-panel__compare">
          <summary>{t('inquiry.panel.compare.title', { count: compareData?.count ?? 0 })}</summary>
          <InquiryComparePanel
            items={(compareData?.items as InquiryCompareItem[]) ?? []}
            probabilitySeries={
              (compareData?.probability_series as Array<{ id: number; probability_pct: number }>) ?? []
            }
            onOpenWizard={(id, pid) => void openWizard(id, pid)}
          />
        </details>
      )}

      {inquiries.length > 0 && (
        <details>
          <summary>{t('inquiry.panel.history.titleWithCount', { count: inquiries.length })}</summary>
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
