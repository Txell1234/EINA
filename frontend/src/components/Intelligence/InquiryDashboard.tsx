import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Line, LineChart, ResponsiveContainer } from 'recharts'
import { useI18n } from '../../contexts/I18nContext'
import { prospectiveInquiryService } from '../../services/api'
import './InquiryDashboard.css'
import './q2fs-tokens.css'

type ProbPoint = { probability_pct: number; at?: string | null; run_number?: number | null }

type DashboardItem = {
  id: number
  case_id: number
  case_name: string
  question: string
  mode: string
  status: string
  run_count: number
  probability_pct?: number | null
  probability_delta?: number | null
  probability_history?: ProbPoint[]
  possibility?: string | null
  parse_confidence?: number | null
  llm_used?: boolean | null
  auto_rerun_enabled?: boolean
  rerun_interval_hours?: number
  next_rerun_at?: string | null
  scheduled_due?: boolean
  wizard_project_id?: number | null
  created_at?: string | null
}

type BatchResult = {
  processed: number
  ok_count: number
  failed_count: number
}

function ProbabilitySparkline({ history }: { history: ProbPoint[] }) {
  if (!history || history.length < 2) {
    return <span className="inquiry-dashboard__muted">—</span>
  }
  const data = history.map((p, i) => ({ i, v: p.probability_pct }))
  return (
    <div className="inquiry-dashboard__sparkline" title={history.map((p) => `${p.probability_pct}%`).join(' → ')}>
      <ResponsiveContainer width={72} height={28}>
        <LineChart data={data}>
          <Line type="monotone" dataKey="v" stroke="var(--color-primary, #1565c0)" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function InquiryDashboard() {
  const { t } = useI18n()
  const [statusFilter, setStatusFilter] = useState('')
  const [modeFilter, setModeFilter] = useState('')
  const [caseIdFilter, setCaseIdFilter] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [minConfidence, setMinConfidence] = useState('')
  const [llmOnly, setLlmOnly] = useState(false)
  const [scheduledOnly, setScheduledOnly] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [exporting, setExporting] = useState(false)
  const [exportingExecutive, setExportingExecutive] = useState(false)
  const [reportLang, setReportLang] = useState<'ca' | 'es' | 'en'>('ca')
  const [rerunning, setRerunning] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [scheduleIntervalHours, setScheduleIntervalHours] = useState(24)
  const [batchResult, setBatchResult] = useState<{ type: 'rerun' | 'schedule'; result: BatchResult } | null>(null)
  const [rerunProgress, setRerunProgress] = useState(0)

  useEffect(() => {
    const timer = window.setTimeout(() => setSearchQuery(searchInput.trim()), 350)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const parsedCaseId = caseIdFilter ? Number(caseIdFilter) : undefined
  const parsedMinConf = minConfidence ? Number(minConfidence) : undefined

  const { data, isLoading, refetch } = useQuery({
    queryKey: [
      'inquiry-dashboard',
      statusFilter,
      modeFilter,
      parsedCaseId,
      searchQuery,
      parsedMinConf,
      llmOnly,
      scheduledOnly,
    ],
    queryFn: () =>
      prospectiveInquiryService.dashboard({
        status: statusFilter || undefined,
        mode: (modeFilter as 'full' | 'lite') || undefined,
        caseId: parsedCaseId && !Number.isNaN(parsedCaseId) ? parsedCaseId : undefined,
        q: searchQuery || undefined,
        minConfidence: parsedMinConf && !Number.isNaN(parsedMinConf) ? parsedMinConf : undefined,
        llmOnly,
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

  const handleExecutiveExport = async (output: 'html' | 'pdf') => {
    if (selected.size === 0) return
    setExportingExecutive(true)
    try {
      await prospectiveInquiryService.exportExecutive({
        ids: Array.from(selected),
        lang: reportLang,
        output,
      })
    } finally {
      setExportingExecutive(false)
    }
  }

  const handleBatchRerun = async (ids: number[]) => {
    if (ids.length === 0) return
    const ok = window.confirm(t('inquiry.confirmRerun', { count: ids.length }))
    if (!ok) return
    setBatchResult(null)
    setRerunning(true)
    setRerunProgress(5)
    const tick = window.setInterval(() => {
      setRerunProgress((p) => Math.min(p + 8, 92))
    }, 800)
    try {
      const result = await prospectiveInquiryService.rerunBatch(ids)
      setRerunProgress(100)
      setBatchResult({ type: 'rerun', result })
      setSelected(new Set())
      await refetch()
    } finally {
      window.clearInterval(tick)
      setRerunning(false)
      window.setTimeout(() => setRerunProgress(0), 600)
    }
  }

  const handleSingleRerun = async (id: number) => {
    const ok = window.confirm(t('inquiry.confirmRerunOne', { id }))
    if (!ok) return
    await handleBatchRerun([id])
  }

  const handleBatchSchedule = async (enabled: boolean) => {
    if (selected.size === 0) return
    setScheduling(true)
    setBatchResult(null)
    try {
      const result = await prospectiveInquiryService.batchSchedule(
        Array.from(selected),
        enabled,
        scheduleIntervalHours,
      )
      setBatchResult({ type: 'schedule', result })
      setSelected(new Set())
      await refetch()
    } finally {
      setScheduling(false)
    }
  }

  const q2fsLink = (caseId: number, inquiryId?: number) => {
    const params = new URLSearchParams({ case: String(caseId), tab: 'activate' })
    if (inquiryId) params.set('inquiry', String(inquiryId))
    return `/prospective/inquiries?${params.toString()}`
  }

  return (
    <div className="card inquiry-dashboard" data-testid="inquiry-dashboard">
      <header className="inquiry-dashboard__header">
        <div>
          <h1 data-testid="inquiry-dashboard-heading">{t('inquiry.title')}</h1>
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

      {batchResult && (
        <div
          className={`inquiry-dashboard__banner inquiry-dashboard__banner--${batchResult.result.failed_count ? 'warn' : 'ok'}`}
          data-testid="inquiry-dashboard-batch-result"
        >
          {batchResult.type === 'rerun'
            ? t('inquiry.batchRerunResult', {
                ok: batchResult.result.ok_count,
                failed: batchResult.result.failed_count,
              })
            : t('inquiry.batchScheduleResult', {
                ok: batchResult.result.ok_count,
                failed: batchResult.result.failed_count,
              })}
        </div>
      )}

      {rerunning && rerunProgress > 0 && (
        <div className="inquiry-dashboard__progress" role="progressbar" aria-valuenow={rerunProgress} aria-valuemin={0} aria-valuemax={100}>
          <div className="inquiry-dashboard__progress-bar" style={{ width: `${rerunProgress}%` }} />
          <span>{t('inquiry.rerunning')}</span>
        </div>
      )}

      <div className="inquiry-dashboard__filters">
        <label>
          {t('inquiry.filter.search')}
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t('inquiry.filter.searchPlaceholder')}
            data-testid="inquiry-dashboard-search"
          />
        </label>
        <label>
          {t('inquiry.filter.caseId')}
          <input
            type="number"
            min={1}
            value={caseIdFilter}
            onChange={(e) => setCaseIdFilter(e.target.value)}
            placeholder="#"
            data-testid="inquiry-dashboard-case-filter"
          />
        </label>
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
        <label>
          {t('inquiry.filter.mode')}
          <select value={modeFilter} onChange={(e) => setModeFilter(e.target.value)}>
            <option value="">{t('inquiry.filter.all')}</option>
            <option value="full">full</option>
            <option value="lite">lite</option>
          </select>
        </label>
        <label>
          {t('inquiry.filter.minConfidence')}
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(e.target.value)}
            placeholder="0.7"
          />
        </label>
        <label className="inquiry-dashboard__check">
          <input type="checkbox" checked={llmOnly} onChange={(e) => setLlmOnly(e.target.checked)} />
          {t('inquiry.filter.llmOnly')}
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
        <label>
          {t('inquiry.filter.scheduleInterval')}
          <select
            value={scheduleIntervalHours}
            onChange={(e) => setScheduleIntervalHours(Number(e.target.value))}
            disabled={scheduling}
            data-testid="inquiry-dashboard-schedule-interval"
          >
            <option value={12}>12h</option>
            <option value={24}>24h</option>
            <option value={48}>48h</option>
            <option value={168}>168h</option>
          </select>
        </label>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={selected.size === 0 || scheduling}
          onClick={() => void handleBatchSchedule(true)}
          data-testid="inquiry-dashboard-schedule-enable"
        >
          {scheduling ? '…' : `${t('inquiry.scheduleEnable')} (${selected.size})`}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={selected.size === 0 || scheduling}
          onClick={() => void handleBatchSchedule(false)}
        >
          {t('inquiry.scheduleDisable')} ({selected.size})
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={selected.size === 0 || exporting}
          onClick={() => void handleBatchExport()}
          data-testid="inquiry-dashboard-export"
        >
          {exporting ? t('inquiry.exporting') : `${t('inquiry.exportZip')} (${selected.size})`}
        </button>
        <label>
          {t('inquiry.filter.reportLang')}
          <select
            value={reportLang}
            onChange={(e) => setReportLang(e.target.value as 'ca' | 'es' | 'en')}
            disabled={exportingExecutive}
          >
            <option value="ca">CA</option>
            <option value="es">ES</option>
            <option value="en">EN</option>
          </select>
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={selected.size === 0 || exportingExecutive}
          onClick={() => void handleExecutiveExport('html')}
          data-testid="inquiry-dashboard-executive"
        >
          {exportingExecutive ? t('inquiry.exportingExecutive') : `${t('inquiry.exportExecutive')} (${selected.size})`}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={selected.size === 0 || exportingExecutive}
          onClick={() => void handleExecutiveExport('pdf')}
          data-testid="inquiry-dashboard-executive-pdf"
        >
          {t('inquiry.exportExecutivePdf')}
        </button>
      </div>

      {isLoading ? (
        <p>…</p>
      ) : items.length === 0 ? (
        <p className="inquiry-dashboard__empty">{t('inquiry.empty')}</p>
      ) : (
        <div className="inquiry-dashboard__table-wrap">
          <table className="inquiry-dashboard__table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={selected.size === items.length && items.length > 0}
                    onChange={toggleAll}
                    aria-label={t('inquiry.selectAll')}
                  />
                </th>
                <th>ID</th>
                <th>{t('inquiry.col.case')}</th>
                <th>{t('inquiry.col.status')}</th>
                <th>{t('inquiry.col.prob')}</th>
                <th>{t('inquiry.col.trend')}</th>
                <th>{t('inquiry.col.parse')}</th>
                <th>{t('inquiry.col.runs')}</th>
                <th>{t('inquiry.col.scheduler')}</th>
                <th>{t('inquiry.col.question')}</th>
                <th>{t('inquiry.col.actions')}</th>
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
                    <Link to={`/intelligence?case=${row.case_id}`}>{row.case_name}</Link>
                    <span className="inquiry-dashboard__muted"> #{row.case_id}</span>
                    <span className="inquiry-dashboard__badge">{row.mode}</span>
                  </td>
                  <td>{row.status}</td>
                  <td>
                    {row.probability_pct != null ? `${row.probability_pct}%` : '—'}
                    {row.probability_delta != null && row.probability_delta !== 0 ? (
                      <span
                        className={
                          row.probability_delta > 0
                            ? 'inquiry-dashboard__delta inquiry-dashboard__delta--up'
                            : 'inquiry-dashboard__delta inquiry-dashboard__delta--down'
                        }
                      >
                        {row.probability_delta > 0 ? '+' : ''}
                        {row.probability_delta}
                      </span>
                    ) : null}
                  </td>
                  <td>
                    <ProbabilitySparkline history={row.probability_history ?? []} />
                  </td>
                  <td>
                    {row.parse_confidence != null ? (
                      <>
                        {(row.parse_confidence * 100).toFixed(0)}%
                        {row.llm_used != null ? (
                          <span className="inquiry-dashboard__muted">
                            {' '}
                            · {row.llm_used ? 'LLM' : 'rules'}
                          </span>
                        ) : null}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{row.run_count}</td>
                  <td>
                    {row.auto_rerun_enabled ? (
                      <>
                        {row.scheduled_due ? `⚠ ${t('inquiry.schedulerDue')}` : t('inquiry.schedulerActive')}
                        {row.next_rerun_at ? (
                          <span className="inquiry-dashboard__muted"> · {row.next_rerun_at.slice(0, 16)}</span>
                        ) : null}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="inquiry-dashboard__question">{row.question}…</td>
                  <td className="inquiry-dashboard__actions">
                    <Link to={q2fsLink(row.case_id, row.id)} title={t('inquiry.action.openInquiry')}>
                      Q2FS
                    </Link>
                    {row.wizard_project_id ? (
                      <Link
                        to={prospectiveInquiryService.buildWizardUrl(row.wizard_project_id, row.id, 'morph')}
                        title={t('inquiry.wizard')}
                      >
                        {t('inquiry.wizard')}
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      className="inquiry-dashboard__link-btn"
                      disabled={rerunning}
                      onClick={() => void handleSingleRerun(row.id)}
                      title={t('inquiry.action.rerun')}
                    >
                      ↻
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
