import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { toActiveCase } from '../../utils/caseUtils'
import { integrationService, osintService } from '../../services/api'
import { formatApiErrorDetail } from '../../utils/apiErrors'
import CreateCaseModal from '../Dashboard/CreateCaseModal'
import ExtractionCoveragePanel from '../shared/ExtractionCoveragePanel'
import AnalysisScopeBar from '../shared/AnalysisScopeBar'
import OSINTResultView from '../shared/OSINTResultView'
import CaseOSINTInventory from '../shared/CaseOSINTInventory'
import { useCasesList } from '../../hooks/useCasesList'
import { useAnalysisScope } from '../../hooks/useAnalysisScope'
import { useCaseScopeProfile } from '../../hooks/useCaseScopeProfile'
import { scopeToOsintParams, resolveOsintSearchQuery, isGenericGeoQuery } from '../../types/analysisScope'
import './OSINTCollection.css'

interface OSINTResult {
  id?: number
  query_id?: number
  result_id?: number
  query_type: string
  status: string
  data: Record<string, unknown>
  created_at: string
  error?: string | null
}

interface SourceConfig {
  id: string
  label: string
  category: 'geopolitica' | 'notícies' | 'infraestructura'
  description: string
  requiresKey: boolean
  fields: Array<{ name: string; label: string; placeholder?: string; type?: string }>
  endpoint: string
  tavilyApi?: boolean
  buildParams: (vals: Record<string, string>, caseId: number | null) => Record<string, unknown>
}

