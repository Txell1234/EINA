import { useEffect, useState } from 'react'
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
}

type CcaSuggestionsPanelProps = {
  projectId: number
  inquiryId?: number | null
  onApplied?: (stats: Record<string, unknown>) => void
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
  })

  const [rules, setRules] = useState<CcaRule[]>([])

  const loadedRules = (data?.rules as CcaRule[]) ?? []
  const displayRules = rules.length > 0 ? rules : loadedRules

  const previewMutation = useMutation({
    mutationFn: () =>
      prospectiveService.previewCcaSuggestions(
        projectId,
        displayRules.filter((r) => r.selected !== false),
      ),
  })

  const applyMutation = useMutation({
    mutationFn: () =>
      prospectiveService.applyCcaSuggestions(
        projectId,
        displayRules.filter((r) => r.selected !== false),
      ),
    onSuccess: (result) => {
      setRules([])
      void refetch()
      previewMutation.reset()
      onApplied?.(result as Record<string, unknown>)
    },
  })

  useEffect(() => {
    if (!displayRules.length) return
    const timer = window.setTimeout(() => {
      previewMutation.mutate()
    }, 400)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounced preview on rule edits
  }, [displayRules, projectId])

  const toggleRule = (id: string) => {
    setRules(
      displayRules.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r)),
    )
  }

  const heatmap = data?.cca_heatmap as { cells?: CcaCell[]; parameters?: Array<{ code: string; name: string; states: string[] }> }

  if (isLoading) return <p className="cca-suggestions__loading">Carregant regles CCA suggerides…</p>
  if (!displayRules.length && !heatmap?.cells?.length) {
    return (
      <p className="cca-suggestions__empty">
        Sense regles CCA suggerides. Completa els components o enllaça una inquiry.
      </p>
    )
  }

  return (
    <div className="cca-suggestions">
      <header>
        <h4>Regles CCA suggerides (editables)</h4>
        <p>
          Selecciona les incompatibilitats Zwicky a aplicar al projecte. Metodologia:{' '}
          {String(data?.methodology ?? 'domain_rule')}
          {data?.valid_combinations_count != null
            ? ` · ${String(data.valid_combinations_count)} combinacions vàlides`
            : ''}
          {previewMutation.data?.after?.valid_combinations != null && (
            <>
              {' '}
              · Live: {String(previewMutation.data.after.valid_combinations)} vàlides (
              {String(previewMutation.data.survival_rate_pct)}% supervivència)
            </>
          )}
        </p>
      </header>

      {previewMutation.data?.delta_valid_combinations != null && (
        <p className="cca-suggestions__preview">
          Impacte CCA: {String(previewMutation.data.before.valid_combinations)} →{' '}
          {String(previewMutation.data.after.valid_combinations)} combinacions (
          {previewMutation.data.delta_valid_combinations >= 0 ? '+' : ''}
          {String(previewMutation.data.delta_valid_combinations)})
        </p>
      )}

      {displayRules.length > 0 && (
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Component A</th>
              <th>Component B</th>
              <th>Justificació</th>
              <th>Font</th>
            </tr>
          </thead>
          <tbody>
            {displayRules.map((rule) => (
              <tr
                key={rule.id}
                className={rule.already_applied ? 'cca-suggestions__applied' : ''}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={rule.selected !== false}
                    disabled={Boolean(rule.already_applied)}
                    onChange={() => toggleRule(rule.id)}
                  />
                </td>
                <td>
                  {rule.component_a}/
                  <input
                    className="cca-suggestions__inline"
                    value={rule.config_a}
                    disabled={Boolean(rule.already_applied)}
                    onChange={(e) =>
                      setRules(
                        displayRules.map((r) =>
                          r.id === rule.id ? { ...r, config_a: e.target.value } : r,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  {rule.component_b}/
                  <input
                    className="cca-suggestions__inline"
                    value={rule.config_b}
                    disabled={Boolean(rule.already_applied)}
                    onChange={(e) =>
                      setRules(
                        displayRules.map((r) =>
                          r.id === rule.id ? { ...r, config_b: e.target.value } : r,
                        ),
                      )
                    }
                  />
                </td>
                <td>{rule.justification ?? '—'}</td>
                <td>{rule.source ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="cca-suggestions__actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={applyMutation.isPending}
          onClick={() => applyMutation.mutate()}
        >
          {applyMutation.isPending ? 'Aplicant…' : 'Aplicar regles seleccionades'}
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
