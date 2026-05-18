import { useState } from 'react'
import { useCase } from '../../contexts/CaseContext'
import RiskDashboard from './RiskDashboard'
import BilateralMatrix from './BilateralMatrix'
import RelationTimeline from './RelationTimeline'
import './AdvancedVisualizations.css'

export default function AdvancedVisualizations() {
  const { activeCase } = useCase()
  const caseId = activeCase?.id
  const [country1, setCountry1] = useState('Espanya')
  const [country2, setCountry2] = useState('França')

  return (
    <div className="advanced-visualizations">
      <h2>Anàlisi geopolítica avançada</h2>
      <RiskDashboard caseId={caseId} />
      <BilateralMatrix caseId={caseId} />
      <div className="timeline-controls">
        <input value={country1} onChange={(e) => setCountry1(e.target.value)} placeholder="País 1" />
        <input value={country2} onChange={(e) => setCountry2(e.target.value)} placeholder="País 2" />
      </div>
      <RelationTimeline country1={country1} country2={country2} />
    </div>
  )
}
