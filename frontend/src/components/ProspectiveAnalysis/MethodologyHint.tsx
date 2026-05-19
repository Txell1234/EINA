import { useState, type ReactNode } from 'react'

interface MethodologyHintProps {
  title: string
  children: ReactNode
  defaultOpen?: boolean
}

export default function MethodologyHint({
  title,
  children,
  defaultOpen = true,
}: MethodologyHintProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="mhint">
      <button
        type="button"
        className="mhint-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="mhint-icon">◈</span>
        <span className="mhint-title">{title}</span>
        <span className="mhint-chevron">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="mhint-body">{children}</div>}
    </div>
  )
}
