import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../../contexts/I18nContext'
import { useCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { toActiveCase } from '../../utils/caseUtils'
import { prospectiveInquiryService } from '../../services/api'
import ProspectiveInquiryPanel from './ProspectiveInquiryPanel'
import GodetLaunchPanel from './GodetLaunchPanel'
import ReportTemplateGallery from './ReportTemplateGallery'
import InquiryDashboard from './InquiryDashboard'
import './Q2fsWorkspace.css'
import './q2fs-tokens.css'

type TabId = 'activate' | 'library' | 'all'

type ReportTemplate = { id: string; label: string; label_ca: string; description: string }

type LibraryItem = {
  id: number
  case_id: number
  case_name: string
  question: string
  status: string
  probability_pct?: number | null
  possibility?: string | null
  report_meta: {
    is_saved: boolean
    keep_forever: boolean
    archived: boolean
    report_title: string
    export_template: string
    saved_at?: string | null
    notes?: string
  }
}

export default function Q2fsWorkspace() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const { activeCase, setActiveCase } = useCase()
  const [tab, setTab] = useState<TabId>('activate')
  const [caseId, setCaseId] = useState<number | null>(activeCase?.id ?? null)
  const [bulkQuestions, setBulkQuestions] = useState('')
  const [bulkMode, setBulkMode] = useState<'full' | 'lite'>('full')
  const [activeInquiryId, setActiveInquiryId] = useState<number | null>(null)
  const [bulkRunning, setBulkRunning] = useState(false)
  const [bulkStatus, setBulkStatus] = useState<string | null>(null)
  const [defaultTemplate, setDefaultTemplate] = useState('eina')

  const { data: cases } = useCasesList()

  useEffect(() => {
    if (activeCase?.id) setCaseId((prev) => prev ?? activeCase.id)
  }, [activeCase?.id])

  useEffect(() => {
    const caseParam = searchParams.get('case')
    const inquiryParam = searchParams.get('inquiry')
    const tabParam = searchParams.get('tab')
    if (caseParam) {
      const id = Number(caseParam)
      if (!Number.isNaN(id)) setCaseId(id)
    }
    if (inquiryParam) {
      const iid = Number(inquiryParam)
      if (!Number.isNaN(iid)) setActiveInquiryId(iid)
    }
    if (tabParam === 'activate' || tabParam === 'library' || tabParam === 'all') {
      setTab(tabParam)
    }
  }, [searchParams])

  useEffect(() => {
    if (!caseId || !cases?.length) return
    const c = cases.find((x) => x.id === caseId)
    if (c) setActiveCase(toActiveCase(c))
  }, [caseId, cases, setActiveCase])

  const { data: templatesData } = useQuery({
    queryKey: ['export-templates'],
    queryFn: () => prospectiveInquiryService.listExportTemplates(),
  })
  const templates = (templatesData?.templates as ReportTemplate[]) ?? []

  const { data: libraryData, refetch: refetchLibrary } = useQuery({
    queryKey: ['inquiry-report-library', caseId],
    queryFn: () =>
      prospectiveInquiryService.reportLibrary({
        caseId: caseId ?? undefined,
        savedOnly: false,
        includeArchived: false,
      }),
    enabled: tab === 'library',
  })

  const libraryItems = (libraryData?.items as LibraryItem[]) ?? []
  const savedCount = useMemo(
    () => libraryItems.filter((i) => i.report_meta?.is_saved).length,
    [libraryItems],
  )

  const handleCaseChange = (id: number | null) => {
    setCaseId(id)
    if (!id) return
    const c = cases?.find((x) => x.id === id)
    if (c) setActiveCase(toActiveCase(c))
  }

  const runBulkActivate = async (autoRun: boolean) => {
    if (!caseId) return
    const lines = bulkQuestions
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length >= 15)
    if (lines.length === 0) {
      setBulkStatus(t('q2fs.bulk.errorMinChars'))
      return
    }
    setBulkRunning(true)
    setBulkStatus(t('q2fs.bulk.creating', { count: lines.length }))
    try {
      const created = await prospectiveInquiryService.createBatch({
        case_id: caseId,
        questions: lines.slice(0, 10),
        mode: bulkMode,
      })
      const ids = (created.created as Array<{ inquiry_id: number }>).map((c) => c.inquiry_id)
      if (!autoRun || ids.length === 0) {
        setBulkStatus(t('q2fs.bulk.createdNoRun', { count: ids.length }))
        void queryClient.invalidateQueries({ queryKey: ['inquiry-dashboard'] })
        return
      }
      setBulkStatus(t('q2fs.bulk.running', { count: ids.length }))
      for (let i = 0; i < ids.length; i++) {
        setBulkStatus(
          t('q2fs.bulk.pipeline', { current: i + 1, total: ids.length, id: ids[i] }),
        )
        await prospectiveInquiryService.runStream(ids[i], () => {}, { forceRefresh: true })
      }
      setBulkStatus(t('q2fs.bulk.done', { count: ids.length }))
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
      void queryClient.invalidateQueries({ queryKey: ['inquiry-dashboard'] })
    } catch (err: unknown) {
      setBulkStatus(err instanceof Error ? err.message : t('q2fs.bulk.error'))
    } finally {
      setBulkRunning(false)
    }
  }

  const toggleSave = async (item: LibraryItem, saved: boolean) => {
    await prospectiveInquiryService.updateReportMeta(item.id, { is_saved: saved })
    await refetchLibrary()
    void queryClient.invalidateQueries({ queryKey: ['inquiry-dashboard'] })
  }

  return (
    <div className="q2fs-workspace" data-testid="q2fs-workspace">
      <header className="q2fs-workspace__hero card">
        <div>
          <h1>{t('q2fs.hero.title')}</h1>
          <p>{t('q2fs.hero.subtitle')}</p>
        </div>
        <div className="q2fs-workspace__case">
          <label>
            {t('q2fs.case.label')}
            <select
              value={caseId ?? ''}
              onChange={(e) => handleCaseChange(e.target.value ? Number(e.target.value) : null)}
              data-testid="q2fs-case-select"
            >
              <option value="">{t('q2fs.case.select')}</option>
              {(cases ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} (#{c.id})
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('q2fs.template.label')}
            <select
              value={defaultTemplate}
              onChange={(e) => setDefaultTemplate(e.target.value)}
              data-testid="q2fs-default-template"
            >
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label_ca || t.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <nav className="q2fs-workspace__tabs" aria-label="Seccions Q2FS">
        <button
          type="button"
          className={tab === 'activate' ? 'active' : ''}
          onClick={() => setTab('activate')}
          data-testid="q2fs-tab-activate"
        >
          {t('q2fs.tab.activate')}
        </button>
        <button
          type="button"
          className={tab === 'library' ? 'active' : ''}
          onClick={() => setTab('library')}
          data-testid="q2fs-tab-library"
        >
          {t('q2fs.tab.library', { count: savedCount })}
        </button>
        <button
          type="button"
          className={tab === 'all' ? 'active' : ''}
          onClick={() => setTab('all')}
          data-testid="q2fs-tab-all"
        >
          {t('q2fs.tab.all')}
        </button>
      </nav>

      {tab === 'activate' && (
        <div className="q2fs-workspace__activate">
          {!caseId ? (
            <div className="card q2fs-workspace__empty">
              <p>{t('q2fs.empty.selectCase')}</p>
              <Link to="/osint-collection" className="btn btn-primary">
                {t('q2fs.empty.osintLink')}
              </Link>
            </div>
          ) : (
            <>
              <GodetLaunchPanel
                caseId={caseId}
                onInquiryStarted={(id) => setActiveInquiryId(id)}
              />

              <ReportTemplateGallery
                templates={templates}
                selected={defaultTemplate}
                onSelect={setDefaultTemplate}
                onPreview={(tpl) => {
                  if (activeInquiryId) {
                    window.open(
                      prospectiveInquiryService.exportHtmlUrl(activeInquiryId, tpl),
                      '_blank',
                    )
                  }
                }}
              />

              <section className="card q2fs-workspace__bulk" data-testid="q2fs-bulk-panel">
                <h2>{t('q2fs.bulk.title')}</h2>
                <p className="q2fs-workspace__hint">{t('q2fs.bulk.hint')}</p>
                <textarea
                  rows={5}
                  value={bulkQuestions}
                  onChange={(e) => setBulkQuestions(e.target.value)}
                  placeholder={t('q2fs.bulk.placeholder')}
                  data-testid="q2fs-bulk-questions"
                />
                <div className="q2fs-workspace__bulk-actions">
                  <label>
                    {t('q2fs.bulk.mode')}
                    <select value={bulkMode} onChange={(e) => setBulkMode(e.target.value as 'full' | 'lite')}>
                      <option value="full">{t('q2fs.bulk.modeFull')}</option>
                      <option value="lite">{t('q2fs.bulk.modeLite')}</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={bulkRunning}
                    onClick={() => void runBulkActivate(false)}
                  >
                    {t('q2fs.bulk.create')}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={bulkRunning}
                    onClick={() => void runBulkActivate(true)}
                    data-testid="q2fs-activate-all"
                  >
                    {bulkRunning ? t('q2fs.bulk.activating') : t('q2fs.bulk.activateAll')}
                  </button>
                </div>
                {bulkStatus ? <p className="q2fs-workspace__status">{bulkStatus}</p> : null}
              </section>

              <ProspectiveInquiryPanel
                caseId={caseId}
                defaultExportTemplate={defaultTemplate}
                showSaveControls
                compact
                activeInquiryId={activeInquiryId}
              />
            </>
          )}
        </div>
      )}

      {tab === 'library' && (
        <section className="card q2fs-workspace__library" data-testid="q2fs-report-library">
          <header>
            <h2>{t('q2fs.library.title')}</h2>
            <p>{t('q2fs.library.subtitle')}</p>
          </header>
          {libraryItems.length === 0 ? (
            <p className="q2fs-workspace__empty-msg">{t('q2fs.library.empty')}</p>
          ) : (
            <table className="q2fs-workspace__library-table">
              <thead>
                <tr>
                  <th>{t('q2fs.library.col.keep')}</th>
                  <th>{t('q2fs.library.col.id')}</th>
                  <th>{t('q2fs.library.col.title')}</th>
                  <th>{t('q2fs.library.col.status')}</th>
                  <th>{t('q2fs.library.col.template')}</th>
                  <th>{t('q2fs.library.col.export')}</th>
                </tr>
              </thead>
              <tbody>
                {libraryItems.map((item) => (
                  <tr key={item.id} className={item.report_meta?.is_saved ? 'saved' : ''}>
                    <td>
                      <input
                        type="checkbox"
                        checked={item.report_meta?.is_saved}
                        onChange={(e) => void toggleSave(item, e.target.checked)}
                        aria-label={`Conservar informe ${item.id}`}
                      />
                      {item.report_meta?.keep_forever ? ' ★' : ''}
                    </td>
                    <td>#{item.id}</td>
                    <td>
                      <strong>{item.report_meta?.report_title || `Inquiry #${item.id}`}</strong>
                      <br />
                      <span className="muted">{item.question.slice(0, 100)}…</span>
                    </td>
                    <td>
                      {item.status}
                      {item.probability_pct != null ? ` · ${item.probability_pct}%` : ''}
                    </td>
                    <td>
                      <select
                        value={item.report_meta?.export_template || 'eina'}
                        onChange={(e) =>
                          void prospectiveInquiryService
                            .updateReportMeta(item.id, { export_template: e.target.value })
                            .then(() => refetchLibrary())
                        }
                      >
                        {templates.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.label_ca || t.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <a
                        href={prospectiveInquiryService.exportHtmlUrl(
                          item.id,
                          item.report_meta?.export_template || defaultTemplate,
                        )}
                        target="_blank"
                        rel="noreferrer"
                      >
                        HTML
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {tab === 'all' && <InquiryDashboard />}
    </div>
  )
}