const SOURCES: SourceConfig[] = [
  {
    id: 'gdelt',
    label: 'GDELT',
    category: 'geopolitica',
    description:
      'Events geopolítics globals en temps real. Cobreix 250+ països, 100+ idiomes. Gratuït.',
    requiresKey: false,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: China BRI Indo-Pacific' },
      { name: 'days', label: 'Dies enrere (màx. 90)', placeholder: '7', type: 'number' },
    ],
    endpoint: 'gdelt',
    buildParams: (v, caseId) => ({
      query: v.query,
      days: Math.min(parseInt(v.days || '7', 10) || 7, 90),
      case_id: caseId,
    }),
  },
  {
    id: 'gdelt_gfg',
    label: 'GDELT Portades (GFG)',
    category: 'geopolitica',
    description:
      'Importància editorial: quins enllaços destaquen a les portades de ~50.000 mitjans globals (GDELT GFG). Gratuït.',
    requiresKey: false,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: Taiwan semiconductor Japan' },
      {
        name: 'domain',
        label: 'Domini (opcional)',
        placeholder: 'Ex.: nikkei.com, reuters.com',
      },
      { name: 'max_results', label: 'Màx. resultats', placeholder: '40', type: 'number' },
    ],
    endpoint: 'gdelt-gfg',
    buildParams: (v, caseId) => ({
      query: v.query,
      domain: v.domain || undefined,
      max_results: Math.min(parseInt(v.max_results || '40', 10) || 40, 100),
      case_id: caseId,
    }),
  },
  {
    id: 'tavily',
    label: 'Tavily (cerca web)',
    category: 'geopolitica',
    description:
      'Cerca web en temps real amb IA. Descobreix fonts, snippets i enllaços rellevants. Requereix TAVILY_API_KEY.',
    requiresKey: true,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: Japan defense spending 2025' },
      { name: 'max_results', label: 'Màx. resultats', placeholder: '10', type: 'number' },
      {
        name: 'topic',
        label: 'Tema',
        placeholder: 'news',
        type: 'select',
      },
    ],
    endpoint: 'tavily',
    buildParams: (v, caseId) => ({
      query: v.query,
      max_results: Math.min(parseInt(v.max_results || '10', 10) || 10, 20),
      topic: v.topic || 'news',
      search_depth: 'advanced',
      case_id: caseId,
    }),
  },
  {
    id: 'tavily_extract',
    label: 'Tavily Extract',
    category: 'geopolitica',
    description:
      'Extreu contingut complet de URLs (markdown). Fins a 10 URLs per petició. Requereix TAVILY_API_KEY.',
    requiresKey: true,
    fields: [
      {
        name: 'urls',
        label: 'URLs (separades per comes)',
        placeholder: 'https://example.com/a, https://example.com/b',
      },
    ],
    endpoint: 'extract',
    tavilyApi: true,
    buildParams: (v, caseId) => ({
      urls: v.urls,
      extract_depth: 'advanced',
      case_id: caseId,
    }),
  },
  {
    id: 'tavily_crawl',
    label: 'Tavily Crawl',
    category: 'geopolitica',
    description:
      'Recorre un lloc web i extreu pàgines en paral·lel (graph crawl). Requereix TAVILY_API_KEY.',
    requiresKey: true,
    fields: [
      { name: 'url', label: 'URL arrel', placeholder: 'https://docs.example.com' },
      {
        name: 'instructions',
        label: 'Instruccions (opcional)',
        placeholder: 'Troba pàgines sobre el SDK Python',
      },
      { name: 'limit', label: 'Límit pàgines', placeholder: '30', type: 'number' },
    ],
    endpoint: 'crawl',
    tavilyApi: true,
    buildParams: (v, caseId) => ({
      url: v.url,
      instructions: v.instructions || undefined,
      limit: Math.min(parseInt(v.limit || '30', 10) || 30, 100),
      max_depth: 2,
      case_id: caseId,
    }),
  },
  {
    id: 'tavily_map',
    label: 'Tavily Map',
    category: 'geopolitica',
    description:
      'Descobreix totes les URLs d\'un domini (mapa del lloc). Requereix TAVILY_API_KEY.',
    requiresKey: true,
    fields: [
      { name: 'url', label: 'URL arrel', placeholder: 'https://docs.example.com' },
      {
        name: 'instructions',
        label: 'Instruccions (opcional)',
        placeholder: 'Només documentació API',
      },
      { name: 'limit', label: 'Límit URLs', placeholder: '50', type: 'number' },
    ],
    endpoint: 'map',
    tavilyApi: true,
    buildParams: (v, caseId) => ({
      url: v.url,
      instructions: v.instructions || undefined,
      limit: Math.min(parseInt(v.limit || '50', 10) || 50, 200),
      case_id: caseId,
    }),
  },
  {
    id: 'tavily_research',
    label: 'Tavily Research',
    category: 'geopolitica',
    description:
      'Recerca profunda multi-font amb informe i cites. Pot trigar 1–5 min. Requereix TAVILY_API_KEY.',
    requiresKey: true,
    fields: [
      {
        name: 'input',
        label: 'Pregunta / tema de recerca',
        placeholder: 'Quins són els últims desenvolupaments del rearmament japonès?',
      },
      {
        name: 'model',
        label: 'Model',
        placeholder: 'auto',
        type: 'select',
      },
    ],
    endpoint: 'research',
    tavilyApi: true,
    buildParams: (v, caseId) => ({
      input: v.input,
      model: v.model || 'auto',
      wait: true,
      max_wait_seconds: 300,
      case_id: caseId,
    }),
  },
  {
    id: 'bloomberg',
    label: 'Bloomberg',
    category: 'geopolitica',
    description:
      'Scraper propi via RSS oficial (feeds.bloomberg.com). Edicions: global, asia, europe, us i temes (markets, politics…). Gratuït.',
    requiresKey: false,
    fields: [
      { name: 'mode', label: 'Mode', type: 'select' },
      { name: 'edition', label: 'Edició / tema', type: 'select' },
      {
        name: 'url',
        label: 'URL Bloomberg (si mode = url)',
        placeholder: 'https://www.bloomberg.com/news/articles/...',
      },
      { name: 'max_results', label: 'Màx. articles', placeholder: '15', type: 'number' },
    ],
    endpoint: 'bloomberg',
    buildParams: (v, caseId) => {
      const mode = v.mode || 'latest'
      const base = {
        edition: v.edition || 'global',
        max_results: parseInt(v.max_results || '15', 10),
        case_id: caseId,
      }
      if (mode === 'latest') {
        return { ...base, mode: 'latest' }
      }
      return { ...base, url: v.url }
    },
  },
  {
    id: 'nikkei',
    label: 'Nikkei Asia',
    category: 'geopolitica',
    description:
      'Articles asia.nikkei.com via scraper propi (RSS + HTTP). Apify opcional (NIKKEI_PROVIDER=auto + APIFY_API_TOKEN) si el cos és curt.',
    requiresKey: false,
    fields: [
      {
        name: 'mode',
        label: 'Mode',
        placeholder: 'latest',
        type: 'select',
      },
      {
        name: 'url',
        label: 'URL Nikkei (si mode = url)',
        placeholder: 'https://asia.nikkei.com/Politics/...',
      },
      { name: 'max_results', label: 'Màx. articles', placeholder: '10', type: 'number' },
    ],
    endpoint: 'nikkei',
    buildParams: (v, caseId) => {
      const mode = v.mode || 'latest'
      if (mode === 'latest') {
        return {
          mode: 'latest',
          max_results: parseInt(v.max_results || '10', 10),
          case_id: caseId,
        }
      }
      return {
        url: v.url,
        max_results: parseInt(v.max_results || '10', 10),
        case_id: caseId,
      }
    },
  },
  {
    id: 'rss_url',
    label: 'RSS/Substack (URL curada)',
    category: 'geopolitica',
    description:
      'Butlletins Substack o feeds RSS personalitzats. Ideal per fonts curades com Tracking People\'s Daily.',
    requiresKey: false,
    fields: [
      { name: 'url', label: 'URL del feed', placeholder: 'https://example.substack.com/feed' },
      { name: 'label', label: 'Etiqueta', placeholder: 'Nom de la font' },
      { name: 'max_items', label: 'Màx. articles', placeholder: '15', type: 'number' },
    ],
    endpoint: 'rss/url',
    buildParams: (v, caseId) => ({
      url: v.url,
      label: v.label || 'custom',
      max_items: parseInt(v.max_items || '15', 10),
      case_id: caseId,
    }),
  },
  {
    id: 'rss',
    label: 'Think-tanks i governs (RSS)',
    category: 'geopolitica',
    description:
      'IISS, Chatham House, RAND, CFR, CSIS, ICG, Brookings, Elcano, Foreign Affairs, ECFR. Gratuït.',
    requiresKey: false,
    fields: [{ name: 'source', label: 'Font', placeholder: 'cfr', type: 'select' }],
    endpoint: 'rss',
    buildParams: (v, caseId) => ({ source: v.source || 'cfr', case_id: caseId }),
  },
  {
    id: 'rss_all',
    label: 'Tots els think-tanks (RSS)',
    category: 'geopolitica',
    description: 'Agrega IISS, CFR, CSIS, Brookings, Elcano i la resta en una sola consulta.',
    requiresKey: false,
    fields: [{ name: 'max_items', label: 'Màx. per font', placeholder: '10', type: 'number' }],
    endpoint: 'rss/all',
    buildParams: (v, caseId) => ({
      max_items: parseInt(v.max_items || '10', 10),
      case_id: caseId,
    }),
  },
  {
    id: 'opensanctions',
    label: 'OpenSanctions',
    category: 'geopolitica',
    description: 'Sancions de 100+ governs (OFAC, UE, ONU, OFSI). Gratuït ús no comercial.',
    requiresKey: false,
    fields: [{ name: 'query', label: 'Entitat o persona', placeholder: 'Ex.: Rosneft' }],
    endpoint: 'opensanctions',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'google_news',
    label: 'Google News',
    category: 'notícies',
    description: 'Articles de premsa en temps real via NewsAPI.',
    requiresKey: true,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: India China trade' }],
    endpoint: 'google-news',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'reddit',
    label: 'Reddit',
    category: 'notícies',
    description: 'Posts i discussions. Sense API key.',
    requiresKey: false,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: geopolitics BRI' },
      { name: 'subreddit', label: 'Subreddit', placeholder: 'worldnews (opcional)' },
    ],
    endpoint: 'reddit',
    buildParams: (v, caseId) => ({
      query: v.query,
      subreddit: v.subreddit || undefined,
      case_id: caseId,
    }),
  },
  {
    id: 'github',
    label: 'GitHub',
    category: 'infraestructura',
    description: 'Repositoris, codi i organitzacions. Útil per a actors tècnics.',
    requiresKey: false,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: chinese military AI' }],
    endpoint: 'github',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'shodan',
    label: 'Shodan',
    category: 'infraestructura',
    description: 'Dispositius i serveis exposats a Internet. Requereix SHODAN_API_KEY.',
    requiresKey: true,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: apache country:ES' }],
    endpoint: 'shodan',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'ip_geolocation',
    label: 'Geolocalització IP',
    category: 'infraestructura',
    description: 'Ubicació i dades de seguretat d\'una adreça IP via ipstack.',
    requiresKey: true,
    fields: [{ name: 'ip', label: 'Adreça IP', placeholder: 'Ex.: 8.8.8.8' }],
    endpoint: 'ip-geolocation',
    buildParams: (v, caseId) => ({ ip_address: v.ip, case_id: caseId }),
  },
  {
    id: 'dns',
    label: 'DNS Lookup',
    category: 'infraestructura',
    description: 'Resolució de noms de domini. Sense API key.',
    requiresKey: false,
    fields: [{ name: 'domain', label: 'Domini', placeholder: 'Ex.: example.com' }],
    endpoint: 'dns',
    buildParams: (v, caseId) => ({ domain: v.domain, case_id: caseId }),
  },
  {
    id: 'whois',
    label: 'WHOIS',
    category: 'infraestructura',
    description: 'Informació de registre de domini. Sense API key.',
    requiresKey: false,
    fields: [{ name: 'domain', label: 'Domini', placeholder: 'Ex.: example.com' }],
    endpoint: 'whois',
    buildParams: (v, caseId) => ({ domain: v.domain, case_id: caseId }),
  },
  {
    id: 'wayback',
    label: 'Wayback Machine',
    category: 'infraestructura',
    description: 'Historial web. Veu contingut eliminat i canvis. Gratuït.',
    requiresKey: false,
    fields: [{ name: 'url', label: 'URL', placeholder: 'https://example.com' }],
    endpoint: 'wayback',
    buildParams: (v, caseId) => ({ url: v.url, case_id: caseId }),
  },
]

