import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { prospectiveInquiryService } from '../../services/api'
import './InquiryDashboard.css'

type DashboardItem = {
  id: number
  case_id: number
  case_name: string
  question: string
  mode: string
  status: string
  run_count: number
  probability_pct?: number | null
  possibility?: string | null
  auto_rerun_enabled?: boolean
  next_rerun_at?: string | null
  scheduled_due?: boolean
  wizard_project_id?: number | null
  created_at?: string | null
}

export default function InquiryDashboard() {
  const [statusFilter, setStatusFilter] = useState('')
  const [scheduledOnly, setScheduledOnly] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [exporting, setExporting] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['inquiry-dashboard', statusFilter, scheduledOnly],
    queryFn: () =>
      prospectiveInquiryService.dashboard({
        status: statusFilter || undefined,
        scheduledOnly,
      }),
  })

  const items = (data?.items as DashboardItem[]) ?? []
  const stats = (data?.stats as Record<string, number>) ?? {}

  const dueItems = useMemo(() => items.filter((i) => i.scheduled_due), [items])

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === items.length) setSelected(new Set())
    else setSelected(new Set(items.map((i) => i.id)))
  }

  const handleBatchExport = async () => {
    if (selected.size === 0) return
    setExporting(true)
    try {
      await prospectiveInquiryService.exportBatch(Array.from(selected))
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="card inquiry-dashboard">
      <header className="inquiry-dashboard__header">
        <div>
          <h1>Inquiries Q2FS</h1>
          <p>Vista global de preguntes analítiques, re-runs programats i export batch.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void refetch()}>
          Actualitzar
        </button>
      </header>

      <div className="inquiry-dashboard__stats">
        <span>Total: {stats.total ?? 0}</span>
        <span>Completades: {stats.completed ?? 0}</span>
        <span>Esperant Godet: {stats.awaiting_godet ?? 0}</span>
        <span>Scheduler actiu: {stats.scheduled_active ?? 0}</span>
        <span className={dueItems.length ? 'inquiry-dashboard__alert' : ''}>
          Re-run pendents: {stats.scheduled_due ?? 0}
        </span>
      </div>

      {dueItems.length > 0 && (
        <div className="inquiry-dashboard__banner">
          {dueItems.length} inquiry(s) amb re-run programat vençut — revisa al Centre
          d&apos;Intel·ligència del cas.
        </div>
      )}

      <div className="inquiry-dashboard__filters">
        <label>
          Estat
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Tots</option>
            <option value="completed">completed</option>
            <option value="awaiting_godet">awaiting_godet</option>
            <option value="failed">failed</option>
            <option value="pending">pending</option>
          </select>
        </label>
        <label className="inquiry-dashboard__check">
          <input
            type="checkbox"
            checked={scheduledOnly}
            onChange={(e) => setScheduledOnly(e.target.checked)}
          />
          Només amb scheduler
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={selected.size === 0 || exporting}
          onClick={() => void handleBatchExport()}
        >
          {exporting ? 'Exportant…' : `Export ZIP (${selected.size})`}
        </button>
      </div>

      {isLoading ? (
        <p>Carregant…</p>
      ) : items.length === 0 ? (
        <p className="inquiry-dashboard__empty">Cap inquiry encara. Crea-ne una al Centre d&apos;Intel·ligència.</p>
      ) : (
        <table className="inquiry-dashboard__table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={selected.size === items.length && items.length > 0}
                  onChange={toggleAll}
                  aria-label="Seleccionar tots"
                />
              </th>
              <th>ID</th>
              <th>Cas</th>
              <th>Estat</th>
              <th>Prob.</th>
              <th>Runs</th>
              <th>Scheduler</th>
              <th>Pregunta</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className={row.scheduled_due ? 'inquiry-dashboard__row--due' : ''}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(row.id)}
                    onChange={() => toggleSelect(row.id)}
                  />
                </td>
                <td>#{row.id}</td>
                <td>
                  <Link to="/intelligence">{row.case_name}</Link>
                  <span className="inquiry-dashboard__muted"> #{row.case_id}</span>
                </td>
                <td>{row.status}</td>
                <td>{row.probability_pct != null ? `${row.probability_pct}%` : '—'}</td>
                <td>{row.run_count}</td>
                <td>
                  {row.auto_rerun_enabled ? (
                    <>
                      {row.scheduled_due ? '⚠ due' : 'actiu'}
                      {row.next_rerun_at ? (
                        <span className="inquiry-dashboard__muted"> · {row.next_rerun_at.slice(0, 16)}</span>
                      ) : null}
                    </>
                  ) : (
                    '—'
                  )}
                </td>
                <td>{row.question}…</td>
                <td>
                  {row.wizard_project_id ? (
                    <Link
                      to={`/prospective/morph?project=${row.wizard_project_id}&inquiry=${row.id}`}
                    >
                      Wizard
                    </Link>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
