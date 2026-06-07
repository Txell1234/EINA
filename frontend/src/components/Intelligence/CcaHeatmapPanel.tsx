import { useI18n } from '../../contexts/I18nContext'
import './CcaHeatmapPanel.css'
import './q2fs-tokens.css'

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
  const { t } = useI18n()
  const inconsistent = cells.filter((c) => c.value === -1)

  if (inconsistent.length === 0 && (!parameters || parameters.length === 0)) {
    return <p className="cca-heatmap__empty">{t('inquiry.panel.cca.empty')}</p>
  }

  return (
    <div className="cca-heatmap">
      <div className="cca-heatmap__summary">
        <span className="cca-heatmap__badge">{t('inquiry.panel.cca.summary', { count: inconsistent.length })}</span>
      </div>

      {parameters && parameters.length > 0 && (
        <div className="cca-heatmap__params">
          {parameters.map((p) => (
            <span key={p.code} className="cca-heatmap__param">
              <strong>{p.code}</strong>: {p.states.join(' · ')}
            </span>
          ))}
        </div>
      )}

      {inconsistent.length > 0 && (
        <>
          <p className="cca-heatmap__chips-title">{t('inquiry.panel.cca.chipsTitle')}</p>
          <div className="cca-heatmap__chips">
            {inconsistent.slice(0, 12).map((c) => (
              <span
                key={`${c.param_a}-${c.state_a}-${c.param_b}-${c.state_b}`}
                className="cca-heatmap__chip"
                title={`${c.param_a}/${c.state_a} ↔ ${c.param_b}/${c.state_b}`}
              >
                {c.param_a}/{c.state_a} ↔ {c.param_b}/{c.state_b}
              </span>
            ))}
          </div>
        </>
      )}

      <div className="cca-heatmap__table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t('inquiry.panel.cca.paramA')}</th>
              <th>{t('inquiry.panel.cca.paramB')}</th>
              <th>{t('inquiry.panel.cca.inconsistent')}</th>
            </tr>
          </thead>
          <tbody>
            {inconsistent.slice(0, 20).map((c) => (
              <tr key={`row-${c.param_a}-${c.state_a}-${c.param_b}-${c.state_b}`}>
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
      </div>
      {inconsistent.length > 20 && (
        <p className="cca-heatmap__more">{t('inquiry.panel.cca.more', { count: inconsistent.length - 20 })}</p>
      )}
    </div>
  )
}
