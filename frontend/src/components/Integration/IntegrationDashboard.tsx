import { useEffect, useState } from 'react'
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
        setErrorMessage('No s’ha pogut carregar l’estat de les integracions.')
      } finally {
        setIsLoading(false)
      }
    }

    fetchStatus()
  }, [])

  return (
    <section className="integration-dashboard">
      <header className="integration-header">
        <h1>Integracions</h1>
        <p>Revisa l’estat de connexió de les APIs disponibles i les claus necessàries.</p>
      </header>

      {isLoading ? (
        <div className="integration-state">Carregant estat d’integracions...</div>
      ) : errorMessage ? (
        <div className="integration-state error">{errorMessage}</div>
      ) : (
        <div className="integration-grid">
          {services.map((service) => (
            <article key={service.key} className="integration-card">
              <div className="integration-card-header">
                <h3>{service.service}</h3>
                <span className={`integration-badge ${service.configured ? 'ok' : 'missing'}`}>
                  {service.configured ? 'Connectat' : 'Claus pendents'}
                </span>
              </div>
              <p className="integration-features">
                {service.features.length > 0 ? service.features.join(' · ') : 'Funcionalitat pendent de definir'}
              </p>
              <div className="integration-keys">
                <strong>Claus necessàries:</strong>
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
