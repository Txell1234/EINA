import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { casesService } from '../../services/api'
import type { RegistryCompany } from './CaseCompaniesPanel'
import {
  FinancialInvestWatchReport,
  type InvestWatchReport,
} from './FinancialInvestWatchReport'
import { FinancialCrossoverHero } from './FinancialCrossoverHero'
import { GeopoliticalConfidencePanel } from './GeopoliticalConfidencePanel'
import './FinancialCrossoverPanel.css'
import './FinancialCrossoverHero.css'

type FinancialCrossoverPanelProps = {
  caseId: number
  focusCompany?: string | null
  focusTicker?: string | null
  projectId?: number | null
  registryCompanies?: RegistryCompany[]
}

type ParsePreview = {
  parse_status?: string
  parse_mode?: string
  company_name?: string
  primary_ticker?: string
  suggested_ticker?: string
  primary_recommendation?: string
  needs_llm_narrative?: boolean
  llm_narrative_reason?: string
  parse_warning?: string
  parse_quality?: string
  derived_signal?: string
  praams_ratio?: number
  fair_value_upside_pct?: number
  return_factors_count?: number
  risk_factors_count?: number
  investwatch_report?: InvestWatchReport
}

type EvidenceRow = {
  kind?: string
  label?: string
  value?: string | number | null
  origin?: string
  because?: string
}

type ReasoningRow = {
  id?: string
  conclusion?: string
  because?: string
  formula?: string
  sources?: Array<{ origin?: string; field?: string; value?: unknown; label?: string; excerpt?: string }>
}

type AlignmentRow = {
  summary?: string
  because?: string
  sources?: ReasoningRow['sources']
}

type NumberExplanation = {
  value?: number
  because?: string
  formula?: string
  sources?: ReasoningRow['sources']
}

const SAMPLE_HINT = `Enganxa text d'InvestWatch/PRAAMS amb puntuacions 1-7, percentatges o recomanacions BUY/HOLD/SELL tal com apareixen a l'informe.`

const AI_NARRATIVE_PREF_KEY = 'eina.financial.interpretNarrative'

type AiNarrativeMode = 'auto' | 'off' | 'on'

function loadAiNarrativePref(): AiNarrativeMode {
  try {
    const saved = localStorage.getItem(AI_NARRATIVE_PREF_KEY)
    if (saved === 'auto' || saved === 'off' || saved === 'on') return saved
  } catch {
    /* localStorage unavailable */
  }
  return 'off'
}

const AI_MODE_LABELS: Record<AiNarrativeMode, { title: string; detail: string }> = {
  off: {
    title: 'Sense IA',
    detail: 'Només regles i parser. Recomanacions i creuament sense cridar cap model.',
  },
  auto: {
    title: 'IA automàtica',
    detail: 'Sense IA si InvestWatch/PRAAMS té prou dades; IA només per resumir text desestructurat.',
  },
  on: {
    title: 'Sempre IA',
    detail: 'Demana IA per resumir l\'informe en català (números i accions continuen per regles).',
  },
}

const ENTITY_ORIGIN_LABELS: Record<string, string> = {
  godet_actor: 'Actor Godet',
  policy_industry: 'Policy×Indústria',
  inquiry: 'Q2FS',
  osint: 'OSINT',
  reference: 'Referència',
}

function entityKindLabel(company: RegistryCompany): string {
  const origins = company.origins ?? []
  if (origins.includes('godet_actor') && !origins.includes('policy_industry')) {
    return 'Actor'
  }
  return 'Empresa'
}

const SOURCE_LABELS_UI: Record<string, string> = {
  informe_extern: 'Informe extern',
  eina_report_link: 'Vinculació EINA',
  eina_synthesis: 'Síntesi EINA',
  eina_investments: 'Inversions EINA',
  eina_policy_industry: 'Policy×Indústria',
  llm_narrative: 'Narrativa IA',
  eina_internal_fallback: 'Referència interna EINA',
  eina_scenarios: 'Escenaris Godet',
}

function ActionJustification({
  justification,
  because,
  sourceLabel,
  source,
}: {
  justification?: string
  because?: string
  sourceLabel?: string
  source?: string
}) {
  const brief = justification || because
  if (!brief) return null
  const src = sourceLabel || (source ? SOURCE_LABELS_UI[source] ?? source : null)
  return (
    <div className="financial-crossover-panel__justification">
      <p>
        <strong>Justificació:</strong> {brief}
      </p>
      {because && justification && because !== justification ? (
        <p className="financial-crossover-panel__justification-detail">{because}</p>
      ) : null}
      {src ? <span className="financial-crossover-panel__source-chip">{src}</span> : null}
    </div>
  )
}

