import { createContext, useContext, useMemo, useState } from 'react'
import { interpolate, panelBundles, type PanelTranslationKey } from '../i18n/panelBundles'
import type { SupportedLocale, TranslateParams } from '../i18n/types'

type CoreTranslationKeys =
  | 'app.name'
  | 'nav.dashboard'
  | 'nav.osintCollection'
  | 'nav.aiAnalysis'
  | 'nav.qualitativeAnalysis'
  | 'nav.reasoningFrameworks'
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
  | 'layout.intelligenceUnit'
  | 'layout.briefing'
  | 'layout.collapseSidebar'
  | 'layout.expandSidebar'
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
  | 'nav.inquiries'
  | 'nav.intelligence'
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
  | 'inquiry.title'
  | 'inquiry.subtitle'
  | 'inquiry.refresh'
  | 'inquiry.stats.total'
  | 'inquiry.stats.completed'
  | 'inquiry.stats.awaitingGodet'
  | 'inquiry.stats.scheduler'
  | 'inquiry.stats.due'
  | 'inquiry.banner.due'
  | 'inquiry.filter.status'
  | 'inquiry.filter.all'
  | 'inquiry.filter.scheduledOnly'
  | 'inquiry.filter.search'
  | 'inquiry.filter.searchPlaceholder'
  | 'inquiry.filter.caseId'
  | 'inquiry.filter.mode'
  | 'inquiry.filter.minConfidence'
  | 'inquiry.filter.llmOnly'
  | 'inquiry.exportZip'
  | 'inquiry.exportExecutive'
  | 'inquiry.exportExecutivePdf'
  | 'inquiry.exportingExecutive'
  | 'inquiry.filter.reportLang'
  | 'inquiry.filter.scheduleInterval'
  | 'inquiry.exporting'
  | 'inquiry.rerunBatch'
  | 'inquiry.rerunning'
  | 'inquiry.rerunDue'
  | 'inquiry.confirmRerun'
  | 'inquiry.confirmRerunOne'
  | 'inquiry.batchRerunResult'
  | 'inquiry.batchScheduleResult'
  | 'inquiry.scheduleEnable'
  | 'inquiry.scheduleDisable'
  | 'inquiry.schedulerActive'
  | 'inquiry.schedulerDue'
  | 'inquiry.selectAll'
  | 'inquiry.col.case'
  | 'inquiry.col.status'
  | 'inquiry.col.prob'
  | 'inquiry.col.trend'
  | 'inquiry.col.parse'
  | 'inquiry.col.runs'
  | 'inquiry.col.scheduler'
  | 'inquiry.col.question'
  | 'inquiry.col.actions'
  | 'inquiry.action.openInquiry'
  | 'inquiry.action.rerun'
  | 'inquiry.empty'
  | 'inquiry.wizard'

export type TranslationKeys = CoreTranslationKeys | PanelTranslationKey

type Translations = Record<CoreTranslationKeys, string>

