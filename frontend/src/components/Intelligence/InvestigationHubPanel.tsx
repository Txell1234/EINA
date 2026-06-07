import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  ClipboardPaste,
  ExternalLink,
  FolderOpen,
  GitCompare,
  Play,
  TrendingUp,
} from 'lucide-react'
import { casesService } from '../../services/api'
import {
  GODET_STEP_ORDER,
  resumeGodetPath,
  useProject,
  withActiveProject,
  type ActiveProject,
} from '../../contexts/ProjectContext'
import CaseCompaniesPanel from './CaseCompaniesPanel'
import './InvestigationHubPanel.css'

const STEP_LABELS: Record<string, string> = {
  project: 'Projecte',
  variables: 'Variables',
  micmac: 'MIC-MAC',
  actors: 'Actors',
  mactor: 'MACTOR',
  morph: 'Morph',
  smic: 'SMIC',
  scenarios: 'Escenaris',
}

type WorkspaceProject = {
  id: number
  title: string
  case_id: number
  created_at?: string | null
  godet_checklist: Record<string, boolean>
  missing_steps: string[]
  suggested_next_step?: string
  scenario_count?: number
}

type WorkspaceInquiry = {
  id: number
  question: string
  mode: string
  status: string
  wizard_project_id?: number | null
  probability_pct?: number | null
}

type FinancialReport = {
  id: number
  source: string
  title: string
  parse_status: string
  created_at?: string | null
}

type InvestigationHubPanelProps = {
  caseId: number
  onScrollToFinancial?: () => void
  selectedCompany?: string | null
  onSelectCompany?: (name: string | null) => void
}

