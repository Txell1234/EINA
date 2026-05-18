import { Navigate, Route, Routes } from 'react-router-dom'
import Dashboard from './components/Dashboard/Dashboard'
import Layout from './components/Layout'
import PlaceholderPage from './components/PlaceholderPage'
import ProtectedRoute from './components/ProtectedRoute'
import ProspectiveAnalysis from './components/ProspectiveAnalysis/ProspectiveAnalysis'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route
          path="/osint-collection"
          element={
            <PlaceholderPage
              title="Fonts OSINT"
              description="Aquí es connectaran les consultes OSINT recurrents i les fonts configurades per cas (proper desenvolupament)."
            />
          }
        />
        <Route
          path="/qualitative-analysis"
          element={<Navigate to="/prospective/variables" replace />}
        />
        <Route path="/ai-analysis" element={<Navigate to="/prospective/mactor" replace />} />
        <Route
          path="/geopolitical-advanced"
          element={<Navigate to="/prospective/morph" replace />}
        />
        <Route
          path="/investment-advanced"
          element={
            <PlaceholderPage
              title="Alertes actives"
              description="Les alertes vinculades a indicadors dels escenaris es definiran en una futura iteració (monitoratge continu)."
            />
          }
        />
        <Route
          path="/reports"
          element={
            <PlaceholderPage
              title="Exportar informe"
              description="Exportació PDF/DOCX amb metodologia i narratives (proper desenvolupament)."
            />
          }
        />
        <Route
          path="/admin"
          element={
            <PlaceholderPage
              title="Administració"
              description="Configuració del sistema i usuaris (proper desenvolupament)."
            />
          }
        />

        <Route
          path="/prospective/extraction"
          element={
            <ProtectedRoute>
              <ProspectiveAnalysis entryStep={0} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prospective/variables"
          element={
            <ProtectedRoute>
              <ProspectiveAnalysis entryStep={2} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prospective/mactor"
          element={
            <ProtectedRoute>
              <ProspectiveAnalysis entryStep={5} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prospective/morph"
          element={
            <ProtectedRoute>
              <ProspectiveAnalysis entryStep={6} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prospective/scenarios"
          element={
            <ProtectedRoute>
              <ProspectiveAnalysis entryStep={7} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prospective-analysis"
          element={<Navigate to="/prospective/extraction" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
