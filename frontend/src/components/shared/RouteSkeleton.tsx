import { useI18n } from '../../contexts/I18nContext'
import './RouteSkeleton.css'

type RouteSkeletonProps = {
  label?: string
}

export default function RouteSkeleton({ label }: RouteSkeletonProps) {
  const { t } = useI18n()
  const displayLabel = label ?? t('common.loading.module')

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
      <span className="route-skeleton__label">{displayLabel}</span>
    </div>
  )
}
