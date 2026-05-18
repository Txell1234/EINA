import { Check, ChevronRight } from 'lucide-react'

interface WorkflowProgressProps {
  caseId?: number
  osintCount?: number
  extractionCount?: number
  hasMicmac?: boolean
  hasMactor?: boolean
  hasScenarios?: boolean
}

export default function WorkflowProgress({
  osintCount = 0,
  extractionCount = 0,
  hasMicmac = false,
  hasMactor = false,
  hasScenarios = false,
}: WorkflowProgressProps) {
  const steps = [
    {
      id: 'osint',
      label: 'OSINT',
      done: osintCount > 0,
      count: osintCount > 0 ? osintCount : undefined,
    },
    {
      id: 'extract',
      label: 'Extracció',
      done: extractionCount > 0,
      count: extractionCount > 0 ? extractionCount : undefined,
    },
    { id: 'micmac', label: 'MIC-MAC', done: hasMicmac, count: undefined as number | undefined },
    { id: 'mactor', label: 'MACTOR', done: hasMactor, count: undefined as number | undefined },
    {
      id: 'scenarios',
      label: 'Escenaris',
      done: hasScenarios,
      count: undefined as number | undefined,
    },
    { id: 'report', label: 'Informe', done: false, count: undefined as number | undefined },
  ]

  return (
    <div className="workflow-progress" role="navigation" aria-label="Flux de treball">
      {steps.map((step, i) => (
        <div key={step.id} className={`workflow-step ${step.done ? 'done' : ''}`}>
          <div className="workflow-step-label">
            {step.done ? (
              <Check className="workflow-step-check" size={14} strokeWidth={2.5} aria-hidden />
            ) : null}
            {step.label}
            {step.count !== undefined && (
              <span className="workflow-step-count">{step.count}</span>
            )}
          </div>
          {i < steps.length - 1 && (
            <ChevronRight className="workflow-step-arrow" size={16} strokeWidth={2} aria-hidden />
          )}
        </div>
      ))}
    </div>
  )
}
