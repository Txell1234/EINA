// @refresh reset
import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './components/Auth/Login'
import { AuthProvider, ProtectedRoute } from './contexts/AuthContext'
import { CaseProvider } from './contexts/CaseContext'
import { I18nProvider } from './contexts/I18nContext'

const OSINTIntelligenceDashboard = lazy(
  () => import('./components/Dashboard/OSINTIntelligenceDashboard'),
)
const OSINTCollection = lazy(() => import('./components/OSINTCollection/OSINTCollection'))
const AIAnalysis = lazy(() => import('./components/AIAnalysis/AIAnalysis'))
const QualitativeAnalysis = lazy(() => import('./components/QualitativeAnalysis/QualitativeAnalysis'))
const ReasoningFrameworks = lazy(() => import('./components/QualitativeAnalysis/ReasoningFrameworks'))
const InvestmentRecommendations = lazy(
  () => import('./components/InvestmentRecommendations/InvestmentRecommendations'),
)
const AdminPanel = lazy(() => import('./components/Admin/AdminPanel'))
const ReputationDashboard = lazy(() => import('./components/Reputation/ReputationDashboard'))
const PublicAffairsDashboard = lazy(
  () => import('./components/PublicAffairs/PublicAffairsDashboard'),
)
const IntegrationDashboard = lazy(() => import('./components/Integration/IntegrationDashboard'))
const AdvancedVisualizations = lazy(
  () => import('./components/Geopolitical/AdvancedVisualizations'),
)
const InvestmentAdvancedDashboard = lazy(
  () => import('./components/InvestmentAdvanced/InvestmentAdvancedDashboard'),
)
const AlertMonitors = lazy(() => import('./components/AlertMonitors/AlertMonitors'))
const ProspectiveAnalysis = lazy(
  () => import('./components/ProspectiveAnalysis/ProspectiveAnalysis'),
)
const DirectAnalysis = lazy(() => import('./components/DirectAnalysis/DirectAnalysis'))
const IntelligenceCenter = lazy(() => import('./components/Intelligence/IntelligenceCenter'))
const InquiryDashboard = lazy(() => import('./components/Intelligence/InquiryDashboard'))

function AppRoutes() {
  return (
    <Suspense fallback={<div className="spinner" style={{ margin: '4rem auto' }} />}>
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
          <Route index element={<OSINTIntelligenceDashboard />} />
          <Route path="osint-collection" element={<OSINTCollection />} />
          <Route path="ai-analysis" element={<AIAnalysis />} />
          <Route path="qualitative-analysis" element={<QualitativeAnalysis />} />
          <Route path="reasoning-frameworks" element={<ReasoningFrameworks />} />
          <Route path="investment-recommendations" element={<InvestmentRecommendations />} />
          <Route path="data-synchronization" element={<ProspectiveAnalysis entryStep={0} />} />
          <Route path="direct-analysis" element={<DirectAnalysis />} />
          <Route path="intelligence" element={<IntelligenceCenter />} />
          <Route path="prospective/inquiries" element={<InquiryDashboard />} />
          <Route path="admin" element={<AdminPanel />} />
          <Route path="reputation" element={<ReputationDashboard />} />
          <Route path="public-affairs" element={<PublicAffairsDashboard />} />
          <Route path="integration" element={<IntegrationDashboard />} />
          <Route path="geopolitical-advanced" element={<AdvancedVisualizations />} />
          <Route path="investment-advanced" element={<InvestmentAdvancedDashboard />} />
          <Route path="alert-monitors" element={<AlertMonitors />} />
          <Route path="prospective/project" element={<ProspectiveAnalysis entryStep={1} />} />
          <Route path="prospective/retrospective" element={<ProspectiveAnalysis entryStep={2} />} />
          <Route path="prospective/variables" element={<ProspectiveAnalysis entryStep={3} />} />
          <Route path="prospective/micmac" element={<ProspectiveAnalysis entryStep={4} />} />
          <Route path="prospective/actors" element={<ProspectiveAnalysis entryStep={5} />} />
          <Route path="prospective/mactor" element={<ProspectiveAnalysis entryStep={6} />} />
          <Route path="prospective/morph" element={<ProspectiveAnalysis entryStep={7} />} />
          <Route path="prospective-analysis" element={<ProspectiveAnalysis entryStep={8} />} />
          <Route path="prospective" element={<Navigate to="/prospective/project" replace />} />
        </Route>
      </Routes>
    </Suspense>
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
      <I18nProvider>
        <CaseProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </CaseProvider>
      </I18nProvider>
    </Router>
  )
}

export default App
