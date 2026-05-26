import './AnalysisScopeBar.css'

type ExtractionFiltersRowProps = {
  decision: string
  domain: string
  onDecisionChange: (v: string) => void
  onDomainChange: (v: string) => void
}

const DECISION_OPTIONS = [
  { value: '', label: 'Totes les decisions' },
  { value: 'KEEP', label: 'KEEP — rellevants' },
  { value: 'REVIEW', label: 'REVIEW — revisar' },
  { value: 'REMOVE', label: 'REMOVE — descartades' },
  { value: 'SYNTHETIC', label: 'SYNTHETIC — sintètiques' },
]

export default function ExtractionFiltersRow({
  decision,
  domain,
  onDecisionChange,
  onDomainChange,
}: ExtractionFiltersRowProps) {
  return (
    <div className="analysis-scope-bar analysis-scope-bar--compact">
      <div className="analysis-scope-bar__header">
        <span className="analysis-scope-bar__title">Filtres de declaracions</span>
      </div>
      <div className="analysis-scope-bar__grid">
        <label className="analysis-scope-field">
          <span>Decisió neteja</span>
          <select value={decision} onChange={(e) => onDecisionChange(e.target.value)}>
            {DECISION_OPTIONS.map((o) => (
              <option key={o.value || 'all'} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="analysis-scope-field analysis-scope-field--wide">
          <span>Domini font</span>
          <input
            type="text"
            placeholder="foreignaffairs.com, nikkei.com"
            value={domain}
            onChange={(e) => onDomainChange(e.target.value)}
          />
        </label>
      </div>
    </div>
  )
}
