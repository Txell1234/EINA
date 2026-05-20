/**
 * DirectAnalysis — Paste any strategic text, get full Godet analysis
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useCase } from '../../contexts/CaseContext'
import { directAnalysisService } from '../../services/api'
import './DirectAnalysis.css'

interface Variable {
  code: string
  name: string
  type: string
  desc: string
  rationale?: string
}
interface Actor {
  code: string
  name: string
  force: number
  strategic_goals: string[]
  rationale?: string
}
interface MorphComponent {
  code: string
  name: string
  configurations: Array<{ label: string; desc: string }>
}
interface Statement {
  actor: string
  posture_toward: string
  posture_value: number
  topic: string
  statement: string
  framing: string
}
interface AnalysisResult {
  hypothesis: string
  context: string
  confidence: number
  warnings: string[]
  variables: Variable[]
  actors: Actor[]
  components: MorphComponent[]
  statements: Statement[]
  text_length: number
  truncated?: boolean
  llm_provider?: string
  llm_model?: string
  error?: string
}

function postureColor(v: number) {
  if (v >= 2) return '#28a745'
  if (v >= 1) return '#85c985'
  if (v === 0) return '#6c757d'
  if (v >= -1) return '#e07840'
  return '#dc3545'
}
function confidenceColor(c: number) {
  if (c >= 0.75) return 'var(--color-success)'
  if (c >= 0.5) return '#e6a817'
  return 'var(--color-danger)'
}
function confidenceLabel(c: number) {
  if (c >= 0.75) return 'Alta'
  if (c >= 0.5) return 'Moderada'
  return 'Baixa'
}

const EXAMPLE_TEXTS = [
  {
    label: 'Indo-Pacífic BRI vs QUAD',
    text: `La Belt and Road Initiative xinesa ha avançat en 8 nous països de l'Indo-Pacífic durant 2024, mentre el QUAD ha intensificat els seus exercicis militars conjunts. Índia ha proposat el corredor IMEC com a alternativa a la BRI, amb suport inicial del G7. La Unió Europea ha actualitzat la seva estratègia Indo-Pacífica, senyalant una implicació més activa. El secretari d'estat nord-americà ha declarat que "la competència estratègica amb la Xina és la definició del nostre temps". El ministre d'afers exteriors xinès ha qualificat el QUAD d'"OTAN asiàtica". L'Índia s'ha negat a condemnar la invasió d'Ucraïna per mantenir la seva autonomia estratègica, mentre aprofundeix els llaços econòmics amb Rússia. Varis països de l'ASEAN han expressat preocupació per quedar atrapats entre els dos blocs.`,
  },
  {
    label: 'Transició energètica Europa',
    text: `La dependència del gas rus ha accelerat la transició energètica europea, però ha creat noves vulnerabilitats en metalls crítics controlats majoritàriament per la Xina. Alemanya ha anunciat un pla d'inversió de 200.000M€ en energies renovables fins 2035. França defensa el nuclear com a energia de transició, provocant tensions amb Alemanya. Els països bàltics han accelerat la desconnexió de la xarxa elèctrica russa. Polònia resisteix el ritme de transició per dependència del carbó. La Comissió Europea ha proposat el Net-Zero Industry Act per reduir dependència exterior en cadenes de subministrament verdes.`,
  },
]

export default function DirectAnalysis() {
  const { activeCase } = useCase()
  const navigate = useNavigate()

  const [text, setText] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [localResult, setLocalResult] = useState<AnalysisResult | null>(null)
  const [editingVar, setEditingVar] = useState<number | null>(null)
  const [projectTitle, setProjectTitle] = useState('')
  const [activeTab, setActiveTab] = useState<
    'variables' | 'actors' | 'components' | 'statements'
  >('variables')
  const [applied, setApplied] = useState(false)

  const { data: llmConfig } = useQuery({
    queryKey: ['llm-config'],
    queryFn: () => directAnalysisService.getLlmConfig(),
  })

  const llmLabel =
    llmConfig?.provider === 'openai'
      ? 'OpenAI'
      : llmConfig?.provider === 'gemini'
        ? 'Google Gemini'
        : llmConfig?.provider === 'anthropic'
          ? 'Anthropic Claude'
          : 'IA'

  const analyzeMutation = useMutation({
    mutationFn: () => directAnalysisService.analyze(text, activeCase?.id),
    onSuccess: (data) => {
      const r = data as AnalysisResult
      setResult(r)
      setLocalResult(JSON.parse(JSON.stringify(r)) as AnalysisResult)
      const hyp = r.hypothesis
      if (hyp) {
        setProjectTitle(hyp.length > 60 ? hyp.slice(0, 57) + '...' : hyp)
      }
      setApplied(false)
      setEditingVar(null)
    },
  })

  const applyMutation = useMutation({
    mutationFn: () =>
      directAnalysisService.applyToProject(
        localResult ?? result,
        projectTitle,
        activeCase?.id,
      ),
    onSuccess: (data) => {
      setApplied(true)
      setTimeout(() => {
        navigate(`/prospective/project?project=${(data as { project_id: number }).project_id}`)
      }, 1500)
    },
  })

  const wordCount = text.trim().split(/\s+/).filter(Boolean).length
  const charCount = text.length

  const displayResult = localResult ?? result

  return (
    <div className="da-page">
      <div className="da-header">
        <div>
          <h1 className="da-title">Anàlisi directa de text</h1>
          <p className="da-subtitle">
            Enganxa qualsevol informe, article o document estratègic.
            EINA extreu automàticament totes les variables MIC-MAC, actors,
            postures i components morfològics per al wizard prospectiu Godet.
          </p>
        </div>
      </div>

      <div className="da-layout">
        <div className="da-input-col">
          <div className="card da-input-card">
            <div className="da-examples">
              <span className="da-examples-label">Exemples ràpids:</span>
              {EXAMPLE_TEXTS.map((ex) => (
                <button
                  key={ex.label}
                  type="button"
                  className="btn da-example-btn"
                  onClick={() => setText(ex.text)}
                >
                  {ex.label}
                </button>
              ))}
            </div>

            <textarea
              className="da-textarea"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                "Enganxa aquí el teu informe d'intel·ligència, article de fons, " +
                "notes de reunió o document estratègic.\n\n" +
                "EINA extraurà:\n" +
                "• Variables MIC-MAC formulades com «Grau en què...»\n" +
                "• Actors amb força estimada (1-5)\n" +
                "• Components morfològics amb configuracions alternatives\n" +
                "• Declaracions amb postures (-2..+2)\n" +
                "• Hipòtesi del conflicte estratègic\n\n" +
                "Longitud recomanada: 300-3.000 paraules.\n" +
                "Textos fins a 6.000 paraules s'analitzen complets."
              }
            />

            <div className="da-input-footer">
              <span className="da-counter">
                {wordCount.toLocaleString()} paraules · {charCount.toLocaleString()} caràcters
                {charCount > 8000 && (
                  <span className="da-counter--warn">
                    {' '}
                    (s&apos;analitzaran els primers ~6.000 paraules)
                  </span>
                )}
              </span>
              <button
                type="button"
                className="btn btn-accent da-analyze-btn"
                disabled={
                  text.trim().length < 100 ||
                  analyzeMutation.isPending ||
                  llmConfig?.configured === false
                }
                onClick={() => analyzeMutation.mutate()}
              >
                {analyzeMutation.isPending ? (
                  <>
                    <span className="spinner da-spinner" />
                    Analitzant...
                  </>
                ) : llmConfig?.configured === false ? (
                  'Configura una clau LLM al .env'
                ) : (
                  `Analitzar amb ${llmLabel} →`
                )}
              </button>
            </div>

            {analyzeMutation.isError && (
              <div className="da-alert da-alert--error">
                {(analyzeMutation.error as Error)?.message ?? 'Error analitzant el text'}
              </div>
            )}
          </div>
        </div>

        <div className="da-result-col">
          {!result && !analyzeMutation.isPending && (
            <div className="card da-placeholder">
              <div className="empty-state">
                <div className="empty-state-icon" style={{ fontSize: '3rem' }}>
                  ◈
                </div>
                <h3 className="empty-state-title">Resultat de l&apos;anàlisi</h3>
                <p className="empty-state-desc">
                  Enganxa el teu text a l&apos;esquerra i fes clic a{' '}
                  <strong>Analitzar amb IA</strong>.
                  <br />
                  El resultat es mostrarà aquí amb tot el projecte Godet pre-emplenat.
                </p>
              </div>
            </div>
          )}

          {analyzeMutation.isPending && (
            <div className="card da-loading">
              <div className="spinner" style={{ margin: '0 auto 1rem' }} />
              <p
                style={{
                  textAlign: 'center',
                  color: 'var(--color-gray-600)',
                  fontSize: 'var(--font-size-sm)',
                }}
              >
                {llmLabel} analitza el text i extreu l&apos;estructura Godet...
                <br />
                <span
                  style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-400)' }}
                >
                  Normalment tarda 10–90 segons segons el proveïdor i la longitud del text.
                </span>
              </p>
            </div>
          )}

          {result && (
            <>
              <div className="card da-result-header">
                <div className="da-confidence">
                  <span className="da-confidence-label">Confiança de l&apos;anàlisi:</span>
                  <span
                    className="da-confidence-value"
                    style={{ color: confidenceColor(result.confidence) }}
                  >
                    {confidenceLabel(result.confidence)} ({Math.round(result.confidence * 100)}%)
                  </span>
                  {result.llm_provider && (
                    <span
                      style={{
                        marginLeft: 12,
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-gray-500)',
                      }}
                    >
                      · {result.llm_provider}
                      {result.llm_model ? ` / ${result.llm_model}` : ''}
                    </span>
                  )}
                </div>

                {result.truncated && (
                  <div className="da-alert da-alert--warn">
                    Text truncat: s&apos;han analitzat els primers 8.000 caràcters de{' '}
                    {result.text_length.toLocaleString()} totals.
                  </div>
                )}

                {result.warnings.length > 0 && (
                  <div className="da-warnings">
                    <p className="da-warnings-title">Avisos de qualitat:</p>
                    {result.warnings.map((w, i) => (
                      <p key={i} className="da-warning-item">
                        ⚠ {w}
                      </p>
                    ))}
                  </div>
                )}

                <div className="da-hypothesis">
                  <p className="da-section-label">Hipòtesi estratègica extreta:</p>
                  <p className="da-hypothesis-text">{result.hypothesis}</p>
                </div>

                <div className="da-context">
                  <p className="da-section-label">Context del sistema:</p>
                  <p className="da-context-text">{result.context}</p>
                </div>
              </div>

              <div className="card da-tabs-card">
                <div className="da-tabs">
                  {(
                    [
                      { id: 'variables', label: 'Variables', count: displayResult?.variables.length ?? 0 },
                      { id: 'actors', label: 'Actors', count: displayResult?.actors.length ?? 0 },
                      { id: 'components', label: 'Morfologia', count: displayResult?.components.length ?? 0 },
                      { id: 'statements', label: 'Postures', count: displayResult?.statements.length ?? 0 },
                    ] as const
                  ).map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      className={`da-tab ${activeTab === tab.id ? 'da-tab--active' : ''}`}
                      onClick={() => setActiveTab(tab.id)}
                    >
                      {tab.label}
                      <span
                        className={`da-tab-count ${activeTab === tab.id ? 'da-tab-count--active' : ''}`}
                      >
                        {tab.count}
                      </span>
                    </button>
                  ))}
                </div>

                {activeTab === 'variables' && (
                  <div className="da-list">
                    {(localResult?.variables ?? []).map((v, i) => (
                      <div key={`${v.code}-${i}`} className="da-item">
                        <div className="da-item-header">
                          <span className="da-code">{v.code}</span>
                          {editingVar === i ? (
                            <input
                              autoFocus
                              value={v.name}
                              style={{
                                flex: 1,
                                padding: '2px 6px',
                                fontSize: 'var(--font-size-sm)',
                                border: '1px solid var(--color-primary)',
                                borderRadius: 3,
                              }}
                              onChange={(e) => {
                                const updated = [...(localResult?.variables ?? [])]
                                updated[i] = { ...updated[i], name: e.target.value }
                                setLocalResult((prev) =>
                                  prev ? { ...prev, variables: updated } : prev,
                                )
                              }}
                              onBlur={() => setEditingVar(null)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') setEditingVar(null)
                              }}
                            />
                          ) : (
                            <>
                              <span
                                className="da-item-name"
                                style={{ cursor: 'pointer' }}
                                title="Fes clic per editar"
                                onClick={() => setEditingVar(i)}
                              >
                                {v.name}
                              </span>
                              <button
                                type="button"
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: 12,
                                  color: 'var(--color-gray-400)',
                                  padding: '0 4px',
                                }}
                                onClick={() => setEditingVar(i)}
                                title="Editar"
                              >
                                ✎
                              </button>
                              <button
                                type="button"
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: 12,
                                  color: 'var(--color-danger)',
                                  padding: '0 4px',
                                }}
                                onClick={() => {
                                  const updated = (localResult?.variables ?? []).filter(
                                    (_, idx) => idx !== i,
                                  )
                                  setLocalResult((prev) =>
                                    prev ? { ...prev, variables: updated } : prev,
                                  )
                                }}
                                title="Eliminar"
                              >
                                ✕
                              </button>
                            </>
                          )}
                          <span className={`da-type-badge da-type-${v.type.toLowerCase()}`}>
                            {v.type === 'I' ? 'Interna' : 'Externa'}
                          </span>
                        </div>
                        <p className="da-item-desc">{v.desc}</p>
                        {v.rationale && <p className="da-item-rationale">{v.rationale}</p>}
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'actors' && (
                  <div className="da-list">
                    {(displayResult?.actors ?? []).map((a) => (
                      <div key={a.code} className="da-item">
                        <div className="da-item-header">
                          <span className="da-code">{a.code}</span>
                          <span className="da-item-name">{a.name}</span>
                          <span className="da-force-badge">Força {a.force}/5</span>
                        </div>
                        {a.strategic_goals.length > 0 && (
                          <div className="da-goals">
                            {a.strategic_goals.map((g, i) => (
                              <span key={i} className="da-goal-chip">
                                {g}
                              </span>
                            ))}
                          </div>
                        )}
                        {a.rationale && <p className="da-item-rationale">{a.rationale}</p>}
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'components' && (
                  <div className="da-list">
                    {(displayResult?.components ?? []).map((c) => (
                      <div key={c.code} className="da-item">
                        <div className="da-item-header">
                          <span className="da-code">{c.code}</span>
                          <span className="da-item-name">{c.name}</span>
                        </div>
                        <div className="da-configs">
                          {c.configurations.map((cfg, i) => (
                            <div key={i} className="da-config">
                              <span className="da-config-label">{cfg.label}</span>
                              {cfg.desc && <span className="da-config-desc">{cfg.desc}</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'statements' && (
                  <div className="da-list">
                    {(displayResult?.statements ?? []).map((s, i) => (
                      <div key={i} className="da-item da-item--stmt">
                        <div className="da-item-header">
                          <span className="da-stmt-actor">{s.actor}</span>
                          <span
                            style={{
                              color: 'var(--color-gray-400)',
                              fontSize: 'var(--font-size-xs)',
                            }}
                          >
                            →
                          </span>
                          <span className="da-stmt-toward">{s.posture_toward}</span>
                          <span
                            className="da-posture-badge"
                            style={{ color: postureColor(s.posture_value) }}
                          >
                            {s.posture_value > 0 ? '+' : ''}
                            {s.posture_value}
                          </span>
                          <span className="da-topic-chip">{s.topic}</span>
                        </div>
                        <p className="da-stmt-text">{s.statement}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card da-apply-card">
                <h3 className="da-apply-title">Crear projecte Godet amb aquest resultat</h3>
                <p className="da-apply-desc">
                  Crea un projecte prospectiu pre-emplenat amb les {displayResult?.variables.length ?? 0}{' '}
                  variables, {displayResult?.actors.length ?? 0} actors i{' '}
                  {displayResult?.components.length ?? 0} components
                  morfològics extrets. Podràs ajustar tots els elements al wizard abans de calcular.
                </p>

                <div className="da-apply-field">
                  <label className="da-apply-label">Títol del projecte</label>
                  <input
                    className="da-apply-input"
                    value={projectTitle}
                    onChange={(e) => setProjectTitle(e.target.value)}
                    placeholder="Títol descriptiu del projecte"
                  />
                </div>

                {applied ? (
                  <div className="da-alert da-alert--success">
                    ✓ Projecte creat. Redirigint al wizard prospectiu...
                  </div>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary da-apply-btn"
                    disabled={!projectTitle.trim() || applyMutation.isPending}
                    onClick={() => applyMutation.mutate()}
                  >
                    {applyMutation.isPending
                      ? 'Creant projecte...'
                      : 'Crear projecte i continuar al wizard →'}
                  </button>
                )}

                {applyMutation.isError && (
                  <div className="da-alert da-alert--error" style={{ marginTop: 8 }}>
                    {(applyMutation.error as Error)?.message ?? 'Error creant el projecte'}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
