import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { intelligenceService } from '../../services/api'
import './PolicyIndustryPanel.css'

type PolicyIndustryPanelProps = {
  caseId: number
  premise?: string
  defaultEnrich?: boolean
}

type CompanyRow = {
  name: string
  country?: string
  region?: string
  roles?: string[]
  sectors?: string[]
  beneficiary_rationale?: string
  policy_link?: string
  confidence?: string
  source?: string
  contractor_relationships?: Array<{ partner?: string; type?: string; region?: string }>
  evidence?: Array<{ excerpt?: string; url?: string; topic?: string }>
}

export default function PolicyIndustryPanel({
  caseId,
  premise,
  defaultEnrich = false,
}: PolicyIndustryPanelProps) {
  const [enrich, setEnrich] = useState(defaultEnrich)
  const [regionTab, setRegionTab] = useState<'all' | 'domestic' | 'overseas'>('all')

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['policy-industry', caseId, premise, enrich],
    queryFn: () =>
      premise
        ? intelligenceService.analyzePolicyIndustry(caseId, { premise, enrich })
        : intelligenceService.getPolicyIndustryMap(caseId, { enrich }),
    enabled: caseId > 0,
  })

  if (isLoading) {
    return <p className="policy-industry-panel__msg">Mapant empreses i contractistes…</p>
  }
  if (error) {
    return <p className="policy-industry-panel__msg">No s&apos;ha pogut carregar el mapa industrial.</p>
  }
  if (!data?.found) {
    return <p className="policy-industry-panel__msg">Cas no trobat.</p>
  }

  const summary = data.summary ?? {}
  const roleLabels = (data.role_labels ?? {}) as Record<string, string>
  let companies = (data.companies ?? []) as CompanyRow[]
  if (regionTab === 'domestic') {
    companies = (data.by_region?.domestic ?? []) as CompanyRow[]
  } else if (regionTab === 'overseas') {
    companies = (data.by_region?.overseas ?? []) as CompanyRow[]
  }

  return (
    <section className="policy-industry-panel card">
      <header className="policy-industry-panel__header">
        <div>
          <h3>Policy × Indústria · empreses i beneficiaris</h3>
          <p className="policy-industry-panel__sub">
            Qui es beneficia i per què (contractistes, proveïdors, offset) — domèstic i overseas ·{' '}
            {summary.companies_total ?? 0} entitats
          </p>
        </div>
        <div className="policy-industry-panel__actions">
          <label className="policy-industry-panel__enrich">
            <input type="checkbox" checked={enrich} onChange={(e) => setEnrich(e.target.checked)} />
            Enriquir amb IA
          </label>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? 'Actualitzant…' : 'Actualitzar'}
          </button>
        </div>
      </header>

      {data.themes?.length ? (
        <div className="policy-industry-panel__themes">
          {(data.themes as string[]).map((t) => (
            <span key={t} className="policy-industry-chip">
              {(data.theme_labels as Record<string, string>)?.[t] ?? t}
            </span>
          ))}
        </div>
      ) : null}

      <div className="policy-industry-panel__stats">
        <span>🇯🇵 Domèstic: {summary.domestic ?? 0}</span>
        <span>🌐 Overseas: {summary.overseas ?? 0}</span>
        <span>OSINT: {summary.from_osint ?? 0}</span>
        <span>Referència: {summary.from_reference ?? 0}</span>
      </div>

      <div className="policy-industry-panel__tabs">
        {(['all', 'domestic', 'overseas'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            className={`policy-industry-tab ${regionTab === tab ? 'active' : ''}`}
            onClick={() => setRegionTab(tab)}
          >
            {tab === 'all' ? 'Totes' : tab === 'domestic' ? 'Japó / domèstic' : 'Overseas'}
          </button>
        ))}
      </div>

      {premise ? (
        <p className="policy-industry-panel__premise">
          <strong>Premisa:</strong> {premise.slice(0, 240)}
          {premise.length > 240 ? '…' : ''}
        </p>
      ) : null}

      {data.premise_links?.length ? (
        <details className="policy-industry-panel__links" open={Boolean(premise)}>
          <summary>Vincle premisa → empresa ({data.premise_links.length})</summary>
          <ul>
            {(data.premise_links as Array<{ company: string; why?: string; policy_mechanism?: string; relevance_score?: number }>).slice(0, 8).map((link) => (
              <li key={link.company}>
                <strong>{link.company}</strong>
                {link.relevance_score != null ? ` (${link.relevance_score})` : ''}: {link.why}
                {link.policy_mechanism ? (
                  <span className="policy-industry-mechanism"> — {link.policy_mechanism}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <div className="policy-industry-panel__grid">
        {companies.length === 0 ? (
          <p className="policy-industry-panel__msg">Cap empresa identificada per aquest filtre.</p>
        ) : (
          companies.map((c) => (
            <article key={c.name} className={`policy-industry-card policy-industry-card--${c.region ?? 'unknown'}`}>
              <header>
                <strong>{c.name}</strong>
                <span className="policy-industry-card__meta">
                  {c.country ?? '—'} · {c.source ?? 'ref'}
                </span>
              </header>
              {c.roles?.length ? (
                <div className="policy-industry-card__roles">
                  {c.roles.map((r) => (
                    <span key={r} className="policy-industry-role">
                      {roleLabels[r] ?? r}
                    </span>
                  ))}
                </div>
              ) : null}
              {c.beneficiary_rationale ? (
                <p className="policy-industry-card__why">
                  <strong>Per què:</strong> {c.beneficiary_rationale}
                </p>
              ) : null}
              {c.policy_link ? (
                <p className="policy-industry-card__policy">
                  <strong>Policy:</strong> {c.policy_link}
                </p>
              ) : null}
              {c.contractor_relationships?.length ? (
                <ul className="policy-industry-card__rels">
                  {c.contractor_relationships.map((rel) => (
                    <li key={`${rel.partner}-${rel.type}`}>
                      → {rel.partner} ({rel.type})
                    </li>
                  ))}
                </ul>
              ) : null}
              {c.evidence?.length ? (
                <details>
                  <summary>Evidència OSINT ({c.evidence.length})</summary>
                  <ul>
                    {c.evidence.slice(0, 3).map((ev, i) => (
                      <li key={i}>
                        {ev.url ? (
                          <a href={ev.url} target="_blank" rel="noreferrer">
                            {ev.excerpt?.slice(0, 120) ?? ev.topic}
                          </a>
                        ) : (
                          ev.excerpt?.slice(0, 120)
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </article>
          ))
        )}
      </div>

      {data.supply_links?.length ? (
        <details className="policy-industry-panel__supply">
          <summary>Cadena contractista ({data.supply_links.length} enllaços)</summary>
          <ul>
            {(data.supply_links as Array<{ from: string; to: string; type?: string }>).slice(0, 12).map((l, i) => (
              <li key={i}>
                {l.from} → {l.to} ({l.type})
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  )
}
