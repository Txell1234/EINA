import { useEffect, useState } from 'react'
import { useI18n } from '../../contexts/I18nContext'
import { integrationService } from '../../services/api'
import './IntegrationDashboard.css'

type IntegrationStatus = {
  service: string
  key: string
  configured: boolean
  required_keys: string[]
  missing_keys: string[]
  features: string[]
}

export default function IntegrationDashboard() {
  const { t } = useI18n()
  const [services, setServices] = useState<IntegrationStatus[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setIsLoading(true)
        const response = await integrationService.getStatus()
        setServices(response.services || [])
        setErrorMessage(null)
      } catch (error) {
        console.error('Error loading integration status', error)
        setErrorMessage('load_failed')
      } finally {
        setIsLoading(false)
      }
    }

    fetchStatus()
  }, [])

  return (
    <section className="integration-dashboard">
      <header className="integration-header">
        <h1>{t('integration.title')}</h1>
        <p>{t('integration.subtitle')}</p>
      </header>

      {isLoading ? (
        <div className="integration-state">{t('integration.loading')}</div>
      ) : errorMessage ? (
        <div className="integration-state error">
          {errorMessage === 'load_failed' ? t('integration.error.load') : errorMessage}
        </div>
      ) : (
        <div className="integration-grid">
          {services.map((service) => (
            <article key={service.key} className="integration-card">
              <div className="integration-card-header">
                <h3>{service.service}</h3>
                <span className={`integration-badge ${service.configured ? 'ok' : 'missing'}`}>
                  {service.configured ? t('integration.badge.connected') : t('integration.badge.missingKeys')}
                </span>
              </div>
              <p className="integration-features">
                {service.features.length > 0
                  ? service.features.join(' · ')
                  : t('integration.features.pending')}
              </p>
              <div className="integration-keys">
                <strong>{t('integration.keys.required')}</strong>
                <ul>
                  {service.required_keys.map((key) => (
                    <li key={key} className={service.missing_keys.includes(key) ? 'missing-key' : 'ok-key'}>
                      {key}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
