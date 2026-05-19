import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 segundos timeout global (aumentado para operaciones largas)
})

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
      console.error(`❌ Error del servidor: ${error.response.status} - ${error.response.statusText}`)
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
  createFromPrompt: async (prompt: string) => {
    const response = await api.post('/api/cases/from-prompt', { 
      prompt: prompt 
    }, {
      timeout: 15000, // 15 segundos timeout (aumentado para dar más margen)
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
  generatePlan: async (caseId: number) => {
    const response = await api.post(`/api/research/plan/${caseId}`)
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
  search: async (endpoint: string, params: Record<string, unknown>) => {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ''),
    )
    const response = await api.post(`/api/osint/${endpoint}`, null, { params: clean })
    return response.data
  },

  getRecentSearches: async (limit = 10): Promise<unknown[]> => {
    const response = await api.get('/api/osint/recent-searches', {
      params: { limit },
    })
    return response.data
  },
}

export const aiAnalysisService = {
  taranis: async (caseId: number, osintResults?: any[]) => {
    const response = await api.post('/api/ai/taranis/analyze', {
      case_id: caseId,
      osint_results: osintResults,
    })
    return response.data
  },
  osintgpt: async (caseId: number, osintResults?: any[]) => {
    const response = await api.post('/api/ai/osintgpt/analyze', {
      case_id: caseId,
      osint_results: osintResults,
    })
    return response.data
  },
  ominis: async (caseId: number, osintResults?: any[]) => {
    const response = await api.post('/api/ai/ominis/analyze', {
      case_id: caseId,
      osint_results: osintResults,
    })
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
  runAnalysis: async (data: any) => {
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
  recommend: async (caseId: number) => {
    const response = await api.post('/api/investments/recommend', {
      case_id: caseId,
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
  getAlertsFeed: async (days: number = 7, caseId?: number | null, limit: number = 5) => {
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

export const extractService = {
  getStreamUrl: (caseId: number): string => `/api/extract/run/${caseId}`,
  getStatements: async (caseId: number, decision?: string) => {
    const response = await api.get(`/api/extract/statements/${caseId}`, {
      params: decision ? { decision } : {},
    })
    return response.data
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
  getScenarios: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/scenarios`)
    return response.data
  },
  getStreamUrl: (projectId: number): string =>
    `/api/prospective/projects/${projectId}/scenarios/stream`,
  getScenariosStreamUrl: (projectId: number): string =>
    `/api/prospective/projects/${projectId}/scenarios/stream`,

  exportPdf: async (projectId: number): Promise<void> => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/export/pdf`,
      { responseType: 'blob' },
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

  exportDocx: async (projectId: number): Promise<void> => {
    const response = await api.get(
      `/api/prospective/projects/${projectId}/export/docx`,
      { responseType: 'blob' },
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

  listMonitors: async (projectId: number) => {
    const response = await api.get(`/api/prospective/projects/${projectId}/monitors`)
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

  addManualMonitor: async (
    projectId: number,
    data: { indicator: string; keywords?: string[]; osint_sources?: string[] },
  ) => {
    const response = await api.post(
      `/api/prospective/projects/${projectId}/monitors/manual`,
      data,
    )
    return response.data
  },
}

