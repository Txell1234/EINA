import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
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

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/osint-collection', label: 'Recopilació OSINT', icon: '🔍' },
    { path: '/ai-analysis', label: 'Anàlisi amb IA', icon: '🤖' },
    { path: '/qualitative-analysis', label: 'Anàlisi Qualitatiu', icon: '📈' },
    { path: '/investment-recommendations', label: 'Recomanacions Inversió', icon: '💰' },
    { path: '/data-synchronization', label: 'Sincronització de Dades', icon: '🔄' },
    { path: '/admin', label: 'Administració', icon: '⚙️' },
  ]

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Amb Tu</h1>
          <p>OSINT Intelligence Platform</p>
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
            Tancar Sessió
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

