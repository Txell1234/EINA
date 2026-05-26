import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Brain, Plus, Sparkles, Save, Trash2, Play, BookOpen } from 'lucide-react'
import { qualitativeService } from '../../services/api'
import { useCase } from '../../contexts/CaseContext'
import AnalysisResultPanel from '../shared/AnalysisResultPanel'
import './ReasoningFrameworks.css'

type FrameworkType = 'deductive' | 'inductive' | 'abductive' | 'causal' | 'custom'

interface AnalysisStep {
  order: number
  title: string
  instruction: string
  llm_hint: string
}

interface OutputSection {
  key: string
  label: string
  instruction: string
}

interface FrameworkDefinition {
  doctrine: string
  epistemology: string
  ontology: string
  methodology: string
  analysis_steps: AnalysisStep[]
  evidence_criteria: string[]
  bias_checks: string[]
  limitations: string
  output_sections: OutputSection[]
  system_prompt_override: string
  application_notes: string
  tags: string[]
  auto_apply: boolean
}

interface ReasoningFramework {
  id: number
  name: string
  framework_type: FrameworkType
  description: string
  definition: FrameworkDefinition
  is_custom: boolean
  is_active: boolean
}

const EMPTY_DEFINITION: FrameworkDefinition = {
  doctrine: '',
  epistemology: '',
  ontology: '',
  methodology: '',
  analysis_steps: [],
  evidence_criteria: [],
  bias_checks: [],
  limitations: '',
  output_sections: [
    { key: 'conclusions', label: 'Conclusions', instruction: 'Síntesi analítica estructurada.' },
    { key: 'evidence', label: 'Evidència', instruction: 'Elements probatoris amb font i rellevància.' },
    { key: 'hypotheses', label: 'Hipòtesis', instruction: 'Hipòtesis operatives derivades.' },
    { key: 'uncertainties', label: 'Incerteses', instruction: 'Buits i límits interpretatius.' },
  ],
  system_prompt_override: '',
  application_notes: '',
  tags: [],
  auto_apply: true,
}

const TABS = [
  { id: 'general', label: 'General' },
  { id: 'doctrine', label: 'Doctrina i base' },
  { id: 'method', label: 'Metodologia' },
  { id: 'evidence', label: 'Evidència i biaixos' },
  { id: 'llm', label: 'Sortida i LLM' },
  { id: 'preview', label: 'Provar' },
] as const

type TabId = (typeof TABS)[number]['id']

const TYPE_LABELS: Record<FrameworkType, string> = {
  deductive: 'Deductive',
  inductive: 'Inductive',
  abductive: 'Abductive',
  causal: 'Causal',
  custom: 'Personalitzat',
}

function parseLines(text: string): string[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
}

function joinLines(items: string[]): string {
  return items.join('\n')
}

