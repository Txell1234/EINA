import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { prospectiveService } from '../../services/api'
import CcaHeatmapPanel, { type CcaCell } from './CcaHeatmapPanel'
import './CcaSuggestionsPanel.css'

export type CcaRule = {
  id: string
  component_a: string
  config_a: string
  component_b: string
  config_b: string
  consistency: number
  justification?: string
  source?: string
  selected?: boolean
  already_applied?: boolean
  status?: 'suggested' | 'applied' | 'manual' | 'draft'
  origin?: string
}

type WizardComponent = { code: string; name: string; configurations?: string[] }

type CcaSuggestionsPanelProps = {
  projectId: number
  inquiryId?: number | null
  onApplied?: (stats: Record<string, unknown>) => void
}

function newRuleId() {
  return `draft_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}

function statusLabel(rule: CcaRule): string {
  if (rule.status === 'manual' || rule.origin === 'manual') return 'Manual'
  if (rule.already_applied || rule.status === 'applied') return 'Aplicada'
  if (rule.status === 'draft') return 'Esborrany'
  return 'Suggerida'
}

export default function CcaSuggestionsPanel({
  projectId,
  inquiryId,
  onApplied,
}: CcaSuggestionsPanelProps) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['cca-suggestions', projectId, inquiryId],
    queryFn: () => prospectiveService.getCcaSuggestions(projectId, inquiryId ?? undefined),
    enabled: projectId > 0,
    retry: false,
  })

  const [rules, setRules] = useState<CcaRule[]>([])
  const [dirty, setDirty] = useState(false)

  const wizardComponents = (data?.wizard_components as WizardComponent[]) ?? []
  const componentCodes = useMemo(() => {
    const codes = wizardComponents.map((c) => c.code).filter(Boolean)
    const fromRules = rules.flatMap((r) => [r.component_a, r.component_b])
    return [...new Set([...codes, ...fromRules])].filter(Boolean)
  }, [wizardComponents, rules])

  const manualRules = (data?.manual_rules as CcaRule[]) ?? []
  const counts = data?.counts as { suggested?: number; applied?: number; manual?: number } | undefined

  useEffect(() => {
    if (dirty || !data?.rules) return
    const suggested = (data.rules as CcaRule[]) ?? []
    const manual = (data.manual_rules as CcaRule[]) ?? []
    const merged = [
      ...suggested,
      ...manual.filter((m) => !suggested.some((s) => s.id === m.id)),
    ]
    setRules(merged)
  }, [data, dirty])

  const canPreviewCca = wizardComponents.length > 0

  const previewMutation = useMutation({
    mutationFn: () =>
      prospectiveService.previewCcaSuggestions(
        projectId,
        rules.filter((r) => r.selected !== false && r.consistency === -1),
      ),
    retry: false,
  })

  const applyMutation = useMutation({
    mutationFn: () =>
      prospectiveService.applyCcaSuggestions(
        projectId,
        rules.filter((r) => r.consistency === -1),
      ),
    onSuccess: (result) => {
      setDirty(false)
      setRules([])
      void refetch()
      previewMutation.reset()
      onApplied?.(result as Record<string, unknown>)
    },
  })

  const updateRule = useCallback((id: string, patch: Partial<CcaRule>) => {
    setDirty(true)
    setRules((prev) =>
      prev.map((r) =>
        r.id === id
          ? {
              ...r,
              ...patch,
              status: r.already_applied ? r.status : 'draft',
            }
          : r,
      ),
    )
  }, [])

  const toggleRule = (id: string) => {
    setDirty(true)
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, selected: r.selected === false } : r)),
    )
  }

  const addRule = () => {
    const codes = componentCodes
    const a = codes[0] ?? 'C1'
    const b = codes[1] ?? codes[0] ?? 'C2'
    setDirty(true)
    setRules((prev) => [
      ...prev,
      {
        id: newRuleId(),
        component_a: a,
        config_a: '',
        component_b: b,
        config_b: '',
        consistency: -1,
        justification: '',
        source: 'user',
        selected: true,
        status: 'draft',
      },
    ])
  }

  const exportRules = () => {
    const payload = {
      project_id: projectId,
      rules: rules.filter((r) => r.consistency === -1),
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cca-rules-project-${projectId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const importRules = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'application/json'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      const text = await file.text()
      const parsed = JSON.parse(text) as { rules?: CcaRule[] }
      const imported = (parsed.rules ?? []).map((r, i) => ({
        ...r,
        id: r.id || `import_${i}`,
        consistency: -1,
        selected: true,
        source: r.source ?? 'import',
        status: 'draft' as const,
      }))
      setDirty(true)
      setRules((prev) => [...prev, ...imported])
    }
    input.click()
  }

  useEffect(() => {
    if (!rules.length || !canPreviewCca) return
    const timer = window.setTimeout(() => {
      previewMutation.mutate()
    }, 450)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounced live preview
  }, [rules, projectId, canPreviewCca])

  const heatmap = data?.cca_heatmap as {
    cells?: CcaCell[]
    parameters?: Array<{ code: string; name: string; states: string[] }>
  }

  if (isLoading) return <p className="cca-suggestions__loading">Carregant regles CCA…</p>

  if (!rules.length && !heatmap?.cells?.length && !manualRules.length) {
    return (
      <p className="cca-suggestions__empty">
        Sense regles CCA. Completa els components morfològics al wizard o enllaça una inquiry.
      </p>
    )
  }

  return (
    <div className="cca-suggestions" data-testid="cca-suggestions-panel">
      <header>
        <h4>Regles CCA — edició bidireccional</h4>
        <p>
          Metodologia: {String(data?.methodology ?? 'domain_rule')}
          {counts ? (
            <>
              {' · '}
              {counts.suggested ?? 0} suggerides · {counts.applied ?? 0} aplicades ·{' '}
              {counts.manual ?? 0} manuals
            </>
          ) : null}
          {previewMutation.data?.after?.valid_combinations != null && canPreviewCca ? (
            <>
              {' · '}
              <strong>Live:</strong> {String(previewMutation.data.after.valid_combinations)} combinacions
              vàlides ({String(previewMutation.data.survival_rate_pct)}% supervivència)
            </>
          ) : null}
        </p>
        {!canPreviewCca && rules.length > 0 ? (
          <p className="cca-suggestions__hint">
            Defineix components al pas Morfològic per previsualitzar l&apos;impacte en viu.
          </p>
        ) : null}
      </header>

      {previewMutation.data?.before && previewMutation.data?.after ? (
        <div className="cca-suggestions__preview cca-suggestions__preview--diff">
          <strong>Impacte CCA (live):</strong>{' '}
          {String(previewMutation.data.before.valid_combinations)} →{' '}
          {String(previewMutation.data.after.valid_combinations)} combinacions (
          {previewMutation.data.delta_valid_combinations >= 0 ? '+' : ''}
          {String(previewMutation.data.delta_valid_combinations)})
          {previewMutation.data.diff ? (
            <span className="cca-suggestions__diff-meta">
              {' '}
              · noves: {String(previewMutation.data.diff.new_rules)} · sense canvi:{' '}
              {String(previewMutation.data.diff.unchanged_rules)}
            </span>
          ) : null}
        </div>
      ) : null}

      {rules.length > 0 && (
        <table>
          <thead>
            <tr>
              <th />
              <th>Estat</th>
              <th>Component A / estat</th>
              <th>Component B / estat</th>
              <th>Justificació</th>
              <th>Font</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr
                key={rule.id}
                className={
                  rule.selected === false
                    ? 'cca-suggestions__deselected'
                    : rule.already_applied
                      ? 'cca-suggestions__applied'
                      : ''
                }
              >
                <td>
                  <input
                    type="checkbox"
                    checked={rule.selected !== false}
                    onChange={() => toggleRule(rule.id)}
                    title={
                      rule.already_applied
                        ? 'Desmarcar per eliminar en aplicar'
                        : 'Incloure en aplicar'
                    }
                  />
                </td>
                <td>
                  <span className={`cca-suggestions__badge cca-suggestions__badge--${statusLabel(rule).toLowerCase()}`}>
                    {statusLabel(rule)}
                  </span>
                </td>
                <td>
                  <select
                    className="cca-suggestions__select"
                    value={rule.component_a}
                    onChange={(e) => updateRule(rule.id, { component_a: e.target.value })}
                  >
                    {componentCodes.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  /
                  <input
                    className="cca-suggestions__inline"
                    value={rule.config_a}
                    onChange={(e) => updateRule(rule.id, { config_a: e.target.value })}
                    placeholder="estat A"
                  />
                </td>
                <td>
                  <select
                    className="cca-suggestions__select"
                    value={rule.component_b}
                    onChange={(e) => updateRule(rule.id, { component_b: e.target.value })}
                  >
                    {componentCodes.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  /
                  <input
                    className="cca-suggestions__inline"
                    value={rule.config_b}
                    onChange={(e) => updateRule(rule.id, { config_b: e.target.value })}
                    placeholder="estat B"
                  />
                </td>
                <td>
                  <input
                    className="cca-suggestions__justification"
                    value={rule.justification ?? ''}
                    onChange={(e) => updateRule(rule.id, { justification: e.target.value })}
                    placeholder="Raó traçable…"
                  />
                </td>
                <td>{rule.source ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="cca-suggestions__actions">
        <button type="button" className="btn" onClick={addRule}>
          Nova regla
        </button>
        <button type="button" className="btn" onClick={exportRules}>
          Exportar JSON
        </button>
        <button type="button" className="btn" onClick={importRules}>
          Importar JSON
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={applyMutation.isPending}
          onClick={() => applyMutation.mutate()}
        >
          {applyMutation.isPending ? 'Aplicant…' : 'Aplicar i sincronitzar matriu'}
        </button>
      </div>

      {heatmap?.cells && heatmap.cells.length > 0 && (
        <details open className="cca-suggestions__heatmap">
          <summary>Heatmap CCA</summary>
          <CcaHeatmapPanel cells={heatmap.cells} parameters={heatmap.parameters} />
        </details>
      )}
    </div>
  )
}
