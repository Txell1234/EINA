/**
 * Client API per la plataforma OSINT
 * Centralitza totes les crides al backend FastAPI
 */
import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Normalitzar errors (evitar renderitzar objectes Pydantic)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      const d = error.response.data;
      let message = 'Error del servidor';
      if (Array.isArray(d?.detail)) {
        message = d.detail.map((e) => e.msg || e.message || String(e)).join('; ');
      } else if (typeof d?.detail === 'string') message = d.detail;
      else if (d?.message) message = d.message;
      return Promise.reject({ ...error, message });
    }
    return Promise.reject({ ...error, message: error.message || 'Error de connexió' });
  }
);

// Cases
export const getCases = () => api.get('/cases');
export const getCase = (id) => api.get(`/cases/${id}`);
export const createCase = (data) => api.post('/cases', data);
export const updateCase = (id, data) => api.put(`/cases/${id}`, data);
export const deleteCase = (id) => api.delete(`/cases/${id}`);
export const getFullCase = (id) => api.get(`/cases/${id}/full`);
export const getCasesWithFilters = (filters) => {
  const params = new URLSearchParams();
  if (filters?.startDate) params.append('start_date', filters.startDate.toISOString?.() || filters.startDate);
  if (filters?.endDate) params.append('end_date', filters.endDate.toISOString?.() || filters.endDate);
  if (filters?.country) params.append('country', filters.country);
  if (filters?.caseType) params.append('case_type', filters.caseType);
  if (filters?.hasOSINT != null) params.append('has_osint', filters.hasOSINT);
  if (filters?.hasAI != null) params.append('has_ai', filters.hasAI);
  if (filters?.hasQualitative != null) params.append('has_qualitative', filters.hasQualitative);
  if (filters?.hasInvestment != null) params.append('has_investment', filters.hasInvestment);
  if (filters?.kpiIds?.length) filters.kpiIds.forEach((id) => params.append('kpi_ids', id));
  if (filters?.thematic) params.append('thematic', filters.thematic);
  return api.get(`/cases/filtered?${params.toString()}`);
};

// Risk analysis
export const getRiskConcepts = (caseId) => api.get(`/cases/${caseId}/risk-concepts`);
export const createRiskConcept = (caseId, data) => api.post(`/cases/${caseId}/risk-concepts`, data);
export const deleteRiskConcept = (caseId, conceptId) => api.delete(`/cases/${caseId}/risk-concepts/${conceptId}`);
export const analyzeRisk = (caseId, options) => api.post(`/risk/analyze/${caseId}`, options ?? {});
export const analyzeRiskAI = (caseId, options) => api.post(`/risk/analyze-ai/${caseId}`, options ?? {});

// OSINT
export const getOSINTTools = () => api.get('/osint/tools');
export const collectOSINT = (data) => api.post('/osint/collect', data);

// AI
export const getAIStatus = () => api.get('/ai/status');
export const analyzeWithAI = (caseId) => api.post(`/ai/analyze/${caseId}`);
export const analyzeConcepts = (caseId) => api.post(`/ai/analyze-concepts/${caseId}`);
export const analyzeTrends = (caseId) => api.post(`/ai/analyze-trends/${caseId}`);
export const analyzeSentiment = (caseId) => api.post(`/ai/analyze-sentiment/${caseId}`);

// KPIs i qualitatiu
export const getKPIs = (caseId) => api.get(`/kpis/${caseId}`);
export const createKPI = (data) => api.post('/kpis', data);
export const qualitativeAnalyze = (data) => api.post('/qualitative/analyze', data);

// Inversió i unificat
export const analyzeInvestment = (caseId) => api.post(`/investment/analyze/${caseId}`);
export const analyzeUnified = (caseId, country = null, actor = null) => {
  const params = new URLSearchParams();
  if (country) params.append('country', country);
  if (actor) params.append('actor', actor);
  return api.post(`/unified/analyze/${caseId}${params.toString() ? '?' + params.toString() : ''}`);
};

// Sync
export const getSyncStatus = (caseId) => api.get(`/sync/status/${caseId}`);
export const forceSync = (caseId) => api.post(`/sync/${caseId}`);

// Dades completes (per dashboard)
export const getAllCasesFull = async () => {
  const { data: cases } = await getCases();
  if (!cases?.length) return [];
  const full = await Promise.all(
    cases.map((c) => getFullCase(c.id).then((r) => r.data).catch(() => null))
  );
  return full.filter(Boolean);
};

export default api;
