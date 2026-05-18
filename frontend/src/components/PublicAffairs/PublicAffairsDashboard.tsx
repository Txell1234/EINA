import { useQuery } from '@tanstack/react-query'
import { publicAffairsService } from '../../services/api'

export default function PublicAffairsDashboard() {
  const { data: policies = [], isLoading: loadingPolicies } = useQuery({
    queryKey: ['public-affairs-policies'],
    queryFn: () => publicAffairsService.getPolicies(),
  })

  const { data: stakeholders = [], isLoading: loadingStakeholders } = useQuery({
    queryKey: ['public-affairs-stakeholders'],
    queryFn: () => publicAffairsService.getStakeholders(),
  })

  const { data: opportunities = [] } = useQuery({
    queryKey: ['public-affairs-advocacy'],
    queryFn: () => publicAffairsService.getAdvocacyOpportunities(),
  })

  return (
    <div className="card">
      <h1>Assumptes públics</h1>
      <p style={{ color: 'var(--color-gray-600)' }}>
        Polítiques, stakeholders i oportunitats d&apos;advocacy vinculades al cas.
      </p>

      <h2 style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-lg)' }}>Polítiques</h2>
      {loadingPolicies && <p>Carregant...</p>}
      <ul className="project-list">
        {(policies as { id?: number; title?: string; name?: string }[]).slice(0, 10).map((p, i) => (
          <li key={p.id ?? i}>{p.title ?? p.name ?? JSON.stringify(p)}</li>
        ))}
      </ul>

      <h2 style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-lg)', marginTop: 'var(--spacing-xl)' }}>
        Stakeholders
      </h2>
      {loadingStakeholders && <p>Carregant...</p>}
      <ul className="project-list">
        {(stakeholders as { id?: number; name?: string }[]).slice(0, 10).map((s, i) => (
          <li key={s.id ?? i}>{s.name ?? JSON.stringify(s)}</li>
        ))}
      </ul>

      <h2 style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-lg)', marginTop: 'var(--spacing-xl)' }}>
        Oportunitats d&apos;advocacy
      </h2>
      <ul className="project-list">
        {(opportunities as { title?: string; name?: string }[]).slice(0, 8).map((o, i) => (
          <li key={i}>{o.title ?? o.name ?? JSON.stringify(o)}</li>
        ))}
      </ul>
    </div>
  )
}
