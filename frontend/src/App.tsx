import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import type { ReactNode } from 'react'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard/Dashboard'
import OSINTCollection from './components/OSINTCollection/OSINTCollection'
import AIAnalysis from './components/AIAnalysis/AIAnalysis'
import QualitativeAnalysis from './components/QualitativeAnalysis/QualitativeAnalysis'
import InvestmentRecommendations from './components/InvestmentRecommendations/InvestmentRecommendations'
import AdminPanel from './components/Admin/AdminPanel'
import Login from './components/Auth/Login'
import ReputationDashboard from './components/Reputation/ReputationDashboard'
import PublicAffairsDashboard from './components/PublicAffairs/PublicAffairsDashboard'
import IntegrationDashboard from './components/Integration/IntegrationDashboard'
import AdvancedVisualizations from './components/Geopolitical/AdvancedVisualizations'
import InvestmentAdvancedDashboard from './components/InvestmentAdvanced/InvestmentAdvancedDashboard'
import ProspectiveAnalysis from './components/ProspectiveAnalysis/ProspectiveAnalysis'
import { AuthProvider } from './contexts/AuthContext'
import { CaseProvider } from './contexts/CaseContext'

function ProtectedRoute({ children }: { children: ReactNode }) {
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="osint-collection" element={<OSINTCollection />} />
        <Route path="ai-analysis" element={<AIAnalysis />} />
        <Route path="qualitative-analysis" element={<QualitativeAnalysis />} />
        <Route path="investment-recommendations" element={<InvestmentRecommendations />} />
        <Route path="data-synchronization" element={<ProspectiveAnalysis entryStep={0} />} />
        <Route path="admin" element={<AdminPanel />} />
        <Route path="reputation" element={<ReputationDashboard />} />
        <Route path="public-affairs" element={<PublicAffairsDashboard />} />
        <Route path="integration" element={<IntegrationDashboard />} />
        <Route path="geopolitical-advanced" element={<AdvancedVisualizations />} />
        <Route path="investment-advanced" element={<InvestmentAdvancedDashboard />} />
        <Route path="prospective-analysis" element={<ProspectiveAnalysis entryStep={7} />} />
        <Route path="prospective/variables" element={<ProspectiveAnalysis entryStep={2} />} />
        <Route path="prospective/mactor" element={<ProspectiveAnalysis entryStep={5} />} />
        <Route path="prospective/morph" element={<ProspectiveAnalysis entryStep={6} />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <CaseProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </CaseProvider>
    </Router>
  )
}

export default App
