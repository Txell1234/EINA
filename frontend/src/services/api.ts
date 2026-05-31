import axios from 'axios'
import { notifySessionExpired } from '../utils/authEvents'
import { scopeToExtractQuery, type AnalysisScope } from '../types/analysisScope'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? '' : 'http://localhost:8000')

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 segundos timeout global (aumentado para operaciones largas)
})

/** Append JWT for EventSource/SSE (cannot set Authorization header). */
export function sseUrl(path: string): string {
  const token = localStorage.getItem('token')
  if (!token) return path
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}access_token=${encodeURIComponent(token)}`
}

// Interceptor per mostrar errors de connexió
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('⏱️ Timeout: El servidor no respon a temps')
    } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
      console.error('🔌 Error de connexió: No es pot connectar al servidor backend')
      console.error('   Assegura\'t que el backend està executant-se a http://localhost:8000')
    } else if (error.response) {
      const requestUrl = error.config?.url ?? ''
      const isAuthRoute =
        requestUrl.includes('/api/auth/login') || requestUrl.includes('/api/auth/register')

      // JWT expired or invalid → clear session and redirect (not on login/register failures)
      if (error.response?.status === 401 && !isAuthRoute) {
        const currentPath = window.location.pathname
        if (currentPath !== '/login' && currentPath !== '/register') {
          notifySessionExpired()
          setTimeout(() => {
            if (window.location.pathname !== '/login') {
              window.location.href = '/login'
            }
          }, 100)
        }
      }
      if (!isAuthRoute) {
        console.error(`❌ Error del servidor: ${error.response.status} - ${error.response.statusText}`)
      }
    } else {
      console.error('❌ Error desconegut:', error.message)
    }
    return Promise.reject(error)
  }
)

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authService = {
  login: async (email: string, password: string) => {
    const response = await api.post('/api/auth/login', {
      email,
      password,
    }, {
      timeout: 10000, // 10 segundos timeout
    })
    return response.data
  },
  register: async (email: string, password: string, fullName: string) => {
    const response = await api.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    return response.data
  },
}

export const casesService = {
  list: async (params?: any) => {
    const response = await api.get('/api/cases/', { params })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get(`/api/cases/${id}`)
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/api/cases/', data)
    return response.data
  },
  createFromPrompt: async (data: {
    prompt: string
    creation_mode?: 'guided' | 'manual'
    name?: string
    case_type?: string
  }) => {
    const response = await api.post('/api/cases/from-prompt', data, {
      timeout: 15000,
    })
    return response.data
  },
  testConnection: async () => {
    const response = await api.get('/api/cases/test-connection', {
      timeout: 5000, // 5 segundos para test
    })
    return response.data
  },
  analyze: async (id: number) => {
    const response = await api.post(`/api/cases/${id}/analyze`)
    return response.data
  },
  getMetrics: async () => {
    const response = await api.get('/api/cases/metrics')
    return response.data
  },
  update: async (id: number, data: any) => {
    const response = await api.put(`/api/cases/${id}`, data)
    return response.data
  },
  rerun: async (id: number) => {
    const response = await api.post(`/api/cases/${id}/rerun`)
    return response.data
  },
  getContext: async (id: number) => {
    const response = await api.get(`/api/cases/${id}/context`)
    return response.data as {
      case_id: number
      name: string
      case_type: string
      description: string
      latest_prompt: string
    }
  },
  getIntsum: async (id: number, days = 7) => {
    const response = await api.get(`/api/cases/${id}/intsum`, { params: { days } })
    return response.data as {
      case_id: number
      found?: boolean
      case_name?: string
      days: number
      has_activity?: boolean
      period_start?: string
      period_end?: string
      summary: {
        alert_matches: number
        new_statements: number
        posture_highlights: number
        milestone_count: number
        alerts_shown?: number
        statements_shown?: number
        alerts_fallback?: boolean
        statements_fallback?: boolean
      }
      alerts: Array<{ id: number; title: string; monitor: string; url?: string; first_seen_at?: string }>
      statements: Array<{
        id: number
        actor: string
        statement: string
        posture_value?: number
        topic?: string
        signal_type?: string | null
        extracted_at?: string | null
      }>
      posture_highlights: Array<{
        actor: string
        avg_posture: number
        statement_count: number
        highlight_type?: 'posture' | 'top_activity'
      }>
      signal_breakdown?: Record<string, number>
    }
  },
  getScopeProfile: async (id: number) => {
    const response = await api.get(`/api/cases/${id}/scope-profile`)
    return response.data as import('../types/analysisScope').CaseScopeProfile
  },
}

export const visualizationsService = {
  networkGraph: async (caseId: number) => {
    const response = await api.get(`/api/visualizations/network/${caseId}`)
    return response.data
  },
  trendAnalysis: async (caseId: number, days = 30) => {
    const response = await api.get(`/api/visualizations/trends/${caseId}`, {
      params: { days }
    })
    return response.data
  },
  trendDetails: async (caseId: number) => {
    const response = await api.get(`/api/visualizations/trends/${caseId}/details`)
    return response.data
  },
  relationshipMap: async (caseId: number) => {
    const response = await api.get(`/api/visualizations/relationships/${caseId}`)
    return response.data
  },
  configureTrendAnalysis: async (caseId: number, kpiIds: number[]) => {
    const response = await api.post(`/api/visualizations/trends/${caseId}/configure`, { kpi_ids: kpiIds })
    return response.data
  },
}

export const researchService = {
  generatePlan: async (caseId: number, osintOnly = false) => {
    const response = await api.post(`/api/research/plan/${caseId}`, null, {
      params: { osint_only: osintOnly },
    })
    return response.data
  },
  getPlan: async (caseId: number) => {
    const response = await api.get(`/api/research/plan/${caseId}`)
    return response.data
  },
  approvePlan: async (caseId: number, plan: any) => {
    const response = await api.post(`/api/research/plan/${caseId}/approve`, plan)
    return response.data
  },
  getStatus: async (caseId: number) => {
    const response = await api.get(`/api/research/status/${caseId}`)
    return response.data
  },
  clearPlan: async (caseId: number) => {
    const response = await api.delete(`/api/research/plan/${caseId}`)
    return response.data
  },
}

export const heatmapService = {
  getPosts: async (caseId: number, granularity = 'city', platform?: string, timeRange?: { start: string; end: string }) => {
    const params = new URLSearchParams({ granularity })
    if (platform) params.append('platform', platform)
    if (timeRange?.start) params.append('start_date', timeRange.start)
    if (timeRange?.end) params.append('end_date', timeRange.end)
    const response = await api.get(`/api/heatmap/${caseId}/posts?${params.toString()}`)
    return response.data
  },
  getSentiment: async (caseId: number, granularity = 'city', platform?: string, timeRange?: { start: string; end: string }) => {
    const params = new URLSearchParams({ granularity })
    if (platform) params.append('platform', platform)
    if (timeRange?.start) params.append('start_date', timeRange.start)
    if (timeRange?.end) params.append('end_date', timeRange.end)
    const response = await api.get(`/api/heatmap/${caseId}/sentiment?${params.toString()}`)
    return response.data
  },
  getEngagement: async (caseId: number, granularity = 'city', platform?: string, timeRange?: { start: string; end: string }) => {
    const params = new URLSearchParams({ granularity })
    if (platform) params.append('platform', platform)
    if (timeRange?.start) params.append('start_date', timeRange.start)
    if (timeRange?.end) params.append('end_date', timeRange.end)
    const response = await api.get(`/api/heatmap/${caseId}/engagement?${params.toString()}`)
    return response.data
  },
  getCustom: async (caseId: number, metric: string, granularity = 'city', platform?: string, timeRange?: { start: string; end: string }) => {
    const params = new URLSearchParams({ metric, granularity })
    if (platform) params.append('platform', platform)
    if (timeRange?.start) params.append('start_date', timeRange.start)
    if (timeRange?.end) params.append('end_date', timeRange.end)
    const response = await api.get(`/api/heatmap/${caseId}/custom?${params.toString()}`)
    return response.data
  },
  getDashboardSummary: async (granularity = 'country') => {
    const params = new URLSearchParams({ granularity })
    const response = await api.get(`/api/heatmap/dashboard/summary?${params.toString()}`)
    return response.data
  },
}

export const integrationService = {
  getStatus: async () => {
    const response = await api.get('/api/integration/status')
    return response.data
  },
}

const OSINT_COLLECT_QUERY_TYPES: Record<string, string> = {
  gdelt: 'gdelt',
  'gdelt-gfg': 'gdelt_gfg',
  tavily: 'tavily',
  extract: 'tavily_extract',
  crawl: 'tavily_crawl',
  map: 'tavily_map',
  research: 'tavily_research',
  bloomberg: 'bloomberg',
  nikkei: 'nikkei',
  'rss/url': 'rss_url',
  rss: 'rss_feed',
  'rss/all': 'rss_all',
  opensanctions: 'opensanctions',
  'google-news': 'google_news',
  reddit: 'reddit',
  github: 'github',
  shodan: 'shodan',
  'ip-geolocation': 'ip_geolocation',
  dns: 'dns',
  whois: 'whois',
  wayback: 'wayback',
}

export const osintService = {
  googleNews: async (query: string, language = 'es', caseId?: number) => {
    const response = await api.post('/api/osint/google-news', null, {
      params: { query, language, case_id: caseId },
    })
    return response.data
  },
  reddit: async (query: string, subreddit?: string, caseId?: number) => {
    const response = await api.post('/api/osint/reddit', null, {
      params: { query, subreddit, case_id: caseId },
    })
    return response.data
  },
  github: async (query: string, type = 'repositories', caseId?: number) => {
    const response = await api.post('/api/osint/github', null, {
      params: { query, type, case_id: caseId },
    })
    return response.data
  },
  shodan: async (query: string, facets?: string, page = 1, caseId?: number) => {
    const response = await api.post('/api/osint/shodan', null, {
      params: { query, facets, page, case_id: caseId },
    })
    return response.data
  },
  wayback: async (url: string, caseId?: number) => {
    const response = await api.post('/api/osint/wayback', null, {
      params: { url, case_id: caseId },
    })
    return response.data
  },
  dnsLookup: async (domain: string, caseId?: number) => {
    const response = await api.post('/api/osint/dns', null, {
      params: { domain, case_id: caseId },
    })
    return response.data
  },
  whois: async (domain: string, caseId?: number) => {
    const response = await api.post('/api/osint/whois', null, {
      params: { domain, case_id: caseId },
    })
    return response.data
  },
  gdelt: async (query: string, days = 7, maxResults = 50, caseId?: number) => {
    const response = await api.post('/api/osint/gdelt', null, {
      params: { query, days, max_results: maxResults, case_id: caseId },
    })
    return response.data
  },
  gdeltGfg: async (
    query: string,
    maxResults = 40,
    domain?: string,
    caseId?: number,
  ) => {
    const response = await api.post('/api/osint/gdelt-gfg', null, {
      params: {
        query,
        max_results: maxResults,
        domain: domain || undefined,
        case_id: caseId,
      },
      timeout: 180_000,
    })
    return response.data
  },
  tavily: async (
    query: string,
    maxResults = 10,
    searchDepth = 'advanced',
    topic = 'news',
    caseId?: number,
    extraParams?: Record<string, unknown>,
  ) => {
    const query_params = {
      query,
      max_results: maxResults,
      search_depth: searchDepth,
      topic,
      ...extraParams,
    }
    const response = await api.post(
      '/api/osint/collect',
      { query_type: 'tavily', query_params, case_id: caseId ?? null },
      { timeout: 120_000 },
    )
    return response.data
  },
  nikkei: async (
    opts: { url?: string; mode?: string; maxResults?: number; caseId?: number },
  ) => {
    const response = await api.post('/api/osint/nikkei', null, {
      params: {
        url: opts.url,
        mode: opts.mode,
        max_results: opts.maxResults ?? 10,
        case_id: opts.caseId,
      },
      timeout: 150_000,
    })
    return response.data
  },
  rssFeed: async (source: string, maxItems = 20, caseId?: number) => {
    const response = await api.post('/api/osint/rss', null, {
      params: { source, max_items: maxItems, case_id: caseId },
    })
    return response.data
  },
  rssAll: async (maxItems = 10, caseId?: number) => {
    const response = await api.post('/api/osint/rss/all', null, {
      params: { max_items: maxItems, case_id: caseId },
    })
    return response.data
  },
  openSanctions: async (query: string, caseId?: number) => {
    const response = await api.post('/api/osint/opensanctions', null, {
      params: { query, case_id: caseId },
    })
    return response.data
  },
  ipGeolocation: async (ip: string, caseId?: number) => {
    const response = await api.post('/api/osint/ip-geolocation', null, {
      params: { ip, case_id: caseId },
    })
    return response.data
  },
  search: async (
    endpoint: string,
    params: Record<string, unknown>,
    options?: { tavilyApi?: boolean },
  ) => {
    const { case_id, ...rest } = params
    const queryParams = Object.fromEntries(
      Object.entries(rest).filter(([, v]) => v !== null && v !== undefined && v !== ''),
    )
    const queryType = OSINT_COLLECT_QUERY_TYPES[endpoint]
    const isSlowSource =
      options?.tavilyApi ||
      endpoint.includes('rss') ||
      endpoint === 'gdelt' ||
      endpoint === 'gdelt-gfg' ||
      endpoint === 'nikkei' ||
      endpoint === 'bloomberg' ||
      endpoint === 'tavily' ||
      endpoint === 'research' ||
      endpoint === 'crawl' ||
      endpoint === 'map' ||
      endpoint === 'extract'
    const timeoutMs = endpoint === 'research' ? 360_000 : isSlowSource ? 180_000 : 30_000

    if (queryType) {
      const normalized = { ...queryParams }
      if (endpoint === 'extract' && typeof normalized.urls === 'string') {
        normalized.urls = normalized.urls
          .split(',')
          .map((u: string) => u.trim())
          .filter(Boolean)
      }
      const response = await api.post(
        '/api/osint/collect',
        {
          query_type: queryType,
          query_params: normalized,
          case_id: (case_id as number | null | undefined) ?? null,
        },
        { timeout: timeoutMs },
      )
      return response.data
    }

    const base = options?.tavilyApi ? '/api/tavily' : '/api/osint'
    const response = await api.post(`${base}/${endpoint}`, null, {
      params: { ...queryParams, case_id },
      timeout: timeoutMs,
    })
    return response.data
  },

  getRecentSearches: async (limit = 10): Promise<unknown[]> => {
    const response = await api.get('/api/osint/recent-searches', {
      params: { limit },
    })
    return response.data
  },

  getCaseInventory: async (caseId: number) => {
    const response = await api.get(`/api/osint/inventory/${caseId}`)
    return response.data
  },

  repairOrphans: async (caseId: number) => {
    const response = await api.post('/api/osint/repair-orphans', null, {
      params: { case_id: caseId },
    })
    return response.data as { repaired: number; case_id: number }
  },

  getCoverage: async (caseId: number) => {
    const response = await api.get(`/api/osint/coverage/${caseId}`)
    return response.data
  },
}

export type AnalysisBriefPayload = {
  user_direction: string
  focus_entity?: string
  focus_topic?: string
  entity_name?: string
  policy_topic?: string
}

export const aiAnalysisService = {
  taranis: async (caseId: number, brief: AnalysisBriefPayload, osintResults?: any[]) => {
    const response = await api.post('/api/ai/taranis/analyze', {
      case_id: caseId,
      osint_results: osintResults,
      ...brief,
    })
    return response.data
  },
  osintgpt: async (caseId: number, brief: AnalysisBriefPayload, osintResults?: any[]) => {
    const response = await api.post('/api/ai/osintgpt/analyze', {
      case_id: caseId,
      osint_results: osintResults,
      ...brief,
    })
    return response.data
  },
  ominis: async (caseId: number, brief: AnalysisBriefPayload, osintResults?: any[]) => {
    const response = await api.post('/api/ai/ominis/analyze', {
      case_id: caseId,
      osint_results: osintResults,
      ...brief,
    })
    return response.data
  },
  expertReputation: async (caseId: number, brief: AnalysisBriefPayload) => {
    const response = await api.post(`/api/ai/expert/reputation-manager/${caseId}`, brief)
    return response.data
  },
  expertPublicAffairs: async (caseId: number, brief: AnalysisBriefPayload) => {
    const response = await api.post(`/api/ai/expert/public-affairs-consultant/${caseId}`, brief)
    return response.data
  },
  expertInvestment: async (caseId: number, brief: AnalysisBriefPayload) => {
    const response = await api.post(`/api/ai/expert/investment-advisor/${caseId}`, brief)
    return response.data
  },
  getConcepts: async (caseId: number) => {
    const response = await api.get('/api/ai/concepts', {
      params: { case_id: caseId },
    })
    return response.data
  },
  getTrends: async (caseId: number) => {
    const response = await api.get('/api/ai/trends', {
      params: { case_id: caseId },
    })
    return response.data
  },
  getSentiment: async (caseId: number) => {
    const response = await api.get('/api/ai/sentiment', {
      params: { case_id: caseId },
    })
    return response.data
  },
}

export const qualitativeService = {
  createPremise: async (data: any) => {
    const response = await api.post('/api/qualitative/premise', data)
    return response.data
  },
  createKPI: async (data: any) => {
    const response = await api.post('/api/qualitative/kpi', data)
    return response.data
  },
  getFrameworks: async () => {
    const response = await api.get('/api/qualitative/frameworks')
    return response.data
  },
  getFramework: async (id: number) => {
    const response = await api.get(`/api/qualitative/frameworks/${id}`)
    return response.data
  },
  createFramework: async (data: Record<string, unknown>) => {
    const response = await api.post('/api/qualitative/frameworks', data)
    return response.data
  },
  updateFramework: async (id: number, data: Record<string, unknown>) => {
    const response = await api.put(`/api/qualitative/frameworks/${id}`, data)
    return response.data
  },
  deleteFramework: async (id: number) => {
    const response = await api.delete(`/api/qualitative/frameworks/${id}`)
    return response.data
  },
  generateFramework: async (data: { brief: string; framework_type?: string; language?: string }) => {
    const response = await api.post('/api/qualitative/frameworks/generate', data, { timeout: 120_000 })
    return response.data
  },
  previewFramework: async (id: number, data: { premise: string; case_context?: string }) => {
    const response = await api.post(`/api/qualitative/frameworks/${id}/preview`, data, { timeout: 90_000 })
    return response.data
  },
  runAnalysis: async (data: {
    case_id: number
    premise: string
    framework?: string
    framework_id?: number
    kpi_ids?: number[]
    focus_entity?: string
    focus_topic?: string
  }) => {
    const response = await api.post('/api/qualitative/analyze', data)
    return response.data
  },
  getKPIs: async () => {
    const response = await api.get('/api/qualitative/kpis')
    return response.data
  },
}

export const predictionsService = {
  generate: async (data: any) => {
    const response = await api.post('/api/predictions/generate', data)
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get(`/api/predictions/${id}`)
    return response.data
  },
  getTrends: async (caseId?: number) => {
    const response = await api.get('/api/predictions/trends', {
      params: { case_id: caseId },
    })
    return response.data
  },
}

export const reportsService = {
  generate: async (data: any) => {
    const response = await api.post('/api/reports/generate', data)
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get(`/api/reports/${id}`)
    return response.data
  },
  export: async (id: number) => {
    const response = await api.get(`/api/reports/${id}/export`, {
      responseType: 'blob',
    })
    return response.data
  },
}

export const investmentsService = {
  recommend: async (
    caseId: number,
    brief: { user_direction: string; focus_entity?: string; focus_topic?: string },
  ) => {
    const response = await api.post('/api/investments/recommend', {
      case_id: caseId,
      ...brief,
    })
    return response.data
  },
  getRisks: async (caseId?: number, recommendationId?: number) => {
    const response = await api.get('/api/investments/risks', {
      params: { case_id: caseId, recommendation_id: recommendationId },
    })
    return response.data
  },
  getOpportunities: async (caseId?: number, recommendationId?: number) => {
    const response = await api.get('/api/investments/opportunities', {
      params: { case_id: caseId, recommendation_id: recommendationId },
    })
    return response.data
  },
}

export const financialService = {
  getQuote: async (symbol: string) => {
    const response = await api.get(`/api/investments/quote/${symbol}`)
    return response.data
  },
  getCurrencyRates: async (base = 'USD') => {
    const response = await api.get('/api/investments/currency/rates', {
      params: { base },
    })
    return response.data
  },
  getRisks: async (caseId?: number) => {
    const response = await api.get('/api/investments/risks', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  getSanctionedEntities: async (query: string) => {
    const response = await api.post('/api/osint/opensanctions', null, {
      params: { query },
      timeout: 15000,
    })
    const data = response.data?.data ?? response.data
    if (data?.results) return data
    if (data?.top_matches) {
      return { results: data.top_matches, total: data.matches ?? data.top_matches.length }
    }
    return data
  },
}

export const publicAffairsService = {
  getPolicies: async (caseId?: number) => {
    const response = await api.get('/api/public-affairs/policies', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },

  getStakeholders: async (caseId?: number) => {
    const response = await api.get('/api/public-affairs/stakeholders', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },

  analyzeImpact: async (data: { policy_id: number; case_id?: number }) => {
    const response = await api.post('/api/public-affairs/analyze-impact', data)
    return response.data
  },

  getAdvocacyOpportunities: async (caseId?: number) => {
    const response = await api.get('/api/public-affairs/advocacy-opportunities', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
}

export const geographicService = {
  getLocations: async (caseId: number) => {
    const response = await api.get(`/api/geographic/locations/${caseId}`)
    return response.data
  },
}

export const syncService = {
  getStatus: async (caseId: number) => {
    const response = await api.get(`/api/sync/status/${caseId}`)
    return response.data
  },
  forceSync: async (caseId: number) => {
    const response = await api.post(`/api/sync/${caseId}`)
    return response.data
  },
}

export const intelligenceService = {
  getStatus: async (caseId: number) => {
    const response = await api.get(`/api/intelligence/${caseId}/status`)
    return response.data
  },
  runPipeline: async (
    caseId: number,
    includeInvestment = true,
    options?: { autoCleanup?: boolean; applyScope?: boolean },
  ) => {
    const response = await api.post(`/api/intelligence/${caseId}/run`, null, {
      params: {
        include_investment: includeInvestment,
        auto_cleanup: options?.autoCleanup ?? false,
        apply_scope: options?.applyScope ?? false,
      },
      timeout: 300_000,
    })
    return response.data
  },
  getActorNetwork: async (caseId: number) => {
    const response = await api.get(`/api/intelligence/${caseId}/actor-network`)
    return response.data
  },
  getActorImpact: async (caseId: number, refresh = false) => {
    const response = await api.get(`/api/intelligence/${caseId}/actor-impact`, {
      params: refresh ? { refresh: true } : {},
    })
    return response.data
  },
  analyzeActorImpact: async (caseId: number, projectId?: number) => {
    const response = await api.post(`/api/intelligence/${caseId}/actor-impact/analyze`, null, {
      params: projectId !== undefined ? { project_id: projectId } : {},
      timeout: 120_000,
    })
    return response.data
  },
}

export const dashboardService = {
  getMetrics: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/metrics?${params.toString()}`)
    return response.data
  },
  getMentions: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/mentions?${params.toString()}`)
    return response.data
  },
  getSentiment: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/sentiment?${params.toString()}`)
    return response.data
  },
  getReach: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/reach?${params.toString()}`)
    return response.data
  },
  getEngagement: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/engagement?${params.toString()}`)
    return response.data
  },
  getAlerts: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/alerts?${params.toString()}`)
    return response.data
  },
  getAlertsFeed: async (days: number = 7, caseId?: number | null, limit: number = 8) => {
    const params = new URLSearchParams({ days: String(days), limit: String(limit) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/alerts/feed?${params.toString()}`)
    return response.data
  },
  getTrendingTopics: async (days: number = 7, caseId?: number | null) => {
    const params = new URLSearchParams({ days: String(days) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/trending-topics?${params.toString()}`)
    return response.data
  },
  getTrendingTopicsList: async (days: number = 7, caseId?: number | null, limit: number = 5) => {
    const params = new URLSearchParams({ days: String(days), limit: String(limit) })
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/trending-topics/list?${params.toString()}`)
    return response.data
  },
  getSources: async (caseId?: number | null) => {
    const params = new URLSearchParams()
    if (caseId) params.set('case_id', String(caseId))
    const response = await api.get(`/api/dashboard/sources?${params.toString()}`)
    return response.data
  },
}