const NIKKEI_MODES = [
  { value: 'latest', label: 'Darrers titulars (RSS)' },
  { value: 'url', label: 'URL concreta' },
]

const BLOOMBERG_MODES = [
  { value: 'latest', label: 'Darrers titulars (RSS)' },
  { value: 'url', label: 'URL concreta' },
]

const TAVILY_TOPICS = [
  { value: 'news', label: 'Notícies' },
  { value: 'general', label: 'General' },
  { value: 'finance', label: 'Finances' },
]

const TAVILY_MODELS = [
  { value: 'auto', label: 'Auto' },
  { value: 'mini', label: 'Mini (ràpid)' },
  { value: 'pro', label: 'Pro (profund)' },
]

const BLOOMBERG_EDITIONS = [
  { value: 'global', label: 'Global' },
  { value: 'asia', label: 'Àsia / Indo-Pacífic' },
  { value: 'europe', label: 'Europa' },
  { value: 'us', label: 'Estats Units' },
  { value: 'markets', label: 'Markets' },
  { value: 'politics', label: 'Politics' },
  { value: 'economics', label: 'Economics' },
  { value: 'technology', label: 'Technology' },
  { value: 'industries', label: 'Industries' },
  { value: 'wealth', label: 'Wealth' },
  { value: 'green', label: 'Green' },
  { value: 'opinion', label: 'Opinion' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'businessweek', label: 'Businessweek' },
]

