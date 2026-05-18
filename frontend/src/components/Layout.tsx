import type { LucideIcon } from 'lucide-react'
import {
  Bell,
  ChartScatter,
  Cpu,
  FileDown,
  Home,
  LayoutGrid,
  Search,
  Settings,
  Telescope,
  Users,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useCase } from '../contexts/CaseContext'
import './Layout.css'

const navGroups: {
  label: string
  items: { path: string; label: string; icon: LucideIcon; end?: boolean }[]
}[] = [
  {
    label: 'Recollida',
    items: [
      { path: '/osint-collection', label: 'Fonts OSINT', icon: Search },
      { path: '/prospective/extraction', label: 'Extracció', icon: Cpu },
    ],
  },
  {
    label: 'Anàlisi',
    items: [
      { path: '/prospective/variables', label: 'Variables · MIC-MAC', icon: ChartScatter },
      { path: '/prospective/mactor', label: 'Actors · MACTOR', icon: Users },
      { path: '/prospective/morph', label: 'Morfològic', icon: LayoutGrid },
    ],
  },
  {
    label: 'Resultats',
    items: [
      { path: '/prospective/scenarios', label: 'Escenaris', icon: Telescope },
      { path: '/investment-advanced', label: 'Alertes actives', icon: Bell },
      { path: '/reports', label: 'Exportar informe', icon: FileDown },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { path: '/', label: 'Dashboard', icon: Home, end: true },
      { path: '/admin', label: 'Admin', icon: Settings },
    ],
  },
]

export default function Layout() {
  const { activeCase } = useCase()

  return (
    <div className="layout-root">
      <aside className="layout-drawer">
        <div className="layout-brand">EINA</div>

        {activeCase ? (
          <div className="sidebar-active-case">
            <div className="active-case-label">Cas actiu</div>
            <div className="active-case-name">{activeCase.name}</div>
            {activeCase.osint_count !== undefined && activeCase.osint_count > 0 && (
              <div className="active-case-meta">{activeCase.osint_count} fonts OSINT</div>
            )}
          </div>
        ) : (
          <div className="sidebar-no-case">
            <span>Cap cas seleccionat</span>
          </div>
        )}

        <nav className="layout-nav">
          {navGroups.map((group) => (
            <div key={group.label} className="layout-nav-group">
              <div className="sidebar-group-label">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.path + item.label}
                    to={item.path}
                    end={item.end ?? false}
                    className={({ isActive }) =>
                      `layout-nav-link ${isActive ? 'layout-nav-link--active' : ''}`
                    }
                  >
                    <span className="layout-nav-icon" aria-hidden>
                      <Icon size={18} strokeWidth={2} />
                    </span>
                    {item.label}
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>
      </aside>
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  )
}
