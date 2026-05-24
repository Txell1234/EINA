import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { casesService, researchService } from '../../services/api'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { countPromptLines, toActiveCase } from '../../utils/caseUtils'
import ResearchPlanReview from '../Research/ResearchPlanReview'
import './CreateCaseModal.css'

type CreationMode = 'guided' | 'manual'

interface CreateCaseModalProps {
  onCaseCreated?: (caseData: ActiveCase) => void
  className?: string
}

function toActiveCaseFromResponse(data: Record<string, unknown>): ActiveCase {
  return toActiveCase(data)
}

export default function CreateCaseModal({ onCaseCreated, className }: CreateCaseModalProps) {
  const { setActiveCase } = useCase()
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<CreationMode>('guided')
  const [prompt, setPrompt] = useState('')
  const [manualName, setManualName] = useState('')
  const [manualType, setManualType] = useState('general')
  const [manualDescription, setManualDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [createdCaseId, setCreatedCaseId] = useState<number | null>(null)
  const [showResearchPlan, setShowResearchPlan] = useState(false)
  const [researchPlan, setResearchPlan] = useState<any>(null)
  const [planOsintOnly, setPlanOsintOnly] = useState(false)
  const queryClient = useQueryClient()

  const resetForm = () => {
    setPrompt('')
    setManualName('')
    setManualDescription('')
    setManualType('general')
    setError(null)
    setSuccessMsg(null)
  }

  const createMutation = useMutation({
    mutationFn: async () => {
      if (mode === 'guided') {
        return casesService.createFromPrompt({
          prompt,
          creation_mode: 'guided',
        })
      }
      return casesService.createFromPrompt({
        prompt: manualDescription.trim() || manualName.trim(),
        creation_mode: 'manual',
        name: manualName.trim(),
        case_type: manualType,
      })
    },
    onSuccess: async (data) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-cases'] })
      queryClient.invalidateQueries({ queryKey: ['cases-list'] })
      const caseId = data.id || data.case_id
      if (!caseId) {
        setIsOpen(false)
        resetForm()
        return
      }

      const active = toActiveCaseFromResponse(data)
      setActiveCase(active)
      onCaseCreated?.(active)
      setCreatedCaseId(caseId)

      const descText = active.description ?? (mode === 'guided' ? prompt : manualDescription)
      setSuccessMsg(
        `Cas creat (${mode === 'guided' ? 'briefing guiat' : 'manual'}): ${countPromptLines(descText)} línies.`,
      )

      const osintOnly = mode === 'manual'
      setPlanOsintOnly(osintOnly)

      try {
        const plan = await researchService.generatePlan(caseId, osintOnly)
        if (plan?.research_phases?.length > 0) {
          setResearchPlan(plan)
          setShowResearchPlan(true)
        } else {
          setIsOpen(false)
          resetForm()
        }
      } catch (err) {
        console.warn('Research plan generation failed:', err)
        setIsOpen(false)
        resetForm()
      }
    },
    onError: (error: any) => {
      let errorMessage = 'Error al crear el cas. Torna-ho a provar.'
      if (error?.response?.data?.detail) {
        const detail = error.response.data.detail
        errorMessage = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(', ')
          : String(detail)
      } else if (error?.message) {
        errorMessage = error.message
      }
      setError(errorMessage)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccessMsg(null)

    if (mode === 'guided') {
      if (!prompt.trim()) {
        setError('Introdueix un briefing amb context del cas.')
        return
      }
    } else if (!manualName.trim()) {
      setError('El nom del cas és obligatori en mode manual.')
      return
    }

    createMutation.mutate()
  }

  const handleClose = () => {
    setIsOpen(false)
    resetForm()
    setCreatedCaseId(null)
    setShowResearchPlan(false)
    setResearchPlan(null)
    setPlanOsintOnly(false)
    createMutation.reset()
  }

  const handleResearchPlanApprove = () => {
    handleClose()
  }

  const isSubmitDisabled =
    createMutation.isPending ||
    (mode === 'guided' ? !prompt.trim() : !manualName.trim())

  return (
    <>
      <button
        type="button"
        className={className ? `${className} btn-create-case` : 'btn-create-case'}
        onClick={() => setIsOpen(true)}
      >
        + Crear Cas
      </button>

      {isOpen &&
        !showResearchPlan &&
        createPortal(
          <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content create-case-modal" onClick={(e) => e.stopPropagation()}>
              <h2>Crear Cas</h2>

              <div className="creation-mode-tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'guided'}
                  className={`mode-tab ${mode === 'guided' ? 'active' : ''}`}
                  onClick={() => {
                    setMode('guided')
                    setError(null)
                  }}
                >
                  Briefing guiat (IA)
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'manual'}
                  className={`mode-tab ${mode === 'manual' ? 'active' : ''}`}
                  onClick={() => {
                    setMode('manual')
                    setError(null)
                  }}
                >
                  Cas manual
                </button>
              </div>

              {mode === 'guided' ? (
                <p className="mode-hint">
                  Enganxa tot el context. La IA proposarà cerques OSINT, factors i variables — cal
                  la teva aprovació abans d&apos;executar res.
                </p>
              ) : (
                <p className="mode-hint">
                  Tu defines el cas. Després aproves només la recollida OSINT (sense extracció
                  automàtica de variables).
                </p>
              )}

              <form onSubmit={handleSubmit}>
                {error && <div className="modal-error-message">{error}</div>}
                {successMsg && <div className="modal-success-message">{successMsg}</div>}

                {mode === 'guided' ? (
                  <>
                    <textarea
                      value={prompt}
                      onChange={(e) => {
                        setPrompt(e.target.value)
                        setError(null)
                        setSuccessMsg(null)
                      }}
                      placeholder={'Ex:\nRearmament Japó — anàlisi geopolítica\n\nContext: …\nObjectius: …'}
                      rows={12}
                      className="prompt-input"
                      disabled={createMutation.isPending}
                      autoFocus
                    />
                    {prompt.trim() ? (
                      <p className="prompt-stats">
                        {countPromptLines(prompt)} línies · {prompt.length.toLocaleString()} caràcters
                      </p>
                    ) : null}
                  </>
                ) : (
                  <>
                    <div className="form-group">
                      <label htmlFor="manual-name">Nom del cas</label>
                      <input
                        id="manual-name"
                        type="text"
                        value={manualName}
                        onChange={(e) => setManualName(e.target.value)}
                        placeholder="Ex: Anàlisi competència Indo-Pacífic"
                        disabled={createMutation.isPending}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="manual-type">Tipus</label>
                      <select
                        id="manual-type"
                        value={manualType}
                        onChange={(e) => setManualType(e.target.value)}
                        disabled={createMutation.isPending}
                      >
                        <option value="general">General</option>
                        <option value="geopolitical">Geopolític</option>
                        <option value="business">Business</option>
                        <option value="political">Polític</option>
                        <option value="social">Social</option>
                        <option value="investigation">Investigació</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label htmlFor="manual-desc">Descripció / notes (opcional)</label>
                      <textarea
                        id="manual-desc"
                        value={manualDescription}
                        onChange={(e) => setManualDescription(e.target.value)}
                        placeholder="Paraules clau per OSINT, context addicional…"
                        rows={8}
                        className="prompt-input"
                        disabled={createMutation.isPending}
                      />
                    </div>
                  </>
                )}

                <div className="modal-actions">
                  <button type="button" onClick={handleClose} disabled={createMutation.isPending}>
                    Cancel·lar
                  </button>
                  <button type="submit" disabled={isSubmitDisabled}>
                    {createMutation.isPending
                      ? 'Creant…'
                      : mode === 'guided'
                        ? 'Generar pla (requereix aprovació)'
                        : 'Crear cas manual'}
                  </button>
                </div>
              </form>
            </div>
          </div>,
          document.body,
        )}

      {showResearchPlan && createdCaseId && researchPlan &&
        createPortal(
          <ResearchPlanReview
            caseId={createdCaseId}
            isOpen={showResearchPlan}
            osintOnly={planOsintOnly}
            onClose={() => {
              setShowResearchPlan(false)
              handleClose()
            }}
            onApprove={handleResearchPlanApprove}
            researchPlan={researchPlan}
          />,
          document.body,
        )}
    </>
  )
}