export default function InvestigationHubPanel({
  caseId,
  onScrollToFinancial,
  selectedCompany = null,
  onSelectCompany,
}: InvestigationHubPanelProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { activeProject, setActiveProject } = useProject()
  const [selectedProjectId, setSelectedProjectId] = useState<number | ''>(
    activeProject?.case_id === caseId ? activeProject.id : '',
  )
  const [praamsText, setPraamsText] = useState('')
  const [praamsTitle, setPraamsTitle] = useState('')
  const [crossoverSummary, setCrossoverSummary] = useState<Record<string, unknown> | null>(null)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [crossoverErr, setCrossoverErr] = useState<string | null>(null)

  const { data: workspace, isLoading } = useQuery({
    queryKey: ['case-workspace', caseId, selectedProjectId || null],
    queryFn: () =>
      casesService.getCaseWorkspace(
        caseId,
        typeof selectedProjectId === 'number' ? selectedProjectId : undefined,
      ),
    enabled: caseId > 0,
  })

  const projects = (workspace?.projects as WorkspaceProject[]) ?? []
  const inquiries = (workspace?.inquiries as WorkspaceInquiry[]) ?? []
  const reports = (workspace?.financial_reports as FinancialReport[]) ?? []

  useEffect(() => {
    if (activeProject?.case_id === caseId) {
      setSelectedProjectId(activeProject.id)
      return
    }
    const suggested = workspace?.suggested_project_id as number | undefined
    if (suggested && !selectedProjectId) {
      setSelectedProjectId(suggested)
    }
  }, [activeProject, caseId, workspace?.suggested_project_id, selectedProjectId])

  const selectedProject = useMemo(
    () => projects.find((p) => p.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  )

  const handleSetActiveProject = () => {
    if (!selectedProject) return
    const next: ActiveProject = {
      id: selectedProject.id,
      title: selectedProject.title,
      case_id: selectedProject.case_id,
    }
    setActiveProject(next)
  }

  const uploadMutation = useMutation({
    mutationFn: () =>
      casesService.uploadFinancialReport(caseId, {
        text: praamsText,
        source: 'praams',
        title: praamsTitle || 'PRAAMS InvestWatch',
      }),
    onSuccess: (data) => {
      setPraamsText('')
      setUploadMsg(`Informe desat (#${(data as { report_id?: number }).report_id ?? '?'})`)
      setCrossoverErr(null)
      void queryClient.invalidateQueries({ queryKey: ['case-workspace', caseId] })
      void queryClient.invalidateQueries({ queryKey: ['financial-reports', caseId] })
    },
    onError: (err: Error) => {
      setUploadMsg(null)
      setCrossoverErr(err.message || 'Error desant informe PRAAMS')
    },
  })

  const crossoverMutation = useMutation({
    mutationFn: (reportId: number) =>
      casesService.runFinancialCrossover(caseId, {
        report_id: reportId,
        external_weight: 0.35,
        focus_company: selectedCompany ?? undefined,
        project_id: typeof selectedProjectId === 'number' ? selectedProjectId : undefined,
      }),
    onSuccess: (data) => {
      setCrossoverSummary(data as Record<string, unknown>)
      setCrossoverErr(null)
      onScrollToFinancial?.()
    },
    onError: (err: Error) => {
      setCrossoverErr(err.message || 'Error en el creuament financer')
    },
  })

  const handlePasteClipboard = async () => {
    try {
      const clip = await navigator.clipboard.readText()
      if (clip.trim()) setPraamsText(clip)
    } catch {
      /* clipboard denied */
    }
  }

  const handleResume = () => {
    if (!selectedProject) return
    handleSetActiveProject()
    navigate(resumeGodetPath(selectedProject.godet_checklist, selectedProject.id))
  }

  if (isLoading && !workspace) {
    return (
      <section className="card investigation-hub" data-testid="investigation-hub">
        <p className="investigation-hub__muted">Carregant hub del cas…</p>
      </section>
    )
  }

  return (
    <section className="card investigation-hub" data-testid="investigation-hub">
      <header className="investigation-hub__header">
        <div>
          <p className="investigation-hub__kicker">Hub d&apos;investigació</p>
          <h2 className="investigation-hub__title">
            {workspace?.case?.name ?? `Cas #${caseId}`}
          </h2>
          {workspace?.case?.briefing_excerpt ? (
            <p className="investigation-hub__brief">{workspace.case.briefing_excerpt}</p>
          ) : null}
        </div>
        <div className="investigation-hub__pipeline">
          Pipeline OSINT: {workspace?.pipeline?.ready_steps ?? 0}/
          {workspace?.pipeline?.total_steps ?? 6} passos
        </div>
      </header>

      <div className="investigation-hub__grid">
        <div className="investigation-hub__block">
          <h3>
            <FolderOpen size={16} /> Projecte Godet actiu
          </h3>
          {projects.length === 0 ? (
            <p className="investigation-hub__muted">
              Cap projecte encara.{' '}
              <Link to={withActiveProject('/prospective/project', null)}>Crear projecte</Link>
            </p>
          ) : (
            <>
              <div className="investigation-hub__row">
                <select
                  value={selectedProjectId}
                  onChange={(e) =>
                    setSelectedProjectId(e.target.value ? Number(e.target.value) : '')
                  }
                >
                  <option value="">Selecciona projecte…</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      #{p.id} — {p.title}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={!selectedProject}
                  onClick={handleSetActiveProject}
                >
                  Marcar actiu
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!selectedProject}
                  onClick={handleResume}
                >
                  <Play size={14} /> Reprendre
                </button>
              </div>
              {selectedProject ? (
                <div className="investigation-hub__godet-steps">
                  {GODET_STEP_ORDER.map((step) => (
                    <span
                      key={step}
                      className={`investigation-hub__step ${
                        selectedProject.godet_checklist[step] ? 'done' : 'pending'
                      }`}
                      title={STEP_LABELS[step]}
                    >
                      {STEP_LABELS[step]}
                    </span>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </div>

        <div className="investigation-hub__block">
          <h3>
            <GitCompare size={16} /> Línies Q2FS
          </h3>
          {inquiries.length === 0 ? (
            <p className="investigation-hub__muted">Sense inquiries. Obre Q2FS per fer una pregunta.</p>
          ) : (
            <ul className="investigation-hub__list">
              {inquiries.slice(0, 5).map((inq) => (
                <li key={inq.id}>
                  <span className="investigation-hub__inq-id">#{inq.id}</span>
                  {inq.question.slice(0, 72)}
                  {inq.question.length > 72 ? '…' : ''}
                  {inq.probability_pct != null ? (
                    <span className="investigation-hub__badge">{inq.probability_pct}%</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          <div className="investigation-hub__links">
            <Link to="/prospective/inquiries">Q2FS workspace</Link>
            {inquiries.length >= 2 ? (
              <a href="#inquiry-compare">Comparar inquiries</a>
            ) : null}
          </div>
        </div>

        <div className="investigation-hub__block investigation-hub__praams">
          <h3>
            PRAAMS / InvestWatch
            <a
              href="https://praa.ms/en"
              target="_blank"
              rel="noreferrer"
              className="investigation-hub__external"
            >
              <ExternalLink size={14} /> Obrir PRAAMS
            </a>
          </h3>
          <p className="investigation-hub__hint">
            1. Cerca ticker a praa.ms · 2. Copia el bloc InvestWatch (puntuacions X/7 + Recommendation) · 3.
            Enganxa aquí · 4. Creuar. Notícies genèriques: enganxa només el resum PRAAMS, no l&apos;article sencer.
          </p>
          <input
            type="text"
            placeholder="Títol informe (opcional)"
            value={praamsTitle}
            onChange={(e) => setPraamsTitle(e.target.value)}
            className="investigation-hub__input"
          />
          <textarea
            rows={3}
            placeholder="Enganxa text InvestWatch / PRAAMS…"
            value={praamsText}
            onChange={(e) => setPraamsText(e.target.value)}
            className="investigation-hub__textarea"
          />
          <div className="investigation-hub__row">
            <button type="button" className="btn btn-secondary" onClick={() => void handlePasteClipboard()}>
              <ClipboardPaste size={14} /> Enganxar
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={praamsText.trim().length < 50 || uploadMutation.isPending}
              onClick={() => uploadMutation.mutate()}
            >
              Desar informe
            </button>
          </div>
          {uploadMsg ? (
            <p className="investigation-hub__hint investigation-hub__success">{uploadMsg}</p>
          ) : null}
          {uploadMutation.isError || crossoverErr ? (
            <p className="investigation-hub__hint investigation-hub__error">{crossoverErr}</p>
          ) : null}
          {praamsText.trim().length > 0 && praamsText.trim().length < 50 ? (
            <p className="investigation-hub__hint">Cal enganxar almenys 50 caràcters del informe PRAAMS.</p>
          ) : null}
          {reports.length > 0 ? (
            <ul className="investigation-hub__reports">
              {reports.slice(0, 6).map((r) => (
                <li key={r.id}>
                  <span>
                    [{r.source}] {r.title || `#${r.id}`}
                  </span>
                  <button
                    type="button"
                    className="btn btn-accent investigation-hub__cross-btn"
                    disabled={crossoverMutation.isPending}
                    onClick={() => crossoverMutation.mutate(r.id)}
                  >
                    Creuar
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="investigation-hub__muted">Cap informe financer guardat encara.</p>
          )}
          {crossoverSummary?.crossover ? (
            <div className="investigation-hub__crossover-preview">
              <strong>Últim creuament</strong>
              <pre>{JSON.stringify(
                (crossoverSummary.crossover as Record<string, unknown>).final_numbers ?? {},
                null,
                2,
              )}</pre>
              <button type="button" className="btn btn-secondary" onClick={onScrollToFinancial}>
                Veure detall <ArrowRight size={14} />
              </button>
            </div>
          ) : null}
        </div>

        <div className="investigation-hub__block">
          <h3>
            <TrendingUp size={16} /> Creuaments ràpids
          </h3>
          <div className="investigation-hub__quick-links">
            <Link to="/investment-recommendations">Recomanacions inversió</Link>
            <Link to="/qualitative-analysis">Anàlisi qualitativa</Link>
            <Link to="/reasoning-frameworks">Marcs de raonament</Link>
            <button type="button" className="investigation-hub__link-btn" onClick={onScrollToFinancial}>
              Crossover financer (detall)
            </button>
          </div>
        </div>
      </div>

      <CaseCompaniesPanel
        registry={workspace?.company_registry}
        isLoading={isLoading}
        selectedCompany={selectedCompany}
        onSelectCompany={onSelectCompany ?? (() => {})}
        onScrollToFinancial={onScrollToFinancial}
        embedded
      />
    </section>
  )
}
