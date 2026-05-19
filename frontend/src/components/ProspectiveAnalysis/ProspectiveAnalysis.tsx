import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { casesService, extractService, prospectiveService } from '../../services/api'
import { computeMicmacPreview } from '../../utils/micmac'
import WorkflowProgress from '../shared/WorkflowProgress'
import MethodologyHint from './MethodologyHint'
import MicmacScatterChart from './MicmacScatterChart'
import './ProspectiveAnalysis.css'

const STEP_LABELS = [
  'Extracció OSINT',
  'Projecte',
  'Retrospectiva',
  'Variables',
  'MIC-MAC',
  'Actors',
  'MACTOR',
  'Morfològic',
  'Escenaris',
]

interface VariableRow {
  code: string
  name: string
  type: string
  desc: string
}

interface ActorRow {
  code: string
  name: string
  force: number
  fins: string
}

interface ObjectiveRow {
  id: string
  name: string
}

interface MorphRow {
  id: string
  name: string
  configsText: string
}

interface StreamPayload {
  event: string
  index?: number
  name?: string
  prob?: string
  config?: string
  text?: string
  message?: string
}

interface ExtractStatementRow {
  id: number
  actor: string
  statement: string
  posture_value: number
  tone: string
  grounding_score: number | null
  cleanup_decision?: string
}

interface ExtractProgressPayload {
  event: string
  current?: number
  total?: number
  text?: string
  message?: string
}

const SCENARIO_NAMES = [
  'Escenari Infern',
  'Escenari Tensió Crònica',
  'Escenari Equilibri Dinàmic',
  'Escenari Cel',
]

function emptyMatrix(n: number): number[][] {
  return Array.from({ length: n }, () => Array.from({ length: n }, () => 0))
}

function emptySmicCross(): number[][] {
  return Array.from({ length: 4 }, () => Array.from({ length: 4 }, () => 0))
}

interface IncompatRow {
  component_a: string
  config_a: string
  component_b: string
  config_b: string
}

