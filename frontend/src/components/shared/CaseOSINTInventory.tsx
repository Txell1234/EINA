import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink, ChevronDown, ChevronRight, Database, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { osintService } from '../../services/api'
import type { CaseInventory } from '../../utils/osintDisplay'
import './CaseOSINTInventory.css'

type CaseOSINTInventoryProps = {
  caseId: number
}

export default function CaseOSINTInventory({ caseId }: CaseOSINTInventoryProps) {
  const [expandedType, setExpandedType] = useState<string | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['osint-inventory', caseId],
    queryFn: () => osintService.getCaseInventory(caseId),
    enabled: caseId > 0,
    staleTime: 15_000,
  })

  const inv = data as CaseInventory | undefined

  if (isLoading || !inv) {
    return <p className="case-osint-inv-loading">Carregant inventari OSINT del cas…</p>
  }

  const s = inv.summary

  return (
    <div className="case-osint-inv">
      <div className="case-osint-inv__header">
        <h3>
          <Database size={16} /> Inventari OSINT del cas
        </h3>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => refetch()}>
          Actualitzar
        </button>
      </div>

      <div className="case-osint-inv__stats">
        <div className="case-osint-inv__stat">
          <span>Consultes</span>
          <strong>{s.total_queries}</strong>
        </div>
        <div className="case-osint-inv__stat">
          <span>Articles</span>
          <strong>{s.unique_articles}</strong>
        </div>
        <div className="case-osint-inv__stat">
          <span>Extrets</span>
          <strong>{s.extracted_urls}</strong>
        </div>
        <div className="case-osint-inv__stat highlight">
          <span>Pendents</span>
          <strong>{s.pending_extraction}</strong>
        </div>
        {s.research_reports > 0 ? (
          <div className="case-osint-inv__stat">
            <span>Informes Research</span>
            <strong>{s.research_reports}</strong>
          </div>
        ) : null}
      </div>

      {s.top_domains.length > 0 ? (
        <p className="case-osint-inv__domains">
          Dominis principals:{' '}
          {s.top_domains.slice(0, 6).map((d) => (
            <span key={d.domain} className="case-osint-inv__domain-chip">
              {d.domain} ({d.count})
            </span>
          ))}
        </p>
      ) : null}

      {inv.recommended_actions.length > 0 ? (
        <ul className="case-osint-inv__actions">
          {inv.recommended_actions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      ) : null}

      <div className="case-osint-inv__quick">
        <Link to="/prospective" className="btn btn-accent btn-sm">
          Extracció prospectiva →
        </Link>
        <Link to="/intelligence" className="btn btn-sm">
          Pipeline intel·ligència →
        </Link>
      </div>

      {inv.research_briefs.length > 0 ? (
        <section className="case-osint-inv__section">
          <h4>
            <FileText size={14} /> Informes Tavily Research
          </h4>
          {inv.research_briefs.map((b, i) => (
            <div key={i} className="case-osint-inv__brief">
              <p>{b.excerpt}</p>
              {b.source_count != null ? (
                <span className="case-osint-inv__brief-meta">{b.source_count} fonts citades</span>
              ) : null}
            </div>
          ))}
        </section>
      ) : null}

      <section className="case-osint-inv__section">
        <h4>Per tipus de font</h4>
        {inv.source_groups.length === 0 ? (
          <p className="case-osint-inv__empty">Encara no hi ha dades OSINT vinculades a aquest cas.</p>
        ) : (
          inv.source_groups.map((g) => {
            const open = expandedType === g.query_type
            return (
              <div key={g.query_type} className="case-osint-inv__group">
                <button
                  type="button"
                  className="case-osint-inv__group-head"
                  onClick={() => setExpandedType(open ? null : g.query_type)}
                >
                  {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span className="case-osint-inv__group-label">{g.label}</span>
                  <span className="case-osint-inv__group-count">
                    {g.query_count} consulta{g.query_count !== 1 ? 'es' : ''} · {g.article_count} articles
                  </span>
                </button>
                {open ? (
                  <div className="case-osint-inv__runs">
                    {g.runs.map((run) => (
                      <div key={run.query_id} className="case-osint-inv__run">
                        <p className="case-osint-inv__run-title">
                          {run.params_summary || g.label}
                          {run.created_at ? (
                            <span> · {new Date(run.created_at).toLocaleDateString('ca-ES')}</span>
                          ) : null}
                        </p>
                        {run.error ? <p className="case-osint-inv__run-error">{run.error}</p> : null}
                        {run.research_report ? (
                          <p className="case-osint-inv__run-research">{run.research_report.excerpt}</p>
                        ) : null}
                        <ul className="case-osint-inv__articles">
                          {run.articles.map((a, i) => (
                            <li key={`${a.url}-${i}`}>
                              <span className={a.extracted ? 'extracted' : 'pending'}>
                                {a.extracted ? '✓' : '○'}
                              </span>
                              {a.url ? (
                                <a href={a.url} target="_blank" rel="noopener noreferrer">
                                  {a.title}
                                  <ExternalLink size={10} />
                                </a>
                              ) : (
                                <span>{a.title}</span>
                              )}
                              {a.domain ? <em>{a.domain}</em> : null}
                            </li>
                          ))}
                          {run.article_count > run.articles.length ? (
                            <li className="case-osint-inv__more">
                              +{run.article_count - run.articles.length} més al resultat #{run.result_id}
                            </li>
                          ) : null}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )
          })
        )}
      </section>
    </div>
  )
}
