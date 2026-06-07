import { Line, LineChart, ResponsiveContainer } from 'recharts'
import { useI18n } from '../../contexts/I18nContext'
import './InquiryComparePanel.css'
import './q2fs-tokens.css'

export type InquiryCompareItem = {
  id: number
  question: string
  status: string
  mode?: string
  run_count?: number
  probability_pct?: number | null
  possibility?: string | null
  confidence?: number | null
  completed_at?: string | null
  wizard_project_id?: number | null
  diff_vs_previous?: {
    probability_delta?: number | null
    possibility_changed?: boolean
  } | null
}

type InquiryComparePanelProps = {
  items: InquiryCompareItem[]
  probabilitySeries?: Array<{ id: number; probability_pct: number }>
  onOpenWizard?: (inquiryId: number, projectId?: number | null) => void
}

export default function InquiryComparePanel({
  items,
  probabilitySeries = [],
  onOpenWizard,
}: InquiryComparePanelProps) {
  const { t } = useI18n()

  if (items.length < 2) {
    return <p className="inquiry-compare__empty">{t('inquiry.panel.compare.empty')}</p>
  }

  const chartData = probabilitySeries
    .filter((p) => p.probability_pct != null)
    .map((p, i) => ({ i, v: p.probability_pct, id: p.id }))

  return (
    <div className="inquiry-compare">
      {chartData.length >= 2 && (
        <div className="inquiry-compare__chart" aria-hidden>
          <ResponsiveContainer width="100%" height={48}>
            <LineChart data={chartData}>
              <Line type="monotone" dataKey="v" stroke="var(--q2fs-accent, #1e3a5f)" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
          <div className="inquiry-compare__sparkline">
            {probabilitySeries.map((p) => (
              <span key={p.id} title={`#${p.id}: ${p.probability_pct}%`}>
                #{p.id}: {p.probability_pct}%
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="inquiry-compare__table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>{t('inquiry.panel.compare.col.status')}</th>
              <th>{t('inquiry.panel.compare.col.prob')}</th>
              <th>{t('inquiry.panel.compare.col.delta')}</th>
              <th>{t('inquiry.panel.compare.col.possibility')}</th>
              <th>{t('inquiry.panel.compare.col.runs')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id}>
                <td>#{row.id}</td>
                <td>{row.status}</td>
                <td>{row.probability_pct != null ? `${row.probability_pct}%` : '—'}</td>
                <td>
                  {row.diff_vs_previous?.probability_delta != null
                    ? `${row.diff_vs_previous.probability_delta > 0 ? '+' : ''}${row.diff_vs_previous.probability_delta}`
                    : '—'}
                </td>
                <td>{row.possibility ?? '—'}</td>
                <td>{row.run_count ?? 0}</td>
                <td>
                  {onOpenWizard && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => onOpenWizard(row.id, row.wizard_project_id)}
                    >
                      {t('inquiry.panel.compare.wizard')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
