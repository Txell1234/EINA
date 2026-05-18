interface WorkflowProgressProps {
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
    { id: 'micmac', label: 'MIC-MAC', done: hasMicmac },
    { id: 'mactor', label: 'MACTOR', done: hasMactor },
    { id: 'scenarios', label: 'Escenaris', done: hasScenarios },
    { id: 'report', label: 'Informe', done: false },
  ]

  return (
    <div className="workflow-progress">
      {steps.map((step, i) => (
        <div key={step.id} className={`workflow-step ${step.done ? 'done' : ''}`}>
          <span className="workflow-step-label">
            {step.done ? '✓ ' : ''}
            {step.label}
            {step.count !== undefined && (
              <span className="workflow-step-count">{step.count}</span>
            )}
          </span>
          {i < steps.length - 1 && <span className="workflow-step-sep">›</span>}
        </div>
      ))}
    </div>
  )
}