function morphConfigsFromText(text: string): string[] {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

function isPairIncompatible(
  list: IncompatRow[],
  compA: string,
  cfgA: string,
  compB: string,
  cfgB: string,
): boolean {
  return list.some(
    (inc) =>
      (inc.component_a === compA &&
        inc.config_a === cfgA &&
        inc.component_b === compB &&
        inc.config_b === cfgB) ||
      (inc.component_a === compB &&
        inc.config_a === cfgB &&
        inc.component_b === compA &&
        inc.config_b === cfgA),
  )
}

export interface ProspectiveAnalysisProps {
  /** Pas inicial del wizard (0–8) quan s’entra des d’una ruta concreta del menú */
  entryStep?: number
}

export default function ProspectiveAnalysis({ entryStep = 0 }: ProspectiveAnalysisProps) {
  const queryClient = useQueryClient()
  const { activeCase, setActiveCase } = useCase()
  const [step, setStep] = useState(entryStep)

  useEffect(() => {
    setStep(entryStep)
  }, [entryStep])
  const [projectId, setProjectId] = useState<number | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [hypothesis, setHypothesis] = useState('')
  const [context, setContext] = useState('')
  const [caseIdStr, setCaseIdStr] = useState('')

  const [variables, setVariables] = useState<VariableRow[]>([
    { code: 'V1', name: '', type: 'I', desc: '' },
    { code: 'V2', name: '', type: 'E', desc: '' },
    { code: 'V3', name: '', type: 'I', desc: '' },
  ])
  const [micmacMatrix, setMicmacMatrix] = useState<number[][]>(emptyMatrix(3))
  const [micmacResult, setMicmacResult] = useState<Record<string, unknown> | null>(null)
  const [mactorResult, setMactorResult] = useState<Record<string, unknown> | null>(null)

  const [actors, setActors] = useState<ActorRow[]>([
    { code: 'A1', name: '', force: 3, fins: '' },
    { code: 'A2', name: '', force: 3, fins: '' },
  ])
  const [objectives, setObjectives] = useState<ObjectiveRow[]>([
    { id: 'O1', name: '' },
    { id: 'O2', name: '' },
  ])
  const [postures, setPostures] = useState<number[][]>(() =>
    Array.from({ length: 2 }, () => Array.from({ length: 2 }, () => 0)),
  )

  const [morphRows, setMorphRows] = useState<MorphRow[]>([
    { id: 'C1', name: '', configsText: 'Opció A\nOpció B' },
    { id: 'C2', name: '', configsText: 'Opció A\nOpció B' },
  ])
  const [incompatibilities, setIncompatibilities] = useState<IncompatRow[]>([])
  const [morphSpaceStats, setMorphSpaceStats] = useState<{
    total_combinations: number
    valid_combinations: number
    filtered_out: number
    scenario_configs?: { scenario_type: string; config: string }[]
  } | null>(null)

  const [smicInitial, setSmicInitial] = useState<number[]>([0.2, 0.35, 0.3, 0.15])
  const [smicCross, setSmicCross] = useState<number[][]>(emptySmicCross)
  const [smicResult, setSmicResult] = useState<{
    final_probs: number[]
    final_labels: string[]
  } | null>(null)
  const [smicMatrix, setSmicMatrix] = useState<number[][]>(
    Array.from({ length: 4 }, (_, i) =>
      Array.from({ length: 4 }, (_, j) => (i === j ? 0 : 0.5)),
    ),
  )
  const [smicBayesianResult, setSmicBayesianResult] = useState<{
    results: Array<{
      name: string
      prior_probability: number
      adjusted_probability: number
      label: string
    }>
  } | null>(null)

  const [streamTexts, setStreamTexts] = useState<Record<number, string>>({})
  const [streamMeta, setStreamMeta] = useState<Record<number, string>>({})
  const [streamingDone, setStreamingDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const extractEsRef = useRef<EventSource | null>(null)

  const [extractionCaseId, setExtractionCaseId] = useState<number | null>(null)
  const [extractRunning, setExtractRunning] = useState(false)
  const [extractProgress, setExtractProgress] = useState<{ current: number; total: number } | null>(
    null,
  )
  const [previewSuggestions, setPreviewSuggestions] = useState<{
    suggested_variables: unknown[]
    suggested_actors: unknown[]
  } | null>(null)
  const [applyTargetProjectId, setApplyTargetProjectId] = useState<number | null>(null)

  const [geoSuggestions, setGeoSuggestions] = useState<Array<{
    row: number
    col: number
    value: number
    reason: string
  }> | null>(null)
  const [retrospectiveData, setRetrospectiveData] = useState<{
    period: string
    osint_articles: number
    variables: Array<{
      code: string
      name: string
      trend: string
      total_mentions: number
      yearly: Array<{ year: number; mentions: number }>
    }>
  } | null>(null)
  const [expertName, setExpertName] = useState('')
  const [panelConsensus, setPanelConsensus] = useState<Record<string, unknown> | null>(null)

  const { data: casesList = [], isLoading: loadingCases } = useQuery({
    queryKey: ['cases-list'],
    queryFn: () => casesService.list(),
  })

  const { data: statements = [], refetch: refetchStatements } = useQuery({
    queryKey: ['extract-statements', extractionCaseId],
    queryFn: () => extractService.getStatements(extractionCaseId!),
    enabled: extractionCaseId !== null,
  })

  const { data: projects = [], isLoading: loadingProjects } = useQuery({
    queryKey: ['prospective-projects'],
    queryFn: () => prospectiveService.listProjects(),
  })

  const { data: projectDetail } = useQuery({
    queryKey: ['prospective-project-detail', projectId],
    queryFn: () => prospectiveService.getProject(projectId!),
    enabled: projectId !== null,
  })

  useEffect(() => {
    if (!projectDetail) return
    const pd = projectDetail as {
      incompatibilities?: IncompatRow[]
      morph_space?: typeof morphSpaceStats
      smic?: {
        initial_probs: number[]
        cross_matrix: number[][]
        final_probs?: number[]
        final_labels?: string[]
      }
      components?: { id: string; name: string; configs: { label: string }[] }[]
    }
    if (pd.incompatibilities) setIncompatibilities(pd.incompatibilities)
    if (pd.morph_space) setMorphSpaceStats(pd.morph_space)
    if (pd.smic) {
      setSmicInitial(pd.smic.initial_probs ?? [0.2, 0.35, 0.3, 0.15])
      setSmicCross(pd.smic.cross_matrix ?? emptySmicCross())
      if (pd.smic.final_probs && pd.smic.final_labels) {
        setSmicResult({ final_probs: pd.smic.final_probs, final_labels: pd.smic.final_labels })
      }
    }
    if (pd.components?.length) {
      setMorphRows(
        pd.components.map((c) => ({
          id: c.id,
          name: c.name,
          configsText: (c.configs ?? []).map((cfg) => cfg.label).join('\n'),
        })),
      )
    }
  }, [projectDetail])

  const createMutation = useMutation({
    mutationFn: () =>
      prospectiveService.createProject({
        title: title.trim() || 'Projecte sense títol',
        hypothesis,
        context,
        case_id: caseIdStr ? Number(caseIdStr) : undefined,
      }),
    onSuccess: (data: { id: number }) => {
      setProjectId(data.id)
      setErrorMsg(null)
      void queryClient.invalidateQueries({ queryKey: ['prospective-projects'] })
      const cid = caseIdStr.trim() ? Number(caseIdStr) : NaN
      if (!Number.isNaN(cid)) {
        const row = (casesList as { id: number; name: string }[]).find((c) => c.id === cid)
        if (row) {
          const next: ActiveCase = {
            id: row.id,
            name: row.name,
            case_type: 'investigació',
            status: 'actiu',
          }
          setActiveCase(next)
          setExtractionCaseId(cid)
        }
      }
      setStep(2)
    },
    onError: () => setErrorMsg('No s\'ha pogut crear el projecte.'),
  })

  const saveVariablesMutation = useMutation({
    mutationFn: () =>
      prospectiveService.saveVariables(
        projectId!,
        variables.map((v) => ({
          code: v.code,
          name: v.name,
          type: v.type,
          desc: v.desc,
        })),
      ),
    onSuccess: () => {
      const n = variables.length
      setMicmacMatrix(emptyMatrix(n))
      setErrorMsg(null)
      setStep(4)
    },
    onError: () => setErrorMsg('Error guardant variables.'),
  })

  const micmacMutation = useMutation({
    mutationFn: () => prospectiveService.computeMicmac(projectId!, micmacMatrix),
    onSuccess: (data: Record<string, unknown>) => {
      setMicmacResult(data)
      setErrorMsg(null)
      setStep(5)
    },
    onError: () => setErrorMsg('Error calculant MIC-MAC.'),
  })

  const submitVoteMutation = useMutation({
    mutationFn: () => {
      if (!projectId) return Promise.reject(new Error('Crea el projecte primer'))
      return prospectiveService.submitExpertVote(projectId, {
        expert_id: `${expertName.replace(/\s+/g, '_')}_${Date.now()}`,
        expert_name: expertName,
        votes: micmacMatrix.flatMap((row, i) =>
          row.map((val, j) => ({ row: i, col: j, value: val })),
        ),
      })
    },
    onSuccess: async () => {
      if (!projectId) return
      const c = await prospectiveService.getPanelConsensus(projectId)
      setPanelConsensus(c)
    },
  })

  const applyConsensusMutation = useMutation({
    mutationFn: () => prospectiveService.applyConsensus(projectId!),
    onSuccess: (data: Record<string, unknown>) => {
      setMicmacResult(data)
      setErrorMsg(null)
    },
  })

  const saveActorsMutation = useMutation({
    mutationFn: () =>
      prospectiveService.saveActors(
        projectId!,
        actors.map((a) => ({
          code: a.code,
          name: a.name,
          force: a.force,
          fins: a.fins,
        })),
      ),
    onSuccess: () => {
      const na = actors.length
      const no = objectives.length
      setPostures(Array.from({ length: na }, () => Array.from({ length: no }, () => 0)))
      setErrorMsg(null)
      setStep(6)
    },
    onError: () => setErrorMsg('Error guardant actors.'),
  })

  const saveObjectivesAndMactorMutation = useMutation({
    mutationFn: async () => {
      await prospectiveService.saveObjectives(
        projectId!,
        objectives.map((o) => ({ id: o.id, name: o.name })),
      )
      return prospectiveService.computeMactor(projectId!, postures)
    },
    onSuccess: (data: Record<string, unknown>) => {
      setMactorResult(data)
      setErrorMsg(null)
      setStep(7)
    },
    onError: () => setErrorMsg('Error amb objectius o MACTOR.'),
  })

  const saveMorphMutation = useMutation({
    mutationFn: async () => {
      await prospectiveService.saveComponents(
        projectId!,
        morphRows.map((m) => ({
          id: m.id,
          name: m.name,
          configs: morphConfigsFromText(m.configsText).map((label) => ({ label, desc: '' })),
        })),
      )
      const stats = await prospectiveService.saveCompatibilities(projectId!, incompatibilities)
      return stats
    },
    onSuccess: (stats) => {
      setMorphSpaceStats(stats)
      setErrorMsg(null)
      setStep(8)
    },
    onError: () => setErrorMsg('Error guardant components morfològics.'),
  })

  const smicMutation = useMutation({
    mutationFn: () => prospectiveService.computeSmic(projectId!, smicInitial, smicCross),
    onSuccess: (data: { final_probs: number[]; final_labels: string[] }) => {
      setSmicResult(data)
      setErrorMsg(null)
    },
    onError: () => setErrorMsg('Error calculant SMIC.'),
  })

  const liveMicmacPreview = useMemo(
    () => computeMicmacPreview(micmacMatrix, variables.map((v) => v.code)),
    [micmacMatrix, variables],
  )

  const toggleMorphCompatibility = (
    compA: string,
    cfgA: string,
    compB: string,
    cfgB: string,
    compatible: boolean,
  ) => {
    setIncompatibilities((prev) => {
      if (compatible) {
        return prev.filter(
          (inc) =>
            !(
              (inc.component_a === compA &&
                inc.config_a === cfgA &&
                inc.component_b === compB &&
                inc.config_b === cfgB) ||
              (inc.component_a === compB &&
                inc.config_a === cfgB &&
                inc.component_b === compA &&
                inc.config_b === cfgA)
            ),
        )
      }
      return [...prev, { component_a: compA, config_a: cfgA, component_b: compB, config_b: cfgB }]
    })
  }

  const liveMorphTotal = useMemo(() => {
    let total = 1
    for (const m of morphRows) {
      total *= Math.max(morphConfigsFromText(m.configsText).length, 1)
    }
    return total
  }, [morphRows])

  const cleanupMutation = useMutation({
    mutationFn: () => extractService.runCleanup(extractionCaseId!),
    onSuccess: () => {
      void refetchStatements()
      setErrorMsg(null)
    },
    onError: () => setErrorMsg('Error en la neteja.'),
  })

  const previewMutation = useMutation({
    mutationFn: () => extractService.getPreview(extractionCaseId!),
    onSuccess: (data) => {
      setPreviewSuggestions(data)
      setErrorMsg(null)
    },
    onError: () => setErrorMsg('Error carregant suggeriments.'),
  })

  const applyMutation = useMutation({
    mutationFn: () =>
      extractService.applyToProject(applyTargetProjectId!, extractionCaseId!),
    onSuccess: (data: {
      variables: { code: string; name: string; type: string; desc: string }[]
      actors: ActorRow[]
    }) => {
      if (data.variables?.length) {
        setVariables(
          data.variables.map((v) => ({
            code: String(v.code ?? ''),
            name: String(v.name ?? ''),
            type: String(v.type ?? 'I'),
            desc: String(v.desc ?? ''),
          })),
        )
      }
      if (data.actors?.length) {
        setActors(
          data.actors.map((a) => ({
            code: String(a.code ?? ''),
            name: String(a.name ?? ''),
            force: Number(a.force ?? 3),
            fins: String(a.fins ?? ''),
          })),
        )
      }
      setProjectId(applyTargetProjectId)
      setErrorMsg(null)
      void queryClient.invalidateQueries({ queryKey: ['prospective-projects'] })
      if (extractionCaseId != null) {
        const row = (casesList as { id: number; name: string }[]).find((c) => c.id === extractionCaseId)
        if (row) {
          setActiveCase({
            id: row.id,
            name: row.name,
            case_type: 'investigació',
            status: 'actiu',
          })
        }
      }
      setStep(2)
    },
    onError: () => setErrorMsg('Error aplicant al projecte.'),
  })

  useEffect(() => {
    const n = variables.length
    if (n < 1) return
    setMicmacMatrix((prev) => {
      if (prev.length === n) return prev
      return emptyMatrix(n)
    })
  }, [variables.length])

  useEffect(() => {
    const na = actors.length
    const no = objectives.length
    if (na < 1 || no < 1) return
    setPostures((prev) => {
      if (prev.length === na && prev[0]?.length === no) return prev
      return Array.from({ length: na }, () => Array.from({ length: no }, () => 0))
    })
  }, [actors.length, objectives.length])

  useEffect(() => {
    return () => {
      esRef.current?.close()
      esRef.current = null
      extractEsRef.current?.close()
      extractEsRef.current = null
    }
  }, [])

  useEffect(() => {
    if (step === 1 && extractionCaseId !== null) {
      setCaseIdStr(String(extractionCaseId))
    }
  }, [step, extractionCaseId])

  useEffect(() => {
    if (activeCase?.id != null) {
      setExtractionCaseId(activeCase.id)
    }
  }, [activeCase?.id])

  const startScenarioStream = () => {
    if (!projectId) return
    setErrorMsg(null)
    setStreamTexts({})
    setStreamMeta({})
    setStreamingDone(false)
    esRef.current?.close()
    const url = prospectiveService.getStreamUrl(projectId)
    const es = new EventSource(url)
    esRef.current = es
    es.onmessage = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as StreamPayload
        if (data.event === 'scenario_start' && data.index !== undefined && data.name) {
          const meta = `${data.name} — ${data.prob ?? ''}${data.config ? ` · ${data.config}` : ''}`
          setStreamMeta((m) => ({ ...m, [data.index!]: meta }))
          setStreamTexts((t) => ({ ...t, [data.index!]: '' }))
        } else if (data.event === 'chunk' && data.index !== undefined && data.text) {
          setStreamTexts((t) => ({
            ...t,
            [data.index!]: (t[data.index!] ?? '') + data.text,
          }))
        } else if (data.event === 'error') {
          setErrorMsg(data.message ?? 'Error en streaming')
        } else if (data.event === 'all_done') {
          setStreamingDone(true)
          es.close()
          void queryClient.invalidateQueries({ queryKey: ['prospective-scenarios', projectId] })
        }
      } catch {
        /* ignore */
      }
    }
    es.onerror = () => {
      setErrorMsg('Connexió SSE interrompuda (comprova el backend i la clau Anthropic).')
      es.close()
    }
  }

  const { data: savedScenarios = [] } = useQuery({
    queryKey: ['prospective-scenarios', projectId],
    queryFn: () => prospectiveService.getScenarios(projectId!),
    enabled: projectId !== null && step === 8,
  })

  const updateMatrixCell = (i: number, j: number, val: number) => {
    if (i === j) return
    const v = Math.max(0, Math.min(3, val))
    setMicmacMatrix((m) =>
      m.map((row, ri) => row.map((c, ci) => (ri === i && ci === j ? v : c))),
    )
  }

  const updatePosture = (i: number, j: number, val: number) => {
    const v = Math.max(-2, Math.min(2, val))
    setPostures((p) =>
      p.map((row, ri) => row.map((c, ci) => (ri === i && ci === j ? v : c))),
    )
  }

  const postureValueClass = (v: number): string => {
    if (v >= 1) return 'posture-positive'
    if (v <= -1) return 'posture-negative'
    return 'posture-neutral'
  }

  const startExtractStream = () => {
    if (!extractionCaseId) {
      setErrorMsg('Selecciona un cas amb dades OSINT.')
      return
    }
    setErrorMsg(null)
    setExtractRunning(true)
    setExtractProgress(null)
    extractEsRef.current?.close()
    const es = new EventSource(extractService.getStreamUrl(extractionCaseId))
    extractEsRef.current = es
    es.onmessage = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as ExtractProgressPayload
        if (data.event === 'start') {
          setExtractProgress({ current: 0, total: data.total ?? 0 })
        }
        if (data.event === 'progress' && data.current !== undefined && data.total !== undefined) {
          setExtractProgress({ current: data.current, total: data.total })
        }
        if (data.event === 'done') {
          setExtractRunning(false)
          es.close()
          void refetchStatements()
        }
        if (data.event === 'error') {
          setErrorMsg(data.message ?? 'Error en extracció')
          setExtractRunning(false)
          es.close()
        }
      } catch {
        /* ignore */
      }
    }
    es.onerror = () => {
      setExtractRunning(false)
      es.close()
    }
  }

  return (
    <div className="card prospective-page">
      <h1 className="prospective-title">Anàlisi prospectiva</h1>
      <p style={{ color: 'var(--color-gray-600)', marginTop: 0 }}>
        Metodologia MIC-MAC, MACTOR, morfològica i escenaris narratius (Claude).
      </p>

      <div className="prospective-steps">
        {STEP_LABELS.map((label, i) => (
          <span
            key={label}
            className={`prospective-step-chip ${step === i ? 'prospective-step-chip--active' : ''}`}
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>

      <WorkflowProgress
        osintCount={activeCase?.osint_count ?? 0}
        extractionCount={
          (statements as ExtractStatementRow[]).filter(
            (s) => s.cleanup_decision === 'KEEP',
          ).length
        }
        hasMicmac={micmacResult !== null}
        hasMactor={mactorResult !== null}
        hasScenarios={savedScenarios.length > 0}
      />

      {errorMsg && <div className="prospective-alert prospective-alert--error">{errorMsg}</div>}

      {step === 0 && (
        <>
          <h2 style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-lg)' }}>
            Pas 0 — Extracció estructurada (OSINT → declaracions)
          </h2>
          <p style={{ color: 'var(--color-gray-600)' }}>
            Selecciona un cas que tingui registres a les taules <code>osint_queries</code> /{' '}
            <code>osint_results</code>. Es fa servir Claude Haiku per extreure declaracions com al patró{' '}
            china-us-rhetoric.
          </p>

          <div className="prospective-field">
            <label htmlFor="extract-case">Cas EINA</label>
            <select
              id="extract-case"
              className="prospective-select"
              value={extractionCaseId ?? ''}
              onChange={(e) => {
                const raw = e.target.value
                const id = raw ? Number(raw) : null
                setExtractionCaseId(id)
                if (id === null) return
                const row = (casesList as { id: number; name: string }[]).find((c) => c.id === id)
                if (row) {
                  setActiveCase({
                    id: row.id,
                    name: row.name,
                    case_type: 'investigació',
                    status: 'actiu',
                  })
                }
              }}
            >
              <option value="">— Selecciona —</option>
              {(casesList as { id: number; name: string }[]).map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} — {c.name}
                </option>
              ))}
            </select>
          </div>

          {loadingCases && <div className="spinner" />}

          <div className="prospective-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={!extractionCaseId || extractRunning}
              onClick={() => startExtractStream()}
            >
              Extreure actors i postures
            </button>
            <button
              type="button"
              className="btn btn-success"
              disabled={!extractionCaseId || cleanupMutation.isPending}
              onClick={() => cleanupMutation.mutate()}
            >
              Netejar falsos positius
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!extractionCaseId || previewMutation.isPending}
              onClick={() => previewMutation.mutate()}
            >
              Carregar suggeriments (matrius)
            </button>
            <button type="button" className="btn" onClick={() => setStep(1)}>
              Saltar extracció · Continuar a projecte
            </button>
          </div>

          {extractRunning && extractProgress && extractProgress.total > 0 && (
            <div className="prospective-alert prospective-alert--success">
              Processant fonts: {extractProgress.current} / {extractProgress.total}
            </div>
          )}

          <h3 style={{ color: 'var(--color-primary)', marginTop: 'var(--spacing-xl)' }}>
            Declaracions extretes
          </h3>
          <div className="extract-table-wrap">
            <table className="extract-table">
              <thead>
                <tr>
                  <th>Actor</th>
                  <th>Declaració</th>
                  <th>Postura</th>
                  <th>To</th>
                  <th>Grounding</th>
                </tr>
              </thead>
              <tbody>
                {(statements as ExtractStatementRow[]).map((s) => (
                  <tr key={s.id}>
                    <td>{s.actor}</td>
                    <td className="extract-statement-cell">{s.statement}</td>
                    <td className={postureValueClass(s.posture_value)}>{s.posture_value}</td>
                    <td>{s.tone}</td>
                    <td>{s.grounding_score !== null ? s.grounding_score.toFixed(3) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {previewSuggestions && (
            <div className="preview-block card" style={{ marginTop: 'var(--spacing-lg)' }}>
              <h3 style={{ color: 'var(--color-primary)' }}>Suggeriments per a les matrius</h3>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)' }}>
                Variables (MIC-MAC)
              </p>
              <ul className="preview-list">
                {(previewSuggestions.suggested_variables as { code: string; name: string }[]).map(
                  (v, i) => (
                    <li key={i}>
                      <strong>{v.code}</strong> — {v.name}
                    </li>
                  ),
                )}
              </ul>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)' }}>
                Actors (MACTOR)
              </p>
              <ul className="preview-list">
                {(previewSuggestions.suggested_actors as { code: string; name: string }[]).map(
                  (a, i) => (
                    <li key={i}>
                      <strong>{a.code}</strong> — {a.name}
                    </li>
                  ),
                )}
              </ul>
            </div>
          )}

          <div className="prospective-field">
            <label htmlFor="apply-project">Projecte prospectiu per aplicar suggeriments</label>
            <select
              id="apply-project"
              className="prospective-select"
              value={applyTargetProjectId ?? ''}
              onChange={(e) =>
                setApplyTargetProjectId(e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">— Selecciona projecte —</option>
              {(projects as { id: number; title: string }[]).map((p) => (
                <option key={p.id} value={p.id}>
                  #{p.id} — {p.title}
                </option>
              ))}
            </select>
          </div>

          <div className="prospective-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={
                !extractionCaseId || applyTargetProjectId === null || applyMutation.isPending
              }
              onClick={() => applyMutation.mutate()}
            >
              Aplicar al projecte
            </button>
          </div>
        </>
      )}

      {step === 1 && (
        <>
          <div className="prospective-actions" style={{ marginBottom: 'var(--spacing-md)' }}>
            <button type="button" className="btn" onClick={() => setStep(0)}>
              Enrere: extracció OSINT
            </button>
          </div>
          <h2 style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-lg)' }}>
            Nou projecte o continuar
          </h2>
          <div className="prospective-field">
            <label htmlFor="title">Títol</label>
            <input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex.: Indo-Pacífic 2030"
            />
          </div>
          <div className="prospective-field">
            <label htmlFor="hypothesis">Hipòtesi / conflicte estratègic</label>
            <textarea
              id="hypothesis"
              rows={3}
              value={hypothesis}
              onChange={(e) => setHypothesis(e.target.value)}
            />
          </div>
          <div className="prospective-field">
            <label htmlFor="context">Context</label>
            <textarea id="context" rows={4} value={context} onChange={(e) => setContext(e.target.value)} />
          </div>
          <div className="prospective-field">
            <label htmlFor="case_id">ID cas (opcional)</label>
            <input
              id="case_id"
              value={caseIdStr}
              onChange={(e) => setCaseIdStr(e.target.value)}
              placeholder="Número del cas enllaçat"
            />
          </div>
          <div className="prospective-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              Crear projecte i continuar
            </button>
          </div>

          <h3 style={{ marginTop: 'var(--spacing-xl)', color: 'var(--color-primary)' }}>
            Projectes existents
          </h3>
          {loadingProjects ? (
            <div className="spinner" />
          ) : (
            <ul className="project-list">
              {(projects as { id: number; title: string; case_id?: number | null }[]).map((p) => (
                <li key={p.id}>
                  <span>{p.title}</span>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      setProjectId(p.id)
                      if (p.case_id != null) {
                        const row = (casesList as { id: number; name: string }[]).find(
                          (c) => c.id === p.case_id,
                        )
                        if (row) {
                          setActiveCase({
                            id: row.id,
                            name: row.name,
                            case_type: 'investigació',
                            status: 'actiu',
                          })
                        }
                        setExtractionCaseId(p.case_id)
                        setCaseIdStr(String(p.case_id))
                      }
                    }}
                  >
                    Obrir
                  </button>
                </li>
              ))}
            </ul>
          )}
          {projectId !== null && (
            <div className="prospective-actions">
              <button type="button" className="btn btn-success" onClick={() => setStep(2)}>
                Continuar amb projecte #{projectId}
              </button>
            </div>
          )}
        </>
      )}

      {step === 2 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Retrospectiva d&apos;actors</h2>
          <MethodologyHint title="Metodologia Godet — Retrospectiva" defaultOpen>
            <p>
              Abans de definir el MIC-MAC, analitza com han evolucionat les variables clau
              en el passat. EINA agrega mencions OSINT dels darrers 10 anys per ancorar
              el judici de l&apos;analista en dades empíriques.
            </p>
          </MethodologyHint>
          <div className="prospective-actions" style={{ marginBottom: 'var(--spacing-md)' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={async () => {
                if (!projectId) return
                try {
                  const data = await prospectiveService.getRetrospective(
                    projectId,
                    variables.map((v) => ({
                      code: v.code,
                      name: v.name,
                      desc: v.desc,
                    })),
                  )
                  setRetrospectiveData(data)
                  setErrorMsg(null)
                } catch {
                  setErrorMsg('No s\'han pogut carregar tendències OSINT. Comprova que el cas té dades.')
                }
              }}
            >
              Carregar tendències OSINT (10 anys)
            </button>
          </div>
          {retrospectiveData && (
            <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)' }}>
                Període {retrospectiveData.period} · {retrospectiveData.osint_articles} articles OSINT
              </p>
              {retrospectiveData.variables.map((v) => (
                <div
                  key={v.code}
                  style={{
                    padding: 'var(--spacing-sm) 0',
                    borderBottom: '1px solid var(--color-gray-100)',
                  }}
                >
                  <strong>{v.code}</strong> — {v.name}{' '}
                  <span
                    style={{
                      marginLeft: 8,
                      fontSize: 'var(--font-size-xs)',
                      color:
                        v.trend === 'pujant'
                          ? 'var(--color-danger)'
                          : v.trend === 'baixant'
                            ? 'var(--color-success)'
                            : 'var(--color-gray-500)',
                    }}
                  >
                    {v.trend} ({v.total_mentions} mencions)
                  </span>
                  <div
                    style={{
                      display: 'flex',
                      gap: 4,
                      marginTop: 6,
                      flexWrap: 'wrap',
                      fontSize: '10px',
                      color: 'var(--color-gray-500)',
                    }}
                  >
                    {v.yearly.map((y) => (
                      <span key={y.year} title={`${y.year}: ${y.mentions}`}>
                        {y.year}:{y.mentions}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(1)}>
              Enrere
            </button>
            <button type="button" className="btn btn-accent" onClick={() => setStep(3)}>
              Continuar a Variables
            </button>
          </div>
        </>
      )}

      {step === 3 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Variables del sistema</h2>
          <MethodologyHint title="Metodologia Godet — Pas 2: Variables del sistema">
            <p>
              Les variables defineixen els elements del sistema que poden evolucionar.
              Una variable ben formulada és una <strong>mesura de variació</strong>, no un tema genèric.
            </p>
            <p>
              <span className="mhint-rule">Regla de formulació</span>{' '}
              Cada variable ha de poder puntuar-se de 0 (mínim) a 3 (màxim) i respondre
              a la pregunta <strong>«Grau en què...»</strong>
            </p>
            <p>
              <strong>Tipus:</strong> I = Interna (accionable) · E = Externa (de l&apos;entorn, no controlable).
              Nombre recomanat: <strong>8–15 variables</strong>.
            </p>
            <code className="mhint-example">
              {'✓ Correcte: «Grau en què la BRI avança sense resistència significativa» (puntuable 0→3)\n'}
              {'✗ Incorrecte: «La BRI», «Economia de l\'Índia» (massa vagues)'}
            </code>
          </MethodologyHint>
          {variables.map((row, idx) => (
            <div key={idx} className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
              <div className="prospective-field">
                <label>Codi</label>
                <input
                  value={row.code}
                  onChange={(e) =>
                    setVariables((v) =>
                      v.map((x, i) => (i === idx ? { ...x, code: e.target.value } : x)),
                    )
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Nom</label>
                <input
                  value={row.name}
                  onChange={(e) =>
                    setVariables((v) =>
                      v.map((x, i) => (i === idx ? { ...x, name: e.target.value } : x)),
                    )
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Tipus (I/E)</label>
                <input
                  value={row.type}
                  onChange={(e) =>
                    setVariables((v) =>
                      v.map((x, i) => (i === idx ? { ...x, type: e.target.value } : x)),
                    )
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Descripció operativa</label>
                <textarea
                  rows={2}
                  value={row.desc}
                  onChange={(e) =>
                    setVariables((v) =>
                      v.map((x, i) => (i === idx ? { ...x, desc: e.target.value } : x)),
                    )
                  }
                />
              </div>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => setVariables((v) => v.filter((_, i) => i !== idx))}
              >
                Eliminar
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-primary"
            onClick={() =>
              setVariables((v) => [...v, { code: `V${v.length + 1}`, name: '', type: 'I', desc: '' }])
            }
          >
            Afegir variable
          </button>
          <div className="prospective-actions" style={{ marginTop: 'var(--spacing-md)' }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!projectId}
              onClick={async () => {
                if (!projectId) return
                try {
                  const data = await prospectiveService.getGeopoliticalMicmacSuggestions(
                    projectId,
                    variables.map((v) => ({
                      code: v.code,
                      name: v.name,
                      desc: v.desc,
                    })),
                  )
                  setGeoSuggestions(data.suggestions ?? [])
                  setErrorMsg(null)
                } catch {
                  setErrorMsg('No s\'han trobat dades geopolítiques per al cas enllaçat.')
                }
              }}
            >
              Enriquir amb context geopolític
            </button>
          </div>
          {geoSuggestions && geoSuggestions.length > 0 && (
            <div className="prospective-alert prospective-alert--success" style={{ marginTop: 'var(--spacing-sm)' }}>
              {geoSuggestions.length} suggeriment(s) MIC-MAC des de relacions bilaterals/esdeveniments.
              S&apos;aplicaran al pas MIC-MAC.
            </div>
          )}
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(2)}>
              Enrere
            </button>
            <button
              type="button"
              className="btn btn-accent"
              disabled={saveVariablesMutation.isPending}
              onClick={() => saveVariablesMutation.mutate()}
            >
              Guardar i MIC-MAC
            </button>
          </div>
        </>
      )}

      {step === 4 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Matriu MIC-MAC (0–3, diagonal 0)</h2>
          {geoSuggestions && geoSuggestions.length > 0 && (
            <div className="prospective-actions" style={{ marginBottom: 'var(--spacing-md)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setMicmacMatrix((prev) => {
                    const next = prev.map((r) => [...r])
                    for (const s of geoSuggestions) {
                      if (s.row < next.length && s.col < next.length && s.row !== s.col) {
                        next[s.row][s.col] = Math.max(next[s.row][s.col], s.value)
                      }
                    }
                    return next
                  })
                }}
              >
                Aplicar {geoSuggestions.length} suggeriment(s) geopolítics
              </button>
            </div>
          )}
          <MethodologyHint title="Metodologia Godet — Pas 3: Matriu MIC-MAC" defaultOpen={false}>
            <p>
              Cel·la (i,j): fins a quin punt la variable <strong>fila i</strong> influeix
              sobre la variable <strong>columna j</strong>.
              <strong> 0</strong>=cap · <strong>1</strong>=feble · <strong>2</strong>=moderada · <strong>3</strong>=forta.
              Diagonal sempre = 0.
            </p>
            <p>
              <strong>Motricitat</strong> (suma fila) = capacitat d&apos;influir.{' '}
              <strong>Dependència</strong> (suma columna) = grau de ser influïda.
            </p>
            <code className="mhint-example">
              {'Sectors Godet:\n'}
              {'• Motriu: alta mot, baixa dep → mouen el sistema\n'}
              {'• Clau/Conflicte: alta mot, alta dep → estratègiques ← VB i VR aquí\n'}
              {'• Resultant: baixa mot, alta dep → mostren el futur\n'}
              {'• Autònom: baixa mot, baixa dep → perifèriques\n\n'}
              {'VB (Variable Blanc) = palanca estratègica\n'}
              {'VR (Variable de Risc) = punt d\'inestabilitat'}
            </code>
          </MethodologyHint>
          <div className="prospective-matrix-wrap">
            <table className="prospective-matrix">
              <thead>
                <tr>
                  <th />
                  {variables.map((v, j) => (
                    <th key={j}>{v.code || `C${j}`}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {micmacMatrix.map((row, i) => (
                  <tr key={i}>
                    <th>{variables[i]?.code ?? i}</th>
                    {row.map((cell, j) => (
                      <td key={j}>
                        {i === j ? (
                          0
                        ) : (
                          <input
                            type="number"
                            min={0}
                            max={3}
                            value={cell}
                            onChange={(e) => updateMatrixCell(i, j, Number(e.target.value))}
                          />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <MicmacScatterChart result={liveMicmacPreview} live />
          {(() => {
            const sectors = liveMicmacPreview.sectors
            const vbIdx = liveMicmacPreview.vb_index
            const vrIdx = liveMicmacPreview.vr_index
            if (vbIdx < 0 && vrIdx < 0) return null
            return (
              <div style={{ display: 'flex', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-md)', flexWrap: 'wrap' }}>
                {vbIdx >= 0 && sectors[vbIdx] && (
                  <div
                    style={{
                      background: 'rgba(212,168,67,0.1)',
                      border: '1px solid rgba(212,168,67,0.4)',
                      borderRadius: 'var(--radius-sm)',
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      fontSize: 'var(--font-size-sm)',
                      flex: 1,
                      minWidth: 200,
                    }}
                  >
                    <strong style={{ color: '#9a7320' }}>VB — Variable Blanc:</strong>{' '}
                    <strong>{sectors[vbIdx].code}</strong>
                  </div>
                )}
                {vrIdx >= 0 && sectors[vrIdx] && (
                  <div
                    style={{
                      background: 'rgba(220,53,69,0.07)',
                      border: '1px solid rgba(220,53,69,0.3)',
                      borderRadius: 'var(--radius-sm)',
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      fontSize: 'var(--font-size-sm)',
                      flex: 1,
                      minWidth: 200,
                    }}
                  >
                    <strong style={{ color: 'var(--color-danger)' }}>VR — Variable de Risc:</strong>{' '}
                    <strong>{sectors[vrIdx].code}</strong>
                  </div>
                )}
              </div>
            )
          })()}
          {micmacResult && (
            <div className="prospective-alert prospective-alert--success" style={{ marginTop: 'var(--spacing-md)' }}>
              Resultat MIC-MAC desat al servidor.
            </div>
          )}

          {micmacResult && (
            <details style={{ marginTop: 'var(--spacing-lg)' }}>
              <summary
                style={{
                  cursor: 'pointer',
                  fontWeight: 600,
                  color: 'var(--color-primary)',
                  fontSize: 'var(--font-size-sm)',
                  padding: 'var(--spacing-sm) 0',
                }}
              >
                Anàlisi de sensibilitat (What-if)
              </summary>
              <div
                style={{
                  marginTop: 'var(--spacing-md)',
                  padding: 'var(--spacing-md)',
                  background: 'rgba(30,58,95,0.03)',
                  border: '1px solid rgba(30,58,95,0.15)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)', marginBottom: 'var(--spacing-md)' }}>
                  Modifica la matriu principal per explorar l&apos;impacte sobre sectors, VB i VR{' '}
                  <strong>sense guardar</strong>. El gràfic superior s&apos;actualitza en viu.
                </p>
                {(() => {
                  const prevSectors =
                    (micmacResult.sectors as Array<{ index: number; code: string; sector: string }>) ?? []
                  const newSectors = liveMicmacPreview.sectors
                  const changed = newSectors.filter((ns) => {
                    const old = prevSectors.find((os) => os.index === ns.index)
                    return old && old.sector !== ns.sector
                  })
                  const oldVB =
                    (micmacResult.vb_index as number | undefined) ??
                    (micmacResult.variable_blanc as { index: number } | undefined)?.index ??
                    -1
                  const oldVR =
                    (micmacResult.vr_index as number | undefined) ??
                    (micmacResult.variable_risc as { index: number } | undefined)?.index ??
                    -1
                  const newVB = liveMicmacPreview.vb_index
                  const newVR = liveMicmacPreview.vr_index
                  if (changed.length === 0 && newVB === oldVB && newVR === oldVR) {
                    return (
                      <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-success)' }}>
                        Cap canvi respecte al resultat desat.
                      </p>
                    )
                  }
                  return (
                    <div style={{ fontSize: 'var(--font-size-xs)' }}>
                      {changed.map((ns) => {
                        const old = prevSectors.find((os) => os.index === ns.index)
                        return (
                          <div
                            key={ns.index}
                            style={{
                              padding: '4px 8px',
                              marginBottom: 4,
                              background: 'rgba(220,53,69,0.08)',
                              borderRadius: '4px',
                              color: 'var(--color-danger)',
                            }}
                          >
                            <strong>{ns.code}</strong>: {old?.sector} → <strong>{ns.sector}</strong>
                          </div>
                        )
                      })}
                      {newVB !== oldVB && (
                        <div style={{ color: '#9a7320', fontWeight: 600, marginTop: 4 }}>
                          VB: {prevSectors[oldVB]?.code ?? oldVB} →{' '}
                          <strong>{newSectors[newVB]?.code ?? newVB}</strong>
                        </div>
                      )}
                      {newVR !== oldVR && newVB !== oldVR && (
                        <div style={{ color: 'var(--color-danger)', fontWeight: 600, marginTop: 4 }}>
                          VR: {prevSectors[oldVR]?.code ?? oldVR} →{' '}
                          <strong>{newSectors[newVR]?.code ?? newVR}</strong>
                        </div>
                      )}
                    </div>
                  )
                })()}
              </div>
            </details>
          )}

          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(3)}>
              Enrere
            </button>
            <button
              type="button"
              className="btn btn-accent"
              disabled={micmacMutation.isPending}
              onClick={() => micmacMutation.mutate()}
            >
              Calcular i continuar
            </button>
          </div>

          <details style={{ marginTop: 'var(--spacing-lg)' }}>
            <summary
              style={{
                cursor: 'pointer',
                fontWeight: 600,
                color: 'var(--color-primary)',
                fontSize: 'var(--font-size-sm)',
                padding: 'var(--spacing-sm) 0',
              }}
            >
              Mode panel d&apos;experts (Delphi)
            </summary>
            <div
              style={{
                padding: 'var(--spacing-md)',
                background: 'var(--color-gray-50)',
                border: '1px solid var(--color-gray-200)',
                borderRadius: 'var(--radius-md)',
                marginTop: 'var(--spacing-sm)',
              }}
            >
              <p
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-gray-600)',
                  marginBottom: 'var(--spacing-md)',
                  lineHeight: 1.6,
                }}
              >
                Cada expert omple la matriu i l&apos;envia. El sistema calcula la mitjana i marca
                les cel·les amb alta discrepància (σ &gt; 1.0) per a debat.
              </p>
              <div className="prospective-field">
                <label>El teu nom</label>
                <input
                  value={expertName}
                  onChange={(e) => setExpertName(e.target.value)}
                  placeholder="Ex.: Dra. García"
                  style={{ maxWidth: 280 }}
                />
              </div>
              <div className="prospective-actions" style={{ marginTop: 'var(--spacing-md)' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!expertName.trim() || submitVoteMutation.isPending || !projectId}
                  onClick={() => submitVoteMutation.mutate()}
                >
                  {submitVoteMutation.isPending ? 'Enviant...' : 'Enviar la meva matriu al panel'}
                </button>
              </div>

              {panelConsensus && !('error' in panelConsensus) && (
                <div style={{ marginTop: 'var(--spacing-lg)' }}>
                  <p style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
                    {panelConsensus.n_experts as number} expert
                    {(panelConsensus.n_experts as number) !== 1 ? 's' : ''} han votat ·{' '}
                    {panelConsensus.n_votes as number} vots registrats
                  </p>

                  {Array.isArray(panelConsensus.high_disagreement) &&
                    (panelConsensus.high_disagreement as unknown[]).length > 0 && (
                      <div
                        style={{
                          marginTop: 'var(--spacing-sm)',
                          padding: 'var(--spacing-sm)',
                          background: 'rgba(220,53,69,.06)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid rgba(220,53,69,.2)',
                        }}
                      >
                        <p
                          style={{
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 600,
                            color: 'var(--color-danger)',
                            marginBottom: 4,
                          }}
                        >
                          {(panelConsensus.high_disagreement as unknown[]).length} cel·les amb alta
                          discrepància (σ &gt; 1.0) — cal debat:
                        </p>
                        <ul
                          style={{
                            paddingLeft: 'var(--spacing-lg)',
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--color-gray-700)',
                            lineHeight: 1.8,
                          }}
                        >
                          {(
                            panelConsensus.high_disagreement as Array<{
                              row: number
                              col: number
                              avg: number
                              stdev: number
                              votes: number[]
                            }>
                          )
                            .slice(0, 6)
                            .map((d) => (
                              <li key={`${d.row}-${d.col}`}>
                                Cel·la ({d.row},{d.col}): mitjana <strong>{d.avg}</strong>, σ=
                                <strong>{d.stdev}</strong>, vots: [{d.votes.join(', ')}]
                              </li>
                            ))}
                        </ul>
                      </div>
                    )}

                  <button
                    type="button"
                    className="btn btn-success"
                    style={{ marginTop: 'var(--spacing-md)' }}
                    disabled={applyConsensusMutation.isPending}
                    onClick={() => applyConsensusMutation.mutate()}
                  >
                    {applyConsensusMutation.isPending
                      ? 'Aplicant...'
                      : 'Aplicar consens com a resultat oficial'}
                  </button>
                </div>
              )}

              {panelConsensus && 'error' in panelConsensus && (
                <p
                  style={{
                    color: 'var(--color-danger)',
                    fontSize: 'var(--font-size-sm)',
                    marginTop: 'var(--spacing-md)',
                  }}
                >
                  {panelConsensus.error as string}
                </p>
              )}
            </div>
          </details>
        </>
      )}

      {step === 5 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Actors</h2>
          <MethodologyHint title="Metodologia Godet — Pas 4: Actors del sistema" defaultOpen={false}>
            <p>
              Actors amb capacitat d&apos;influir sobre l&apos;evolució del sistema.
              <strong> Força (1–5):</strong> 5=caps d&apos;estat · 4=ministres/grans institucions ·
              3=alts funcionaris · 2=portaveus · 1=actors locals.
            </p>
            <p>
              <strong>Fins estratègics:</strong> objectius a 10–20 anys.
              El MACTOR analitzarà convergències i divergències entre actors respecte als objectius.
              Nombre recomanat: <strong>5–10 actors</strong>.
            </p>
          </MethodologyHint>
          {actors.map((a, idx) => (
            <div key={idx} className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
              <div className="prospective-field">
                <label>Codi</label>
                <input
                  value={a.code}
                  onChange={(e) =>
                    setActors((x) => x.map((row, i) => (i === idx ? { ...row, code: e.target.value } : row)))
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Nom</label>
                <input
                  value={a.name}
                  onChange={(e) =>
                    setActors((x) => x.map((row, i) => (i === idx ? { ...row, name: e.target.value } : row)))
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Força (1–5)</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={a.force}
                  onChange={(e) =>
                    setActors((x) =>
                      x.map((row, i) => (i === idx ? { ...row, force: Number(e.target.value) } : row)),
                    )
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Fins (separats per coma)</label>
                <input
                  value={a.fins}
                  onChange={(e) =>
                    setActors((x) => x.map((row, i) => (i === idx ? { ...row, fins: e.target.value } : row)))
                  }
                />
              </div>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => setActors((x) => x.filter((_, i) => i !== idx))}
              >
                Eliminar
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-primary"
            onClick={() =>
              setActors((x) => [...x, { code: `A${x.length + 1}`, name: '', force: 3, fins: '' }])
            }
          >
            Afegir actor
          </button>
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(4)}>
              Enrere
            </button>
            <button
              type="button"
              className="btn btn-accent"
              disabled={saveActorsMutation.isPending}
              onClick={() => saveActorsMutation.mutate()}
            >
              Guardar i MACTOR
            </button>
          </div>
        </>
      )}

      {step === 6 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Objectius i matriu de postures (−2…+2)</h2>
          <MethodologyHint title="Metodologia Godet — Pas 5: MACTOR (postures actors/objectius)" defaultOpen={false}>
            <p>
              Puntua la postura de cada actor respecte a cada objectiu estratègic.
            </p>
            <code className="mhint-example">
              {'+2 = molt favorable (objectiu prioritari)\n'}
              {'+1 = favorable (suporta però no prioritari)\n'}
              {' 0 = neutral\n'}
              {'−1 = contrari (s\'hi oposa però no prioritàriament)\n'}
              {'−2 = molt contrari (oposició activa i prioritària)'}
            </code>
            <p>
              El càlcul mesura la <strong>mobilització</strong> de cada actor (quant s&apos;implica)
              i les <strong>convergències</strong> (quants objectius comparteixen actors).
              Alta convergència = aliança potencial.
            </p>
          </MethodologyHint>
          {objectives.map((o, idx) => (
            <div key={idx} className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
              <div className="prospective-field">
                <label>Codi objectiu</label>
                <input
                  value={o.id}
                  onChange={(e) =>
                    setObjectives((x) => x.map((row, i) => (i === idx ? { ...row, id: e.target.value } : row)))
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Nom</label>
                <input
                  value={o.name}
                  onChange={(e) =>
                    setObjectives((x) => x.map((row, i) => (i === idx ? { ...row, name: e.target.value } : row)))
                  }
                />
              </div>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => setObjectives((x) => x.filter((_, i) => i !== idx))}
              >
                Eliminar
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-primary"
            onClick={() =>
              setObjectives((x) => [...x, { id: `O${x.length + 1}`, name: '' }])
            }
          >
            Afegir objectiu
          </button>

          <h3 style={{ marginTop: 'var(--spacing-lg)', color: 'var(--color-primary)' }}>
            Postures actors × objectius
          </h3>
          <div className="prospective-matrix-wrap">
            <table className="prospective-matrix">
              <thead>
                <tr>
                  <th />
                  {objectives.map((o, j) => (
                    <th key={j}>{o.id}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {postures.map((row, i) => (
                  <tr key={i}>
                    <th>{actors[i]?.code ?? i}</th>
                    {row.map((cell, j) => (
                      <td key={j}>
                        <input
                          type="number"
                          min={-2}
                          max={2}
                          value={cell}
                          onChange={(e) => updatePosture(i, j, Number(e.target.value))}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(5)}>
              Enrere
            </button>
            <button
              type="button"
              className="btn btn-accent"
              disabled={saveObjectivesAndMactorMutation.isPending}
              onClick={() => saveObjectivesAndMactorMutation.mutate()}
            >
              Guardar objectius i calcular MACTOR
            </button>
          </div>

          {mactorResult && (() => {
            const mobA = (mactorResult.mobilisation_actors as number[]) ?? []
            const mobO = (mactorResult.mobilisation_objectives as number[]) ?? []
            const conv = (mactorResult.convergences as number[][]) ?? []
            const aCodes =
              (mactorResult.actor_codes as string[]) ?? actors.map((_, i) => `A${i + 1}`)
            const oCodes =
              (mactorResult.objective_codes as string[]) ?? objectives.map((_, i) => `O${i + 1}`)
            const maxMob = Math.max(...mobA, ...mobO, 1)
            const maxConv = Math.max(...conv.flat(), 1)

            const convBg = (v: number, i: number, j: number) => {
              if (i === j) return 'var(--color-gray-100)'
              const pct = v / maxConv
              if (pct > 0.6) return 'rgba(40,167,69,0.2)'
              if (pct > 0.3) return 'rgba(255,193,7,0.2)'
              return 'transparent'
            }

            return (
              <div className="mactor-result-wrap">
                <p className="mactor-result-title">Resultat MACTOR</p>

                <p style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-gray-600)', marginBottom: 6 }}>
                  Mobilització per actor
                </p>
                {mobA.map((mob, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span
                      style={{
                        width: 32,
                        fontWeight: 600,
                        color: 'var(--color-primary)',
                        flexShrink: 0,
                        fontSize: 'var(--font-size-xs)',
                      }}
                    >
                      {aCodes[i]}
                    </span>
                    <div style={{ flex: 1, background: 'var(--color-gray-200)', borderRadius: 3, height: 14, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${(mob / maxMob) * 100}%`,
                          background: 'var(--color-primary)',
                          height: '100%',
                          borderRadius: 3,
                          transition: 'width .4s',
                        }}
                      />
                    </div>
                    <span style={{ width: 24, textAlign: 'right', fontWeight: 600, fontSize: 'var(--font-size-xs)' }}>
                      {mob}
                    </span>
                  </div>
                ))}

                <p style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-gray-600)', marginTop: 12, marginBottom: 6 }}>
                  Mobilització per objectiu
                </p>
                {mobO.map((mob, j) => (
                  <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span
                      style={{
                        width: 32,
                        fontWeight: 600,
                        color: 'var(--color-success)',
                        flexShrink: 0,
                        fontSize: 'var(--font-size-xs)',
                      }}
                    >
                      {oCodes[j]}
                    </span>
                    <div style={{ flex: 1, background: 'var(--color-gray-200)', borderRadius: 3, height: 14, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${(mob / maxMob) * 100}%`,
                          background: 'var(--color-success)',
                          height: '100%',
                          borderRadius: 3,
                        }}
                      />
                    </div>
                    <span style={{ width: 24, textAlign: 'right', fontWeight: 600, fontSize: 'var(--font-size-xs)' }}>
                      {mob}
                    </span>
                  </div>
                ))}

                {conv.length > 1 && (
                  <>
                    <p style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-gray-600)', marginTop: 16, marginBottom: 6 }}>
                      Convergències entre actors (objectius compartits)
                    </p>
                    <div style={{ overflowX: 'auto' }}>
                      <table className="mactor-conv-table">
                        <thead>
                          <tr>
                            <th>↓ vs →</th>
                            {aCodes.map((c, j) => (
                              <th key={j}>{c}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {conv.map((row, i) => (
                            <tr key={i}>
                              <th style={{ textAlign: 'left', background: 'var(--color-primary)', color: 'white' }}>
                                {aCodes[i]}
                              </th>
                              {row.map((val, j) => (
                                <td
                                  key={j}
                                  style={{ background: convBg(val, i, j) }}
                                  className={
                                    i !== j
                                      ? val / maxConv > 0.6
                                        ? 'mactor-conv-high'
                                        : val / maxConv > 0.3
                                          ? 'mactor-conv-mid'
                                          : 'mactor-conv-low'
                                      : ''
                                  }
                                >
                                  {i === j ? '—' : val}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)', marginTop: 4 }}>
                      Verd = alta convergència (aliança) · Groc = moderada · Gris = baixa (possible conflicte)
                    </p>
                  </>
                )}
              </div>
            )
          })()}
        </>
      )}

      {step === 7 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Components morfològics</h2>
          <MethodologyHint title="Metodologia Godet — Pas 6: Anàlisi morfològic (Zwicky)" defaultOpen={false}>
            <p>
              Explora sistemàticament tots els futurs possibles.
              Cada <strong>component</strong> és una dimensió d&apos;evolució del sistema.
              Cada component té <strong>2–4 configuracions</strong> (estats alternatius).
            </p>
            <code className="mhint-example">
              {'C1: Estat BRI → Expansió plena | Estancament | Retrocés\n'}
              {'C2: Cohesió QUAD → Alta cohesió | Divisió interna\n'}
              {'Espai morfològic = 3 × 2 = 6 combinacions possibles'}
            </code>
            <p>
              EINA selecciona automàticament 4 escenaris representatius de l&apos;espai:
              Infern (pitjor), Tensió Crònica, Equilibri Dinàmic, i Cel (millor).
            </p>
          </MethodologyHint>
          <p style={{ color: 'var(--color-gray-600)' }}>
            Una configuració per línia dins de cada component (espai combinatori simplificat).
          </p>
          {morphRows.map((m, idx) => (
            <div key={idx} className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
              <div className="prospective-field">
                <label>Codi</label>
                <input
                  value={m.id}
                  onChange={(e) =>
                    setMorphRows((x) => x.map((row, i) => (i === idx ? { ...row, id: e.target.value } : row)))
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Nom del component</label>
                <input
                  value={m.name}
                  onChange={(e) =>
                    setMorphRows((x) => x.map((row, i) => (i === idx ? { ...row, name: e.target.value } : row)))
                  }
                />
              </div>
              <div className="prospective-field">
                <label>Configuracions (una per línia)</label>
                <textarea
                  rows={4}
                  value={m.configsText}
                  onChange={(e) =>
                    setMorphRows((x) =>
                      x.map((row, i) => (i === idx ? { ...row, configsText: e.target.value } : row)),
                    )
                  }
                />
              </div>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => setMorphRows((x) => x.filter((_, i) => i !== idx))}
              >
                Eliminar
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-primary"
            onClick={() =>
              setMorphRows((x) => [...x, { id: `C${x.length + 1}`, name: '', configsText: 'Estat A\nEstat B' }])
            }
          >
            Afegir component
          </button>

          <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
            <h3 style={{ color: 'var(--color-primary)', marginBottom: 'var(--spacing-sm)' }}>
              Matriu de compatibilitat Zwicky
            </h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)' }}>
              Desmarca les parelles de configuracions <strong>incompatibles</strong> entre components
              diferents. L&apos;espai combinatori es filtra abans de seleccionar els 4 escenaris.
            </p>
            <p style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-sm)' }}>
              Combinacions totals: <strong>{liveMorphTotal}</strong>
              {morphSpaceStats && (
                <>
                  {' · '}
                  Vàlides després del filtre: <strong>{morphSpaceStats.valid_combinations}</strong>
                  {morphSpaceStats.filtered_out > 0 && (
                    <span> ({morphSpaceStats.filtered_out} excloses)</span>
                  )}
                </>
              )}
              {!morphSpaceStats && incompatibilities.length > 0 && (
                <span> · {incompatibilities.length} parelles marcades com a incompatibles</span>
              )}
            </p>
            {morphRows.flatMap((rowA, i) =>
              morphRows.slice(i + 1).map((rowB, jOff) => {
                const j = i + 1 + jOff
                const cfgsA = morphConfigsFromText(rowA.configsText)
                const cfgsB = morphConfigsFromText(rowB.configsText)
                if (cfgsA.length === 0 || cfgsB.length === 0) return null
                return (
                  <div key={`${rowA.id}-${rowB.id}`} style={{ marginTop: 'var(--spacing-md)' }}>
                    <h4 style={{ fontSize: 'var(--font-size-sm)', marginBottom: 4 }}>
                      {rowA.id || `C${i + 1}`} × {rowB.id || `C${j + 1}`}
                    </h4>
                    <div style={{ overflowX: 'auto' }}>
                      <table className="prospective-matrix morph-compat-table">
                        <thead>
                          <tr>
                            <th />
                            {cfgsB.map((cb) => (
                              <th key={cb} style={{ fontSize: 'var(--font-size-xs)' }}>
                                {cb}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {cfgsA.map((ca) => (
                            <tr key={ca}>
                              <th style={{ fontSize: 'var(--font-size-xs)', textAlign: 'left' }}>{ca}</th>
                              {cfgsB.map((cb) => {
                                const compatible = !isPairIncompatible(
                                  incompatibilities,
                                  rowA.id,
                                  ca,
                                  rowB.id,
                                  cb,
                                )
                                return (
                                  <td key={cb} style={{ textAlign: 'center' }}>
                                    <input
                                      type="checkbox"
                                      checked={compatible}
                                      title={compatible ? 'Compatible' : 'Incompatible'}
                                      onChange={(e) =>
                                        toggleMorphCompatibility(
                                          rowA.id,
                                          ca,
                                          rowB.id,
                                          cb,
                                          e.target.checked,
                                        )
                                      }
                                    />
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )
              }),
            )}
            {morphSpaceStats?.scenario_configs && (
              <div style={{ marginTop: 'var(--spacing-md)' }}>
                <h4 style={{ fontSize: 'var(--font-size-sm)' }}>Configuracions d&apos;escenari seleccionades</h4>
                <ul style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-700)' }}>
                  {morphSpaceStats.scenario_configs.map((s) => (
                    <li key={s.scenario_type}>
                      <strong>{s.scenario_type}</strong>: {s.config || '—'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(6)}>
              Enrere
            </button>
            <button
              type="button"
              className="btn btn-accent"
              disabled={saveMorphMutation.isPending}
              onClick={() => saveMorphMutation.mutate()}
            >
              Guardar i escenaris
            </button>
          </div>
        </>
      )}

      {step === 8 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Escenaris narratius (SSE + Claude)</h2>

          <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
            <h3 style={{ color: 'var(--color-primary)' }}>SMIC — Probabilitats creuades</h3>
            <MethodologyHint title="Metodologia Godet — SMIC" defaultOpen={false}>
              <p>
                Matriu d&apos;impacte creuat 4×4: com cada escenari condiciona la probabilitat dels
                altres. Valors de <strong>-2</strong> (inhibeix) a <strong>+2</strong> (reforça).
              </p>
            </MethodologyHint>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              {SCENARIO_NAMES.map((name, i) => (
                <div key={name} className="prospective-field">
                  <label style={{ fontSize: 'var(--font-size-xs)' }}>{name}</label>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={smicInitial[i]}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      setSmicInitial((prev) => prev.map((p, j) => (j === i ? v : p)))
                    }}
                  />
                </div>
              ))}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="prospective-matrix">
                <thead>
                  <tr>
                    <th>Impacte →</th>
                    {SCENARIO_NAMES.map((n) => (
                      <th key={n} style={{ fontSize: 'var(--font-size-xs)' }}>
                        {n.split(' ').slice(-1)[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SCENARIO_NAMES.map((rowName, i) => (
                    <tr key={rowName}>
                      <th style={{ fontSize: 'var(--font-size-xs)', textAlign: 'left' }}>
                        {rowName.split(' ').slice(-1)[0]}
                      </th>
                      {SCENARIO_NAMES.map((_, j) => (
                        <td key={j}>
                          <input
                            type="number"
                            min={-2}
                            max={2}
                            step={0.5}
                            value={smicCross[i][j]}
                            disabled={i === j}
                            onChange={(e) => {
                              const v = Number(e.target.value)
                              setSmicCross((prev) =>
                                prev.map((row, ri) =>
                                  ri === i ? row.map((cell, ci) => (ci === j ? v : cell)) : row,
                                ),
                              )
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="prospective-actions" style={{ marginTop: 'var(--spacing-md)' }}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={smicMutation.isPending}
                onClick={() => smicMutation.mutate()}
              >
                Calcular probabilitats SMIC
              </button>
            </div>
            {smicResult && (
              <div className="prospective-alert prospective-alert--success" style={{ marginTop: 'var(--spacing-md)' }}>
                Probabilitats finals:{' '}
                {SCENARIO_NAMES.map((name, i) => (
                  <span key={name}>
                    {name.split(' ').slice(-1)[0]}={smicResult.final_labels[i]} (
                    {(smicResult.final_probs[i] * 100).toFixed(0)}%)
                    {i < 3 ? ' · ' : ''}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(7)}>
              Enrere
            </button>
            <button type="button" className="btn btn-accent" onClick={() => startScenarioStream()}>
              Generar escenaris (streaming)
            </button>
          </div>
          {streamingDone && (
            <div className="prospective-alert prospective-alert--success">Generació completada.</div>
          )}

          {[0, 1, 2, 3].map((idx) => (
            <div key={idx} className="prospective-stream-panel">
              <h3>{streamMeta[idx] ?? `Escenari ${idx + 1}`}</h3>
              <div className="prospective-narrative">{streamTexts[idx] ?? ''}</div>
            </div>
          ))}

          <h3 style={{ marginTop: 'var(--spacing-xl)', color: 'var(--color-primary)' }}>
            Desats al servidor
          </h3>
          <ul className="project-list">
            {(savedScenarios as { id: number; name: string; narrative: string }[]).map((s) => (
              <li key={s.id} style={{ cursor: 'default' }}>
                <strong>{s.name}</strong>
                <span className="badge">{s.narrative.length} caràcters</span>
                <button
                  type="button"
                  className="btn"
                  style={{ fontSize: 'var(--font-size-xs)', marginTop: 'var(--spacing-sm)' }}
                  onClick={async () => {
                    if (!projectId || !s.id) return
                    try {
                      const res = await prospectiveService.createMonitors(projectId, s.id)
                      alert(
                        `${res.created} indicador${res.created !== 1 ? 's' : ''} d'alerta activat${res.created !== 1 ? 's' : ''} per "${s.name}"`,
                      )
                    } catch {
                      alert("Error activant el monitoratge. Comprova la consola.")
                    }
                  }}
                >
                  Activar monitoratge d&apos;alertes
                </button>
              </li>
            ))}
          </ul>

          {savedScenarios.length >= 2 && (
            <details style={{ marginTop: 'var(--spacing-xl)' }}>
              <summary
                style={{
                  cursor: 'pointer',
                  fontWeight: 600,
                  color: 'var(--color-primary)',
                  fontSize: 'var(--font-size-sm)',
                  padding: 'var(--spacing-sm) 0',
                }}
              >
                SMIC — Probabilitats creuades entre escenaris
              </summary>
              <div
                style={{
                  marginTop: 'var(--spacing-md)',
                  padding: 'var(--spacing-md)',
                  background: 'var(--color-gray-50)',
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)', marginBottom: 'var(--spacing-md)' }}>
                  Si l&apos;escenari de la <strong>fila</strong> ocorre, quina probabilitat té el de la{' '}
                  <strong>columna</strong>? (0.0 = impossibilita · 1.0 = garanteix · 0.5 = independent)
                </p>
                <div style={{ overflowX: 'auto' }}>
                  <table className="prospective-matrix">
                    <thead>
                      <tr>
                        <th>Si ocorre ↓ / Prob de →</th>
                        {(savedScenarios as { id: number; name: string }[]).slice(0, 4).map((s) => (
                          <th key={s.id} style={{ fontSize: '10px' }}>
                            {s.name.replace('Escenari ', '')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(savedScenarios as { id: number; name: string }[]).slice(0, 4).map((s, i) => (
                        <tr key={s.id}>
                          <th style={{ fontSize: '10px', textAlign: 'left' }}>
                            {s.name.replace('Escenari ', '')}
                          </th>
                          {Array.from({ length: Math.min(4, savedScenarios.length) }, (_, j) => (
                            <td key={j} style={{ textAlign: 'center' }}>
                              {i === j ? (
                                '—'
                              ) : (
                                <input
                                  type="number"
                                  min={0}
                                  max={1}
                                  step={0.1}
                                  value={smicMatrix[i]?.[j] ?? 0.5}
                                  style={{ width: 52, textAlign: 'center' }}
                                  onChange={(e) => {
                                    const val = Math.max(0, Math.min(1, parseFloat(e.target.value) || 0))
                                    setSmicMatrix((prev) => {
                                      const next = prev.map((r) => [...r])
                                      if (!next[i]) next[i] = []
                                      next[i][j] = val
                                      return next
                                    })
                                  }}
                                />
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ marginTop: 'var(--spacing-md)' }}
                  disabled={!projectId}
                  onClick={async () => {
                    if (!projectId) return
                    const result = await prospectiveService.computeSmicBayesian(projectId, smicMatrix)
                    setSmicBayesianResult(result)
                    void queryClient.invalidateQueries({ queryKey: ['prospective-scenarios', projectId] })
                  }}
                >
                  Calcular probabilitats ajustades (SMIC)
                </button>
                {smicBayesianResult && (
                  <div style={{ marginTop: 'var(--spacing-md)' }}>
                    <p style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--color-primary)' }}>
                      Probabilitats ajustades:
                    </p>
                    {smicBayesianResult.results.map((r) => (
                      <div
                        key={r.name}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 'var(--spacing-md)',
                          padding: '6px 0',
                          borderBottom: '1px solid var(--color-gray-100)',
                          fontSize: 'var(--font-size-xs)',
                        }}
                      >
                        <span style={{ flex: 1, fontWeight: 500 }}>{r.name}</span>
                        <span style={{ color: 'var(--color-gray-500)' }}>
                          P(prior)={Math.round(r.prior_probability * 100)}%
                        </span>
                        <span
                          style={{
                            fontWeight: 700,
                            color:
                              r.adjusted_probability > 0.45
                                ? 'var(--color-danger)'
                                : r.adjusted_probability > 0.25
                                  ? '#856404'
                                  : 'var(--color-success)',
                          }}
                        >
                          → P(SMIC)={Math.round(r.adjusted_probability * 100)}% [{r.label}]
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </details>
          )}

          {projectId !== null && savedScenarios.length > 0 && (
            <div
              className="prospective-actions"
              style={{
                marginTop: 'var(--spacing-xl)',
                paddingTop: 'var(--spacing-lg)',
                borderTop: '1px solid var(--color-gray-200)',
              }}
            >
              <span
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-gray-600)',
                  alignSelf: 'center',
                }}
              >
                Descarregar informe complet:
              </span>
              <button
                type="button"
                className="btn btn-accent"
                onClick={() => prospectiveService.exportPdf(projectId)}
              >
                PDF
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => prospectiveService.exportDocx(projectId)}
              >
                DOCX (Word)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
