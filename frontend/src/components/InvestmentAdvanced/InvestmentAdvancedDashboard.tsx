import { useState } from 'react'
import ESGAnalysis from './ESGAnalysis'
import GeopoliticalImpactChart from './GeopoliticalImpactChart'
import MarketOpportunityComparison from './MarketOpportunityComparison'
import RegulatoryRiskAssessment from './RegulatoryRiskAssessment'
import './InvestmentAdvancedDashboard.css'

const DEMO_ESG = {
  esg_score: 68,
  environmental_score: 72,
  social_score: 65,
  governance_score: 67,
  recommendations: ['Millorar transparència de supply chain', 'Reforçar polítiques socials'],
}

export default function InvestmentAdvancedDashboard() {
  const [tab, setTab] = useState<'esg' | 'geo' | 'market' | 'regulatory'>('esg')

  return (
    <div className="investment-advanced-dashboard">
      <h2>Inversió avançada</h2>
      <div className="tab-bar">
        <button type="button" className={tab === 'esg' ? 'active' : ''} onClick={() => setTab('esg')}>
          ESG
        </button>
        <button type="button" className={tab === 'geo' ? 'active' : ''} onClick={() => setTab('geo')}>
          Impacte geopolític
        </button>
        <button type="button" className={tab === 'market' ? 'active' : ''} onClick={() => setTab('market')}>
          Mercat
        </button>
        <button type="button" className={tab === 'regulatory' ? 'active' : ''} onClick={() => setTab('regulatory')}>
          Risc regulatori
        </button>
      </div>
      {tab === 'esg' && <ESGAnalysis data={DEMO_ESG} />}
      {tab === 'geo' && (
        <GeopoliticalImpactChart
          data={{ impacts: [], investment_type: 'equity' }}
        />
      )}
      {tab === 'market' && (
        <MarketOpportunityComparison
          data={{ opportunities: [], comparison_date: new Date().toISOString() }}
        />
      )}
      {tab === 'regulatory' && (
        <RegulatoryRiskAssessment data={{}} country="Espanya" />
      )}
    </div>
  )
}
