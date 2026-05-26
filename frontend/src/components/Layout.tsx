// @refresh reset
import { useEffect, useMemo, useState } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  Brain,
  ChartScatter,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileText,
  FolderOpen,
  Globe2,
  Grid3x3,
  Home,
  Landmark,
  LayoutGrid,
  LogOut,
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
import { useCasesList } from '../hooks/useCasesList'
import { briefCaseDescription, countPromptLines, toActiveCase } from '../utils/caseUtils'
import { useI18n } from '../contexts/I18nContext'
import { prospectiveService } from '../services/api'
import './Layout.css'

const SIDEBAR_STORAGE_KEY = 'eina_sidebar_collapsed'

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
  | 'nav.intelligence'
  | 'nav.alertMonitors'
  | 'nav.alertMonitorsTriggered'
  | 'nav.aiAnalysis'
  | 'nav.qualitativeAnalysis'
  | 'nav.reasoningFrameworks'
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
      { path: '/intelligence', labelKey: 'nav.intelligence', icon: Globe2 },
      { path: '/prospective-analysis', labelKey: 'nav.scenarios', icon: Telescope },
      { path: '/alert-monitors', labelKey: 'nav.alertMonitors', icon: Bell },
    ],
  },
  {
    labelKey: 'nav.group.complementaries',
    items: [
      { path: '/ai-analysis', labelKey: 'nav.aiAnalysis', icon: Sparkles },
      { path: '/qualitative-analysis', labelKey: 'nav.qualitativeAnalysis', icon: MessageSquareText },
      { path: '/reasoning-frameworks', labelKey: 'nav.reasoningFrameworks', icon: Brain },
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

const PAGE_TITLES: Record<string, NavLabelKey | 'nav.intelligence'> = {
  '/': 'nav.dashboard',
  '/osint-collection': 'nav.osintSources',
  '/direct-analysis': 'nav.directAnalysis',
  '/data-synchronization': 'nav.extraction',
  '/intelligence': 'nav.intelligence',
  '/prospective-analysis': 'nav.scenarios',
  '/alert-monitors': 'nav.alertMonitors',
  '/ai-analysis': 'nav.aiAnalysis',
  '/qualitative-analysis': 'nav.qualitativeAnalysis',
  '/reasoning-frameworks': 'nav.reasoningFrameworks',
  '/investment-recommendations': 'nav.investmentRecommendations',
  '/reputation': 'nav.reputation',
  '/public-affairs': 'nav.publicAffairs',
  '/admin': 'nav.admin',
  '/prospective/project': 'nav.project',
  '/prospective/retrospective': 'nav.retrospective',
  '/prospective/variables': 'nav.variables',
  '/prospective/micmac': 'nav.micmac',
  '/prospective/actors': 'nav.actors',
  '/prospective/mactor': 'nav.mactor',
  '/prospective/morph': 'nav.morph',
}

function isNavActive(pathname: string, path: string, end?: boolean): boolean {
  if (end || path === '/') {
    return pathname === path
  }
  return pathname === path || pathname.startsWith(`${path}/`)
}

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { activeCase, setActiveCase, clearActiveCase } = useCase()
  const { logout } = useAuth()
  const { t, locale, setLocale } = useI18n()
  const [collapsed, setCollapsed] = useState(readSidebarCollapsed)

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0')
    } catch {
      /* ignore */
    }
    document.documentElement.style.setProperty(
      '--sidebar-current-width',
      collapsed ? 'var(--sidebar-width-collapsed)' : 'var(--sidebar-width)',
    )
  }, [collapsed])

  const { data: monitorSummary } = useQuery({
    queryKey: ['monitor-summary', activeCase?.id],
    queryFn: () => prospectiveService.getMonitorSummary(activeCase?.id),
    enabled: Boolean(activeCase?.id),
    retry: 1,
    retryDelay: 10_000,
    refetchOnWindowFocus: false,
    staleTime: 90_000,
    refetchInterval: (query) => (query.state.error ? false : 120_000),
  })

  const triggeredMonitors = monitorSummary?.triggered_count ?? 0

  const { data: casesForHydrate } = useCasesList({
    enabled: !!activeCase?.id && !activeCase.description,
  })

  useEffect(() => {
    if (!activeCase?.id || activeCase.description || !casesForHydrate?.length) return
    const match = casesForHydrate.find((c) => c.id === activeCase.id)
    if (match?.description) {
      setActiveCase(toActiveCase({ ...activeCase, ...match }))
    }
  }, [activeCase, casesForHydrate, setActiveCase])

  const pageTitleKey = PAGE_TITLES[location.pathname]
  const briefingDate = useMemo(() => {
    const localeMap: Record<string, string> = {
      ca: 'ca-ES',
      es: 'es-ES',
      en: 'en-GB',
      fr: 'fr-FR',
    }
    return new Date().toLocaleDateString(localeMap[locale] ?? 'ca-ES', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  }, [locale])

  const handleLogout = () => {
    logout()
    clearActiveCase()
    navigate('/login')
  }

  return (
    <div className={`layout ${collapsed ? 'layout--sidebar-collapsed' : ''}`}>
      <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`} aria-label="Navegació principal">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="brand-mark">EINA</span>
            {!collapsed && (
              <>
                <span className="brand-unit">{t('layout.intelligenceUnit')}</span>
                <span className="brand-rule" aria-hidden />
              </>
            )}
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? t('layout.expandSidebar') : t('layout.collapseSidebar')}
            title={collapsed ? t('layout.expandSidebar') : t('layout.collapseSidebar')}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {activeCase ? (
          <div
            className="sidebar-active-case"
            title={
              activeCase.description
                ? `${activeCase.name}\n\n${activeCase.description.slice(0, 500)}${activeCase.description.length > 500 ? '…' : ''}`
                : activeCase.name
            }
          >
            {!collapsed && <div className="active-case-label">{t('layout.activeCase')}</div>}
            <div className="active-case-name">{collapsed ? `#${activeCase.id}` : activeCase.name}</div>
            {!collapsed && activeCase.description ? (
              <div className="active-case-briefing">
                {countPromptLines(activeCase.description)} línies ·{' '}
                {briefCaseDescription(activeCase.description, 72)}
              </div>
            ) : null}
            {!collapsed && (activeCase.osint_count !== undefined || activeCase.extraction_count) && (
              <div className="active-case-meta">
                {activeCase.osint_count !== undefined && `${activeCase.osint_count} fonts`}
                {activeCase.extraction_count ? ` · ${activeCase.extraction_count} decl.` : ''}
              </div>
            )}
          </div>
        ) : (
          !collapsed && <div className="sidebar-no-case">{t('layout.noCase')}</div>
        )}

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.labelKey} className="nav-group">
              {!collapsed && <div className="nav-group-label">{t(group.labelKey)}</div>}
              {group.items.map((item) => {
                const Icon = item.icon
                const active = isNavActive(location.pathname, item.path, item.end)
                const showAlertBadge = item.path === '/alert-monitors' && triggeredMonitors > 0
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-item ${active ? 'active' : ''}`}
                    title={collapsed ? t(item.labelKey) : undefined}
                  >
                    <span className="nav-icon" aria-hidden>
                      <Icon size={18} strokeWidth={1.75} />
                    </span>
                    {!collapsed && <span className="nav-label">{t(item.labelKey)}</span>}
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
          {!collapsed ? (
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
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            className="logout-btn"
            title={collapsed ? t('layout.logout') : undefined}
          >
            {collapsed ? <LogOut size={16} /> : t('layout.logout')}
          </button>
        </div>
      </aside>

      <div className="layout-main">
        <header className="intel-topbar">
          <div className="intel-topbar-left">
            <span className="intel-kicker">{t('layout.briefing')}</span>
            <span className="intel-date">{briefingDate}</span>
          </div>
          <div className="intel-topbar-right">
            {pageTitleKey && <span className="intel-section">{t(pageTitleKey)}</span>}
            {activeCase && (
              <span className="intel-case-pill">
                {activeCase.name.length > 36 ? `${activeCase.name.slice(0, 34)}…` : activeCase.name}
              </span>
            )}
          </div>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
