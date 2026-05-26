import { useQuery } from '@tanstack/react-query'
import { intelligenceService } from '../../services/api'
import './ActorNetworkPanel.css'

type ActorNetworkPanelProps = {
  caseId: number
}

export default function ActorNetworkPanel({ caseId }: ActorNetworkPanelProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['actor-network', caseId],
    queryFn: () => intelligenceService.getActorNetwork(caseId),
    enabled: caseId > 0,
  })

  if (isLoading) return <p className="actor-network-panel__msg">Carregant xarxa d&apos;actors…</p>
  if (error) return <p className="actor-network-panel__msg">No s&apos;ha pogut carregar la xarxa d&apos;actors.</p>
  if (!data?.found) return <p className="actor-network-panel__msg">Sense dades d&apos;actors per aquest cas.</p>

  const summary = data.summary ?? {}
  const scenarios = (data.scenarios ?? []) as Array<{
    scenario_type?: string
    name?: string
    label?: string
    risk_profile?: string
    reversibility?: string
  }>

  return (
    <section className="actor-network-panel card">
      <header className="actor-network-panel__header">
        <h3>Xarxa d&apos;actors i institucions</h3>
        <p className="actor-network-panel__sub">
          {summary.actor_count ?? 0} actors · {summary.edge_count ?? 0} relacions · diferenciació per tipus i temàtica
        </p>
      </header>

      {scenarios.length > 0 ? (
        <div className="actor-network-panel__scenarios">
          <h4>Escenaris (Godet)</h4>
          <div className="actor-network-panel__scenario-grid">
            {scenarios.map((sc) => (
              <div
                key={sc.scenario_type ?? sc.name}
                className={`actor-scenario-card actor-scenario-card--${sc.scenario_type ?? 'other'}`}
              >
                <strong>{sc.label ?? sc.name}</strong>
                <span>{sc.risk_profile?.replace(/_/g, ' ') ?? sc.scenario_type}</span>
                {sc.reversibility ? (
                  <span className="actor-scenario-card__rev">Reversibilitat: {sc.reversibility}</span>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="actor-network-panel__summary-row">
        {Object.entries(summary.by_actor_class ?? {}).map(([cls, n]) => (
          <span key={cls} className="actor-network-stat">
            <strong>{n as number}</strong> {cls}
          </span>
        ))}
      </div>

      <div className="actor-network-panel__table-wrap">
        <table className="actor-network-table">
          <thead>
            <tr>
              <th>Actor</th>
              <th>Classe</th>
              <th>Institució</th>
              <th>Declaracions</th>
              <th>Postura mitjana</th>
              <th>Temes</th>
            </tr>
          </thead>
          <tbody>
            {(data.actors ?? []).slice(0, 20).map(
              (a: {
                id: string
                name: string
                actor_class: string
                institution_subtype: string
                statement_count: number
                avg_posture: number
                topics: [string, number][]
              }) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>
                    <span className="actor-tag actor-tag--class">{a.actor_class}</span>
                  </td>
                  <td>
                    <span className="actor-tag actor-tag--inst">
                      {a.institution_subtype?.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>{a.statement_count}</td>
                  <td>{a.avg_posture}</td>
                  <td>{(a.topics ?? []).slice(0, 2).map(([t]) => t).join(', ')}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
