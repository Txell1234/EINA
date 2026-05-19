import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  ChartScatter,
  Cpu,
  FileText,
  FolderOpen,
  Grid3x3,
  Home,
  Landmark,
  LayoutGrid,
  MessageSquareText,
  Network,
  Search,
  Settings,
  Shield,
  Sparkles,
  Telescope,
  TrendingUp,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useCase } from '../contexts/CaseContext'
import { useI18n } from '../contexts/I18nContext'
import { prospectiveService } from '../services/api'
import './Layout.css'

type NavLabelKey =
  | 'nav.osintSources'
  | 'nav.directAnalysis'
  | 'nav.extraction'
  | 'nav.project'
  | 'nav.retrospective'
  | 'nav.variables'
  | 'nav.micmac'
  | 'nav.actors'
  | 'nav.mactor'
  | 'nav.morph'
  | 'nav.scenarios'
  | 'nav.alertMonitors'
  | 'nav.alertMonitorsTriggered'
  | 'nav.aiAnalysis'
  | 'nav.qualitativeAnalysis'
  | 'nav.investmentRecommendations'
  | 'nav.reputation'
  | 'nav.publicAffairs'
  | 'nav.dashboard'
  | 'nav.admin'

type GroupLabelKey =
  | 'nav.group.recollida'
  | 'nav.group.analisi'
  | 'nav.group.resultats'
  | 'nav.group.complementaries'
  | 'nav.group.sistema'

const NAV_GROUPS: {
  labelKey: GroupLabelKey
  items: { path: string; labelKey: NavLabelKey; icon: LucideIcon; end?: boolean }[]
}[] = [
  {
    labelKey: 'nav.group.recollida',
    items: [
      { path: '/osint-collection', labelKey: 'nav.osintSources', icon: Search },
      { path: '/direct-analysis', labelKey: 'nav.directAnalysis', icon: FileText },
      { path: '/data-synchronization', labelKey: 'nav.extraction', icon: Cpu },
    ],
  },
  {
    labelKey: 'nav.group.analisi',
    items: [
      { path: '/prospective/project', labelKey: 'nav.project', icon: FolderOpen },
      { path: '/prospective/retrospective', labelKey: 'nav.retrospective', icon: ChartScatter },
      { path: '/prospective/variables', labelKey: 'nav.variables', icon: ChartScatter },
      { path: '/prospective/micmac', labelKey: 'nav.micmac', icon: Grid3x3 },
      { path: '/prospective/actors', labelKey: 'nav.actors', icon: Users },
      { path: '/prospective/mactor', labelKey: 'nav.mactor', icon: Network },
      { path: '/prospective/morph', labelKey: 'nav.morph', icon: LayoutGrid },
    ],
  },
  {
    labelKey: 'nav.group.resultats',
    items: [
      { path: '/prospective-analysis', labelKey: 'nav.scenarios', icon: Telescope },
      { path: '/alert-monitors', labelKey: 'nav.alertMonitors', icon: Bell },
    ],
  },
  {
    labelKey: 'nav.group.complementaries',
    items: [
      { path: '/ai-analysis', labelKey: 'nav.aiAnalysis', icon: Sparkles },
      { path: '/qualitative-analysis', labelKey: 'nav.qualitativeAnalysis', icon: MessageSquareText },
      { path: '/investment-recommendations', labelKey: 'nav.investmentRecommendations', icon: TrendingUp },
      { path: '/reputation', labelKey: 'nav.reputation', icon: Shield },
      { path: '/public-affairs', labelKey: 'nav.publicAffairs', icon: Landmark },
    ],
  },
  {
    labelKey: 'nav.group.sistema',
    items: [
      { path: '/', labelKey: 'nav.dashboard', icon: Home, end: true },
      { path: '/admin', labelKey: 'nav.admin', icon: Settings },
    ],
  },
]

function isNavActive(pathname: string, path: string, end?: boolean): boolean {
  if (end || path === '/') {
    return pathname === path
  }
  return pathname === path
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { activeCase, clearActiveCase } = useCase()
  const { logout } = useAuth()
  const { t, locale, setLocale } = useI18n()

  const { data: monitorSummary } = useQuery({
    queryKey: ['monitor-summary', activeCase?.id],
    queryFn: () => prospectiveService.getMonitorSummary(activeCase?.id),
    refetchInterval: 60_000,
  })

  const triggeredMonitors = monitorSummary?.triggered_count ?? 0

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
          <p>{t('layout.subtitle')}</p>
        </div>

        {activeCase ? (
          <div className="sidebar-active-case">
            <div className="active-case-label">{t('layout.activeCase')}</div>
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
          <div className="sidebar-no-case">{t('layout.noCase')}</div>
        )}

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.labelKey} className="nav-group">
              <div className="nav-group-label">{t(group.labelKey)}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                const active = isNavActive(location.pathname, item.path, item.end)
                const showAlertBadge =
                  item.path === '/alert-monitors' && triggeredMonitors > 0
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-item ${active ? 'active' : ''}`}
                  >
                    <span className="nav-icon" aria-hidden>
                      <Icon size={18} strokeWidth={2} />
                    </span>
                    <span className="nav-label">{t(item.labelKey)}</span>
                    {showAlertBadge && (
                      <span
                        className="nav-alert-badge"
                        title={t('nav.alertMonitorsTriggered')}
                        aria-label={t('nav.alertMonitorsTriggered')}
                      >
                        {triggeredMonitors > 9 ? '9+' : triggeredMonitors}
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <select
            className="locale-select"
            value={locale}
            onChange={(e) => setLocale(e.target.value as typeof locale)}
            aria-label="Idioma"
          >
            <option value="ca">CA</option>
            <option value="es">ES</option>
            <option value="en">EN</option>
            <option value="fr">FR</option>
          </select>
          <button type="button" onClick={handleLogout} className="logout-btn">
            {t('layout.logout')}
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
