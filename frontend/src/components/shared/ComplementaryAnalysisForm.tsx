/**
 * Formulari obligatori per eines complementàries:
 * cas actiu + direcció analítica de l'usuari (mai anàlisi a l'atzar).
 */
import { useEffect, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { casesService } from '../../services/api'

export type ComplementaryAnalysisFormProps = {
  children?: ReactNode
  extraFields?: ReactNode
  submitLabel: string
  isPending?: boolean
  disabled?: boolean
  onSubmit: (payload: {
    caseId: number
    userDirection: string
    focusEntity?: string
    focusTopic?: string
  }) => void
  showFocusFields?: boolean
}

const MIN_DIRECTION_LEN = 30

export default function ComplementaryAnalysisForm({
  children,
  extraFields,
  submitLabel,
  isPending = false,
  disabled = false,
  onSubmit,
  showFocusFields = false,
}: ComplementaryAnalysisFormProps) {
  const { activeCase, setActiveCase } = useCase()
  const { data: cases } = useCasesList()
  const [userDirection, setUserDirection] = useState('')
  const [focusEntity, setFocusEntity] = useState('')
  const [focusTopic, setFocusTopic] = useState('')
  const [seededCaseId, setSeededCaseId] = useState<number | null>(null)

  const { data: caseContext } = useQuery({
    queryKey: ['case-context', activeCase?.id],
    queryFn: () => casesService.getContext(activeCase!.id),
    enabled: Boolean(activeCase?.id),
  })

  useEffect(() => {
    if (!activeCase?.id || !caseContext) return
    if (seededCaseId === activeCase.id) return
    const brief = caseContext as { latest_prompt?: string; description?: string }
    const seed = brief.latest_prompt || brief.description || ''
    if (seed) {
      setUserDirection(seed.slice(0, 2000))
      setSeededCaseId(activeCase.id)
    }
  }, [activeCase?.id, caseContext, seededCaseId])

  const directionOk = userDirection.trim().length >= MIN_DIRECTION_LEN
  const canSubmit = Boolean(activeCase) && directionOk && !isPending && !disabled

  return (
    <div className="complementary-form">
      <div className="prospective-field" style={{ maxWidth: 480 }}>
        <label>Cas actiu *</label>
        <select
          className="prospective-select"
          value={activeCase?.id ?? ''}
          onChange={(e) => {
            const id = Number(e.target.value)
            const c = (cases as { id: number; name: string }[])?.find((x) => x.id === id)
            if (c) {
              setActiveCase({ id: c.id, name: c.name, case_type: '', status: 'actiu' })
              setUserDirection('')
              setSeededCaseId(null)
            }
          }}
        >
          <option value="">— Selecciona un cas —</option>
          {((cases as { id: number; name: string }[]) ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              #{c.id} — {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="prospective-field">
        <label>
          Direcció analítica i pensament estratègic *
          <span style={{ fontWeight: 400, color: 'var(--color-gray-500)', marginLeft: 8 }}>
            (mín. {MIN_DIRECTION_LEN} caràcters)
          </span>
        </label>
        <textarea
          className="prospective-textarea"
          rows={6}
          placeholder="Ex: Vull entendre com el rearmament japonès afecta la percepció de la Xina i els aliats regionals..."
          value={userDirection}
          onChange={(e) => setUserDirection(e.target.value)}
        />
        <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)', margin: '6px 0 0' }}>
          {userDirection.trim().length}/{MIN_DIRECTION_LEN} — L&apos;anàlisi seguirà aquesta direcció.
        </p>
      </div>

      {showFocusFields && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', maxWidth: 640 }}>
          <div className="prospective-field">
            <label>Entitat focus (opcional)</label>
            <input
              className="prospective-input"
              value={focusEntity}
              onChange={(e) => setFocusEntity(e.target.value)}
              placeholder="Ex: Govern del Japó"
            />
          </div>
          <div className="prospective-field">
            <label>Tema focus (opcional)</label>
            <input
              className="prospective-input"
              value={focusTopic}
              onChange={(e) => setFocusTopic(e.target.value)}
              placeholder="Ex: Indo-Pacífic"
            />
          </div>
        </div>
      )}

      {extraFields}

      <div className="prospective-actions">
        <button
          type="button"
          className="btn btn-accent"
          disabled={!canSubmit}
          onClick={() => {
            if (!activeCase || !directionOk) return
            onSubmit({
              caseId: activeCase.id,
              userDirection: userDirection.trim(),
              focusEntity: focusEntity.trim() || undefined,
              focusTopic: focusTopic.trim() || undefined,
            })
          }}
        >
          {isPending ? 'Analitzant...' : submitLabel}
        </button>
      </div>

      {children}
    </div>
  )
}
