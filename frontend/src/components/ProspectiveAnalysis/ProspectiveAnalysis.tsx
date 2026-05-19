import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { casesService, extractService, prospectiveService } from '../../services/api'
import WorkflowProgress from '../shared/WorkflowProgress'
import MethodologyHint from './MethodologyHint'
import './ProspectiveAnalysis.css'

const STEP_LABELS = [
  'Extracció OSINT',
  'Projecte',
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

function emptyMatrix(n: number): number[][] {
  return Array.from({ length: n }, () => Array.from({ length: n }, () => 0))
}

export interface ProspectiveAnalysisProps {
  /** Pas inicial del wizard (0–7) quan s’entra des d’una ruta concreta del menú */
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
      setStep(3)
    },
    onError: () => setErrorMsg('Error guardant variables.'),
  })

  const micmacMutation = useMutation({
    mutationFn: () => prospectiveService.computeMicmac(projectId!, micmacMatrix),
    onSuccess: (data: Record<string, unknown>) => {
      setMicmacResult(data)
      setErrorMsg(null)
      setStep(4)
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
      setStep(5)
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
      setStep(6)
    },
    onError: () => setErrorMsg('Error amb objectius o MACTOR.'),
  })

  const saveMorphMutation = useMutation({
    mutationFn: () =>
      prospectiveService.saveComponents(
        projectId!,
        morphRows.map((m) => ({
          id: m.id,
          name: m.name,
          configs: m.configsText
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean)
            .map((label) => ({ label, desc: '' })),
        })),
      ),
    onSuccess: () => {
      setErrorMsg(null)
      setStep(7)
    },
    onError: () => setErrorMsg('Error guardant components morfològics.'),
  })

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
    enabled: projectId !== null && step === 7,
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
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(1)}>
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

      {step === 3 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Matriu MIC-MAC (0–3, diagonal 0)</h2>
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
          {micmacResult && (() => {
            const sectors = (micmacResult.sectors as Array<{
              index: number
              code: string
              sector: string
              motricitat: number
              dependencia: number
            }>) ?? []
            const vbFromKey = micmacResult.vb_index as number | undefined
            const vrFromKey = micmacResult.vr_index as number | undefined
            const vbFromObj = (micmacResult.variable_blanc as { index: number } | undefined)?.index
            const vrFromObj = (micmacResult.variable_risc as { index: number } | undefined)?.index
            const vbIdx = vbFromKey ?? vbFromObj ?? -1
            const vrIdx = vrFromKey ?? vrFromObj ?? -1

            if (sectors.length === 0) {
              return (
                <div className="prospective-alert prospective-alert--success">
                  MIC-MAC calculat. VB={vbIdx} VR={vrIdx}
                </div>
              )
            }

            const allMot = sectors.map((s) => s.motricitat)
            const allDep = sectors.map((s) => s.dependencia)
            const maxMot = Math.max(...allMot, 1)
            const maxDep = Math.max(...allDep, 1)
            const avgMot = allMot.reduce((a, b) => a + b, 0) / allMot.length
            const avgDep = allDep.reduce((a, b) => a + b, 0) / allDep.length

            const W = 480
            const H = 380
            const PAD = 52
            const toX = (dep: number) => PAD + (dep / maxDep) * (W - PAD * 2)
            const toY = (mot: number) => H - PAD - (mot / maxMot) * (H - PAD * 2)
            const avgX = toX(avgDep)
            const avgY = toY(avgMot)

            const COLORS: Record<string, string> = {
              Motriu: '#1e3a5f',
              'Clau/Conflicte': '#dc3545',
              Resultant: '#28a745',
              Excluyent: '#6c757d',
              Autònom: '#6c757d',
            }

            return (
              <div className="micmac-chart-wrap">
                <p className="micmac-chart-title">Gràfic motricitat / dependència — Sectors Godet</p>
                <svg
                  viewBox={`0 0 ${W} ${H}`}
                  style={{
                    width: '100%',
                    maxWidth: W,
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: 'var(--radius-md)',
                    background: '#fafbfc',
                  }}
                  aria-label="Gràfic MIC-MAC"
                >
                  <rect x={PAD} y={PAD} width={avgX - PAD} height={avgY - PAD} fill="rgba(30,58,95,0.07)" />
                  <rect x={avgX} y={PAD} width={W - PAD - avgX} height={avgY - PAD} fill="rgba(220,53,69,0.08)" />
                  <rect x={avgX} y={avgY} width={W - PAD - avgX} height={H - PAD - avgY} fill="rgba(40,167,69,0.07)" />
                  <rect x={PAD} y={avgY} width={avgX - PAD} height={H - PAD - avgY} fill="rgba(108,117,125,0.05)" />

                  <text x={PAD + 6} y={PAD + 16} fontSize="10" fill="#1e3a5f" fontWeight="600">Motriu</text>
                  <text x={avgX + 4} y={PAD + 16} fontSize="10" fill="#dc3545" fontWeight="600">Clau/Conflicte</text>
                  <text x={avgX + 4} y={H - PAD - 6} fontSize="10" fill="#28a745" fontWeight="600">Resultant</text>
                  <text x={PAD + 6} y={H - PAD - 6} fontSize="10" fill="#6c757d" fontWeight="600">Autònom</text>

                  <line x1={avgX} y1={PAD} x2={avgX} y2={H - PAD} stroke="#bbb" strokeWidth="1" strokeDasharray="4 3" />
                  <line x1={PAD} y1={avgY} x2={W - PAD} y2={avgY} stroke="#bbb" strokeWidth="1" strokeDasharray="4 3" />

                  <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#999" strokeWidth="1.5" />
                  <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#999" strokeWidth="1.5" />
                  <text x={W / 2} y={H - 8} fontSize="11" fill="#6c757d" textAnchor="middle">Dependència →</text>
                  <text
                    x={14}
                    y={H / 2}
                    fontSize="11"
                    fill="#6c757d"
                    textAnchor="middle"
                    transform={`rotate(-90,14,${H / 2})`}
                  >
                    Motricitat →
                  </text>

                  {sectors.map((s) => {
                    const cx = toX(s.dependencia)
                    const cy = toY(s.motricitat)
                    const col = COLORS[s.sector] ?? '#6c757d'
                    const isVB = s.index === vbIdx
                    const isVR = s.index === vrIdx && s.index !== vbIdx
                    const r = isVB || isVR ? 11 : 8
                    return (
                      <g key={s.index}>
                        <circle
                          cx={cx}
                          cy={cy}
                          r={r}
                          fill={col}
                          opacity={0.85}
                          stroke={isVB ? '#d4a843' : isVR ? '#ff4444' : 'white'}
                          strokeWidth={isVB || isVR ? 2.5 : 1.5}
                        />
                        <text x={cx + r + 3} y={cy + 4} fontSize="11" fontWeight="600" fill={col}>
                          {s.code}
                          {isVB ? ' VB' : isVR ? ' VR' : ''}
                        </text>
                      </g>
                    )
                  })}
                </svg>

                <div className="micmac-sectors-legend">
                  {([
                    { l: 'Motriu', c: '#1e3a5f', d: 'Alta mot, baixa dep' },
                    { l: 'Clau/Conflicte', c: '#dc3545', d: 'Alta mot, alta dep' },
                    { l: 'Resultant', c: '#28a745', d: 'Baixa mot, alta dep' },
                    { l: 'Autònom', c: '#6c757d', d: 'Baixa mot, baixa dep' },
                  ] as const).map(({ l, c, d }) => (
                    <span key={l} className="micmac-sector-badge" style={{ background: `${c}18`, color: c }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
                      {l} — {d}
                    </span>
                  ))}
                </div>

                {(vbIdx >= 0 || vrIdx >= 0) && (
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
                        <br />
                        <span style={{ color: 'var(--color-gray-600)', fontSize: 'var(--font-size-xs)' }}>
                          La palanca estratègica del sistema. Actua sobre ella per canviar el futur.
                        </span>
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
                        <br />
                        <span style={{ color: 'var(--color-gray-600)', fontSize: 'var(--font-size-xs)' }}>
                          Punt d&apos;inestabilitat: petits canvis, efectes imprevisibles.
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })()}
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(2)}>
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

      {step === 4 && projectId !== null && (
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
            <button type="button" className="btn" onClick={() => setStep(3)}>
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

      {step === 5 && projectId !== null && (
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
            <button type="button" className="btn" onClick={() => setStep(4)}>
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

      {step === 6 && projectId !== null && (
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
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(5)}>
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

      {step === 7 && projectId !== null && (
        <>
          <h2 style={{ color: 'var(--color-primary)' }}>Escenaris narratius (SSE + Claude)</h2>
          <div className="prospective-actions">
            <button type="button" className="btn" onClick={() => setStep(6)}>
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
