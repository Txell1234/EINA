import EmptyState from './EmptyState'

interface PlaceholderPageProps {
  title: string
  description: string
}

export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="card">
      <EmptyState icon="◎" title={title} description={description} />
    </div>
  )
}
