import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { casesService, publicAffairsService } from '../../services/api'

export default function PublicAffairsDashboard() {
  const { activeCase, setActiveCase } = useCase()
  const [tab, setTab] = useState<'policies' | 'stakeholders' | 'advocacy'>('policies')

  const { data: cases } = useQuery({
    queryKey: ['cases-for-pa'],
    queryFn: () => casesService.list(),
  })

  const { data: policies = [], isLoading: loadingPolicies } = useQuery({
    queryKey: ['pa-policies', activeCase?.id],
    queryFn: () => publicAffairsService.getPolicies(activeCase?.id),
  })

  const { data: stakeholders = [], isLoading: loadingStakeholders } = useQuery({
    queryKey: ['pa-stakeholders', activeCase?.id],
    queryFn: () => publicAffairsService.getStakeholders(activeCase?.id),
    enabled: activeCase !== null,
  })

  const { data: opportunities = [] } = useQuery({
    queryKey: ['pa-advocacy', activeCase?.id],
    queryFn: () => publicAffairsService.getAdvocacyOpportunities(activeCase?.id),
  })

  const TABS = [
    { id: 'policies' as const, label: 'Polítiques', count: (policies as unknown[]).length },
    { id: 'stakeholders' as const, label: 'Stakeholders', count: (stakeholders as unknown[]).length },
    { id: 'advocacy' as const, label: 'Oportunitats', count: (opportunities as unknown[]).length },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--spacing-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700,
                       color: 'var(--color-primary)', margin: 0 }}>
            Assumptes Públics
          </h1>
          <p style={{ color: 'var(--color-gray-600)', fontSize: 'var(--font-size-sm)',
                      margin: '4px 0 0' }}>
            Polítiques, stakeholders i oportunitats d&apos;advocacy vinculades al cas actiu.
          </p>
        </div>

        <select
          style={{ padding: '8px 12px', border: '1px solid var(--color-gray-300)',
                   borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)',
                   minWidth: 220, background: 'var(--color-white)' }}
          value={activeCase?.id ?? ''}
          onChange={(e) => {
            const id = Number(e.target.value)
            const c = (cases as { id: number; name: string }[] | undefined)?.find((x) => x.id === id)
            if (c) setActiveCase({ id: c.id, name: c.name, case_type: '', status: 'actiu' })
          }}
        >
          <option value="">— Selecciona un cas —</option>
          {((cases as { id: number; name: string }[]) ?? []).map((c) => (
            <option key={c.id} value={c.id}>#{c.id} — {c.name}</option>
          ))}
        </select>
      </div>

      {!activeCase && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">⊙</div>
            <h3 className="empty-state-title">Cap cas seleccionat</h3>
            <p className="empty-state-desc">
              Selecciona un cas per veure les polítiques, stakeholders i
              oportunitats d&apos;advocacy associades.
            </p>
          </div>
        </div>
      )}

      {activeCase && (
        <div className="card">
          <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--color-gray-200)',
                        marginBottom: 'var(--spacing-lg)' }}>
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                style={{
                  padding: '10px 20px',
                  border: 'none',
                  borderBottom: tab === t.id
                    ? '2px solid var(--color-primary)' : '2px solid transparent',
                  background: 'none',
                  color: tab === t.id ? 'var(--color-primary)' : 'var(--color-gray-500)',
                  fontWeight: tab === t.id ? 600 : 400,
                  fontSize: 'var(--font-size-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {t.label}
                {t.count > 0 && (
                  <span style={{
                    background: tab === t.id ? 'var(--color-primary)' : 'var(--color-gray-200)',
                    color: tab === t.id ? 'white' : 'var(--color-gray-600)',
                    borderRadius: '999px',
                    padding: '0 6px',
                    fontSize: '11px',
                    fontWeight: 600,
                  }}>
                    {t.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === 'policies' && (
            <>
              {loadingPolicies && (
                <div className="spinner" style={{ margin: '2rem auto' }} />
              )}
              {!loadingPolicies && (policies as unknown[]).length === 0 && (
                <div className="empty-state">
                  <div className="empty-state-icon">⊙</div>
                  <h3 className="empty-state-title">Sense polítiques per a aquest cas</h3>
                  <p className="empty-state-desc">
                    Les polítiques s&apos;associen automàticament als casos quan
                    s&apos;analitza l&apos;impacte regulatori.
                  </p>
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                {(policies as {
                  id?: number; policy_topic?: string; title?: string; name?: string
                  jurisdiction?: string; impact_level?: string
                }[]).map((p, i) => (
                  <div key={p.id ?? i} style={{
                    padding: 'var(--spacing-sm) var(--spacing-md)',
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 'var(--spacing-md)',
                  }}>
                    <div>
                      <p style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)',
                                  color: 'var(--color-gray-800)', margin: 0 }}>
                        {p.policy_topic ?? p.title ?? p.name ?? `Política #${i + 1}`}
                      </p>
                      {p.jurisdiction && (
                        <p style={{ fontSize: 'var(--font-size-xs)',
                                    color: 'var(--color-gray-500)', margin: '2px 0 0' }}>
                          {p.jurisdiction}
                        </p>
                      )}
                    </div>
                    {p.impact_level && (
                      <span className={`status-badge ${
                        p.impact_level === 'high' || p.impact_level === 'critical'
                          ? 'danger' : p.impact_level === 'moderate' ? 'warning' : 'neutral'
                      }`}>
                        {p.impact_level}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {tab === 'stakeholders' && (
            <>
              {loadingStakeholders && (
                <div className="spinner" style={{ margin: '2rem auto' }} />
              )}
              {!loadingStakeholders && (stakeholders as unknown[]).length === 0 && (
                <div className="empty-state">
                  <div className="empty-state-icon">◉</div>
                  <h3 className="empty-state-title">Sense stakeholders per a aquest cas</h3>
                  <p className="empty-state-desc">
                    Els stakeholders s&apos;afegeixen quan s&apos;analitza l&apos;impacte
                    de les polítiques del cas.
                  </p>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))',
                            gap: 'var(--spacing-md)' }}>
                {(stakeholders as {
                  id?: number; name?: string; stakeholder_type?: string
                  influence_level?: string
                }[]).map((s, i) => (
                  <div key={s.id ?? i} style={{
                    padding: 'var(--spacing-md)',
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-gray-50)',
                  }}>
                    <p style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)',
                                color: 'var(--color-primary)', margin: '0 0 4px' }}>
                      {s.name ?? `Stakeholder #${i + 1}`}
                    </p>
                    {s.stakeholder_type && (
                      <p style={{ fontSize: 'var(--font-size-xs)',
                                  color: 'var(--color-gray-500)', margin: 0 }}>
                        {s.stakeholder_type}
                        {s.influence_level ? ` · ${s.influence_level}` : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {tab === 'advocacy' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              {(opportunities as unknown[]).length === 0 && (
                <div className="empty-state">
                  <div className="empty-state-icon">△</div>
                  <h3 className="empty-state-title">Sense oportunitats identificades</h3>
                  <p className="empty-state-desc">
                    Les oportunitats d&apos;advocacy s&apos;identifiquen a partir de
                    l&apos;anàlisi de polítiques i stakeholders.
                  </p>
                </div>
              )}
              {(opportunities as {
                title?: string; name?: string; description?: string
              }[]).map((o, i) => (
                <div key={i} style={{
                  padding: 'var(--spacing-md)',
                  border: '1px solid var(--color-gray-200)',
                  borderLeft: '3px solid var(--color-accent)',
                  borderRadius: 'var(--radius-sm)',
                }}>
                  <p style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)',
                              color: 'var(--color-gray-800)', margin: 0 }}>
                    {o.title ?? o.name ?? `Oportunitat #${i + 1}`}
                  </p>
                  {o.description && (
                    <p style={{ fontSize: 'var(--font-size-xs)',
                                color: 'var(--color-gray-500)', margin: '4px 0 0',
                                lineHeight: 1.5 }}>
                      {o.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