export default function ReasoningFrameworks() {
  const queryClient = useQueryClient()
  const { activeCase } = useCase()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [tab, setTab] = useState<TabId>('general')
  const [draft, setDraft] = useState<Partial<ReasoningFramework>>({})
  const [generateBrief, setGenerateBrief] = useState('')
  const [previewPremise, setPreviewPremise] = useState('')
  const [previewResult, setPreviewResult] = useState<unknown>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  const { data: frameworks = [], isLoading } = useQuery({
    queryKey: ['qualitative-frameworks'],
    queryFn: () => qualitativeService.getFrameworks() as Promise<ReasoningFramework[]>,
  })

  const selected = useMemo(
    () => frameworks.find((f) => f.id === selectedId) ?? null,
    [frameworks, selectedId],
  )

  useEffect(() => {
    if (selected) {
      setDraft({
        ...selected,
        definition: { ...EMPTY_DEFINITION, ...selected.definition },
      })
    }
  }, [selected])

  useEffect(() => {
    if (!selectedId && frameworks.length) {
      setSelectedId(frameworks[0].id)
    }
  }, [frameworks, selectedId])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: draft.name?.trim(),
        framework_type: draft.framework_type ?? 'custom',
        description: draft.description ?? '',
        definition: draft.definition ?? EMPTY_DEFINITION,
      }
      if (selectedId && selected?.is_custom) {
        return qualitativeService.updateFramework(selectedId, payload)
      }
      if (selectedId && !selected?.is_custom) {
        return qualitativeService.updateFramework(selectedId, {
          description: payload.description,
          definition: payload.definition,
        })
      }
      return qualitativeService.createFramework(payload)
    },
    onSuccess: (data: ReasoningFramework) => {
      queryClient.invalidateQueries({ queryKey: ['qualitative-frameworks'] })
      setSelectedId(data.id)
      setStatusMsg('Marc desat correctament.')
    },
    onError: (err: Error) => setStatusMsg(err.message || 'Error en desar'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => qualitativeService.deleteFramework(selectedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['qualitative-frameworks'] })
      setSelectedId(null)
      setStatusMsg('Marc eliminat.')
    },
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      qualitativeService.generateFramework({
        brief: generateBrief,
        framework_type: draft.framework_type ?? 'custom',
        language: 'ca',
      }),
    onSuccess: (data: Partial<ReasoningFramework>) => {
      setDraft({
        name: data.name ?? 'Marc generat',
        framework_type: (data.framework_type as FrameworkType) ?? 'custom',
        description: data.description ?? '',
        definition: { ...EMPTY_DEFINITION, ...(data.definition as FrameworkDefinition) },
        is_custom: true,
      })
      setSelectedId(null)
      setTab('doctrine')
      setStatusMsg('Esborrany generat amb IA. Revisa i desa.')
    },
    onError: (err: Error) => setStatusMsg(err.message || 'Error en generar'),
  })

  const previewMutation = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error('Selecciona un marc')
      return qualitativeService.previewFramework(selectedId, {
        premise: previewPremise,
        case_context: activeCase?.description ?? activeCase?.name ?? '',
      })
    },
    onSuccess: (data) => {
      setPreviewResult(data)
      setPreviewError(null)
    },
    onError: (err: Error) => {
      setPreviewError(err.message)
      setPreviewResult(null)
    },
  })

  const def = draft.definition ?? EMPTY_DEFINITION

  const updateDef = (patch: Partial<FrameworkDefinition>) => {
    setDraft((prev) => ({
      ...prev,
      definition: { ...(prev.definition ?? EMPTY_DEFINITION), ...patch },
    }))
  }

  const addStep = () => {
    const steps = [...(def.analysis_steps ?? [])]
    steps.push({
      order: steps.length + 1,
      title: `Pas ${steps.length + 1}`,
      instruction: '',
      llm_hint: '',
    })
    updateDef({ analysis_steps: steps })
  }

  const newFramework = () => {
    setSelectedId(null)
    setDraft({
      name: 'Nou marc personalitzat',
      framework_type: 'custom',
      description: '',
      definition: { ...EMPTY_DEFINITION, analysis_steps: [] },
      is_custom: true,
    })
    setTab('general')
  }

  return (
    <div className="reasoning-frameworks-page card">
      <header className="rf-header">
        <div>
          <h1>
            <Brain size={22} style={{ verticalAlign: 'middle', marginRight: 8 }} />
            Marcs de raonament
          </h1>
          <p className="rf-subtitle">
            Defineix doctrina, metodologia, passos d&apos;anàlisi i criteris d&apos;evidència.
            El LLM aplica el marc automàticament en l&apos;
            <Link to="/qualitative-analysis">anàlisi qualitativa</Link>.
          </p>
        </div>
        <div className="rf-header-actions">
          <button type="button" className="btn-secondary" onClick={newFramework}>
            <Plus size={16} /> Nou marc
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={saveMutation.isPending || !draft.name?.trim()}
            onClick={() => saveMutation.mutate()}
          >
            <Save size={16} /> Desar
          </button>
        </div>
      </header>

      {statusMsg && (
        <p className="rf-status" role="status">{statusMsg}</p>
      )}

      <div className="rf-layout">
        <aside className="rf-sidebar">
          <h2>Biblioteca</h2>
          {isLoading && <p>Carregant…</p>}
          <ul className="rf-list">
            {frameworks.map((fw) => (
              <li key={fw.id}>
                <button
                  type="button"
                  className={`rf-list-item${fw.id === selectedId ? ' active' : ''}`}
                  onClick={() => setSelectedId(fw.id)}
                >
                  <span className="rf-list-name">{fw.name}</span>
                  <span className="rf-list-meta">
                    {TYPE_LABELS[fw.framework_type]}
                    {fw.is_custom ? ' · custom' : ' · built-in'}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <div className="rf-generate-box">
            <h3>
              <Sparkles size={16} /> Generar amb IA
            </h3>
            <textarea
              className="prospective-textarea"
              rows={4}
              placeholder="Descriu l'objectiu analític, domini (geopolítica, risc…), estil epistemològic i sortida esperada…"
              value={generateBrief}
              onChange={(e) => setGenerateBrief(e.target.value)}
            />
            <button
              type="button"
              className="btn-accent"
              disabled={generateMutation.isPending || generateBrief.trim().length < 20}
              onClick={() => generateMutation.mutate()}
            >
              {generateMutation.isPending ? 'Generant…' : 'Generar esborrany'}
            </button>
          </div>
        </aside>

        <main className="rf-editor">
          {!draft.name && !selectedId && !frameworks.length && (
            <p>Crea un marc nou o genera&apos;n un amb IA.</p>
          )}

          {(draft.name || selectedId) && (
            <>
              <nav className="rf-tabs">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={tab === t.id ? 'active' : ''}
                    onClick={() => setTab(t.id)}
                  >
                    {t.label}
                  </button>
                ))}
              </nav>

              {tab === 'general' && (
                <section className="rf-section">
                  <div className="prospective-field">
                    <label>Nom del marc *</label>
                    <input
                      className="prospective-input"
                      value={draft.name ?? ''}
                      onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
                      disabled={Boolean(selected && !selected.is_custom)}
                    />
                  </div>
                  <div className="prospective-field">
                    <label>Tipus base</label>
                    <select
                      className="prospective-select"
                      value={draft.framework_type ?? 'custom'}
                      onChange={(e) =>
                        setDraft((p) => ({ ...p, framework_type: e.target.value as FrameworkType }))
                      }
                    >
                      {(Object.keys(TYPE_LABELS) as FrameworkType[]).map((k) => (
                        <option key={k} value={k}>{TYPE_LABELS[k]}</option>
                      ))}
                    </select>
                  </div>
                  <div className="prospective-field">
                    <label>Descripció curta</label>
                    <textarea
                      className="prospective-textarea"
                      rows={3}
                      value={draft.description ?? ''}
                      onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value }))}
                    />
                  </div>
                  <div className="prospective-field">
                    <label>Notes d&apos;aplicació</label>
                    <textarea
                      className="prospective-textarea"
                      rows={2}
                      value={def.application_notes ?? ''}
                      onChange={(e) => updateDef({ application_notes: e.target.value })}
                      placeholder="Quan usar aquest marc? Quin tipus de preguntes analítiques resol?"
                    />
                  </div>
                  <label className="rf-checkbox">
                    <input
                      type="checkbox"
                      checked={def.auto_apply ?? true}
                      onChange={(e) => updateDef({ auto_apply: e.target.checked })}
                    />
                    Aplicar automàticament el prompt LLM en analitzar
                  </label>
                </section>
              )}

              {tab === 'doctrine' && (
                <section className="rf-section">
                  {(['doctrine', 'epistemology', 'ontology'] as const).map((field) => (
                    <div key={field} className="prospective-field">
                      <label>{field === 'doctrine' ? 'Doctrina' : field === 'epistemology' ? 'Epistemologia' : 'Ontologia'}</label>
                      <textarea
                        className="prospective-textarea"
                        rows={4}
                        value={def[field] ?? ''}
                        onChange={(e) => updateDef({ [field]: e.target.value })}
                      />
                    </div>
                  ))}
                </section>
              )}

              {tab === 'method' && (
                <section className="rf-section">
                  <div className="prospective-field">
                    <label>Metodologia</label>
                    <textarea
                      className="prospective-textarea"
                      rows={4}
                      value={def.methodology ?? ''}
                      onChange={(e) => updateDef({ methodology: e.target.value })}
                    />
                  </div>
                  <div className="rf-steps-header">
                    <h3>
                      <BookOpen size={18} /> Passos d&apos;anàlisi
                    </h3>
                    <button type="button" className="btn-secondary btn-sm" onClick={addStep}>
                      + Afegir pas
                    </button>
                  </div>
                  {(def.analysis_steps ?? []).map((step, idx) => (
                    <div key={idx} className="rf-step-card">
                      <div className="rf-step-row">
                        <input
                          type="number"
                          className="prospective-input rf-step-order"
                          value={step.order}
                          onChange={(e) => {
                            const steps = [...def.analysis_steps]
                            steps[idx] = { ...step, order: Number(e.target.value) }
                            updateDef({ analysis_steps: steps })
                          }}
                        />
                        <input
                          className="prospective-input"
                          placeholder="Títol del pas"
                          value={step.title}
                          onChange={(e) => {
                            const steps = [...def.analysis_steps]
                            steps[idx] = { ...step, title: e.target.value }
                            updateDef({ analysis_steps: steps })
                          }}
                        />
                      </div>
                      <textarea
                        className="prospective-textarea"
                        rows={2}
                        placeholder="Instrucció per a l'analista / LLM"
                        value={step.instruction}
                        onChange={(e) => {
                          const steps = [...def.analysis_steps]
                          steps[idx] = { ...step, instruction: e.target.value }
                          updateDef({ analysis_steps: steps })
                        }}
                      />
                      <input
                        className="prospective-input"
                        placeholder="Pista LLM (opcional)"
                        value={step.llm_hint}
                        onChange={(e) => {
                          const steps = [...def.analysis_steps]
                          steps[idx] = { ...step, llm_hint: e.target.value }
                          updateDef({ analysis_steps: steps })
                        }}
                      />
                    </div>
                  ))}
                </section>
              )}

              {tab === 'evidence' && (
                <section className="rf-section">
                  <div className="prospective-field">
                    <label>Criteris d&apos;evidència (un per línia)</label>
                    <textarea
                      className="prospective-textarea"
                      rows={4}
                      value={joinLines(def.evidence_criteria ?? [])}
                      onChange={(e) => updateDef({ evidence_criteria: parseLines(e.target.value) })}
                    />
                  </div>
                  <div className="prospective-field">
                    <label>Comprovacions de biaix (un per línia)</label>
                    <textarea
                      className="prospective-textarea"
                      rows={3}
                      value={joinLines(def.bias_checks ?? [])}
                      onChange={(e) => updateDef({ bias_checks: parseLines(e.target.value) })}
                    />
                  </div>
                  <div className="prospective-field">
                    <label>Limitacions del marc</label>
                    <textarea
                      className="prospective-textarea"
                      rows={3}
                      value={def.limitations ?? ''}
                      onChange={(e) => updateDef({ limitations: e.target.value })}
                    />
                  </div>
                </section>
              )}

              {tab === 'llm' && (
                <section className="rf-section">
                  <p className="rf-hint">
                    Les seccions de sortida es mapegen al JSON que retorna el LLM. Pots sobreescriure tot el system prompt.
                  </p>
                  {(def.output_sections ?? []).map((sec, idx) => (
                    <div key={sec.key} className="rf-step-card">
                      <strong>{sec.label}</strong> <code>{sec.key}</code>
                      <textarea
                        className="prospective-textarea"
                        rows={2}
                        value={sec.instruction}
                        onChange={(e) => {
                          const sections = [...(def.output_sections ?? [])]
                          sections[idx] = { ...sec, instruction: e.target.value }
                          updateDef({ output_sections: sections })
                        }}
                      />
                    </div>
                  ))}
                  <div className="prospective-field">
                    <label>System prompt (override complet, opcional)</label>
                    <textarea
                      className="prospective-textarea rf-monospace"
                      rows={8}
                      value={def.system_prompt_override ?? ''}
                      onChange={(e) => updateDef({ system_prompt_override: e.target.value })}
                      placeholder="Si es deixa buit, es construeix automàticament des de doctrina, metodologia i passos."
                    />
                  </div>
                </section>
              )}

              {tab === 'preview' && (
                <section className="rf-section">
                  <div className="prospective-field">
                    <label>Premisa / pregunta analítica</label>
                    <textarea
                      className="prospective-textarea"
                      rows={5}
                      value={previewPremise}
                      onChange={(e) => setPreviewPremise(e.target.value)}
                      placeholder="Formula la pregunta que vols analitzar amb aquest marc…"
                    />
                  </div>
                  {activeCase && (
                    <p className="rf-hint">
                      Context del cas actiu: <strong>{activeCase.name}</strong>
                    </p>
                  )}
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={previewMutation.isPending || !selectedId || previewPremise.length < 20}
                    onClick={() => previewMutation.mutate()}
                  >
                    <Play size={16} /> Provar marc amb LLM
                  </button>
                  <AnalysisResultPanel
                    title="Resultat de la prova"
                    data={previewResult}
                    error={previewError}
                  />
                </section>
              )}

              {selected?.is_custom && selectedId && (
                <footer className="rf-footer">
                  <button
                    type="button"
                    className="btn-danger-outline"
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      if (window.confirm('Eliminar aquest marc personalitzat?')) {
                        deleteMutation.mutate()
                      }
                    }}
                  >
                    <Trash2 size={16} /> Eliminar
                  </button>
                </footer>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}