const ORIGIN_LABELS: Record<string, string> = {
  informe_extern: 'Informe extern',
  eina_prospective: 'EINA · Escenaris',
  eina_investments: 'EINA · Inversions',
  eina_smic: 'EINA · SMIC',
  eina_policy_industry: 'EINA · Policy×Indústria',
}

export default function FinancialCrossoverPanel({
  caseId,
  focusCompany = null,
  focusTicker = null,
  projectId = null,
  registryCompanies = [],
}: FinancialCrossoverPanelProps) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [source, setSource] = useState('praams')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [externalWeight, setExternalWeight] = useState(0.35)
  const [interpretNarrative, setInterpretNarrative] = useState<AiNarrativeMode>(loadAiNarrativePref)
  const [referenceEntity, setReferenceEntity] = useState('')
  const [parsePreview, setParsePreview] = useState<ParsePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [crossoverResult, setCrossoverResult] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (focusCompany) setReferenceEntity(focusCompany)
  }, [focusCompany])

  const selectedEntityMeta = useMemo(
    () => registryCompanies.find((c) => c.name === referenceEntity) ?? null,
    [registryCompanies, referenceEntity],
  )

  const effectiveReference = referenceEntity.trim() || undefined

  useEffect(() => {
    if (!focusCompany) return
    setTitle((prev) => {
      if (prev.trim()) return prev
      const ticker = focusTicker ? ` (${focusTicker})` : ''
      return `${focusCompany}${ticker} — InvestWatch`
    })
  }, [focusCompany, focusTicker])

  const handleAiModeChange = (mode: AiNarrativeMode) => {
    setInterpretNarrative(mode)
    try {
      localStorage.setItem(AI_NARRATIVE_PREF_KEY, mode)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (previewTimer.current) clearTimeout(previewTimer.current)
    const trimmed = text.trim()
    if (trimmed.length < 50) {
      setParsePreview(null)
      return
    }
    previewTimer.current = setTimeout(() => {
      setPreviewLoading(true)
      void casesService
        .previewFinancialReport(caseId, {
          text: trimmed,
          source,
          title,
          focus_company: effectiveReference ?? focusCompany ?? undefined,
        })
        .then((data) => setParsePreview(data as ParsePreview))
        .catch(() => setParsePreview(null))
        .finally(() => setPreviewLoading(false))
    }, 450)
    return () => {
      if (previewTimer.current) clearTimeout(previewTimer.current)
    }
  }, [caseId, text, source, title, focusCompany, effectiveReference])

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['financial-reports', caseId],
    queryFn: () => casesService.listFinancialReports(caseId),
  })

  const uploadMutation = useMutation({
    mutationFn: () =>
      casesService.uploadFinancialReport(caseId, {
        text,
        source,
        title,
        enrich_llm: false,
        reference_entity: effectiveReference,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['financial-reports', caseId] })
      void queryClient.invalidateQueries({ queryKey: ['case-workspace', caseId] })
      setText('')
    },
  })

  const fileMutation = useMutation({
    mutationFn: (file: File) =>
      casesService.uploadFinancialReportFile(caseId, file, {
        source,
        title,
        enrich_llm: false,
        reference_entity: effectiveReference,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['financial-reports', caseId] })
    },
  })

  const crossoverMutation = useMutation({
    mutationFn: (payload: { report_id?: number; text?: string }) =>
      casesService.runFinancialCrossover(caseId, {
        ...payload,
        source,
        external_weight: externalWeight,
        enrich_llm: false,
        interpret_narrative: interpretNarrative,
        focus_company: effectiveReference ?? focusCompany ?? undefined,
        project_id: projectId ?? undefined,
      }),
    onSuccess: (data) => setCrossoverResult(data),
  })

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) fileMutation.mutate(file)
    e.target.value = ''
  }

  const crossover = crossoverResult?.crossover as Record<string, unknown> | undefined
  const numberExplanations = crossover?.final_numbers_explanations as Record<string, NumberExplanation> | undefined
  const externalEvidence = (crossover?.external_evidence as EvidenceRow[]) ?? []
  const einaEvidence = (crossover?.eina_evidence as EvidenceRow[]) ?? []
  const reasoning = (crossover?.reasoning as ReasoningRow[]) ?? []
  const alignments = (crossover?.alignments as AlignmentRow[]) ?? []
  const divergences = (crossover?.divergences as AlignmentRow[]) ?? []
  const suggestedActions =
    (crossover?.suggested_actions as Array<{
      action?: string
      horizon?: string
      because?: string
      source?: string
      company?: string
    }>) ?? []

  type TierRec = {
    tier?: string
    tier_label?: string
    action?: string
    target?: string
    ticker?: string | null
    horizon?: string
    confidence?: string
    weight?: string
    because?: string
    justification?: string
    source?: string
    source_label?: string
  }

  const tiered = crossover?.tiered_recommendations as
    | {
        summary?: string
        external_signal?: string
        focus_entity?: string
        private?: TierRec[]
        public?: TierRec[]
        industries?: TierRec[]
        satellites?: TierRec[]
      }
    | undefined

  const tierSections: Array<{ key: string; title: string; items: TierRec[] }> = [
    { key: 'private', title: 'Inversió privada', items: tiered?.private ?? [] },
    { key: 'public', title: 'Sector públic', items: tiered?.public ?? [] },
    { key: 'industries', title: 'Indústries', items: tiered?.industries ?? [] },
    { key: 'satellites', title: 'Satèl·lits', items: tiered?.satellites ?? [] },
  ]

  const investwatchReport =
    (crossover?.investwatch_report as InvestWatchReport | undefined) ||
    (parsePreview?.investwatch_report as InvestWatchReport | undefined)

  const reportContextNarrative = String(
    (crossoverResult?.report_context as Record<string, unknown> | undefined)?.narrative ?? '',
  )
  const fullInvestwatchReport: InvestWatchReport | undefined = investwatchReport
    ? {
        ...investwatchReport,
        narrative:
          investwatchReport.narrative ||
          (crossover ? reportContextNarrative : investwatchReport.narrative),
        narrative_source:
          investwatchReport.narrative_source ||
          String(
            (crossoverResult?.report_context as Record<string, unknown> | undefined)
              ?.narrative_source ?? 'rules',
          ),
      }
    : undefined

  const finalNumbers = crossover?.final_numbers as
    | {
        blended_return_index?: number
        blended_risk_index?: number
        external_return_index?: number
        external_risk_index?: number
        eina_investment_confidence_avg?: number
        geopolitical_confidence_index?: number
        crossover_score_10?: number
      }
    | undefined

  const einaCaseSummary = crossover?.eina_case_summary as
    | {
        investment_recommendation?: string
        investment_confidence_pct?: number
        investment_rationale?: string
        investment_posture_source?: string
        investment_posture_detail?: string
        geopolitical_confidence_index?: number | null
        geopolitical_confidence_components?: Array<{
          name?: string
          label?: string
          value?: number
          weight?: number
          base_weight?: number
          because?: string
        }>
        geopolitical_confidence_formula?: string
        gpr_case_level?: number | null
        gpr_multiplier_applied?: number | null
        eina_gma?: number | null
        eina_gma_formula?: string
        sanction_impact_score?: number | null
        sanction_drivers?: Array<{ type?: string; excerpt?: string; weight?: number }>
        sanction_entity_impacts?: Array<{
          entity?: string
          entity_type?: string
          score?: number
          prob_adjust_pp?: number
          because?: string
        }>
        sanction_scenario_adjustments?: Record<string, number>
        sanction_trend_signals?: string[]
        eina_confidence_source?: string
        eina_confidence_detail?: string
        eina_confidence_pct?: number
        scenario_count?: number
        tense_scenarios?: string[]
        osint_signals?: {
          avg_geopolitical_risk?: number
          hostility_ratio?: number
          conflict_events?: number
          countries_at_risk?: number
        }
      }
    | undefined

  const geoFinParagraphs = (
    tiered as { geopolitical_financial_synthesis?: { paragraphs?: string[] } } | undefined
  )?.geopolitical_financial_synthesis?.paragraphs

  const einaOverlay = fullInvestwatchReport?.eina_overlay

  return (
    <section className="financial-crossover-panel card">
      <header className="financial-crossover-panel__header">
        <div>
          <h3>Informes financers × EINA</h3>
          <p className="financial-crossover-panel__sub">
            Creua informes (PRAAMS, DeGiro, research, PDF) amb escenaris, SMIC, inversions i
            Policy×Indústria. El creuament i les recomanacions funcionen sense IA; tu tries si vols
            resum narratiu amb model.
          </p>
          {focusCompany ? (
            <p className="financial-crossover-panel__focus">
              Empresa focus: <strong>{focusCompany}</strong>
              {focusTicker ? ` · ticker ${focusTicker}` : null}
            </p>
          ) : null}
          <span
            className={`financial-crossover-panel__badge ${
              interpretNarrative === 'off'
                ? 'financial-crossover-panel__badge--rules'
                : interpretNarrative === 'on'
                  ? 'financial-crossover-panel__badge--llm'
                  : ''
            }`}
          >
            {interpretNarrative === 'off'
              ? 'Mode: sense IA'
              : interpretNarrative === 'on'
                ? 'Mode: IA activa'
                : 'Mode: IA automàtica'}
          </span>
        </div>
      </header>

      <div className="financial-crossover-panel__form">
        <fieldset className="financial-crossover-panel__ai-choice" aria-label="Ús d'intel·ligència artificial">
          <legend>Vols usar IA per resumir l&apos;informe?</legend>
          <p className="financial-crossover-panel__ai-note">
            El <strong>creuament</strong>, els <strong>números</strong> i les <strong>accions</strong> es
            calculen sempre per regles. La IA només afecta el text «De què va l&apos;informe» (opcional).
          </p>
          <div className="financial-crossover-panel__ai-options">
            {(['off', 'auto', 'on'] as const).map((mode) => (
              <label
                key={mode}
                className={`financial-crossover-panel__ai-option ${
                  interpretNarrative === mode ? 'active' : ''
                }`}
              >
                <input
                  type="radio"
                  name="interpret-narrative"
                  value={mode}
                  checked={interpretNarrative === mode}
                  onChange={() => handleAiModeChange(mode)}
                />
                <span className="financial-crossover-panel__ai-option-title">
                  {AI_MODE_LABELS[mode].title}
                </span>
                <span className="financial-crossover-panel__ai-option-detail">
                  {AI_MODE_LABELS[mode].detail}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="financial-crossover-panel__row">
          <label className="financial-crossover-panel__entity-label">
            Empresa o actor de referència
            <select
              value={referenceEntity}
              onChange={(e) => setReferenceEntity(e.target.value)}
              aria-label="Empresa o actor al qual es refereix l'informe"
            >
              <option value="">Automàtic (parser + títol)</option>
              {registryCompanies.map((c) => (
                <option key={c.key || c.name} value={c.name}>
                  [{entityKindLabel(c)}] {c.name}
                  {c.ticker ? ` · ${c.ticker}` : ''}
                  {(c.origins ?? []).length
                    ? ` (${(c.origins ?? []).map((o) => ENTITY_ORIGIN_LABELS[o] ?? o).join(', ')})`
                    : ''}
                </option>
              ))}
            </select>
          </label>
        </div>
        {selectedEntityMeta ? (
          <p className="financial-crossover-panel__entity-note">
            Les dades d&apos;aquest informe es referenciaran com a{' '}
            <strong>{selectedEntityMeta.name}</strong> ({entityKindLabel(selectedEntityMeta)}). El
            creuament continuarà usant <strong>tot el cas EINA</strong> (escenaris, SMIC, inversions).
          </p>
        ) : referenceEntity ? (
          <p className="financial-crossover-panel__entity-note">
            Referència manual: <strong>{referenceEntity}</strong>. Creuament amb tot el cas EINA.
          </p>
        ) : (
          <p className="financial-crossover-panel__entity-note financial-crossover-panel__entity-note--muted">
            Sense referència explícita — el parser intentarà detectar l&apos;empresa. Selecciona una
            entitat del registre per vincular l&apos;informe.
          </p>
        )}

        <div className="financial-crossover-panel__row">
          <label>
            Font
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="praams">PRAAMS / InvestWatch</option>
              <option value="degiro">DeGiro / informe broker</option>
              <option value="bloomberg">Bloomberg / research</option>
              <option value="custom">Altres</option>
            </select>
          </label>
          <label>
            Títol (recomanat)
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={
                focusCompany
                  ? `${focusCompany}${focusTicker ? ` (${focusTicker})` : ''} — InvestWatch`
                  : 'Ex. Kawasaki Heavy Industries (7012.T) — InvestWatch'
              }
            />
          </label>
        </div>

        <textarea
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={SAMPLE_HINT}
        />

        {parsePreview && text.trim().length >= 50 ? (
          <div className="financial-crossover-panel__preview" data-testid="financial-parse-preview">
            <h4>Vista prèvia del parser</h4>
            {previewLoading ? <p className="financial-crossover-panel__preview-muted">Actualitzant…</p> : null}
            <p>
              {parsePreview.company_name || effectiveReference ? (
                <>
                  Aquest informe sembla sobre:{' '}
                  <strong>{effectiveReference || parsePreview.company_name}</strong>
                  {parsePreview.primary_ticker ? ` (${parsePreview.primary_ticker})` : null}
                  {effectiveReference &&
                  parsePreview.company_name &&
                  effectiveReference !== parsePreview.company_name ? (
                    <span className="financial-crossover-panel__preview-muted">
                      {' '}
                      · parser detecta «{parsePreview.company_name}»
                    </span>
                  ) : null}
                </>
              ) : (
                'Empresa no detectada — selecciona-la al desplegable o al registre del cas.'
              )}
            </p>
            {parsePreview.primary_recommendation ? (
              <p>Recomanació detectada: <strong>{parsePreview.primary_recommendation}</strong></p>
            ) : null}
            {parsePreview.parse_mode === 'investwatch' || parsePreview.parse_mode === 'praams_investwatch' ? (
              <p>
                {parsePreview.parse_mode === 'praams_investwatch' ? 'PRAAMS InvestWatch PDF' : 'InvestWatch'}:{' '}
                {parsePreview.return_factors_count ?? 0} factors retorn ·{' '}
                {parsePreview.risk_factors_count ?? 0} factors risc
                {parsePreview.praams_ratio != null ? ` · Ratio ${parsePreview.praams_ratio}/7` : ''}
              </p>
            ) : null}
            {parsePreview.investwatch_report?.has_clock ? (
              <FinancialInvestWatchReport report={parsePreview.investwatch_report} compact showNarrative={false} />
            ) : null}
            {parsePreview.needs_llm_narrative && interpretNarrative === 'off' ? (
              <p className="financial-crossover-panel__preview-warn">
                Aquest text costaria d&apos;interpretar sense IA. Activa «IA automàtica» o «Sempre IA» si
                vols un resum narratiu.
              </p>
            ) : null}
            {parsePreview.needs_llm_narrative && interpretNarrative !== 'off' ? (
              <p className="financial-crossover-panel__preview-hint">
                El creuament pot demanar IA per resumir la narrativa ({parsePreview.llm_narrative_reason}).
              </p>
            ) : null}
            {parsePreview.parse_warning ? (
              <p className="financial-crossover-panel__preview-warn">{parsePreview.parse_warning}</p>
            ) : null}
            {parsePreview.parse_quality && parsePreview.parse_quality !== 'good' ? (
              <p className="financial-crossover-panel__preview-warn">
                Qualitat parseig: {parsePreview.parse_quality}
                {parsePreview.derived_signal
                  ? ` · senyal inferit: ${parsePreview.derived_signal}`
                  : ''}
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="financial-crossover-panel__actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={text.trim().length < 50 || uploadMutation.isPending}
            onClick={() => uploadMutation.mutate()}
          >
            {uploadMutation.isPending ? 'Desant…' : 'Desar informe'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => fileRef.current?.click()}>
            Pujar fitxer (.txt, .pdf)
          </button>
          <input ref={fileRef} type="file" accept=".txt,.md,.pdf,.html,.csv" hidden onChange={handleFile} />
        </div>

        <label className="financial-crossover-panel__weight">
          Pes informe extern en números finals: {Math.round(externalWeight * 100)}%
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={externalWeight}
            onChange={(e) => setExternalWeight(parseFloat(e.target.value))}
          />
        </label>
      </div>

      {!isLoading && reports.length > 0 && (
        <div className="financial-crossover-panel__reports">
          <h4>Informes desats</h4>
          <ul>
            {(reports as Array<{
              id: number
              title?: string
              source: string
              parse_status: string
              reference_entity?: string
              company_name?: string
              suggested_ticker?: string
            }>).map((r) => (
              <li key={r.id}>
                <span>
                  #{r.id} — {r.title || r.source} ({r.parse_status})
                  {r.reference_entity ? (
                    <span className="financial-crossover-panel__report-entity">
                      {' '}
                      · Ref: {r.reference_entity}
                      {r.suggested_ticker ? ` (${r.suggested_ticker})` : ''}
                    </span>
                  ) : r.company_name ? (
                    <span className="financial-crossover-panel__report-entity">
                      {' '}
                      · Detectat: {r.company_name}
                    </span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={crossoverMutation.isPending}
                  onClick={() => crossoverMutation.mutate({ report_id: r.id })}
                >
                  Creuar
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {text.trim().length >= 50 && (
        <button
          type="button"
          className="btn btn-primary financial-crossover-panel__cross-inline"
          disabled={crossoverMutation.isPending}
          onClick={() => crossoverMutation.mutate({ text })}
        >
          {crossoverMutation.isPending ? 'Creuant…' : 'Crear crossover sense desar'}
        </button>
      )}

      {crossoverMutation.isError && (
        <p className="financial-crossover-panel__msg financial-crossover-panel__msg--error">
          Error en el crossover:{' '}
          {(crossoverMutation.error as Error)?.message ||
            'Comprova la sessió (torna a login) i que hi ha dades EINA al cas.'}
        </p>
      )}

      {uploadMutation.isSuccess && (
        <p className="financial-crossover-panel__msg financial-crossover-panel__msg--ok">
          Informe desat correctament.
        </p>
      )}

      {uploadMutation.isError && (
        <p className="financial-crossover-panel__msg financial-crossover-panel__msg--error">
          Error desant informe: {(uploadMutation.error as Error)?.message}
        </p>
      )}

      {crossover && (
        <div className="financial-crossover-panel__results">
          {(crossoverResult?.crossover_scope as Record<string, unknown> | undefined)?.note ||
          crossover.scope_note ? (
            <details className="financial-crossover-panel__scope" data-testid="crossover-scope">
              <summary>Abast del creuament</summary>
              <p>
                {String(
                  (crossoverResult?.crossover_scope as Record<string, unknown> | undefined)?.note ||
                    crossover.scope_note,
                )}
              </p>
              {(crossoverResult?.reference_entity as string | undefined) ||
              (crossoverResult?.crossover_scope as { external_entity?: string } | undefined)
                ?.external_entity ? (
                <p className="financial-crossover-panel__scope-entity">
                  Dades externes:{' '}
                  <strong>
                    {String(
                      (crossoverResult?.crossover_scope as { external_entity?: string })
                        ?.external_entity || crossoverResult?.reference_entity,
                    )}
                  </strong>
                  {' · '}
                  Context EINA: <strong>tot el cas</strong>
                </p>
              ) : null}
            </details>
          ) : null}

          <FinancialCrossoverHero
            entity={tiered?.focus_entity || fullInvestwatchReport?.company}
            externalSignal={tiered?.external_signal || fullInvestwatchReport?.recommendation}
            einaRecommendation={einaCaseSummary?.investment_recommendation}
            privateAction={tiered?.private?.[0]?.action}
            finalNumbers={finalNumbers}
            synthesisParagraphs={geoFinParagraphs}
            alignments={alignments}
            divergences={divergences}
            confidenceSource={einaCaseSummary?.eina_confidence_source}
            confidenceDetail={einaCaseSummary?.eina_confidence_detail}
            geopoliticalConfidenceIndex={
              einaCaseSummary?.entity_confidence_index ??
              einaCaseSummary?.geopolitical_confidence_index ??
              einaCaseSummary?.eina_confidence_pct
            }
            caseGeopoliticalConfidenceIndex={einaCaseSummary?.case_geopolitical_confidence_index}
            entityGeopoliticalConfidenceIndex={einaCaseSummary?.entity_confidence_index}
            entityIcgDelta={einaCaseSummary?.entity_icg_delta}
            investmentPostureSource={einaCaseSummary?.investment_posture_source}
          />

          <GeopoliticalConfidencePanel summary={einaCaseSummary} />

          <div className="financial-crossover-panel__recommendations-block">
            {suggestedActions.length > 0 && (
              <div className="financial-crossover-panel__actions-block">
                <h4>Accions del creuament</h4>
                <ul className="financial-crossover-panel__actions-list">
                  {suggestedActions.map((act, i) => (
                    <li key={`${act.action}-${i}`}>
                      <strong>{act.action}</strong>
                      {act.horizon ? (
                        <span className="financial-crossover-panel__horizon"> · {act.horizon}</span>
                      ) : null}
                      {act.company ? <span> · {act.company}</span> : null}
                      <ActionJustification
                        justification={(act as { justification?: string }).justification}
                        because={act.because}
                        source={(act as { source?: string }).source}
                        sourceLabel={(act as { source_label?: string }).source_label}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {tiered ? (
              <div className="financial-crossover-panel__tiered" data-testid="tiered-recommendations">
                <h4>Recomanacions per capes</h4>
                {tiered.summary ? (
                  <p className="financial-crossover-panel__tiered-summary">{tiered.summary}</p>
                ) : null}
                {tiered.external_signal && tiered.focus_entity ? (
                  <p className="financial-crossover-panel__tiered-meta">
                    Senyal extern <strong>{tiered.external_signal}</strong> · focus{' '}
                    <strong>{tiered.focus_entity}</strong>
                  </p>
                ) : null}

                {(tiered as { industry_implications?: Array<Record<string, unknown>> }).industry_implications
                  ?.length ? (
                  <div className="financial-crossover-panel__industry-implications">
                    <h5>Implicacions per indústria</h5>
                    <div className="financial-crossover-panel__industry-grid">
                      {(
                        tiered as {
                          industry_implications: Array<Record<string, string | string[] | undefined>>
                        }
                      ).industry_implications.map((imp) => (
                        <article
                          key={String(imp.sector)}
                          className="financial-crossover-panel__industry-card"
                        >
                          <h5>{String(imp.sector_label || imp.sector)}</h5>
                          {imp.financial_read ? (
                            <p>
                              <strong>Finances:</strong> {String(imp.financial_read)}
                            </p>
                          ) : null}
                          {imp.geopolitical_read ? (
                            <p>
                              <strong>Geopolítica:</strong> {String(imp.geopolitical_read)}
                            </p>
                          ) : null}
                          {imp.suggested_play ? (
                            <p className="financial-crossover-panel__industry-play">
                              <strong>Acció sectorial:</strong> {String(imp.suggested_play)}
                            </p>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="financial-crossover-panel__tiered-grid">
                  {tierSections.map((section) => (
                    <section
                      key={section.key}
                      className={`financial-crossover-panel__tier-col financial-crossover-panel__tier-col--${section.key}`}
                    >
                      <h5>{section.title}</h5>
                      {section.items.length === 0 ? (
                        <p className="financial-crossover-panel__tier-empty">—</p>
                      ) : (
                        <ul>
                          {section.items.map((item) => (
                            <li key={`${section.key}-${item.target}-${item.action}`}>
                              <strong>{item.action}</strong>
                              {item.target ? ` · ${item.target}` : null}
                              {item.ticker ? ` (${item.ticker})` : null}
                              {item.horizon ? (
                                <span className="financial-crossover-panel__horizon"> · {item.horizon}</span>
                              ) : null}
                              {item.confidence ? (
                                <span className="financial-crossover-panel__tier-conf">
                                  {' '}
                                  · conf. {item.confidence}
                                </span>
                              ) : null}
                              <ActionJustification
                                justification={item.justification}
                                because={item.because}
                                source={item.source}
                                sourceLabel={item.source_label}
                              />
                            </li>
                          ))}
                        </ul>
                      )}
                    </section>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          {fullInvestwatchReport?.has_clock || fullInvestwatchReport?.company ? (
            <section className="financial-crossover-panel__source-section">
              <h4>
                Anàlisi informe extern
                <span className="financial-crossover-panel__source-tag financial-crossover-panel__source-tag--external">
                  PRAAMS / extern
                </span>
              </h4>
              <div className="financial-crossover-panel__report-card">
                <FinancialInvestWatchReport
                  report={fullInvestwatchReport}
                  variant="external"
                  showNarrative
                />
              </div>
            </section>
          ) : (crossoverResult?.report_context as Record<string, unknown> | undefined)?.narrative ? (
            <section className="financial-crossover-panel__source-section">
              <h4>
                Anàlisi informe extern
                <span className="financial-crossover-panel__source-tag financial-crossover-panel__source-tag--external">
                  Text enganxat
                </span>
              </h4>
              <div className="financial-crossover-panel__report-context">
                {(crossoverResult?.report_context as Record<string, unknown>)?.narrative_source === 'llm' ? (
                  <span className="financial-crossover-panel__badge financial-crossover-panel__badge--llm">
                    Resum IA
                  </span>
                ) : (
                  <span className="financial-crossover-panel__badge">Resum per regles</span>
                )}
                <p>{String((crossoverResult?.report_context as Record<string, unknown>).narrative)}</p>
              </div>
            </section>
          ) : null}

          <section className="financial-crossover-panel__source-section">
            <h4>
              Context EINA del cas
              <span className="financial-crossover-panel__source-tag financial-crossover-panel__source-tag--eina">
                Godet · OSINT · Policy
              </span>
            </h4>
            <div className="financial-crossover-panel__eina-context">
              <div className="financial-crossover-panel__eina-stats">
                {einaCaseSummary?.eina_confidence_pct != null ? (
                  <div className="financial-crossover-panel__eina-stat">
                    <strong>Confiança calculada:</strong> {einaCaseSummary.eina_confidence_pct}%
                    {einaCaseSummary.eina_confidence_source === 'computed' ? ' (OSINT/escenaris)' : null}
                  </div>
                ) : null}
                {einaCaseSummary?.investment_confidence_pct != null ? (
                  <div className="financial-crossover-panel__eina-stat">
                    <strong>Recomanació inversió (cas):</strong> {einaCaseSummary.investment_recommendation}{' '}
                    ({einaCaseSummary.investment_confidence_pct}%)
                  </div>
                ) : null}
                {einaCaseSummary?.scenario_count != null ? (
                  <div className="financial-crossover-panel__eina-stat">
                    <strong>Escenaris Godet:</strong> {einaCaseSummary.scenario_count}
                  </div>
                ) : null}
              </div>
              {einaCaseSummary?.eina_confidence_detail ? (
                <p className="financial-crossover-panel__eina-confidence-detail">
                  {einaCaseSummary.eina_confidence_detail}
                </p>
              ) : null}
              {einaOverlay?.policy_link ? (
                <p>
                  <strong>Policy×Indústria:</strong> {einaOverlay.policy_link}
                </p>
              ) : null}
              {einaOverlay?.beneficiary_rationale ? (
                <p>{einaOverlay.beneficiary_rationale}</p>
              ) : null}
              {(einaCaseSummary?.tense_scenarios?.length ?? 0) > 0 ? (
                <p>
                  <strong>Escenaris de tensió:</strong> {einaCaseSummary!.tense_scenarios!.join(', ')}
                </p>
              ) : null}
              {(einaOverlay?.sectors?.length ?? 0) > 0 ? (
                <p>
                  <strong>Sectors mapa industrial:</strong> {einaOverlay!.sectors!.join(', ')}
                </p>
              ) : null}
            </div>
          </section>

          {typeof crossover.note === 'string' && (
            <p className="financial-crossover-panel__method-note">{crossover.note}</p>
          )}

          {externalEvidence.length > 0 && (
            <details className="financial-crossover-panel__evidence" open>
              <summary>Dades extretes de l&apos;informe ({externalEvidence.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Camp</th>
                    <th>Valor</th>
                    <th>Per què comptem aquesta dada</th>
                  </tr>
                </thead>
                <tbody>
                  {externalEvidence.map((row, i) => (
                    <tr key={`ext-${row.label}-${i}`}>
                      <td>{row.label || row.kind}</td>
                      <td>{row.value ?? '—'}</td>
                      <td>{row.because}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {einaEvidence.length > 0 && (
            <details className="financial-crossover-panel__evidence">
              <summary>Dades EINA del cas ({einaEvidence.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Origen</th>
                    <th>Camp</th>
                    <th>Valor</th>
                    <th>Per què</th>
                  </tr>
                </thead>
                <tbody>
                  {einaEvidence.map((row, i) => (
                    <tr key={`eina-${row.label}-${i}`}>
                      <td>{ORIGIN_LABELS[row.origin ?? ''] ?? row.origin}</td>
                      <td>{row.label || row.kind}</td>
                      <td>{row.value ?? '—'}</td>
                      <td>{row.because}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {numberExplanations && Object.keys(numberExplanations).length > 0 && (
            <div className="financial-crossover-panel__numbers-block">
              <h4>Números finals i el seu càlcul</h4>
              {Object.entries(numberExplanations).map(([key, expl]) => (
                <article key={key} className="financial-crossover-panel__number-card">
                  <h5>{key.replace(/_/g, ' ')}</h5>
                  <p className="financial-crossover-panel__number-value">{expl.value}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {expl.because}
                  </p>
                  {expl.formula && (
                    <p className="financial-crossover-panel__formula">
                      Fórmula: <code>{expl.formula}</code>
                    </p>
                  )}
                  {expl.sources && expl.sources.length > 0 && (
                    <ul className="financial-crossover-panel__sources">
                      {expl.sources.map((s, i) => (
                        <li key={`${s.field}-${i}`}>
                          {ORIGIN_LABELS[s.origin ?? ''] ?? s.origin}: {s.label ?? s.field} ={' '}
                          {String(s.value)}
                          {s.excerpt ? ` — «${s.excerpt.slice(0, 80)}…»` : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}

          {alignments.length > 0 && (
            <div className="financial-crossover-panel__align">
              <h5>Alineacions (amb motiu)</h5>
              {alignments.map((a) => (
                <article key={a.summary} className="financial-crossover-panel__judgment">
                  <p>{a.summary}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {a.because}
                  </p>
                </article>
              ))}
            </div>
          )}

          {divergences.length > 0 && (
            <div className="financial-crossover-panel__diverge">
              <h5>Divergències (amb motiu)</h5>
              {divergences.map((d) => (
                <article key={d.summary} className="financial-crossover-panel__judgment">
                  <p>{d.summary}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {d.because}
                  </p>
                </article>
              ))}
            </div>
          )}

          {reasoning.length > 0 && (
            <div className="financial-crossover-panel__conclusions">
              <h5>Raonament pas a pas</h5>
              <ol>
                {reasoning.map((r) => (
                  <li key={r.id}>
                    {r.conclusion}
                    <span className="financial-crossover-panel__because-inline"> — Per què: {r.because}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {(crossover.conclusions as string[])?.length > 0 && (
            <div className="financial-crossover-panel__conclusions">
              <h5>Resum</h5>
              <ul>
                {(crossover.conclusions as string[]).map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
