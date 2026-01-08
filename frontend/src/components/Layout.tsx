import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useI18n } from '../contexts/I18nContext'
import './Layout.css'

export default function Layout() {
  const location = useLocation()
  // Temporalmente deshabilitado - no usar useAuth si no está disponible
  let logout = () => {}
  try {
    const auth = useAuth()
    logout = auth.logout
  } catch (e) {
    // Si no hay AuthProvider, usar función vacía
    console.warn('AuthContext no disponible, usando logout vacío')
  }

  const { t, locale, setLocale } = useI18n()

  const navItems = [
    { path: '/', label: t('nav.dashboard'), icon: '📊' },
    { path: '/osint-collection', label: t('nav.osintCollection'), icon: '🔍' },
    { path: '/ai-analysis', label: t('nav.aiAnalysis'), icon: '🤖' },
    { path: '/qualitative-analysis', label: t('nav.qualitativeAnalysis'), icon: '📈' },
    { path: '/investment-recommendations', label: t('nav.investmentRecommendations'), icon: '💰' },
    { path: '/data-synchronization', label: t('nav.dataSynchronization'), icon: '🔄' },
    { path: '/admin', label: t('nav.admin'), icon: '⚙️' },
  ]

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Amb Tu</h1>
          <p>{t('app.name')}</p>
          <div style={{ marginTop: '0.75rem' }}>
            <select
              aria-label="Language"
              value={locale}
              onChange={(event) => setLocale(event.target.value as any)}
              style={{ padding: '0.25rem 0.5rem', borderRadius: '6px' }}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="ca">Català</option>
              <option value="fr">Français</option>
            </select>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button onClick={logout} className="logout-btn">
            {t('nav.logout')}
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