const RSS_SOURCES = [
  { value: 'cfr', label: 'Council on Foreign Relations' },
  { value: 'iiss', label: 'IISS' },
  { value: 'chatham_house', label: 'Chatham House' },
  { value: 'rand', label: 'RAND Corporation' },
  { value: 'csis', label: 'CSIS' },
  { value: 'icg', label: 'International Crisis Group' },
  { value: 'brookings', label: 'Brookings Institution' },
  { value: 'elcano', label: 'Real Instituto Elcano' },
  { value: 'foreign_affairs', label: 'Foreign Affairs' },
  { value: 'ecfr', label: 'ECFR' },
]

const CATEGORIES = [
  { id: 'geopolitica', label: '◈ Geopolítica' },
  { id: 'notícies', label: '○ Notícies' },
  { id: 'infraestructura', label: '⊞ Infraestructura' },
] as const

export default function OSINTCollection() {
  const { activeCase, setActiveCase, clearActiveCase } = useCase()
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState<string>('geopolitica')
  const [selectedSource, setSelectedSource] = useState<string>('gdelt')
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})
  const [results, setResults] = useState<OSINTResult[]>([])
  const [resultView, setResultView] = useState<'session' | 'inventory'>('session')
  const [resultError, setResultError] = useState<string | null>(null)
  const [resultInfo, setResultInfo] = useState<string | null>(null)
  const [includeTavilyCompanion, setIncludeTavilyCompanion] = useState(true)
  const [applyScopeExtraction, setApplyScopeExtraction] = useState(false)

  const { scope, setScope, setPeriodPreset, timeRange } = useAnalysisScope(activeCase?.id ?? null)
  const { data: scopeProfile } = useCaseScopeProfile(activeCase?.id ?? null)
  const appliedScopeCaseRef = useRef<number | null>(null)
  const userEditedQueryRef = useRef(false)

  const resolvedQuery = scopeProfile ? resolveOsintSearchQuery(scopeProfile) : ''

  const { data: integrationStatus } = useQuery({
    queryKey: ['integration-status'],
    queryFn: () => integrationService.getStatus(),
  })

  const tavilyConfigured =
    integrationStatus?.osint_apis?.tavily?.configured === true ||
    integrationStatus?.osint_apis?.tavily?.status === 'configured'

  const source = SOURCES.find((s) => s.id === selectedSource) || SOURCES[0]

  useEffect(() => {
    userEditedQueryRef.current = false
    appliedScopeCaseRef.current = null
  }, [activeCase?.id])

  // Sempre substituir llistes genèriques de països
  useEffect(() => {
    if (!resolvedQuery || !activeCase?.id) return
    if (!source.fields.some((f) => f.name === 'query')) return
    if (!fieldValues.query?.trim() || !isGenericGeoQuery(fieldValues.query)) return

    setFieldValues((prev) => ({
      ...prev,
      query: resolvedQuery,
    }))
  }, [resolvedQuery, activeCase?.id, fieldValues.query, source.fields])

  // Omple la consulta des de la premissa/descripció del cas
  useEffect(() => {
    if (!resolvedQuery || !activeCase?.id) return
    if (!source.fields.some((f) => f.name === 'query')) return

    const caseChanged = appliedScopeCaseRef.current !== activeCase.id
    const shouldApply =
      caseChanged ||
      !fieldValues.query?.trim() ||
      isGenericGeoQuery(fieldValues.query) ||
      (userEditedQueryRef.current === false && fieldValues.query !== resolvedQuery)

    if (shouldApply && !userEditedQueryRef.current) {
      appliedScopeCaseRef.current = activeCase.id
      setFieldValues((prev) => ({
        ...prev,
        query: resolvedQuery,
      }))
    }
  }, [resolvedQuery, activeCase?.id, selectedSource, source.fields, fieldValues.query])

  const companionQueryText = fieldValues.query?.trim() ?? ''
  const canRunTavilyCompanion =
    includeTavilyCompanion &&
    tavilyConfigured &&
    source.id !== 'tavily' &&
    Boolean(companionQueryText) &&
    source.fields.some((f) => f.name === 'query')

  const validateFields = (): string | null => {
    if (source.id === 'nikkei') {
      const mode = fieldValues.mode || 'latest'
      if (mode === 'url' && !fieldValues.url?.trim()) {
        return 'Omple la URL de Nikkei Asia abans de cercar.'
      }
      return null
    }
    if (source.id === 'bloomberg') {
      const mode = fieldValues.mode || 'latest'
      if (mode === 'url' && !fieldValues.url?.trim()) {
        return 'Omple la URL de Bloomberg abans de cercar.'
      }
      return null
    }
    for (const field of source.fields) {
      if (field.type === 'select') continue
      if (field.name === 'domain' || field.name === 'instructions') continue
      const val = fieldValues[field.name]?.trim()
      if (!val) {
        return `Omple el camp «${field.label}» abans de cercar.`
      }
    }
    return null
  }

  const canSearch =
    source.id === 'nikkei' || source.id === 'bloomberg'
      ? (fieldValues.mode || 'latest') === 'latest' || Boolean(fieldValues.url?.trim())
      : source.fields.every((field) => {
          if (field.type === 'select') return true
          if (field.name === 'domain' || field.name === 'instructions') return true
          return Boolean(fieldValues[field.name]?.trim())
        })

  const runSearch = () => {
    if (!activeCase?.id) {
      setResultError('Selecciona un cas actiu abans de cercar — sinó les dades no entraran a l\'extracció.')
      return
    }
    const validationError = validateFields()
    if (validationError) {
      setResultError(validationError)
      return
    }
    searchMutation.mutate()
  }

  const { data: cases } = useCasesList()

  const { data: recentSearches, refetch: refetchHistory } = useQuery({
    queryKey: ['osint-recent-searches'],
    queryFn: () => osintService.getRecentSearches(8),
    staleTime: 30_000,
  })

  const appendSearchResult = (
    payload: OSINTResult,
    options?: { skipError?: boolean; appendOnly?: boolean },
  ) => {
    const inner = (payload.data ?? {}) as Record<string, unknown>
    const failed =
      payload.status === 'error' ||
      payload.status === 'failed' ||
      inner.status === 'error'

    if (failed) {
      if (options?.skipError) return false
      const raw = String(
        inner.error ?? inner.message ?? payload.data?.error ?? 'Error de la font OSINT',
      )
      const userMsg =
        raw.includes('429') || raw.toLowerCase().includes('rate limit')
          ? 'GDELT ha limitat les peticions. Espera 1-2 minuts i torna-ho a provar (màx. 90 dies).'
          : raw
      setResultError(userMsg)
      return false
    }

    if (options?.appendOnly) {
      setResults((prev) => [payload, ...prev].slice(0, 50))
      return true
    }

    setResultError(null)
    const coverage = (payload as { coverage?: { pending_extraction?: number; coverage_percent?: number } })
      .coverage
    if (coverage?.pending_extraction != null) {
      setResultInfo(
        `Recollida completada. ${coverage.pending_extraction} articles pendents d'extracció (${coverage.coverage_percent ?? 0}% cobert).`,
      )
    } else if (inner.fallback) {
      setResultInfo(
        String(
          inner.message ??
            'GDELT no disponible — resultats obtinguts via Google News RSS.',
        ),
      )
    } else {
      setResultInfo(null)
    }
    setResults((prev) => [payload, ...prev].slice(0, 50))
    return true
  }

  const normalizeApiResult = (
    raw: Record<string, unknown>,
    queryType: string,
  ): OSINTResult => ({
    query_id: raw.query_id as number | undefined,
    result_id: raw.result_id as number | undefined,
    query_type: queryType,
    status: String(raw.status ?? 'completed'),
    data: (raw.data as Record<string, unknown>) ?? {},
    created_at: new Date().toISOString(),
    error: (raw.error as string | null) ?? null,
  })

  const searchMutation = useMutation({
    mutationFn: async () => {
      setResultError(null)
      setResultInfo(null)
      const scopeParams = scopeToOsintParams(scope)
      const params = {
        ...source.buildParams(fieldValues, activeCase?.id ?? null),
        ...scopeParams,
      }
      if (scopeParams.days != null && (source.id === 'gdelt' || !fieldValues.days)) {
        params.days = scopeParams.days
      }
      const primary = normalizeApiResult(
        (await osintService.search(source.endpoint, params, {
          tavilyApi: source.tavilyApi,
        })) as Record<string, unknown>,
        source.id,
      )

      if (!canRunTavilyCompanion) {
        return { primary, companion: null as OSINTResult | null }
      }

      try {
        const companion = normalizeApiResult(
          (await osintService.tavily(
            companionQueryText,
            Math.min(parseInt(fieldValues.max_results || '10', 10) || 10, 20),
            'advanced',
            'news',
            activeCase?.id ?? undefined,
            scopeToOsintParams(scope),
          )) as Record<string, unknown>,
          'tavily',
        )
        return { primary, companion }
      } catch {
        return { primary, companion: null }
      }
    },
    onSuccess: ({ primary, companion }) => {
      const primaryOk = appendSearchResult(primary)
      if (!primaryOk) return

      let infoExtra: string | undefined
      if (companion) {
        const companionOk = appendSearchResult(companion, { skipError: true, appendOnly: true })
        if (companionOk) {
          const inner = (companion.data ?? {}) as Record<string, unknown>
          const n =
            typeof inner.count === 'number'
              ? inner.count
              : Array.isArray(inner.articles)
                ? inner.articles.length
                : 0
          infoExtra = `Tavily ha afegit ${n} resultats web complementaris al cas.`
        }
      }

      if (infoExtra) {
        setResultInfo((prev) => (prev ? `${prev} ${infoExtra}` : infoExtra))
      }

      refetchHistory()
      if (activeCase?.id) {
        void queryClient.invalidateQueries({ queryKey: ['extraction-coverage', activeCase.id] })
      }
    },
    onError: (err: unknown) => {
      const axiosErr = err as {
        response?: { data?: { detail?: unknown }; status?: number }
        message?: string
      }
      const raw = formatApiErrorDetail(
        axiosErr?.response?.data?.detail ?? axiosErr?.message,
        'Error inesperat. Revisa la consola per a més detalls.',
      )

      const userMsg =
        axiosErr?.response?.status === 422
          ? raw.includes('query') || raw.includes('Field required')
            ? 'Omple tots els camps obligatoris abans de cercar.'
            : raw
          : raw.includes('timeout') || raw.includes('TIMEOUT')
          ? 'La font OSINT no ha respost a temps. Torna a intentar-ho en uns segons.'
          : raw.includes('429') || raw.includes('rate')
          ? 'La font OSINT ha limitat les peticions. Espera 1 minut i torna a intentar-ho.'
          : raw.includes('403') || raw.includes('Forbidden')
          ? 'Accés denegat a la font OSINT. Comprova la configuració de la clau API.'
          : raw.includes('404') || raw.includes('Not Found')
          ? 'La font OSINT no ha trobat resultats per a aquesta cerca.'
          : raw.includes('Network') || raw.includes('ECONNREFUSED')
          ? 'Error de connexió. Comprova que el servidor backend és accessible.'
          : raw

      setResultError(userMsg)
    },
  })

  const sourcesInCategory = SOURCES.filter((s) => s.category === selectedCategory)

  return (
    <div className="osint-layout">
      <aside className="osint-sidebar">
        <div className="osint-case-selector">
          <label className="osint-field-label">Cas actiu</label>
          <select
            className="osint-select"
            value={activeCase?.id ?? ''}
            onChange={(e) => {
              const value = e.target.value
              if (!value) {
                clearActiveCase()
                return
              }
              const id = Number(value)
              const c = cases?.find((x) => x.id === id)
              if (c) {
                setActiveCase(toActiveCase(c))
              }
            }}
          >
            <option value="">— Sense cas —</option>
            {(cases ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>
          {!activeCase && (
            <p className="osint-case-hint">
              Crea un cas nou o selecciona&apos;n un per associar les cerques OSINT.
            </p>
          )}
          <CreateCaseModal className="btn-create-case-osint" />
          {activeCase && (
            <div className="osint-case-badge">
              Cas: <strong>{activeCase.name}</strong>
            </div>
          )}
          {activeCase?.id ? (
            <>
              <label className="osint-scope-extract-opt">
                <input
                  type="checkbox"
                  checked={applyScopeExtraction}
                  onChange={(e) => setApplyScopeExtraction(e.target.checked)}
                />
                Aplicar delimitació (dates, dominis, temàtica) a l&apos;extracció de pendents
              </label>
              <ExtractionCoveragePanel
                caseId={activeCase.id}
                compact
                showRepairOrphans
                scope={scope}
                applyScopeToExtraction={applyScopeExtraction}
              />
            </>
          ) : null}
          {activeCase?.id ? (
            <AnalysisScopeBar
              scope={scope}
              onChange={(patch) => setScope(patch)}
              onPeriodPreset={setPeriodPreset}
              focusLabel={scopeProfile?.focus_label}
              suggestedQuery={scopeProfile?.suggested_query}
              suggestedQueries={scopeProfile?.suggested_queries}
              themes={scopeProfile?.themes}
              analyticalProfile={scopeProfile?.analytical_profile}
              compact
            />
          ) : null}
        </div>

        <div className="osint-categories">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`osint-category-btn ${selectedCategory === cat.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedCategory(cat.id)
                const first = SOURCES.find((s) => s.category === cat.id)
                if (first) {
                  setSelectedSource(first.id)
                  setFieldValues({})
                }
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="osint-source-list">
          {sourcesInCategory.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`osint-source-btn ${selectedSource === s.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedSource(s.id)
                setFieldValues({})
              }}
            >
              <span className="osint-source-name">{s.label}</span>
              {s.requiresKey && <span className="osint-key-badge">clau API</span>}
            </button>
          ))}
        </div>
      </aside>

      <main className="osint-main">
        <div className="card osint-form-card">
          <h2 className="osint-source-title">{source.label}</h2>
          <p className="osint-source-desc">{source.description}</p>

          {scopeProfile && source.fields.some((f) => f.name === 'query') && (
            <div className="osint-case-concepts">
              <span className="osint-case-concepts__label">Conceptes del cas:</span>
              {scopeProfile.themes?.length ? (
                <span className="osint-case-concepts__chip">
                  {scopeProfile.themes.join(', ')}
                </span>
              ) : null}
              {scopeProfile.primary_geos?.slice(0, 4).map((g) => (
                <span key={g} className="osint-case-concepts__chip osint-case-concepts__chip--geo">
                  {g}
                </span>
              ))}
              {resolvedQuery && (
                <button
                  type="button"
                  className="btn btn-sm osint-case-concepts__apply"
                  onClick={() => {
                    userEditedQueryRef.current = false
                    setFieldValues((prev) => ({
                      ...prev,
                      query: resolvedQuery,
                    }))
                  }}
                >
                  Aplicar: {resolvedQuery}
                </button>
              )}
            </div>
          )}

          <div className="osint-fields">
            {source.fields.map((field) => (
              <div key={field.name} className="osint-field">
                <label className="osint-field-label" htmlFor={`field-${field.name}`}>
                  {field.label}
                </label>
                {field.type === 'select' && field.name === 'source' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'cfr'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {RSS_SOURCES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'select' && field.name === 'mode' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'latest'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {(source.id === 'bloomberg' ? BLOOMBERG_MODES : NIKKEI_MODES).map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'select' && field.name === 'edition' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'global'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {BLOOMBERG_EDITIONS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'select' && field.name === 'topic' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'news'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {TAVILY_TOPICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'select' && field.name === 'model' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'auto'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {TAVILY_MODELS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`field-${field.name}`}
                    className="osint-input"
                    type={field.type || 'text'}
                    placeholder={field.placeholder}
                    value={fieldValues[field.name] ?? ''}
                    onChange={(e) => {
                      if (field.name === 'query') userEditedQueryRef.current = true
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') runSearch()
                    }}
                  />
                )}
              </div>
            ))}
          </div>

          {source.fields.some((f) => f.name === 'query') && source.id !== 'tavily' && (
            <label className="osint-tavily-companion">
              <input
                type="checkbox"
                checked={includeTavilyCompanion}
                disabled={!tavilyConfigured}
                onChange={(e) => setIncludeTavilyCompanion(e.target.checked)}
              />
              <span>
                També cercar amb Tavily (web en temps real)
                {!tavilyConfigured && (
                  <span className="osint-tavily-companion-hint">
                    {' '}
                    — configura TAVILY_API_KEY al backend
                  </span>
                )}
              </span>
            </label>
          )}

          <div className="osint-form-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={searchMutation.isPending || !canSearch}
              onClick={runSearch}
            >
              {searchMutation.isPending ? 'Cercant...' : `Cercar amb ${source.label}`}
            </button>
            {results.length > 0 && (
              <button type="button" className="btn" onClick={() => setResults([])}>
                Netejar resultats
              </button>
            )}
          </div>

          {resultError && <div className="osint-alert osint-alert--error">{resultError}</div>}
          {resultInfo && !resultError && (
            <div className="osint-alert osint-alert--info">{resultInfo}</div>
          )}
        </div>

        {activeCase?.id ? (
          <div className="osint-view-tabs">
            <button
              type="button"
              className={resultView === 'session' ? 'active' : ''}
              onClick={() => setResultView('session')}
            >
              Última sessió
            </button>
            <button
              type="button"
              className={resultView === 'inventory' ? 'active' : ''}
              onClick={() => setResultView('inventory')}
            >
              Inventari del cas
            </button>
          </div>
        ) : null}

        {resultView === 'inventory' && activeCase?.id ? (
          <CaseOSINTInventory caseId={activeCase.id} />
        ) : null}

        {resultView === 'session' && results.length > 0 && (
          <div className="osint-results">
            <h3 className="osint-results-title">
              {results.length} resultat{results.length !== 1 ? 's' : ''} (sessió actual)
            </h3>
            {results.map((r, i) => (
              <div key={i} className="card osint-result-card">
                <OSINTResultView
                  data={r.data}
                  queryType={r.query_type}
                  status={r.status}
                  createdAt={r.created_at}
                  resultId={r.result_id}
                />
              </div>
            ))}
          </div>
        )}

        {resultView === 'session' && results.length === 0 && !searchMutation.isPending && (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">◎</div>
              <h3 className="empty-state-title">Cap resultat encara</h3>
              <p className="empty-state-desc">
                Selecciona una font OSINT, omple els camps i executa la cerca.
              </p>
            </div>
          </div>
        )}

        {Array.isArray(recentSearches) && recentSearches.length > 0 && (
          <div className="card osint-history-card">
            <h3 className="osint-history-title">Cerques recents</h3>
            <ul className="osint-history-list">
              {(recentSearches as Array<{
                id: number
                query_type: string
                query_text: string
                created_at: string
                status?: string
              }>).map((q) => (
                <li key={q.id} className="osint-history-item">
                  <span className="status-badge neutral osint-history-type">{q.query_type}</span>
                  <span className="osint-history-text">{q.query_text || '—'}</span>
                  <span className="osint-history-date">
                    {q.created_at
                      ? new Date(q.created_at).toLocaleDateString('ca-ES', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  )
}
