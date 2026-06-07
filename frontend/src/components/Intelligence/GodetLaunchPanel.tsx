import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { prospectiveInquiryService } from '../../services/api'
import './GodetLaunchPanel.css'

const PIPELINE_STEPS = [
  { key: 'parse', label: 'Parse' },
  { key: 'osint', label: 'OSINT' },
  { key: 'intelligence', label: 'Intel·ligència' },
  { key: 'policy', label: 'Policy' },
  { key: 'financial', label: 'Financer' },
  { key: 'morph_bootstrap', label: 'Morph' },
  { key: 'monitors', label: 'Monitors' },
  { key: 'synthesis', label: 'Síntesi' },
]

const GODET_WIZARD = [
  { label: 'Projecte', path: '/prospective/project' },
  { label: 'Variables', path: '/prospective/variables' },
  { label: 'MIC-MAC', path: '/prospective/micmac' },
  { label: 'Actors', path: '/prospective/actors' },
  { label: 'MACTOR', path: '/prospective/mactor' },
  { label: 'Morph', path: '/prospective/morph' },
  { label: 'SMIC', path: '/prospective-analysis' },
  { label: 'Escenaris', path: '/prospective-analysis' },
]

type GodetLaunchPanelProps = {
  caseId: number
  onInquiryStarted?: (inquiryId: number) => void
  onStepsUpdate?: (steps: Array<{ step: string; status: string }>) => void
}

export default function GodetLaunchPanel({
  caseId,
  onInquiryStarted,
  onStepsUpdate,
}: GodetLaunchPanelProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [question, setQuestion] = useState('')
  const [activeStep, setActiveStep] = useState<string | null>(null)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)
  const [lastInquiryId, setLastInquiryId] = useState<number | null>(null)
  const [awaitingGodet, setAwaitingGodet] = useState(false)
  const [wizardProjectId, setWizardProjectId] = useState<number | null>(null)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())

  const launchMutation = useMutation({
    mutationFn: async () => {
      setStatusMsg('Creant inquiry i activant pipeline Q2FS complet (mode Godet)…')
      setActiveStep('parse')
      setAwaitingGodet(false)
      setCompletedSteps(new Set())

      const created = await prospectiveInquiryService.create({
        case_id: caseId,
        question: question.trim(),
        mode: 'full',
      })
      setLastInquiryId(created.inquiry_id)
      onInquiryStarted?.(created.inquiry_id)

      const steps: Array<{ step: string; status: string }> = []
      await prospectiveInquiryService.runStream(
        created.inquiry_id,
        (event) => {
          if (event.event === 'step') {
            const stepKey = String(event.step)
            setActiveStep(stepKey)
            if (event.status === 'ok' || event.status === 'cached') {
              setCompletedSteps((prev) => new Set([...prev, stepKey]))
            }
            const row = { step: stepKey, status: String(event.status) }
            const idx = steps.findIndex((s) => s.step === row.step)
            if (idx >= 0) steps[idx] = row
            else steps.push(row)
            onStepsUpdate?.(steps)
          }
          if (event.event === 'awaiting_godet') {
            setAwaitingGodet(true)
            setStatusMsg(
              'Pipeline OSINT/intel·ligència completat. Completa el wizard Godet per la síntesi final.',
            )
          }
          if (event.event === 'done') {
            setStatusMsg('Síntesi completada. Informe disponible a la biblioteca.')
            setAwaitingGodet(false)
          }
        },
        { forceRefresh: true },
      )

      try {
        const applied = await prospectiveInquiryService.applyToWizard(created.inquiry_id)
        if (applied.project_id) {
          setWizardProjectId(applied.project_id as number)
          setStatusMsg((prev) =>
            prev
              ? `${prev} Projecte Godet #${applied.project_id} creat/actualitzat.`
              : `Projecte Godet #${applied.project_id} preparat.`,
          )
        }
      } catch {
        /* wizard seed optional */
      }

      return created.inquiry_id
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['prospective-inquiries', caseId] })
      void queryClient.invalidateQueries({ queryKey: ['inquiry-dashboard'] })
    },
    onError: (err: Error) => {
      setStatusMsg(err.message || 'Error activant Q2FS')
    },
  })

  const openWizard = () => {
    if (!wizardProjectId && !lastInquiryId) return
    if (wizardProjectId) {
      navigate(
        prospectiveInquiryService.buildWizardUrl(wizardProjectId, lastInquiryId ?? undefined, 'morph'),
      )
      return
    }
    navigate('/prospective/morph')
  }

  return (
    <section className="godet-launch card" data-testid="godet-launch-panel">
      <header className="godet-launch__header">
        <div>
          <span className="godet-launch__eyebrow">Q2FS · Prospectiva Godet</span>
          <h2>Fes una pregunta i activa tota la prospectiva</h2>
          <p>
            Escriu la teva pregunta analítica i llança el pipeline complet: OSINT, intel·ligència,
            morfologia Zwicky, monitors i wizard Godet (MIC-MAC → MACTOR → escenaris).
          </p>
        </div>
      </header>

      <textarea
        className="godet-launch__question"
        rows={4}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ex: Quina probabilitat té una escalada militar al Taiwan Strait en els propers 12 mesos, i com afectaria el rearmament japonès als actors regionals?"
        data-testid="godet-launch-question"
      />

      <div className="godet-launch__pipeline" aria-label="Pipeline Q2FS">
        {PIPELINE_STEPS.map((step, i) => {
          const done = completedSteps.has(step.key)
          const current = activeStep === step.key && launchMutation.isPending
          return (
            <div
              key={step.key}
              className={`godet-launch__step${done ? ' godet-launch__step--done' : ''}${current ? ' godet-launch__step--active' : ''}`}
            >
              <span className="godet-launch__step-num">{i + 1}</span>
              <span>{step.label}</span>
            </div>
          )
        })}
      </div>

      <div className="godet-launch__godet-row">
        <span className="godet-launch__godet-label">Wizard Godet:</span>
        {GODET_WIZARD.map((w) => (
          <span key={w.label} className="godet-launch__godet-chip">
            {w.label}
          </span>
        ))}
      </div>

      <div className="godet-launch__actions">
        <button
          type="button"
          className="btn btn-primary godet-launch__cta"
          disabled={question.trim().length < 15 || launchMutation.isPending}
          onClick={() => launchMutation.mutate()}
          data-testid="godet-launch-activate"
        >
          {launchMutation.isPending
            ? 'Activant prospectiva Godet…'
            : 'Activar prospectiva Godet completa'}
        </button>
        {awaitingGodet && (
          <button type="button" className="btn btn-accent" onClick={openWizard}>
            Continuar wizard Godet →
          </button>
        )}
        {lastInquiryId && (
          <Link
            to={`/prospective-analysis?inquiry=${lastInquiryId}${wizardProjectId ? `&project=${wizardProjectId}` : ''}`}
            className="btn btn-secondary"
          >
            Anàlisi prospectiva
          </Link>
        )}
      </div>

      {statusMsg && <p className="godet-launch__status">{statusMsg}</p>}
      {awaitingGodet && (
        <p className="godet-launch__hint">
          Mode <strong>full</strong>: completa MIC-MAC, MACTOR, Morph i escenaris al wizard, després
          prem <strong>Síntesi 1-clic</strong> al panell inferior.
        </p>
      )}
    </section>
  )
}
