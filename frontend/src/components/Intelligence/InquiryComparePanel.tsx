import './InquiryComparePanel.css'

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
  if (items.length < 2) {
    return (
      <p className="inquiry-compare__empty">
        Calen almenys 2 inquiries al cas per mostrar la comparativa.
      </p>
    )
  }

  return (
    <div className="inquiry-compare">
      {probabilitySeries.length >= 2 && (
        <div className="inquiry-compare__sparkline" aria-hidden>
          {probabilitySeries.map((p) => (
            <span key={p.id} title={`#${p.id}: ${p.probability_pct}%`}>
              #{p.id}: {p.probability_pct}%
            </span>
          ))}
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Estat</th>
            <th>Prob.</th>
            <th>Δ prev</th>
            <th>Possibilitat</th>
            <th>Runs</th>
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
                    Wizard
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