const translations: Record<SupportedLocale, Translations> = {
  en: {
    'app.name': 'OSINT Intelligence Platform',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'OSINT Collection',
    'nav.aiAnalysis': 'AI Analysis',
    'nav.qualitativeAnalysis': 'Qualitative Analysis',
    'nav.reasoningFrameworks': 'Reasoning Frameworks',
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
    'layout.intelligenceUnit': 'Intelligence Unit',
    'layout.briefing': 'Briefing',
    'layout.collapseSidebar': 'Collapse sidebar',
    'layout.expandSidebar': 'Expand sidebar',
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
    'nav.inquiries': 'Q2FS · Godet',
    'nav.intelligence': 'Intelligence Unit',
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
    'inquiry.title': 'Q2FS Inquiries',
    'inquiry.subtitle': 'Global view of analytic questions, scheduled re-runs and batch export.',
    'inquiry.refresh': 'Refresh',
    'inquiry.stats.total': 'Total',
    'inquiry.stats.completed': 'Completed',
    'inquiry.stats.awaitingGodet': 'Awaiting Godet',
    'inquiry.stats.scheduler': 'Active scheduler',
    'inquiry.stats.due': 'Pending re-runs',
    'inquiry.banner.due': 'inquiry(s) with overdue scheduled re-run — check the case Intelligence Center.',
    'inquiry.filter.status': 'Status',
    'inquiry.filter.all': 'All',
    'inquiry.filter.scheduledOnly': 'Scheduler only',
    'inquiry.filter.search': 'Search',
    'inquiry.filter.searchPlaceholder': 'Question text…',
    'inquiry.filter.caseId': 'Case ID',
    'inquiry.filter.mode': 'Mode',
    'inquiry.filter.minConfidence': 'Min. confidence',
    'inquiry.filter.llmOnly': 'LLM parse only',
    'inquiry.exportZip': 'Export ZIP',
    'inquiry.exportExecutive': 'Executive report',
    'inquiry.exportExecutivePdf': 'Executive PDF',
    'inquiry.exportingExecutive': 'Generating report…',
    'inquiry.filter.reportLang': 'Report lang',
    'inquiry.filter.scheduleInterval': 'Scheduler interval',
    'inquiry.exporting': 'Exporting…',
    'inquiry.rerunBatch': 'Re-run selected',
    'inquiry.rerunning': 'Re-running…',
    'inquiry.rerunDue': 'Re-run due',
    'inquiry.confirmRerun': 'Re-run {count} inquiry(s)? This may take several minutes.',
    'inquiry.confirmRerunOne': 'Re-run inquiry #{id}?',
    'inquiry.batchRerunResult': 'Batch re-run: {ok} OK, {failed} failed.',
    'inquiry.batchScheduleResult': 'Batch schedule: {ok} updated, {failed} failed.',
    'inquiry.scheduleEnable': 'Enable scheduler',
    'inquiry.scheduleDisable': 'Disable scheduler',
    'inquiry.schedulerActive': 'active',
    'inquiry.schedulerDue': 'due',
    'inquiry.selectAll': 'Select all',
    'inquiry.col.case': 'Case',
    'inquiry.col.status': 'Status',
    'inquiry.col.prob': 'Prob.',
    'inquiry.col.trend': 'Trend',
    'inquiry.col.parse': 'Parse',
    'inquiry.col.runs': 'Runs',
    'inquiry.col.scheduler': 'Scheduler',
    'inquiry.col.question': 'Question',
    'inquiry.col.actions': 'Actions',
    'inquiry.action.openInquiry': 'Open in Q2FS workspace',
    'inquiry.action.rerun': 'Re-run',
    'inquiry.empty': 'No inquiries yet. Create one in the Intelligence Center.',
    'inquiry.wizard': 'Wizard',
  },
  es: {
    'app.name': 'Plataforma de Inteligencia OSINT',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'Recopilación OSINT',
    'nav.aiAnalysis': 'Análisis con IA',
    'nav.qualitativeAnalysis': 'Análisis Cualitativo',
    'nav.reasoningFrameworks': 'Marcos de razonamiento',
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
    'layout.intelligenceUnit': 'Unidad de Inteligencia',
    'layout.briefing': 'Informe',
    'layout.collapseSidebar': 'Contraer barra',
    'layout.expandSidebar': 'Expandir barra',
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
    'nav.inquiries': 'Q2FS · Godet',
    'nav.intelligence': 'Unidad de Inteligencia',
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
    'inquiry.title': 'Inquiries Q2FS',
    'inquiry.subtitle': 'Vista global de preguntas analíticas, re-runs programados y exportación batch.',
    'inquiry.refresh': 'Actualizar',
    'inquiry.stats.total': 'Total',
    'inquiry.stats.completed': 'Completadas',
    'inquiry.stats.awaitingGodet': 'Esperando Godet',
    'inquiry.stats.scheduler': 'Scheduler activo',
    'inquiry.stats.due': 'Re-runs pendientes',
    'inquiry.banner.due': 'inquiry(s) con re-run programado vencido — revisa el Centro de Inteligencia del caso.',
    'inquiry.filter.status': 'Estado',
    'inquiry.filter.all': 'Todos',
    'inquiry.filter.scheduledOnly': 'Solo con scheduler',
    'inquiry.filter.search': 'Buscar',
    'inquiry.filter.searchPlaceholder': 'Texto de la pregunta…',
    'inquiry.filter.caseId': 'ID caso',
    'inquiry.filter.mode': 'Modo',
    'inquiry.filter.minConfidence': 'Conf. mínima',
    'inquiry.filter.llmOnly': 'Solo parse LLM',
    'inquiry.exportZip': 'Exportar ZIP',
    'inquiry.exportExecutive': 'Informe ejecutivo',
    'inquiry.exportExecutivePdf': 'PDF ejecutivo',
    'inquiry.exportingExecutive': 'Generando informe…',
    'inquiry.filter.reportLang': 'Idioma informe',
    'inquiry.filter.scheduleInterval': 'Intervalo scheduler',
    'inquiry.exporting': 'Exportando…',
    'inquiry.rerunBatch': 'Re-ejecutar seleccionadas',
    'inquiry.rerunning': 'Re-ejecutando…',
    'inquiry.rerunDue': 'Re-run vencidos',
    'inquiry.confirmRerun': '¿Re-ejecutar {count} inquiry(s)? Puede tardar varios minutos.',
    'inquiry.confirmRerunOne': '¿Re-ejecutar inquiry #{id}?',
    'inquiry.batchRerunResult': 'Re-run batch: {ok} OK, {failed} fallidas.',
    'inquiry.batchScheduleResult': 'Scheduler batch: {ok} actualizadas, {failed} fallidas.',
    'inquiry.scheduleEnable': 'Activar scheduler',
    'inquiry.scheduleDisable': 'Desactivar scheduler',
    'inquiry.schedulerActive': 'activo',
    'inquiry.schedulerDue': 'vencido',
    'inquiry.selectAll': 'Seleccionar todo',
    'inquiry.col.case': 'Caso',
    'inquiry.col.status': 'Estado',
    'inquiry.col.prob': 'Prob.',
    'inquiry.col.trend': 'Tendencia',
    'inquiry.col.parse': 'Parse',
    'inquiry.col.runs': 'Runs',
    'inquiry.col.scheduler': 'Scheduler',
    'inquiry.col.question': 'Pregunta',
    'inquiry.col.actions': 'Acciones',
    'inquiry.action.openInquiry': 'Abrir en Q2FS',
    'inquiry.action.rerun': 'Re-ejecutar',
    'inquiry.empty': 'Sin inquiries aún. Crea una en el Centro de Inteligencia.',
    'inquiry.wizard': 'Wizard',
  },
  ca: {
    'app.name': 'Plataforma d’Intel·ligència OSINT',
    'nav.dashboard': 'Dashboard',
    'nav.osintCollection': 'Recopilació OSINT',
    'nav.aiAnalysis': 'Anàlisi amb IA',
    'nav.qualitativeAnalysis': 'Anàlisi Qualitatiu',
    'nav.reasoningFrameworks': 'Marcs de raonament',
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
    'layout.intelligenceUnit': 'Intelligence Unit',
    'layout.briefing': 'Briefing',
    'layout.collapseSidebar': 'Replegar barra',
    'layout.expandSidebar': 'Desplegar barra',
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
    'nav.inquiries': 'Q2FS · Godet',
    'nav.intelligence': 'Intelligence Unit',
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
    'inquiry.title': 'Q2FS — Pregunta → Godet',
    'inquiry.subtitle': 'Escriu preguntes, activa prospectiva completa i gestiona informes amb plantilles EINA.',
    'inquiry.refresh': 'Actualitzar',
    'inquiry.stats.total': 'Total',
    'inquiry.stats.completed': 'Completades',
    'inquiry.stats.awaitingGodet': 'Esperant Godet',
    'inquiry.stats.scheduler': 'Scheduler actiu',
    'inquiry.stats.due': 'Re-run pendents',
    'inquiry.banner.due': 'inquiry(s) amb re-run programat vençut — revisa al Centre d\'Intel·ligència del cas.',
    'inquiry.filter.status': 'Estat',
    'inquiry.filter.all': 'Tots',
    'inquiry.filter.scheduledOnly': 'Només amb scheduler',
    'inquiry.filter.search': 'Cerca',
    'inquiry.filter.searchPlaceholder': 'Text de la pregunta…',
    'inquiry.filter.caseId': 'ID cas',
    'inquiry.filter.mode': 'Mode',
    'inquiry.filter.minConfidence': 'Conf. mínima',
    'inquiry.filter.llmOnly': 'Només parse LLM',
    'inquiry.exportZip': 'Export ZIP',
    'inquiry.exportExecutive': 'Informe executiu',
    'inquiry.exportExecutivePdf': 'PDF executiu',
    'inquiry.exportingExecutive': 'Generant informe…',
    'inquiry.filter.reportLang': 'Idioma informe',
    'inquiry.filter.scheduleInterval': 'Interval scheduler',
    'inquiry.exporting': 'Exportant…',
    'inquiry.rerunBatch': 'Re-run seleccionades',
    'inquiry.rerunning': 'Re-run en curs…',
    'inquiry.rerunDue': 'Re-run vençuts',
    'inquiry.confirmRerun': 'Re-run {count} inquiry(s)? Pot trigar diversos minuts.',
    'inquiry.confirmRerunOne': 'Re-run inquiry #{id}?',
    'inquiry.batchRerunResult': 'Re-run batch: {ok} OK, {failed} fallides.',
    'inquiry.batchScheduleResult': 'Scheduler batch: {ok} actualitzades, {failed} fallides.',
    'inquiry.scheduleEnable': 'Activar scheduler',
    'inquiry.scheduleDisable': 'Desactivar scheduler',
    'inquiry.schedulerActive': 'actiu',
    'inquiry.schedulerDue': 'vençut',
    'inquiry.selectAll': 'Seleccionar tot',
    'inquiry.col.case': 'Cas',
    'inquiry.col.status': 'Estat',
    'inquiry.col.prob': 'Prob.',
    'inquiry.col.trend': 'Tendència',
    'inquiry.col.parse': 'Parse',
    'inquiry.col.runs': 'Runs',
    'inquiry.col.scheduler': 'Scheduler',
    'inquiry.col.question': 'Pregunta',
    'inquiry.col.actions': 'Accions',
    'inquiry.action.openInquiry': 'Obrir a Q2FS',
    'inquiry.action.rerun': 'Re-run',
    'inquiry.empty': 'Cap inquiry encara. Crea-ne una al Centre d\'Intel·ligència.',
    'inquiry.wizard': 'Wizard',
  },
  fr: {
    'app.name': 'Plateforme d’intelligence OSINT',
    'nav.dashboard': 'Tableau de bord',
    'nav.osintCollection': 'Collecte OSINT',
    'nav.aiAnalysis': 'Analyse IA',
    'nav.qualitativeAnalysis': 'Analyse qualitative',
    'nav.reasoningFrameworks': 'Cadres de raisonnement',
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
    'layout.intelligenceUnit': 'Unité de renseignement',
    'layout.briefing': 'Briefing',
    'layout.collapseSidebar': 'Réduire le panneau',
    'layout.expandSidebar': 'Développer le panneau',
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
    'nav.inquiries': 'Q2FS · Godet',
    'nav.intelligence': 'Unité de renseignement',
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
    'inquiry.title': 'Inquiries Q2FS',
    'inquiry.subtitle': 'Vue globale des questions analytiques, re-runs planifiés et export batch.',
    'inquiry.refresh': 'Actualiser',
    'inquiry.stats.total': 'Total',
    'inquiry.stats.completed': 'Terminées',
    'inquiry.stats.awaitingGodet': 'En attente Godet',
    'inquiry.stats.scheduler': 'Planificateur actif',
    'inquiry.stats.due': 'Re-runs en attente',
    'inquiry.banner.due': 'inquiry(s) avec re-run planifié en retard — voir le Centre d\'intelligence du cas.',
    'inquiry.filter.status': 'Statut',
    'inquiry.filter.all': 'Tous',
    'inquiry.filter.scheduledOnly': 'Planificateur uniquement',
    'inquiry.filter.search': 'Rechercher',
    'inquiry.filter.searchPlaceholder': 'Texte de la question…',
    'inquiry.filter.caseId': 'ID dossier',
    'inquiry.filter.mode': 'Mode',
    'inquiry.filter.minConfidence': 'Conf. min.',
    'inquiry.filter.llmOnly': 'Parse LLM uniquement',
    'inquiry.exportZip': 'Export ZIP',
    'inquiry.exportExecutive': 'Rapport exécutif',
    'inquiry.exportExecutivePdf': 'PDF exécutif',
    'inquiry.exportingExecutive': 'Génération du rapport…',
    'inquiry.filter.reportLang': 'Langue rapport',
    'inquiry.filter.scheduleInterval': 'Intervalle planificateur',
    'inquiry.exporting': 'Export…',
    'inquiry.rerunBatch': 'Relancer la sélection',
    'inquiry.rerunning': 'Relance…',
    'inquiry.rerunDue': 'Relancer les échus',
    'inquiry.confirmRerun': 'Relancer {count} inquiry(s) ? Cela peut prendre plusieurs minutes.',
    'inquiry.confirmRerunOne': 'Relancer l\'inquiry #{id} ?',
    'inquiry.batchRerunResult': 'Relance batch : {ok} OK, {failed} échecs.',
    'inquiry.batchScheduleResult': 'Planificateur batch : {ok} mises à jour, {failed} échecs.',
    'inquiry.scheduleEnable': 'Activer le planificateur',
    'inquiry.scheduleDisable': 'Désactiver le planificateur',
    'inquiry.schedulerActive': 'actif',
    'inquiry.schedulerDue': 'échu',
    'inquiry.selectAll': 'Tout sélectionner',
    'inquiry.col.case': 'Dossier',
    'inquiry.col.status': 'Statut',
    'inquiry.col.prob': 'Prob.',
    'inquiry.col.trend': 'Tendance',
    'inquiry.col.parse': 'Parse',
    'inquiry.col.runs': 'Runs',
    'inquiry.col.scheduler': 'Planificateur',
    'inquiry.col.question': 'Question',
    'inquiry.col.actions': 'Actions',
    'inquiry.action.openInquiry': 'Ouvrir dans Q2FS',
    'inquiry.action.rerun': 'Relancer',
    'inquiry.empty': 'Aucune inquiry. Créez-en une dans le Centre d\'intelligence.',
    'inquiry.wizard': 'Wizard',
  },
}

type I18nContextValue = {
  locale: SupportedLocale
  setLocale: (locale: SupportedLocale) => void
  t: (key: TranslationKeys, params?: TranslateParams) => string
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
    t: (key, params) => {
      const core = translations[locale][key as CoreTranslationKeys]
      const panel = panelBundles[locale][key as PanelTranslationKey]
      const template = core ?? panel ?? key
      return interpolate(template, params)
    },
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
