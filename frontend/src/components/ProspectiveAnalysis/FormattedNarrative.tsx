import { useMemo } from 'react'
import { formatProspectiveMarkdown } from '../../utils/prospectiveMarkdown'
import './FormattedNarrative.css'

type Props = {
  text: string
  className?: string
}

export default function FormattedNarrative({ text, className = '' }: Props) {
  const html = useMemo(() => formatProspectiveMarkdown(text), [text])
  if (!html) return null
  return (
    <div
      className={`formatted-narrative ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
