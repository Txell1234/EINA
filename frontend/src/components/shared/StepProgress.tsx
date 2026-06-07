import './StepProgress.css'

export type StepProgressItem = {
  id: string
  label: string
  status?: string
  cached?: boolean
  detail?: string
}

type StepProgressProps = {
  steps: StepProgressItem[]
  title?: string
  cachedLabel?: string
  testId?: string
}

function normalizeStatus(status?: string, cached?: boolean): string {
  if (cached) return 'cached'
  const s = (status || 'pending').toLowerCase()
  if (s.includes('fail') || s.includes('error')) return 'failed'
  if (s.includes('run') || s.includes('active') || s === 'parsing') return 'running'
  if (s.includes('done') || s === 'completed' || s === 'ok') return 'done'
  return s.replace(/\s+/g, '_')
}

function markFor(statusKey: string): string {
  if (statusKey === 'done') return '✓'
  if (statusKey === 'failed') return '!'
  if (statusKey === 'running') return '…'
  if (statusKey === 'cached') return '↺'
  return '○'
}

export default function StepProgress({ steps, title, cachedLabel, testId }: StepProgressProps) {
  if (steps.length === 0) return null

  return (
    <div className="step-progress" data-testid={testId}>
      {title ? <h4 className="step-progress__title">{title}</h4> : null}
      <ul className="step-progress__list">
        {steps.map((step) => {
          const statusKey = normalizeStatus(step.status, step.cached)
          return (
            <li
              key={step.id}
              className={`step-progress__item step-progress__item--${statusKey}`}
            >
              <span className="step-progress__mark" aria-hidden>
                {markFor(statusKey)}
              </span>
              <span className="step-progress__label">{step.label}</span>
              <span className="step-progress__meta">
                {step.status ? <span>{step.status}</span> : null}
                {step.cached && cachedLabel ? <span>{cachedLabel}</span> : null}
              </span>
              {step.detail ? <span className="step-progress__detail">{step.detail}</span> : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
