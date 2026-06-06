import './CcaHeatmapPanel.css'

export type CcaCell = {
  param_a: string
  state_a: string
  param_b: string
  state_b: string
  value: number
}

type CcaHeatmapPanelProps = {
  cells: CcaCell[]
  parameters?: Array<{ code: string; name: string; states: string[] }>
}

export default function CcaHeatmapPanel({ cells, parameters }: CcaHeatmapPanelProps) {
  const inconsistent = cells.filter((c) => c.value === -1)
  if (inconsistent.length === 0 && (!parameters || parameters.length === 0)) {
    return <p className="cca-heatmap__empty">Cap inconsistència CCA detectada.</p>
  }

  return (
    <div className="cca-heatmap">
      {parameters && parameters.length > 0 && (
        <div className="cca-heatmap__params">
          {parameters.map((p) => (
            <span key={p.code} className="cca-heatmap__param">
              <strong>{p.code}</strong>: {p.states.join(' · ')}
            </span>
          ))}
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>Paràmetre A</th>
            <th>Paràmetre B</th>
            <th>Inconsistent</th>
          </tr>
        </thead>
        <tbody>
          {inconsistent.slice(0, 20).map((c) => (
            <tr key={`${c.param_a}-${c.state_a}-${c.param_b}-${c.state_b}`}>
              <td>
                {c.param_a}/{c.state_a}
              </td>
              <td>
                {c.param_b}/{c.state_b}
              </td>
              <td className="cca-heatmap__bad">−1</td>
            </tr>
          ))}
        </tbody>
      </table>
      {inconsistent.length > 20 && (
        <p className="cca-heatmap__more">+{inconsistent.length - 20} més…</p>
      )}
    </div>
  )
}
