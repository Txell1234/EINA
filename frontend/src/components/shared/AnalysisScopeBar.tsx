import type { AnalysisScope, AnalyticalProfile, PeriodPreset } from '../../types/analysisScope'
import './AnalysisScopeBar.css'

type AnalysisScopeBarProps = {
  scope: AnalysisScope
  onChange: (patch: Partial<AnalysisScope>) => void
  onPeriodPreset: (preset: PeriodPreset) => void
  focusLabel?: string
  suggestedQuery?: string
  suggestedQueries?: string[]
  compact?: boolean
  showTopic?: boolean
  showDomain?: boolean
  showSource?: boolean
  showRelevance?: boolean
  themes?: string[]
  analyticalProfile?: AnalyticalProfile | null
}

const PERIOD_OPTIONS: { value: PeriodPreset; label: string }[] = [  { value: '7', label: '7 dies' },
  { value: '30', label: '30 dies' },
  { value: '90', label: '90 dies' },
  { value: '180', label: '6 mesos' },
  { value: '365', label: '1 any' },
  { value: 'custom', label: 'Personalitzat' },
]

export default function AnalysisScopeBar({
  scope,
  onChange,
  onPeriodPreset,
  focusLabel,
  suggestedQuery,
  suggestedQueries,
  compact = false,
  showTopic = true,
  showDomain = true,
  showSource = true,
  showRelevance = true,
  themes,
  analyticalProfile,
}: AnalysisScopeBarProps) {
  const themeLabels = analyticalProfile?.theme_labels ?? {}
  const lensLabels = analyticalProfile?.lens_labels ?? {}
  const institutionLabels = analyticalProfile?.institution_subtype_labels ?? {}

  return (    <div className={`analysis-scope-bar ${compact ? 'analysis-scope-bar--compact' : ''}`}>
      <div className="analysis-scope-bar__header">
        <span className="analysis-scope-bar__title">Delimitació d&apos;anàlisi</span>
        {focusLabel && (
          <span className="analysis-scope-bar__focus" title={suggestedQuery}>
            Focus: {focusLabel}
          </span>
        )}
      </div>

      <div className="analysis-scope-bar__grid">
        <label className="analysis-scope-field">
          <span>Període</span>
          <select
            value={scope.periodPreset}
            onChange={(e) => onPeriodPreset(e.target.value as PeriodPreset)}
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        {scope.periodPreset === 'custom' && (
          <>
            <label className="analysis-scope-field">
              <span>Des de</span>
              <input
                type="date"
                value={scope.startDate}
                onChange={(e) => onChange({ startDate: e.target.value, periodPreset: 'custom' })}
              />
            </label>
            <label className="analysis-scope-field">
              <span>Fins a</span>
              <input
                type="date"
                value={scope.endDate}
                onChange={(e) => onChange({ endDate: e.target.value, periodPreset: 'custom' })}
              />
            </label>
          </>
        )}

        {showDomain && (
          <label className="analysis-scope-field analysis-scope-field--wide">
            <span>Dominis (opcional)</span>
            <input
              type="text"
              placeholder="nikkei.com, reuters.com"
              value={scope.domains}
              onChange={(e) => onChange({ domains: e.target.value })}
            />
          </label>
        )}

        {showSource && (
          <label className="analysis-scope-field">
            <span>Fonts OSINT</span>
            <input
              type="text"
              placeholder="gdelt, tavily, rss"
              value={scope.sources}
              onChange={(e) => onChange({ sources: e.target.value })}
            />
          </label>
        )}

        {showTopic && (
          <label className="analysis-scope-field analysis-scope-field--check">
            <input
              type="checkbox"
              checked={scope.applyTopicFilter}
              onChange={(e) => onChange({ applyTopicFilter: e.target.checked })}
            />
            <span>Filtrar per temàtica del cas</span>
          </label>
        )}

        {showRelevance && showTopic && (
          <label className="analysis-scope-field">
            <span>Mín. rellevància ({Math.round(scope.minRelevance * 100)}%)</span>
            <input
              type="range"
              min={0.15}
              max={0.6}
              step={0.01}
              value={scope.minRelevance}
              onChange={(e) => onChange({ minRelevance: parseFloat(e.target.value) })}
            />
          </label>
        )}
      </div>

      {suggestedQuery && (
        <p className="analysis-scope-bar__hint">
          Consulta suggerida: <code>{suggestedQuery}</code>
          {suggestedQueries && suggestedQueries.length > 1 && (
            <span className="analysis-scope-bar__alt-queries">
              {' '}
              Altres:{' '}
              {suggestedQueries.slice(1).map((q) => (
                <code key={q}>{q}</code>
              ))}
            </span>
          )}
        </p>
      )}

      {(themes?.length || analyticalProfile?.analysis_lenses?.length) ? (
        <div className="analysis-scope-bar__chips">
          {(themes ?? Object.keys(themeLabels)).map((t) => (
            <span key={t} className="analysis-scope-chip analysis-scope-chip--theme" title="Temàtica del cas">
              {themeLabels[t] ?? t.replace(/_/g, ' ')}
            </span>
          ))}
          {analyticalProfile?.analysis_lenses?.map((lens) => (
            <span key={lens} className="analysis-scope-chip analysis-scope-chip--lens" title="Marc analític aplicable">
              {lensLabels[lens] ?? lens.replace(/_/g, ' ')}
            </span>
          ))}
          {analyticalProfile?.institution_subtypes_focus?.slice(0, 4).map((inst) => (
            <span key={inst} className="analysis-scope-chip analysis-scope-chip--institution" title="Tipus d'institució rellevant">
              {institutionLabels[inst] ?? inst.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}