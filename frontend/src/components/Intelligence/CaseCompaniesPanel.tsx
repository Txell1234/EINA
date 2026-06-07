import { Building2, TrendingUp } from 'lucide-react'
import { useMemo, useState } from 'react'
import './CaseCompaniesPanel.css'

export type RegistryCompany = {
  key: string
  name: string
  ticker?: string
  country?: string
  region?: string
  roles?: string[]
  sectors?: string[]
  beneficiary_rationale?: string
  policy_link?: string
  creation_signal?: boolean
  creation_note?: string | null
  linked_aspects?: Array<{ type?: string; id?: number; label?: string }>
  origins?: string[]
  confidence?: string
  evidence_count?: number
}

type CompanyRegistry = {
  found?: boolean
  summary?: {
    total?: number
    domestic?: number
    overseas?: number
    with_creation_signal?: number
    from_godet?: number
    from_inquiry?: number
  }
  role_labels?: Record<string, string>
  companies?: RegistryCompany[]
  by_region?: { domestic?: RegistryCompany[]; overseas?: RegistryCompany[] }
  creation_opportunities?: RegistryCompany[]
}

type CaseCompaniesPanelProps = {
  registry: CompanyRegistry | null | undefined
  isLoading?: boolean
  selectedCompany: string | null
  onSelectCompany: (name: string | null) => void
  onScrollToFinancial?: () => void
  embedded?: boolean
}

const ORIGIN_LABELS: Record<string, string> = {
  policy_industry: 'Policy×Indústria',
  reference: 'Referència',
  osint: 'OSINT',
  llm: 'IA',
  godet_actor: 'Godet',
  inquiry: 'Q2FS',
}

export default function CaseCompaniesPanel({
  registry,
  isLoading,
  selectedCompany,
  onSelectCompany,
  onScrollToFinancial,
  embedded = false,
}: CaseCompaniesPanelProps) {
  const [regionTab, setRegionTab] = useState<'all' | 'domestic' | 'overseas' | 'creation'>('all')
  const [originFilter, setOriginFilter] = useState<string>('all')

  const roleLabels = registry?.role_labels ?? {}
  const summary = registry?.summary ?? {}

  const companies = useMemo(() => {
    let list = registry?.companies ?? []
    if (regionTab === 'domestic') list = registry?.by_region?.domestic ?? []
    else if (regionTab === 'overseas') list = registry?.by_region?.overseas ?? []
    else if (regionTab === 'creation') list = registry?.creation_opportunities ?? []
    if (originFilter !== 'all') {
      list = list.filter((c) => (c.origins ?? []).includes(originFilter))
    }
    return list
  }, [registry, regionTab, originFilter])

  if (isLoading && !registry) {
    return (
      <section
        className={embedded ? 'case-companies case-companies--embedded' : 'card case-companies'}
        data-testid="case-companies-panel"
      >
        <p className="case-companies__muted">Carregant empreses del cas…</p>
      </section>
    )
  }

  return (
    <section
      className={embedded ? 'case-companies case-companies--embedded' : 'card case-companies'}
      data-testid="case-companies-panel"
    >
      <header className="case-companies__header">
        <div>
          <p className="case-companies__kicker">
            <Building2 size={16} /> Registre d&apos;empreses del cas
          </p>
          <h2 className="case-companies__title">
            {summary.total ?? 0} entitats · {summary.domestic ?? 0} domèstic · {summary.overseas ?? 0}{' '}
            overseas
          </h2>
          <p className="case-companies__sub">
            Agregat de Godet, Q2FS, OSINT i Policy×Indústria — selecciona una empresa per al creuament
            financer (PRAAMS, DeGiro, etc.)
          </p>
        </div>
        {selectedCompany ? (
          <div className="case-companies__focus">
            <span>Focus:</span>
            <strong>{selectedCompany}</strong>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onSelectCompany(null)}>
              Desmarcar
            </button>
            {onScrollToFinancial ? (
              <button type="button" className="btn btn-accent btn-sm" onClick={onScrollToFinancial}>
                <TrendingUp size={14} /> Financer
              </button>
            ) : null}
          </div>
        ) : null}
      </header>

      <div className="case-companies__stats">
        <span>Godet: {summary.from_godet ?? 0}</span>
        <span>Q2FS: {summary.from_inquiry ?? 0}</span>
        <span>Oportunitats creació: {summary.with_creation_signal ?? 0}</span>
      </div>

      <div className="case-companies__filters">
        <div className="case-companies__tabs">
          {(
            [
              ['all', 'Totes'],
              ['domestic', 'Domèstic'],
              ['overseas', 'Overseas'],
              ['creation', 'Creació mercat'],
            ] as const
          ).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              className={`case-companies__tab ${regionTab === tab ? 'active' : ''}`}
              onClick={() => setRegionTab(tab)}
            >
              {label}
            </button>
          ))}
        </div>
        <select
          value={originFilter}
          onChange={(e) => setOriginFilter(e.target.value)}
          className="case-companies__origin-select"
          aria-label="Filtrar per origen"
        >
          <option value="all">Tots els orígens</option>
          {Object.entries(ORIGIN_LABELS).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="case-companies__grid">
        {companies.length === 0 ? (
          <p className="case-companies__muted">
            Cap empresa encara. Completa Godet (actors), Q2FS o OSINT — o usa un cas amb temàtica defensa
            per perfils de referència.
          </p>
        ) : (
          companies.map((c) => {
            const selected = selectedCompany === c.name
            return (
              <article
                key={c.key || c.name}
                className={`case-companies__card ${selected ? 'selected' : ''} case-companies__card--${c.region ?? 'unknown'}`}
              >
                <header>
                  <button
                    type="button"
                    className="case-companies__select-btn"
                    onClick={() => onSelectCompany(selected ? null : c.name)}
                  >
                    <strong>{c.name}</strong>
                    {selected ? <span className="case-companies__badge">Focus financer</span> : null}
                  </button>
                  <span className="case-companies__meta">
                    {c.country ?? '—'}
                    {c.ticker ? ` · ${c.ticker}` : ''} · {c.confidence ?? 'medium'}
                  </span>
                </header>
                {c.origins?.length ? (
                  <div className="case-companies__origins">
                    {c.origins.map((o) => (
                      <span key={o} className="case-companies__origin-chip">
                        {ORIGIN_LABELS[o] ?? o}
                      </span>
                    ))}
                  </div>
                ) : null}
                {c.roles?.length ? (
                  <div className="case-companies__roles">
                    {c.roles.map((r) => (
                      <span key={r} className="case-companies__role">
                        {roleLabels[r] ?? r}
                      </span>
                    ))}
                  </div>
                ) : null}
                {c.creation_signal ? (
                  <p className="case-companies__creation">
                    Oportunitat mercat{c.creation_note ? `: ${c.creation_note}` : ''}
                  </p>
                ) : null}
                {c.beneficiary_rationale ? (
                  <p className="case-companies__why">{c.beneficiary_rationale}</p>
                ) : null}
                {c.policy_link ? (
                  <p className="case-companies__policy">
                    <strong>Policy:</strong> {c.policy_link}
                  </p>
                ) : null}
                {c.linked_aspects?.length ? (
                  <ul className="case-companies__aspects">
                    {c.linked_aspects.slice(0, 3).map((a) => (
                      <li key={`${a.type}-${a.id}`}>{a.label}</li>
                    ))}
                  </ul>
                ) : null}
              </article>
            )
          })
        )}
      </div>
    </section>
  )
}
