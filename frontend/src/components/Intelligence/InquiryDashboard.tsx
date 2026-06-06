import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useI18n } from '../../contexts/I18nContext'
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
  const { t } = useI18n()
  const [statusFilter, setStatusFilter] = useState('')
  const [scheduledOnly, setScheduledOnly] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [exporting, setExporting] = useState(false)
  const [rerunning, setRerunning] = useState(false)

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

  const handleBatchRerun = async (ids: number[]) => {
    if (ids.length === 0) return
    setRerunning(true)
    try {
      await prospectiveInquiryService.rerunBatch(ids)
      setSelected(new Set())
      await refetch()
    } finally {
      setRerunning(false)
    }
  }

  return (
    <div className="card inquiry-dashboard" data-testid="inquiry-dashboard">
      <header className="inquiry-dashboard__header">
        <div>
          <h1>{t('inquiry.title')}</h1>
          <p>{t('inquiry.subtitle')}</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void refetch()}>
          {t('inquiry.refresh')}
        </button>
      </header>

      <div className="inquiry-dashboard__stats">
        <span>
          {t('inquiry.stats.total')}: {stats.total ?? 0}
        </span>
        <span>
          {t('inquiry.stats.completed')}: {stats.completed ?? 0}
        </span>
        <span>
          {t('inquiry.stats.awaitingGodet')}: {stats.awaiting_godet ?? 0}
        </span>
        <span>
          {t('inquiry.stats.scheduler')}: {stats.scheduled_active ?? 0}
        </span>
        <span className={dueItems.length ? 'inquiry-dashboard__alert' : ''}>
          {t('inquiry.stats.due')}: {stats.scheduled_due ?? 0}
        </span>
      </div>

      {dueItems.length > 0 && (
        <div className="inquiry-dashboard__banner">
          {dueItems.length} {t('inquiry.banner.due')}
        </div>
      )}

      <div className="inquiry-dashboard__filters">
        <label>
          {t('inquiry.filter.status')}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">{t('inquiry.filter.all')}</option>
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
          {t('inquiry.filter.scheduledOnly')}
        </label>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={selected.size === 0 || rerunning}
          onClick={() => void handleBatchRerun(Array.from(selected))}
          data-testid="inquiry-dashboard-rerun"
        >
          {rerunning ? t('inquiry.rerunning') : `${t('inquiry.rerunBatch')} (${selected.size})`}
        </button>
        {dueItems.length > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={rerunning}
            onClick={() => void handleBatchRerun(dueItems.map((i) => i.id))}
          >
            {t('inquiry.rerunDue')} ({dueItems.length})
          </button>
        )}
        <button
          type="button"
          className="btn btn-primary"
          disabled={selected.size === 0 || exporting}
          onClick={() => void handleBatchExport()}
          data-testid="inquiry-dashboard-export"
        >
          {exporting ? t('inquiry.exporting') : `${t('inquiry.exportZip')} (${selected.size})`}
        </button>
      </div>

      {isLoading ? (
        <p>…</p>
      ) : items.length === 0 ? (
        <p className="inquiry-dashboard__empty">{t('inquiry.empty')}</p>
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
                      {t('inquiry.wizard')}
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
