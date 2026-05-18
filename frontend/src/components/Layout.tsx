import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  Cpu,
  FileDown,
  Home,
  LayoutGrid,
  Search,
  Settings,
  Telescope,
  Users,
  ChartScatter,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useCase } from '../contexts/CaseContext'
import './Layout.css'

const NAV_GROUPS: {
  label: string
  items: { path: string; label: string; icon: LucideIcon; end?: boolean }[]
}[] = [
  {
    label: 'Recollida',
    items: [
      { path: '/osint-collection', label: 'Fonts OSINT', icon: Search },
      { path: '/data-synchronization', label: 'Extracció', icon: Cpu },
    ],
  },
  {
    label: 'Anàlisi',
    items: [
      { path: '/qualitative-analysis', label: 'Variables · MIC-MAC', icon: ChartScatter },
      { path: '/ai-analysis', label: 'Actors · MACTOR', icon: Users },
      { path: '/geopolitical-advanced', label: 'Morfològic', icon: LayoutGrid },
    ],
  },
  {
    label: 'Resultats',
    items: [
      { path: '/prospective-analysis', label: 'Escenaris', icon: Telescope },
      { path: '/investment-advanced', label: 'Alertes actives', icon: Bell },
      { path: '/investment-recommendations', label: 'Exportar informe', icon: FileDown },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { path: '/', label: 'Dashboard', icon: Home, end: true },
      { path: '/admin', label: 'Administració', icon: Settings },
    ],
  },
]

function isNavActive(pathname: string, path: string, end?: boolean): boolean {
  if (end || path === '/') {
    return pathname === path
  }
  return pathname === path || pathname.startsWith(`${path}/`)
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { activeCase, clearActiveCase } = useCase()
  const { logout } = useAuth()

  const handleLogout = () => {
    logout()
    clearActiveCase()
    navigate('/login')
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>EINA</h1>
          <p>Intel·ligència Estratègica</p>
        </div>

        {activeCase ? (
          <div className="sidebar-active-case">
            <div className="active-case-label">Cas actiu</div>
            <div className="active-case-name">{activeCase.name}</div>
            {(activeCase.osint_count !== undefined || activeCase.extraction_count) && (
              <div className="active-case-meta">
                {activeCase.osint_count !== undefined && `${activeCase.osint_count} fonts`}
                {activeCase.extraction_count
                  ? ` · ${activeCase.extraction_count} declaracions`
                  : ''}
              </div>
            )}
          </div>
        ) : (
          <div className="sidebar-no-case">Cap cas seleccionat</div>
        )}

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="nav-group">
              <div className="nav-group-label">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                const active = isNavActive(location.pathname, item.path, item.end)
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-item ${active ? 'active' : ''}`}
                  >
                    <span className="nav-icon" aria-hidden>
                      <Icon size={18} strokeWidth={2} />
                    </span>
                    <span className="nav-label">{item.label}</span>
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button type="button" onClick={handleLogout} className="logout-btn">
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