export const postsService = {
  getCasePosts: async (caseId: number, filters?: {
    sentiment?: string;
    category?: string;
    concept?: string;
    content_type?: string;
    search_text?: string;
    skip?: number;
    limit?: number;
  }) => {
    const params: any = { skip: filters?.skip || 0, limit: filters?.limit || 100 }
    if (filters?.sentiment) params.sentiment = filters.sentiment
    if (filters?.category) params.category = filters.category
    if (filters?.concept) params.concept = filters.concept
    if (filters?.content_type) params.content_type = filters.content_type
    if (filters?.search_text) params.search_text = filters.search_text
    const response = await api.get(`/api/posts/case/${caseId}`, { params })
    return response.data
  },
  getPost: async (postId: number) => {
    const response = await api.get(`/api/posts/${postId}`)
    return response.data
  },
  getPostsStats: async (caseId: number) => {
    const response = await api.get(`/api/posts/case/${caseId}/stats`)
    return response.data
  },
}

export const adminService = {
  // Classifications
  listClassifications: async (caseId?: number, sentiment?: string, hasFeedback?: boolean, skip = 0, limit = 100) => {
    const params: any = { skip, limit }
    if (caseId) params.case_id = caseId
    if (sentiment) params.sentiment = sentiment
    if (hasFeedback !== undefined) params.has_feedback = hasFeedback
    const response = await api.get('/api/admin/classifications', { params })
    return response.data
  },
  getClassification: async (classificationId: number) => {
    const response = await api.get(`/api/admin/classifications/${classificationId}`)
    return response.data
  },
  reclassifyCase: async (caseId: number) => {
    const response = await api.post(`/api/admin/classifications/${caseId}/reclassify`)
    return response.data
  },
  // Categories (KPIs de categorització)
  listCategories: async (categoryType?: string, isActive?: boolean) => {
    const params: any = {}
    if (categoryType) params.category_type = categoryType
    if (isActive !== undefined) params.is_active = isActive
    const response = await api.get('/api/admin/categories', { params })
    return response.data
  },
  createCategory: async (categoryData: any) => {
    const response = await api.post('/api/admin/categories', categoryData)
    return response.data
  },
  updateCategory: async (categoryId: number, categoryData: any) => {
    const response = await api.put(`/api/admin/categories/${categoryId}`, categoryData)
    return response.data
  },
  deleteCategory: async (categoryId: number) => {
    const response = await api.delete(`/api/admin/categories/${categoryId}`)
    return response.data
  },
  // Feedback
  addFeedback: async (feedbackData: any) => {
    const response = await api.post('/api/admin/feedback', feedbackData)
    return response.data
  },
  listFeedback: async (classificationId?: number, feedbackType?: string, skip = 0, limit = 100) => {
    const params: any = { skip, limit }
    if (classificationId) params.classification_id = classificationId
    if (feedbackType) params.feedback_type = feedbackType
    const response = await api.get('/api/admin/feedback', { params })
    return response.data
  },
  // Statistics
  getClassificationStats: async (caseId?: number) => {
    const params: any = {}
    if (caseId) params.case_id = caseId
    const response = await api.get('/api/admin/stats/classifications', { params })
    return response.data
  },
  getCategoryStats: async () => {
    const response = await api.get('/api/admin/stats/categories')
    return response.data
  },
  listUsers: async (): Promise<unknown[]> => {
    const response = await api.get('/api/admin/users')
    return response.data
  },
  createUser: async (data: {
    email: string
    full_name: string
    password: string
    is_superuser?: boolean
  }) => {
    const response = await api.post('/api/admin/users', data)
    return response.data
  },
  toggleUserActive: async (userId: number) => {
    const response = await api.patch(`/api/admin/users/${userId}/toggle-active`)
    return response.data
  },
  makeSuperuser: async (userId: number) => {
    const response = await api.patch(`/api/admin/users/${userId}/make-superuser`)
    return response.data
  },
  changePassword: async (userId: number, newPassword: string) => {
    const response = await api.patch(`/api/admin/users/${userId}/password`, {
      new_password: newPassword,
    })
    return response.data
  },
}

