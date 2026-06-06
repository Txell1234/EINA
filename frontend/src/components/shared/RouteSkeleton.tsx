import './RouteSkeleton.css'

type RouteSkeletonProps = {
  label?: string
}

export default function RouteSkeleton({ label = 'Carregant mòdul…' }: RouteSkeletonProps) {
  return (
    <div className="route-skeleton" role="status" aria-live="polite" aria-busy="true">
      <div className="route-skeleton__header" />
      <div className="route-skeleton__line route-skeleton__line--wide" />
      <div className="route-skeleton__line" />
      <div className="route-skeleton__line route-skeleton__line--short" />
      <div className="route-skeleton__grid">
        <div className="route-skeleton__card" />
        <div className="route-skeleton__card" />
        <div className="route-skeleton__card" />
      </div>
      <span className="route-skeleton__label">{label}</span>
    </div>
  )
}
