import React, { Component, ErrorInfo, ReactNode } from 'react'
import { useI18n } from '../contexts/I18nContext'
import './ErrorBoundary.css'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

function ErrorBoundaryFallback({
  error,
  onReload,
}: {
  error: Error | null
  onReload: () => void
}) {
  const { t } = useI18n()
  return (
    <div className="error-boundary" role="alert">
      <h1 className="error-boundary__title">{t('error.boundary.title')}</h1>
      <p className="error-boundary__message">
        {error?.message || t('error.boundary.fallbackMessage')}
      </p>
      <button
        type="button"
        className="error-boundary__reload btn btn-primary"
        onClick={onReload}
      >
        {t('error.boundary.reload')}
      </button>
      <details className="error-boundary__details">
        <summary>{t('error.boundary.details')}</summary>
        <pre className="error-boundary__stack">{error?.stack}</pre>
      </details>
    </div>
  )
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error capturado por ErrorBoundary:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <ErrorBoundaryFallback
          error={this.state.error}
          onReload={() => {
            this.setState({ hasError: false, error: null })
            window.location.reload()
          }}
        />
      )
    }

    return this.props.children
  }
}