export const geopoliticalService = {
  getRisks: async (caseId?: number) => {
    const response = await api.get('/api/geopolitical/risks', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  calculateRisks: async (caseId?: number) => {
    const response = await api.post('/api/geopolitical/risks/calculate', null, {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  getBilateralMatrix: async (caseId?: number) => {
    const response = await api.get('/api/geopolitical/relations/matrix', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  getRelationTimeline: async (country1: string, country2: string, days = 90) => {
    const response = await api.get('/api/geopolitical/relations/timeline', {
      params: { country1, country2, days },
    })
    return response.data
  },
  compareRisks: async (countries: string[]) => {
    const response = await api.get('/api/geopolitical/risks/comparison', {
      params: { countries: countries.join(',') },
    })
    return response.data
  },
  getEvents: async (caseId?: number, eventType?: string, days = 90) => {
    const response = await api.get('/api/geopolitical/events', {
      params: {
        ...(caseId !== undefined ? { case_id: caseId } : {}),
        ...(eventType ? { event_type: eventType } : {}),
        days,
      },
    })
    const data = response.data
    return Array.isArray(data) ? { events: data } : data
  },
  extractEvents: async (caseId?: number) => {
    const response = await api.post('/api/geopolitical/events/extract', null, {
      params: caseId !== undefined ? { case_id: caseId } : {},
      timeout: 120_000,
    })
    return response.data
  },
}

export const reputationService = {
  getProfiles: async (caseId?: number) => {
    const response = await api.get('/api/reputation/profiles', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  getScore: async (entityId: number | string, entityType = 'company') => {
    const entityName = String(entityId)
    const response = await api.get(`/api/reputation/${encodeURIComponent(entityName)}/score`, {
      params: { entity_type: entityType },
    })
    return response.data
  },
  getHistory: async (entityId: number | string, days = 30) => {
    const entityName = String(entityId)
    const response = await api.get(`/api/reputation/${encodeURIComponent(entityName)}/history`, {
      params: { days },
    })
    return response.data
  },
  getCrisisIndicators: async (entityId: number | string, caseId?: number) => {
    const entityName = String(entityId)
    const response = await api.get(
      `/api/reputation/${encodeURIComponent(entityName)}/crisis-indicators`,
      { params: caseId !== undefined ? { case_id: caseId } : {} },
    )
    return response.data
  },
  getStakeholders: async (caseId?: number, entityName?: string) => {
    const response = await api.get('/api/reputation/stakeholders', {
      params: {
        ...(entityName ? { entity_name: entityName } : {}),
        ...(caseId !== undefined ? { case_id: caseId } : {}),
      },
    })
    return response.data
  },
  analyze: async (entityName: string, entityType = 'company', caseId?: number) => {
    const response = await api.post('/api/reputation/analyze', null, {
      params: {
        entity_name: entityName,
        entity_type: entityType,
        ...(caseId !== undefined ? { case_id: caseId } : {}),
      },
    })
    return response.data
  },
}

export default api

export type ExportReadiness = {
  export_ready: boolean
  can_export_with_warning?: boolean
  issue_count?: number
  warning_count?: number
  issues?: Array<{ type: string; message: string; count?: number }>
  warnings?: Array<{ type: string; message: string; source_url?: string; count?: number }>
  validation_summary?: {
    flagged_grounding?: Array<{
      id: number
      score: number
      actor: string
      statement: string
      source_url?: string
    }>
  }
}

export async function confirmExportIfNeeded(readiness: ExportReadiness): Promise<boolean> {
  if (readiness.export_ready) return true
  const issues = (readiness.issues ?? []).map((i) => i.message).join('\n')
  const warnings = (readiness.warnings ?? []).slice(0, 5).map((w) => w.message).join('\n')
  const msg = [
    'L\'informe té problemes de traçabilitat:',
    issues,
    warnings ? `\nAvísos:\n${warnings}` : '',
    '\nVols exportar igualment?',
  ].join('\n')
  return window.confirm(msg)
}

export const extractService = {
  getStreamUrl: (
    caseId: number,
    options?: { applyScope?: boolean; scope?: AnalysisScope },
  ): string => {
    const qs =
      options?.applyScope && options.scope ? scopeToExtractQuery(options.scope, true) : ''
    const path = qs ? `/api/extract/run/${caseId}?${qs}` : `/api/extract/run/${caseId}`
    return sseUrl(path)
  },
  getPendingStreamUrl: (
    caseId: number,
    options?: { applyScope?: boolean; scope?: AnalysisScope },
  ): string => {
    const qs =
      options?.applyScope && options.scope ? scopeToExtractQuery(options.scope, true) : ''
    const path = qs
      ? `/api/extract/run-pending/${caseId}?${qs}`
      : `/api/extract/run-pending/${caseId}`
    return sseUrl(path)
  },
  getCoverage: async (caseId: number) => {
    const response = await api.get(`/api/extract/coverage/${caseId}`)
    return response.data
  },
  getStatements: async (
    caseId: number,
    decision?: string,
    skip = 0,
    limit = 50,
    domain?: string,
    relevantOnly = false,
    dateFrom?: string,
    dateTo?: string,
  ) => {
    const response = await api.get(`/api/extract/statements/${caseId}`, {
      params: {
        ...(decision ? { decision } : {}),
        ...(domain ? { domain } : {}),
        ...(relevantOnly ? { relevant_only: true } : {}),
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
        skip,
        limit,
      },
    })
    return response.data
  },
  reclassifyRelevance: async (caseId: number) => {
    const response = await api.post(`/api/extract/relevance-cleanup/${caseId}`)
    return response.data
  },
  getStatementProvenance: async (statementId: number) => {
    const response = await api.get(`/api/extract/provenance/statement/${statementId}`)
    return response.data
  },
  getExportReadiness: async (caseId: number) => {
    const response = await api.get(`/api/extract/export-readiness/${caseId}`)
    return response.data as ExportReadiness
  },
  runCleanup: async (caseId: number) => {
    const response = await api.post(`/api/extract/cleanup/${caseId}`)
    return response.data
  },
  getPreview: async (caseId: number) => {
    const response = await api.get(`/api/extract/preview/${caseId}`)
    return response.data
  },
  applyToProject: async (projectId: number, caseId: number) => {
    const response = await api.post(`/api/extract/apply/${projectId}`, null, {
      params: { case_id: caseId },
    })
    return response.data
  },
  getSourceReliability: async (caseId: number) => {
    const response = await api.get(`/api/extract/source-reliability/${caseId}`)
    return response.data
  },
  validate: async (caseId: number) => {
    const response = await api.get(`/api/extract/validate/${caseId}`)
    return response.data
  },
}

export const prospectiveService = {
  listProjects: async (caseId?: number) => {
    const response = await api.get('/api/prospective/projects', {
      params: caseId !== undefined ? { case_id: caseId } : {},
    })
    return response.data
  },
  createProject: async (data: {
    title: string
    hypothesis: string
    context: string
    case_id?: number
  }) => {
    const response = await api.post('/api/prospective/projects', data)
    return response.data
  },
  getProject: async (id: number) => {
    const response = await api.get(`/api/prospective/projects/${id}`)
    return response.data
  },
  saveVariables: async (projectId: number, variables: unknown[]) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/variables`, {
      variables,
    })
    return response.data
  },
  computeMicmac: async (projectId: number, matrix: number[][]) => {
    const response = await api.post(`/api/prospective/projects/${projectId}/micmac`, { matrix })
    return response.data
  },
  saveActors: async (projectId: number, actors: unknown[]) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/actors`, { actors })
    return response.data
  },
  saveObjectives: async (projectId: number, objectives: unknown[]) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/objectives`, {
      objectives,
    })
    return response.data
  },
  computeMactor: async (projectId: number, postures: number[][]) => {
    const response = await api.post(`/api/prospective/projects/${projectId}/mactor`, { postures })
    return response.data
  },
  saveComponents: async (projectId: number, components: unknown[]) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/components`, {
      components,
    })
    return response.data
  },
  saveCompatibilities: async (
    projectId: number,
    incompatibilities: Array<{
      component_a: string
      config_a: string
      component_b: string
      config_b: string
    }>,
  ) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/compatibilities`, {
      incompatibilities,
    })
    return response.data
  },
  saveCompatibility: async (
    projectId: number,
    pairs: Array<{
      comp_a: string
      cfg_a: string
      comp_b: string
      cfg_b: string
      compatible: boolean
    }>,
  ) => {
    const response = await api.put(`/api/prospective/projects/${projectId}/compatibility`, {
      pairs,
    })
    return response.data
  },
  getCompatibility: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/compatibility`)
    return response.data
  },
  getMorphologicalSpace: async (projectId: number) => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/morphological-space`,
    )
    return response.data
  },
  getMorphSpace: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/morph-space`)
    return response.data
  },
  previewMicmac: async (projectId: number, matrix: number[][]) => {
    const response = await api.post(`/api/prospective/projects/${projectId}/micmac/preview`, {
      matrix,
    })
    return response.data
  },
  getSmic: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/smic`)
    return response.data
  },
  computeSmic: async (
    projectId: number,
    initial_probs: number[],
    cross_matrix: number[][],
  ) => {
    const response = await api.post(`/api/prospective/projects/${projectId}/smic/compute`, {
      initial_probs,
      cross_matrix,
    })
    return response.data
  },
  computeSmicBayesian: async (projectId: number, conditionalMatrix: number[][]) => {
    const response = await api.post(`/api/prospective/projects/${projectId}/smic`, {
      conditional_matrix: conditionalMatrix,
    })
    return response.data
  },

  getRetrospective: async (projectId: number) => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/retrospective`,
    )
    return response.data
  },

  getGeopoliticalMicmacSuggestions: async (
    projectId: number,
    variables: Array<{ code: string; name: string; desc: string }>,
    caseId?: number,
  ) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/geopolitical/micmac-suggestions`,
      { variables, case_id: caseId },
    )
    return response.data
  },
  getScenarios: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/scenarios`)
    return response.data
  },
  getStreamUrl: (projectId: number, includeTemporalContext = false): string => {
    const qs = includeTemporalContext ? 'include_temporal_context=true' : ''
    const path = qs
      ? `/api/prospective/projects/${projectId}/scenarios/stream?${qs}`
      : `/api/prospective/projects/${projectId}/scenarios/stream`
    return sseUrl(path)
  },
  getScenariosStreamUrl: (projectId: number, includeTemporalContext = false): string => {
    const qs = includeTemporalContext ? 'include_temporal_context=true' : ''
    const path = qs
      ? `/api/prospective/projects/${projectId}/scenarios/stream?${qs}`
      : `/api/prospective/projects/${projectId}/scenarios/stream`
    return sseUrl(path)
  },

  exportPdf: async (
    projectId: number,
    lang = 'ca',
    includeDecisionAnnex = false,
  ): Promise<void> => {
    const readiness = await prospectiveService.getExportReadiness(projectId)
    const ok = await confirmExportIfNeeded(readiness)
    if (!ok) return
    const response = await api.get(
      `/api/prospective/projects/${projectId}/export/pdf`,
      {
        params: { lang, include_decision_annex: includeDecisionAnnex },
        responseType: 'blob',
      },
    )
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `informe_prospectiu_${projectId}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  exportDocx: async (
    projectId: number,
    lang = 'ca',
    includeDecisionAnnex = false,
  ): Promise<void> => {
    const readiness = await prospectiveService.getExportReadiness(projectId)
    const ok = await confirmExportIfNeeded(readiness)
    if (!ok) return
    const response = await api.get(
      `/api/prospective/projects/${projectId}/export/docx`,
      {
        params: { lang, include_decision_annex: includeDecisionAnnex },
        responseType: 'blob',
      },
    )
    const url = URL.createObjectURL(
      new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      }),
    )
    const a = document.createElement('a')
    a.href = url
    a.download = `informe_prospectiu_${projectId}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  exportHtml: async (
    projectId: number,
    lang = 'ca',
    includeDecisionAnnex = false,
  ): Promise<void> => {
    const readiness = await prospectiveService.getExportReadiness(projectId)
    const ok = await confirmExportIfNeeded(readiness)
    if (!ok) return
    const response = await api.get(
      `/api/prospective/projects/${projectId}/export/html`,
      {
        params: { lang, include_decision_annex: includeDecisionAnnex },
        responseType: 'blob',
      },
    )
    const url = URL.createObjectURL(new Blob([response.data], { type: 'text/html;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `informe_prospectiu_${projectId}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  submitExpertVote: async (
    projectId: number,
    data: {
      expert_id: string
      expert_name: string
      votes: Array<{ row: number; col: number; value: number }>
    },
  ) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/panel/vote`,
      data,
    )
    return response.data
  },

  getPanelConsensus: async (projectId: number) => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/panel/consensus`,
    )
    return response.data
  },

  applyConsensus: async (projectId: number) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/panel/apply`,
    )
    return response.data
  },

  createMonitors: async (projectId: number, scenarioId: number) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/scenarios/${scenarioId}/monitors`,
    )
    return response.data
  },

  createMonitorsFromMilestones: async (projectId: number, scenarioId: number) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/scenarios/${scenarioId}/milestones/monitors`,
    )
    return response.data
  },

  parseScenarioMilestones: async (projectId: number, scenarioId: number) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/scenarios/${scenarioId}/milestones/parse`,
    )
    return response.data
  },

  getScenarioMilestones: async (projectId: number, scenarioId: number) => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/scenarios/${scenarioId}/milestones`,
    )
    return response.data
  },

  listMonitors: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/monitors`)
    return response.data
  },

  getMonitorSummary: async (caseId?: number) => {
    const params = caseId != null ? `?case_id=${caseId}` : ''
    const emptySummary = {
      triggered_count: 0,
      total_matches: 0,
      total_monitors: 0,
      unread_count: 0,
      new_matches: 0,
    }
    try {
      const response = await api.get(`/api/prospective/monitors/summary${params}`, {
        timeout: 15_000,
      })
      return response.data as typeof emptySummary
    } catch {
      return emptySummary
    }
  },

  getMonitorMatches: async (
    monitorId: number,
    opts?: {
      includeArchived?: boolean
      skip?: number
      limit?: number
      dateFrom?: string
      dateTo?: string
    },
  ) => {
    const response = await api.get(`/api/prospective/monitors/${monitorId}/matches`, {
      params: {
        include_archived: opts?.includeArchived ?? false,
        skip: opts?.skip ?? 0,
        limit: opts?.limit ?? 100,
        ...(opts?.dateFrom ? { date_from: opts.dateFrom } : {}),
        ...(opts?.dateTo ? { date_to: opts.dateTo } : {}),
      },
    })
    return response.data
  },

  getCaseAlertMatches: async (
    caseId: number,
    opts?: { includeArchived?: boolean; dateFrom?: string; dateTo?: string; limit?: number },
  ) => {
    const response = await api.get(`/api/prospective/cases/${caseId}/alert-matches`, {
      params: {
        include_archived: opts?.includeArchived ?? false,
        limit: opts?.limit ?? 50,
        ...(opts?.dateFrom ? { date_from: opts.dateFrom } : {}),
        ...(opts?.dateTo ? { date_to: opts.dateTo } : {}),
      },
    })
    return response.data
  },

  updateMatchStatus: async (matchId: number, status: string, actionTaken = '') => {
    const response = await api.patch(`/api/prospective/matches/${matchId}/status`, {
      status,
      action_taken: actionTaken,
    })
    return response.data
  },

  archiveMatch: async (matchId: number) => {
    const response = await api.post(`/api/prospective/matches/${matchId}/archive`)
    return response.data
  },

  extractMatch: async (matchId: number) => {
    const response = await api.post(`/api/prospective/matches/${matchId}/extract`)
    return response.data
  },

  bulkExtractMatches: async (opts: { caseId?: number; monitorId?: number; limit?: number }) => {
    const response = await api.post('/api/prospective/matches/bulk-extract', null, {
      params: {
        case_id: opts.caseId,
        monitor_id: opts.monitorId,
        limit: opts.limit ?? 25,
      },
    })
    return response.data
  },

  analyzeMatch: async (matchId: number) => {
    const response = await api.post(`/api/prospective/matches/${matchId}/analyze`)
    return response.data
  },

  exportMonitorMatchesUrl: (monitorId: number, fmt: 'json' | 'csv' = 'csv') =>
    `/api/prospective/monitors/${monitorId}/matches/export?fmt=${fmt}&include_archived=true`,

  exportProjectMatchesUrl: (projectId: number, fmt: 'json' | 'csv' = 'csv') =>
    `/api/prospective/projects/${projectId}/matches/export?fmt=${fmt}&include_archived=true`,

  getProjectMatches: async (
    projectId: number,
    opts?: { includeArchived?: boolean; skip?: number; limit?: number },
  ) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/matches`, {
      params: {
        include_archived: opts?.includeArchived ?? false,
        skip: opts?.skip ?? 0,
        limit: opts?.limit ?? 100,
      },
    })
    return response.data
  },

  getExportReadiness: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/export-readiness`)
    return response.data as ExportReadiness
  },

  getMatchProvenance: async (matchId: number) => {
    const response = await api.get(`/api/prospective/matches/${matchId}/provenance`)
    return response.data
  },

  checkMonitor: async (monitorId: number) => {
    const response = await api.post(`/api/prospective/monitors/${monitorId}/check`)
    return response.data
  },

  toggleMonitor: async (monitorId: number, isActive: boolean) => {
    const response = await api.patch(`/api/prospective/monitors/${monitorId}/toggle`, {
      is_active: isActive,
    })
    return response.data
  },

  updateMonitorSettings: async (
    monitorId: number,
    data: {
      lookback_days?: number | null
      horizon_label?: string | null
      min_match_score?: number | null
      min_keywords_matched?: number | null
      clear_thresholds?: boolean
    },
  ) => {
    const response = await api.patch(`/api/prospective/monitors/${monitorId}/settings`, data)
    return response.data
  },

  addManualMonitor: async (
    projectId: number,
    data: {
      indicator: string
      keywords?: string[]
      osint_sources?: string[]
      lookback_days?: number
      horizon_label?: string
      min_match_score?: number
      min_keywords_matched?: number
    },
  ) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/monitors/manual`,
      data,
    )
    return response.data
  },
}

export const directAnalysisService = {
  getLlmConfig: async () => {
    const response = await api.get('/api/analysis/llm-config')
    return response.data as {
      provider: 'anthropic' | 'openai' | 'gemini' | null
      configured: boolean
      llm_provider_setting: string
      providers: Record<string, { configured: boolean; extract_model?: string; scenario_model?: string }>
    }
  },

  analyze: async (
    text: string,
    caseId?: number,
    runTavilyOsint = true,
    runTavilyResearch = false,
    runTavilyCrawl = false,
  ) => {
    const response = await api.post(
      '/api/analysis/direct',
      {
        text,
        case_id: caseId ?? null,
        run_tavily_osint: Boolean(caseId && runTavilyOsint),
        run_tavily_research: Boolean(caseId && runTavilyResearch),
        run_tavily_crawl: Boolean(caseId && runTavilyCrawl),
      },
      { timeout: runTavilyResearch ? 360_000 : 180_000 },
    )
    return response.data
  },

  applyToProject: async (
    analysis: unknown,
    projectTitle: string,
    caseId?: number,
    sourceText?: string,
  ) => {
    const response = await api.post('/api/analysis/apply', {
      analysis,
      project_title: projectTitle,
      case_id: caseId ?? null,
      source_text: sourceText ?? null,
    })
    return response.data
  },
}

