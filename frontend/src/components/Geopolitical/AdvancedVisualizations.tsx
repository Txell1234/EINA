import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { prospectiveService } from '../../services/api'
import RiskDashboard from './RiskDashboard'
import BilateralMatrix from './BilateralMatrix'
import RelationTimeline from './RelationTimeline'
import './AdvancedVisualizations.css'

interface MicmacSuggestion {
  row: number
  col: number
  value: number
  reason: string
  source: string
}

interface SuggestionsResult {
  suggestions: MicmacSuggestion[]
  n_relations: number
  n_events: number
  variables_matched: number
}

interface Project {
  id: number
  title: string
  case_id?: number | null
}

interface ProspectiveVariable {
  code: string
  name: string
  type: string
  desc: string
}

function influenceLabel(v: number): string {
  if (v === 3) return 'Forta (3)'
  if (v === 2) return 'Moderada (2)'
  if (v === 1) return 'Feble (1)'
  return 'Cap (0)'
}

function influenceColor(v: number): string {
  if (v === 3) return 'var(--color-danger)'
  if (v === 2) return '#e07840'
  if (v === 1) return '#e6a817'
  return 'var(--color-gray-400)'
}

function emptyMatrix(n: number): number[][] {
  return Array.from({ length: n }, () => Array(n).fill(0))
}

