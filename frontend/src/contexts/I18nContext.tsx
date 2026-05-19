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
  | 'metrics.triggeredMonitors'
  | 'metrics.triggeredMonitorsNote'
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
  | 'layout.subtitle'
  | 'layout.activeCase'
  | 'layout.noCase'
  | 'layout.logout'
  | 'nav.group.recollida'
  | 'nav.group.analisi'
  | 'nav.group.resultats'
  | 'nav.group.complementaries'
  | 'nav.group.sistema'
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
  | 'nav.alerts'
  | 'nav.alertMonitors'
  | 'nav.alertMonitorsTriggered'
  | 'nav.exportReport'
  | 'nav.reputation'
  | 'nav.publicAffairs'
  | 'alerts.title'
  | 'alerts.noProject'
  | 'alerts.noMonitors'
  | 'alerts.checkNow'
  | 'alerts.activate'
  | 'alerts.deactivate'
  | 'alerts.indicator'
  | 'alerts.keywords'
  | 'alerts.sources'
  | 'alerts.lastCheck'
  | 'alerts.lastMatch'
  | 'alerts.matches'
  | 'alerts.triggered'
  | 'alerts.monitoring'
  | 'alerts.selectProject'

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
    'metrics.triggeredMonitors': 'Triggered monitors',
    'metrics.triggeredMonitorsNote': 'OSINT matches pending review',
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
    'layout.subtitle': 'Strategic Intelligence',
    'layout.activeCase': 'Active case',
    'layout.noCase': 'No case selected',
    'layout.logout': 'Log Out',
    'nav.group.recollida': 'Collection',
    'nav.group.analisi': 'Godet prospective',
    'nav.group.resultats': 'Results',
    'nav.group.complementaries': 'Complementary tools',
    'nav.group.sistema': 'System',
    'nav.osintSources': 'OSINT Sources',
    'nav.directAnalysis': 'Direct Analysis',
    'nav.extraction': '0. Structured extraction',
    'nav.project': '1. Project',
    'nav.retrospective': '1.5 Retrospective',
    'nav.variables': '2. Variables',
    'nav.micmac': '3. MIC-MAC',
    'nav.actors': '4. Actors',
    'nav.mactor': '5. MACTOR',
    'nav.morph': '6. Morphological',
    'nav.scenarios': '7. Scenarios & export',
    'nav.reputation': 'Reputation',
    'nav.publicAffairs': 'Public affairs',
    'nav.alerts': 'Active alerts',
    'nav.alertMonitors': 'Alert Monitors',
    'nav.alertMonitorsTriggered': 'Monitors with OSINT matches',
    'nav.exportReport': 'Export report',
    'alerts.title': 'Active Alert Monitors',
    'alerts.noProject': 'Select a prospective project to see its monitors.',
    'alerts.noMonitors': 'No monitors yet. Generate scenarios and activate monitoring from the Scenarios step.',
    'alerts.checkNow': 'Check now',
    'alerts.activate': 'Activate',
    'alerts.deactivate': 'Pause',
    'alerts.indicator': 'Indicator',
    'alerts.keywords': 'Keywords',
    'alerts.sources': 'Sources',
    'alerts.lastCheck': 'Last check',
    'alerts.lastMatch': 'Last match',
    'alerts.matches': 'Matches',
    'alerts.triggered': 'Triggered',
    'alerts.monitoring': 'Monitoring',
    'alerts.selectProject': 'Select project',
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
    'metrics.triggeredMonitors': 'Monitores disparados',
    'metrics.triggeredMonitorsNote': 'Coincidencias OSINT pendientes',
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
    'layout.subtitle': 'Inteligencia Estratégica',
    'layout.activeCase': 'Caso activo',
    'layout.noCase': 'Ningún caso seleccionado',
    'layout.logout': 'Cerrar sesión',
    'nav.group.recollida': 'Recopilación',
    'nav.group.analisi': 'Prospectiva Godet',
    'nav.group.resultats': 'Resultados',
    'nav.group.complementaries': 'Herramientas complementarias',
    'nav.group.sistema': 'Sistema',
    'nav.osintSources': 'Fuentes OSINT',
    'nav.directAnalysis': 'Análisis directo',
    'nav.extraction': '0. Extracción estructurada',
    'nav.project': '1. Proyecto',
    'nav.retrospective': '1.5 Retrospectiva',
    'nav.variables': '2. Variables',
    'nav.micmac': '3. MIC-MAC',
    'nav.actors': '4. Actores',
    'nav.mactor': '5. MACTOR',
    'nav.morph': '6. Morfológico',
    'nav.scenarios': '7. Escenarios y exportación',
    'nav.reputation': 'Reputación',
    'nav.publicAffairs': 'Asuntos públicos',
    'nav.alerts': 'Alertas activas',
    'nav.alertMonitors': 'Monitores de alerta',
    'nav.alertMonitorsTriggered': 'Monitores con coincidencias OSINT',
    'nav.exportReport': 'Exportar informe',
    'alerts.title': 'Monitores de alerta activos',
    'alerts.noProject': 'Selecciona un proyecto prospectivo para ver sus monitores.',
    'alerts.noMonitors': 'Sin monitores todavía. Genera escenarios y activa el monitoreo desde el paso Escenarios.',
    'alerts.checkNow': 'Comprobar ahora',
    'alerts.activate': 'Activar',
    'alerts.deactivate': 'Pausar',
    'alerts.indicator': 'Indicador',
    'alerts.keywords': 'Palabras clave',
    'alerts.sources': 'Fuentes',
    'alerts.lastCheck': 'Última comprobación',
    'alerts.lastMatch': 'Última coincidencia',
    'alerts.matches': 'Coincidencias',
    'alerts.triggered': 'Disparado',
    'alerts.monitoring': 'Monitorizando',
    'alerts.selectProject': 'Seleccionar proyecto',
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
    'metrics.triggeredMonitors': 'Monitors disparats',
    'metrics.triggeredMonitorsNote': 'Coincidències OSINT pendents de revisió',
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
    'layout.subtitle': 'Intel·ligència Estratègica',
    'layout.activeCase': 'Cas actiu',
    'layout.noCase': 'Cap cas seleccionat',
    'layout.logout': 'Tancar sessió',
    'nav.group.recollida': 'Recollida',
    'nav.group.analisi': 'Prospectiva Godet',
    'nav.group.resultats': 'Resultats',
    'nav.group.complementaries': 'Eines complementàries',
    'nav.group.sistema': 'Sistema',
    'nav.osintSources': 'Fonts OSINT',
    'nav.directAnalysis': 'Anàlisi directa',
    'nav.extraction': '0. Extracció estructurada',
    'nav.project': '1. Projecte',
    'nav.retrospective': '1.5 Retrospectiva',
    'nav.variables': '2. Variables',
    'nav.micmac': '3. MIC-MAC',
    'nav.actors': '4. Actors',
    'nav.mactor': '5. MACTOR',
    'nav.morph': '6. Morfològic',
    'nav.scenarios': '7. Escenaris i exportació',
    'nav.reputation': 'Reputació',
    'nav.publicAffairs': 'Assumptes públics',
    'nav.alerts': 'Alertes actives',
    'nav.alertMonitors': 'Monitors d\'alerta',
    'nav.alertMonitorsTriggered': 'Monitors amb coincidències OSINT',
    'nav.exportReport': 'Exportar informe',
    'alerts.title': 'Monitors d\'alerta actius',
    'alerts.noProject': 'Selecciona un projecte prospectiu per veure els seus monitors.',
    'alerts.noMonitors': 'Sense monitors encara. Genera escenaris i activa el monitoratge des del pas Escenaris.',
    'alerts.checkNow': 'Comprovar ara',
    'alerts.activate': 'Activar',
    'alerts.deactivate': 'Pausar',
    'alerts.indicator': 'Indicador',
    'alerts.keywords': 'Paraules clau',
    'alerts.sources': 'Fonts',
    'alerts.lastCheck': 'Última comprovació',
    'alerts.lastMatch': 'Última coincidència',
    'alerts.matches': 'Coincidències',
    'alerts.triggered': 'Disparat',
    'alerts.monitoring': 'Monitoritzant',
    'alerts.selectProject': 'Selecciona projecte',
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
    'metrics.triggeredMonitors': 'Moniteurs déclenchés',
    'metrics.triggeredMonitorsNote': 'Correspondances OSINT à examiner',
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
    'layout.subtitle': 'Intelligence stratégique',
    'layout.activeCase': 'Cas actif',
    'layout.noCase': 'Aucun cas sélectionné',
    'layout.logout': 'Se déconnecter',
    'nav.group.recollida': 'Collecte',
    'nav.group.analisi': 'Prospective Godet',
    'nav.group.resultats': 'Résultats',
    'nav.group.complementaries': 'Outils complémentaires',
    'nav.group.sistema': 'Système',
    'nav.osintSources': 'Sources OSINT',
    'nav.directAnalysis': 'Analyse directe',
    'nav.extraction': '0. Extraction structurée',
    'nav.project': '1. Projet',
    'nav.retrospective': '1.5 Rétrospective',
    'nav.variables': '2. Variables',
    'nav.micmac': '3. MIC-MAC',
    'nav.actors': '4. Acteurs',
    'nav.mactor': '5. MACTOR',
    'nav.morph': '6. Morphologique',
    'nav.scenarios': '7. Scénarios et export',
    'nav.reputation': 'Réputation',
    'nav.publicAffairs': 'Affaires publiques',
    'nav.alerts': 'Alertes actives',
    'nav.alertMonitors': 'Moniteurs d\'alerte',
    'nav.alertMonitorsTriggered': 'Moniteurs avec correspondances OSINT',
    'nav.exportReport': 'Exporter le rapport',
    'alerts.title': 'Moniteurs d\'alerte actifs',
    'alerts.noProject': 'Sélectionnez un projet prospectif pour voir ses moniteurs.',
    'alerts.noMonitors': 'Pas encore de moniteurs. Générez des scénarios et activez la surveillance depuis l\'étape Scénarios.',
    'alerts.checkNow': 'Vérifier maintenant',
    'alerts.activate': 'Activer',
    'alerts.deactivate': 'Mettre en pause',
    'alerts.indicator': 'Indicateur',
    'alerts.keywords': 'Mots-clés',
    'alerts.sources': 'Sources',
    'alerts.lastCheck': 'Dernière vérification',
    'alerts.lastMatch': 'Dernière correspondance',
    'alerts.matches': 'Correspondances',
    'alerts.triggered': 'Déclenché',
    'alerts.monitoring': 'Surveillance',
    'alerts.selectProject': 'Sélectionner projet',
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
