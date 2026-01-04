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

export const osintService = {
  sherlock: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/sherlock', null, {
      params: { username, case_id: caseId },
    })
    return response.data
  },
  reconngDomain: async (domain: string, caseId?: number) => {
    const response = await api.post('/api/osint/recon-ng/domain', null, {
      params: { domain, case_id: caseId },
    })
    return response.data
  },
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
  theharvester: async (domain: string, sources?: string, limit: number = 500, caseId?: number) => {
    const response = await api.post('/api/osint/theharvester', null, {
      params: { domain, sources, limit, case_id: caseId },
    })
    return response.data
  },
  shodan: async (query: string, facets?: string, page: number = 1, caseId?: number) => {
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
  dnsLookup: async (domain: string, recordType: string = 'A', caseId?: number) => {
    const response = await api.post('/api/osint/dns', null, {
      params: { domain, record_type: recordType, case_id: caseId },
    })
    return response.data
  },
  whois: async (domain: string, caseId?: number) => {
    const response = await api.post('/api/osint/whois', null, {
      params: { domain, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - TikTok
  ensembledataTikTokUserInfo: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/tiktok/user-info', null, {
      params: { username, case_id: caseId },
    })
    return response.data
  },
  ensembledataTikTokUserPosts: async (username: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/tiktok/user-posts', null, {
      params: { username, count, case_id: caseId },
    })
    return response.data
  },
  ensembledataTikTokHashtagPosts: async (hashtag: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/tiktok/hashtag-posts', null, {
      params: { hashtag, count, case_id: caseId },
    })
    return response.data
  },
  ensembledataTikTokKeywordPosts: async (keyword: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/tiktok/keyword-posts', null, {
      params: { keyword, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Instagram
  ensembledataInstagramUserInfo: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/instagram/user-info', null, {
      params: { username, case_id: caseId },
    })
    return response.data
  },
  ensembledataInstagramUserPosts: async (username: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/instagram/user-posts', null, {
      params: { username, count, case_id: caseId },
    })
    return response.data
  },
  ensembledataInstagramHashtagPosts: async (hashtag: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/instagram/hashtag-posts', null, {
      params: { hashtag, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - YouTube
  ensembledataYouTubeChannelInfo: async (channelId: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/youtube/channel-info', null, {
      params: { channel_id: channelId, case_id: caseId },
    })
    return response.data
  },
  ensembledataYouTubeChannelVideos: async (channelId: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/youtube/channel-videos', null, {
      params: { channel_id: channelId, count, case_id: caseId },
    })
    return response.data
  },
  ensembledataYouTubeKeywordPosts: async (keyword: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/youtube/keyword-posts', null, {
      params: { keyword, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Threads
  ensembledataThreadsUserInfo: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/threads/user-info', null, {
      params: { username, case_id: caseId },
    })
    return response.data
  },
  ensembledataThreadsUserPosts: async (username: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/threads/user-posts', null, {
      params: { username, count, case_id: caseId },
    })
    return response.data
  },
  ensembledataThreadsKeywordPosts: async (keyword: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/threads/keyword-posts', null, {
      params: { keyword, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Reddit (adicional)
  ensembledataRedditSubredditPosts: async (subreddit: string, count: number = 25, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/reddit/subreddit-posts', null, {
      params: { subreddit, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Twitter/X
  ensembledataTwitterUserInfo: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/twitter/user-info', null, {
      params: { username, case_id: caseId },
    })
    return response.data
  },
  ensembledataTwitterUserTweets: async (username: string, count: number = 20, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/twitter/user-tweets', null, {
      params: { username, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Twitch
  ensembledataTwitchKeywordPosts: async (keyword: string, count: number = 30, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/twitch/keyword-posts', null, {
      params: { keyword, count, case_id: caseId },
    })
    return response.data
  },
  // EnsembleData - Snapchat
  ensembledataSnapchatUserInfo: async (username: string, caseId?: number) => {
    const response = await api.post('/api/osint/ensembledata/snapchat/user-info', null, {
      params: { username, case_id: caseId },
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
  getMetrics: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/metrics?days=${days}`)
    return response.data
  },
  getMentions: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/mentions?days=${days}`)
    return response.data
  },
  getSentiment: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/sentiment?days=${days}`)
    return response.data
  },
  getReach: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/reach?days=${days}`)
    return response.data
  },
  getEngagement: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/engagement?days=${days}`)
    return response.data
  },
  getAlerts: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/alerts?days=${days}`)
    return response.data
  },
  getTrendingTopics: async (days: number = 7) => {
    const response = await api.get(`/api/dashboard/trending-topics?days=${days}`)
    return response.data
  },
  getSources: async () => {
    const response = await api.get('/api/dashboard/sources')
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

export default api

