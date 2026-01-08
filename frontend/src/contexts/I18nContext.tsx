import { createContext, useContext, useMemo, useState } from 'react'

type SupportedLocale = 'en' | 'es' | 'ca' | 'fr'

type TranslationKeys =
  | 'app.name'
  | 'nav.dashboard'
  | 'nav.osintCollection'
  | 'nav.aiAnalysis'
  | 'nav.qualitativeAnalysis'
  | 'nav.investmentRecommendations'
  | 'nav.dataSynchronization'
  | 'nav.admin'
  | 'nav.logout'
  | 'dashboard.title'
  | 'dashboard.statusLive'
  | 'dashboard.description'
  | 'dashboard.allCases'
  | 'dashboard.update'
  | 'dashboard.export'
  | 'dashboard.exportGenerating'
  | 'dashboard.exportDownloading'
  | 'dashboard.exportQueued'
  | 'dashboard.exportError'
  | 'time.24h'
  | 'time.7days'
  | 'time.30days'
  | 'time.90days'
  | 'metrics.totalMentions'
  | 'metrics.sentimentScore'
  | 'metrics.sentimentPoints'
  | 'metrics.estimatedReach'
  | 'metrics.estimatedReachChange'
  | 'metrics.previousPeriod'
  | 'metrics.engagementRate'
  | 'metrics.engagement'
  | 'metrics.criticalAlerts'
  | 'metrics.criticalAlertsChange'
  | 'metrics.trendingTopics'
  | 'metrics.trendingTopicsNote'
  | 'panels.dataSources'
  | 'panels.dataSourcesNoData'
  | 'panels.trendingTopics'
  | 'panels.trendingTopicsNoData'
  | 'panels.mentionsLabel'
  | 'panels.alerts'
  | 'panels.alertsNoData'
  | 'panels.geographic'
  | 'quickAccess.title'
  | 'quickAccess.integrations'
  | 'quickAccess.reputation'
  | 'quickAccess.publicAffairs'

type Translations = Record<TranslationKeys, string>

