import { Construction } from 'lucide-react'
import EmptyState from './shared/EmptyState'

interface PlaceholderPageProps {
  title: string
  description: string
}

export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="card">
      <div className="section-header">
        <h2>{title}</h2>
      </div>
      <EmptyState
        icon={<Construction aria-hidden />}
        title="Mòdul en desenvolupament"
        description={description}
      />
    </div>
  )
}
