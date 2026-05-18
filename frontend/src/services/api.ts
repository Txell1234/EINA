import axios from 'axios'

const api = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
})

export default api

export const casesService = {
  list: async () => {
    const response = await api.get('/api/cases')
    return response.data
  },
}

export const extractService = {
  getStreamUrl: (caseId: number) => `/api/extract/run/${caseId}`,
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
    const response = await api.post(`/api/extract/apply/${projectId}`, {}, {
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
  getStreamUrl: (projectId: number) => `/api/prospective/projects/${projectId}/scenarios/stream`,
}