const translations: Record<SupportedLocale, Translations> = {
  en: {
    'app.name': 'OSINT Intelligence Platform',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'OSINT Collection',
    'nav.aiAnalysis': 'AI Analysis',
    'nav.qualitativeAnalysis': 'Qualitative Analysis',
    'nav.investmentRecommendations': 'Investment Recommendations',
    'nav.dataSynchronization': 'Data Synchronization',
    'nav.admin': 'Administration',
    'nav.logout': 'Log Out',
    'dashboard.title': 'OSINT Intelligence Center',
    'dashboard.statusLive': 'LIVE',
    'dashboard.description': 'Actionable open-source intelligence in real time',
    'dashboard.allCases': 'All cases',
    'dashboard.update': 'Update',
    'dashboard.export': 'Export',
    'dashboard.exportGenerating': 'Generating report...',
    'dashboard.exportDownloading': 'Downloading report...',
    'dashboard.exportQueued': 'Report queued. Try again later.',
    'dashboard.exportError': 'Error generating report',
    'time.24h': '24h',
    'time.7days': '7 days',
    'time.30days': '30 days',
    'time.90days': '90 days',
    'metrics.totalMentions': 'Total mentions',
    'metrics.sentimentScore': 'Sentiment Score',
    'metrics.sentimentPoints': 'pts',
    'metrics.estimatedReach': 'Estimated reach',
    'metrics.estimatedReachChange': 'reach',
    'metrics.previousPeriod': 'vs previous period',
    'metrics.engagementRate': 'Engagement rate',
    'metrics.engagement': 'Engagement',
    'metrics.criticalAlerts': 'Critical alerts',
    'metrics.criticalAlertsChange': 'new alerts',
    'metrics.trendingTopics': 'Trending topics',
    'metrics.trendingTopicsNote': 'Top topics detected',
    'panels.dataSources': 'Data Sources',
    'panels.dataSourcesNoData': 'No data sources available',
    'panels.trendingTopics': 'Trending Topics',
    'panels.trendingTopicsNoData': 'No topics detected',
    'panels.mentionsLabel': 'mentions',
    'panels.alerts': 'Critical Alerts',
    'panels.alertsNoData': 'No recent alerts',
    'panels.geographic': 'Geographic distribution',
    'quickAccess.title': 'Quick access',
    'quickAccess.integrations': 'Integrations',
    'quickAccess.reputation': 'Reputation',
    'quickAccess.publicAffairs': 'Public Affairs',
  },
  es: {
    'app.name': 'Plataforma de Inteligencia OSINT',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'Recopilación OSINT',
    'nav.aiAnalysis': 'Análisis con IA',
    'nav.qualitativeAnalysis': 'Análisis Cualitativo',
    'nav.investmentRecommendations': 'Recomendaciones de Inversión',
    'nav.dataSynchronization': 'Sincronización de Datos',
    'nav.admin': 'Administración',
    'nav.logout': 'Cerrar sesión',
    'dashboard.title': 'OSINT Intelligence Center',
    'dashboard.statusLive': 'EN VIVO',
    'dashboard.description': 'Inteligencia de fuentes abiertas en tiempo real',
    'dashboard.allCases': 'Todos los casos',
    'dashboard.update': 'Actualizar',
    'dashboard.export': 'Exportar',
    'dashboard.exportGenerating': 'Generando informe...',
    'dashboard.exportDownloading': 'Descargando informe...',
    'dashboard.exportQueued': 'Informe en cola. Intenta más tarde.',
    'dashboard.exportError': 'Error generando informe',
    'time.24h': '24h',
    'time.7days': '7 días',
    'time.30days': '30 días',
    'time.90days': '90 días',
    'metrics.totalMentions': 'Menciones totales',
    'metrics.sentimentScore': 'Sentiment Score',
    'metrics.sentimentPoints': 'pts',
    'metrics.estimatedReach': 'Alcance estimado',
    'metrics.estimatedReachChange': 'alcance',
    'metrics.previousPeriod': 'vs período anterior',
    'metrics.engagementRate': 'Engagement rate',
    'metrics.engagement': 'Engagement',
    'metrics.criticalAlerts': 'Alertas críticas',
    'metrics.criticalAlertsChange': 'alertas nuevas',
    'metrics.trendingTopics': 'Trending topics',
    'metrics.trendingTopicsNote': 'Top temas detectados',
    'panels.dataSources': 'Fuentes de datos',
    'panels.dataSourcesNoData': 'Sin fuentes disponibles',
    'panels.trendingTopics': 'Trending Topics',
    'panels.trendingTopicsNoData': 'Sin topics detectados',
    'panels.mentionsLabel': 'menciones',
    'panels.alerts': 'Alertas críticas',
    'panels.alertsNoData': 'No hay alertas recientes',
    'panels.geographic': 'Distribución geográfica',
    'quickAccess.title': 'Accesos rápidos',
    'quickAccess.integrations': 'Integraciones',
    'quickAccess.reputation': 'Reputación',
    'quickAccess.publicAffairs': 'Asuntos públicos',
  },
  ca: {
    'app.name': 'Plataforma d’Intel·ligència OSINT',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'Recopilació OSINT',
    'nav.aiAnalysis': 'Anàlisi amb IA',
    'nav.qualitativeAnalysis': 'Anàlisi Qualitatiu',
    'nav.investmentRecommendations': 'Recomanacions Inversió',
    'nav.dataSynchronization': 'Sincronització de Dades',
    'nav.admin': 'Administració',
    'nav.logout': 'Tancar sessió',
    'dashboard.title': 'OSINT Intelligence Center',
    'dashboard.statusLive': 'EN VIU',
    'dashboard.description': 'Intel·ligència accionable de fonts obertes en temps real',
    'dashboard.allCases': 'Tots els casos',
    'dashboard.update': 'Actualitzar',
    'dashboard.export': 'Exportar',
    'dashboard.exportGenerating': 'Generant informe...',
    'dashboard.exportDownloading': 'Descarregant informe...',
    'dashboard.exportQueued': 'Informe en cua. Torna-ho a provar més tard.',
    'dashboard.exportError': 'Error generant informe',
    'time.24h': '24h',
    'time.7days': '7 dies',
    'time.30days': '30 dies',
    'time.90days': '90 dies',
    'metrics.totalMentions': 'Mencions totals',
    'metrics.sentimentScore': 'Sentiment Score',
    'metrics.sentimentPoints': 'pts',
    'metrics.estimatedReach': 'Abast estimat',
    'metrics.estimatedReachChange': 'abast',
    'metrics.previousPeriod': 'vs període anterior',
    'metrics.engagementRate': 'Engagement rate',
    'metrics.engagement': 'Engagement',
    'metrics.criticalAlerts': 'Alertes crítiques',
    'metrics.criticalAlertsChange': 'alertes noves',
    'metrics.trendingTopics': 'Trending topics',
    'metrics.trendingTopicsNote': 'Top temes detectats',
    'panels.dataSources': 'Fonts de dades',
    'panels.dataSourcesNoData': 'Sense dades de fonts disponibles',
    'panels.trendingTopics': 'Trending Topics',
    'panels.trendingTopicsNoData': 'Sense topics detectats',
    'panels.mentionsLabel': 'mencions',
    'panels.alerts': 'Alertes crítiques',
    'panels.alertsNoData': 'No hi ha alertes recents',
    'panels.geographic': 'Distribució geogràfica',
    'quickAccess.title': 'Accesos ràpids',
    'quickAccess.integrations': 'Integracions',
    'quickAccess.reputation': 'Reputació',
    'quickAccess.publicAffairs': 'Assumptes públics',
  },
  fr: {
    'app.name': 'Plateforme d’intelligence OSINT',
    'nav.dashboard': 'Tableau de bord',
    'nav.osintCollection': 'Collecte OSINT',
    'nav.aiAnalysis': 'Analyse IA',
    'nav.qualitativeAnalysis': 'Analyse qualitative',
    'nav.investmentRecommendations': 'Recommandations d’investissement',
    'nav.dataSynchronization': 'Synchronisation des données',
    'nav.admin': 'Administration',
    'nav.logout': 'Se déconnecter',
    'dashboard.title': 'OSINT Intelligence Center',
    'dashboard.statusLive': 'EN DIRECT',
    'dashboard.description': 'Renseignement open source exploitable en temps réel',
    'dashboard.allCases': 'Tous les cas',
    'dashboard.update': 'Actualiser',
    'dashboard.export': 'Exporter',
    'dashboard.exportGenerating': 'Génération du rapport...',
    'dashboard.exportDownloading': 'Téléchargement du rapport...',
    'dashboard.exportQueued': 'Rapport en file d’attente. Réessayez plus tard.',
    'dashboard.exportError': 'Erreur lors de la génération du rapport',
    'time.24h': '24 h',
    'time.7days': '7 jours',
    'time.30days': '30 jours',
    'time.90days': '90 jours',
    'metrics.totalMentions': 'Mentions totales',
    'metrics.sentimentScore': 'Sentiment Score',
    'metrics.sentimentPoints': 'pts',
    'metrics.estimatedReach': 'Portée estimée',
    'metrics.estimatedReachChange': 'portée',
    'metrics.previousPeriod': 'vs période précédente',
    'metrics.engagementRate': 'Engagement rate',
    'metrics.engagement': 'Engagement',
    'metrics.criticalAlerts': 'Alertes critiques',
    'metrics.criticalAlertsChange': 'nouvelles alertes',
    'metrics.trendingTopics': 'Trending topics',
    'metrics.trendingTopicsNote': 'Sujets principaux détectés',
    'panels.dataSources': 'Sources de données',
    'panels.dataSourcesNoData': 'Aucune source disponible',
    'panels.trendingTopics': 'Trending Topics',
    'panels.trendingTopicsNoData': 'Aucun sujet détecté',
    'panels.mentionsLabel': 'mentions',
    'panels.alerts': 'Alertes critiques',
    'panels.alertsNoData': 'Aucune alerte récente',
    'panels.geographic': 'Répartition géographique',
    'quickAccess.title': 'Accès rapide',
    'quickAccess.integrations': 'Intégrations',
    'quickAccess.reputation': 'Réputation',
    'quickAccess.publicAffairs': 'Affaires publiques',
  },
}

type I18nContextValue = {
  locale: SupportedLocale
  setLocale: (locale: SupportedLocale) => void
  t: (key: TranslationKeys) => string
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined)

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<SupportedLocale>(() => {
    const stored = window.localStorage.getItem('locale') as SupportedLocale | null
    if (stored && ['en', 'es', 'ca', 'fr'].includes(stored)) {
      return stored
    }
    return 'ca'
  })

  const value = useMemo<I18nContextValue>(() => ({
    locale,
    setLocale: (nextLocale) => {
      window.localStorage.setItem('locale', nextLocale)
      setLocale(nextLocale)
    },
    t: (key) => translations[locale][key] ?? key,
  }), [locale])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider')
  }
  return context
}