export default function AdvancedVisualizations() {
  const { activeCase } = useCase()
  const caseId = activeCase?.id
  const qc = useQueryClient()

  const [country1, setCountry1] = useState('Espanya')
  const [country2, setCountry2] = useState('França')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestionsResult | null>(null)
  const [appliedCells, setAppliedCells] = useState<Set<string>>(new Set())
  const [currentMatrix, setCurrentMatrix] = useState<number[][] | null>(null)

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ['prospective-projects-for-geo', caseId],
    queryFn: () => prospectiveService.listProjects(caseId),
    enabled: caseId !== undefined,
  })

  const { data: projectDetail } = useQuery({
    queryKey: ['project-detail-for-geo', selectedProjectId],
    queryFn: () => prospectiveService.getProject(selectedProjectId!),
    enabled: selectedProjectId !== null,
  })

  const variables: ProspectiveVariable[] =
    (projectDetail as { variables?: ProspectiveVariable[] })?.variables ?? []

  useEffect(() => {
    setCurrentMatrix(null)
    setSuggestions(null)
    setAppliedCells(new Set())
  }, [selectedProjectId])

  const suggestMutation = useMutation({
    mutationFn: () => {
      if (!selectedProjectId || variables.length === 0) {
        return Promise.reject(new Error('Selecciona un projecte amb variables definides'))
      }
      return prospectiveService.getGeopoliticalMicmacSuggestions(
        selectedProjectId,
        variables.map((v) => ({ code: v.code, name: v.name, desc: v.desc })),
        caseId,
      )
    },
    onSuccess: (data) => setSuggestions(data as SuggestionsResult),
  })

  const applyMutation = useMutation({
    mutationFn: async (sug: MicmacSuggestion) => {
      if (!selectedProjectId || variables.length === 0) return
      const n = variables.length
      const base = currentMatrix ?? emptyMatrix(n)
      const matrix = base.map((row) => [...row])
      if (sug.row < n && sug.col < n) {
        matrix[sug.row][sug.col] = sug.value
      }
      return prospectiveService.computeMicmac(selectedProjectId, matrix)
    },
    onSuccess: (data, sug) => {
      const result = data as { matrix_direct?: number[][] } | undefined
      if (result?.matrix_direct) {
        setCurrentMatrix(result.matrix_direct.map((row) => [...row]))
      }
      setAppliedCells((prev) => new Set([...prev, `${sug.row}-${sug.col}`]))
      qc.invalidateQueries({ queryKey: ['project-detail-for-geo', selectedProjectId] })
    },
  })

  const applyAllMutation = useMutation({
    mutationFn: async () => {
      if (!selectedProjectId || !suggestions || variables.length === 0) return
      const n = variables.length
      const base = currentMatrix ?? emptyMatrix(n)
      const matrix = base.map((row) => [...row])
      for (const sug of suggestions.suggestions) {
        if (sug.row < n && sug.col < n) {
          matrix[sug.row][sug.col] = sug.value
        }
      }
      return prospectiveService.computeMicmac(selectedProjectId, matrix)
    },
    onSuccess: (data) => {
      const result = data as { matrix_direct?: number[][] } | undefined
      if (result?.matrix_direct) {
        setCurrentMatrix(result.matrix_direct.map((row) => [...row]))
      }
      const allKeys = new Set(
        (suggestions?.suggestions ?? []).map((s) => `${s.row}-${s.col}`),
      )
      setAppliedCells(allKeys)
      qc.invalidateQueries({ queryKey: ['project-detail-for-geo', selectedProjectId] })
    },
  })

  return (
    <div className="advanced-visualizations">
      <h2>Anàlisi geopolítica avançada</h2>

      <div className="card geo-bridge-card">
        <div className="geo-bridge-header">
          <div>
            <h3 className="geo-bridge-title">
              Enriquiment MIC-MAC des de dades geopolítiques
            </h3>
            <p className="geo-bridge-desc">
              Genera suggeriments de puntuació per a la matriu MIC-MAC basant-se
              en les relacions bilaterals i els esdeveniments diplomàtics del cas.
            </p>
          </div>
        </div>

        {!caseId && (
          <div className="empty-state">
            <div className="empty-state-icon">⊙</div>
            <h3 className="empty-state-title">Cap cas seleccionat</h3>
            <p className="empty-state-desc">
              Selecciona un cas actiu al menú lateral per veure les relacions
              geopolítiques i generar suggeriments MIC-MAC.
            </p>
          </div>
        )}

        {caseId && (
          <div className="geo-bridge-controls">
            <div className="geo-bridge-field">
              <label className="geo-bridge-label">Projecte prospectiu</label>
              {projects.length === 0 ? (
                <p
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-gray-500)',
                    margin: 0,
                  }}
                >
                  Cap projecte prospectiu per a aquest cas.
                  Crea&apos;n un des del wizard prospectiu.
                </p>
              ) : (
                <select
                  className="geo-select"
                  value={selectedProjectId ?? ''}
                  onChange={(e) => {
                    setSelectedProjectId(e.target.value ? Number(e.target.value) : null)
                  }}
                >
                  <option value="">— Selecciona projecte —</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      #{p.id} — {p.title}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {selectedProjectId && (
              <>
                {variables.length === 0 ? (
                  <p
                    style={{
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-warning)',
                      margin: 0,
                    }}
                  >
                    El projecte no té variables MIC-MAC definides.
                    Defineix les variables al wizard prospectiu (pas 2) primer.
                  </p>
                ) : (
                  <div className="geo-bridge-vars">
                    <p
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-gray-600)',
                        marginBottom: 6,
                      }}
                    >
                      {variables.length} variables detectades:{' '}
                      {variables.map((v) => (
                        <span key={v.code} className="geo-var-chip">
                          {v.code}
                        </span>
                      ))}
                    </p>
                    <button
                      type="button"
                      className="btn btn-accent"
                      disabled={suggestMutation.isPending}
                      onClick={() => suggestMutation.mutate()}
                    >
                      {suggestMutation.isPending
                        ? 'Analitzant relacions...'
                        : 'Generar suggeriments MIC-MAC'}
                    </button>
                  </div>
                )}
              </>
            )}

            {suggestMutation.isError && (
              <div className="geo-alert geo-alert--error">
                {(suggestMutation.error as Error)?.message ?? 'Error generant suggeriments'}
              </div>
            )}
          </div>
        )}

        {suggestions && (
          <div className="geo-suggestions">
            <div className="geo-suggestions-header">
              <div>
                <p className="geo-suggestions-title">
                  {suggestions.suggestions.length} suggeriments generats
                </p>
                <p
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-gray-500)',
                    margin: 0,
                  }}
                >
                  {suggestions.n_relations} relacions bilaterals ·{' '}
                  {suggestions.n_events} esdeveniments ·{' '}
                  {suggestions.variables_matched} variables amb correspondència
                </p>
              </div>
              {suggestions.suggestions.length > 0 && (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={applyAllMutation.isPending}
                  onClick={() => applyAllMutation.mutate()}
                >
                  {applyAllMutation.isPending ? 'Aplicant...' : 'Aplicar tots al MIC-MAC'}
                </button>
              )}
            </div>

            {suggestions.suggestions.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--spacing-lg)' }}>
                <div className="empty-state-icon">⊞</div>
                <h3 className="empty-state-title">Cap correspondència trobada</h3>
                <p className="empty-state-desc">
                  Les variables del projecte no coincideixen amb cap país de les
                  relacions bilaterals. Comprova que les variables fan referència
                  a actors geopolítics identificables.
                </p>
              </div>
            ) : (
              <div className="geo-suggestions-list">
                {suggestions.suggestions.map((sug, i) => {
                  const varRow = variables[sug.row]
                  const varCol = variables[sug.col]
                  const key = `${sug.row}-${sug.col}`
                  const isApplied = appliedCells.has(key)
                  return (
                    <div
                      key={i}
                      className={`geo-suggestion-item ${isApplied ? 'geo-suggestion-item--applied' : ''}`}
                    >
                      <div className="geo-suggestion-pair">
                        <span className="geo-suggestion-var">
                          {varRow?.code ?? sug.row} — {varRow?.name ?? '?'}
                        </span>
                        <span className="geo-suggestion-arrow">→</span>
                        <span className="geo-suggestion-var">
                          {varCol?.code ?? sug.col} — {varCol?.name ?? '?'}
                        </span>
                      </div>
                      <div className="geo-suggestion-value">
                        <span
                          className="geo-influence-badge"
                          style={{ color: influenceColor(sug.value) }}
                        >
                          {influenceLabel(sug.value)}
                        </span>
                        <span className="geo-suggestion-reason">{sug.reason}</span>
                        {sug.source && (
                          <span className="geo-suggestion-source">{sug.source}</span>
                        )}
                      </div>
                      <button
                        type="button"
                        className={`btn geo-apply-btn ${isApplied ? 'btn-success' : ''}`}
                        disabled={applyMutation.isPending || isApplied}
                        onClick={() => applyMutation.mutate(sug)}
                      >
                        {isApplied ? '✓ Aplicat' : 'Aplicar'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <RiskDashboard caseId={caseId} />
      <BilateralMatrix caseId={caseId} />
      <div className="timeline-controls">
        <input
          value={country1}
          onChange={(e) => setCountry1(e.target.value)}
          placeholder="País 1"
          className="geo-input"
        />
        <input
          value={country2}
          onChange={(e) => setCountry2(e.target.value)}
          placeholder="País 2"
          className="geo-input"
        />
      </div>
      <RelationTimeline country1={country1} country2={country2} />
    </div>
  )
}
