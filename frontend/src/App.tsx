import { lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './components/Auth/Login'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CaseProvider } from './contexts/CaseContext'
import { I18nProvider } from './contexts/I18nContext'

const OSINTIntelligenceDashboard = lazy(
  () => import('./components/Dashboard/OSINTIntelligenceDashboard'),
)
const OSINTCollection = lazy(() => import('./components/OSINTCollection/OSINTCollection'))
const AIAnalysis = lazy(() => import('./components/AIAnalysis/AIAnalysis'))
const QualitativeAnalysis = lazy(() => import('./components/QualitativeAnalysis/QualitativeAnalysis'))
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

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <>{children}</>
}

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
          <Route path="investment-recommendations" element={<InvestmentRecommendations />} />
          <Route path="data-synchronization" element={<ProspectiveAnalysis entryStep={0} />} />
          <Route path="admin" element={<AdminPanel />} />
          <Route path="reputation" element={<ReputationDashboard />} />
          <Route path="public-affairs" element={<PublicAffairsDashboard />} />
          <Route path="integration" element={<IntegrationDashboard />} />
          <Route path="geopolitical-advanced" element={<AdvancedVisualizations />} />
          <Route path="investment-advanced" element={<InvestmentAdvancedDashboard />} />
          <Route path="alert-monitors" element={<AlertMonitors />} />
          <Route path="prospective-analysis" element={<ProspectiveAnalysis entryStep={7} />} />
          <Route path="prospective/variables" element={<ProspectiveAnalysis entryStep={2} />} />
          <Route path="prospective/mactor" element={<ProspectiveAnalysis entryStep={5} />} />
          <Route path="prospective/morph" element={<ProspectiveAnalysis entryStep={6} />} />
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
