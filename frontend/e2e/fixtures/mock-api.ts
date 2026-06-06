import type { Page, Route } from '@playwright/test'
import { MOCK_CASE, MOCK_INQUIRY_ID, SAMPLE_QUESTION } from './auth'

export function sseBody(events: Record<string, unknown>[]): string {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')
}

export const LITE_SSE_EVENTS: Record<string, unknown>[] = [
  { event: 'step', step: 'parse', status: 'ok' },
  { event: 'step', step: 'osint', status: 'ok', audit: { kept: 12, rejected: 3 } },
  { event: 'step', step: 'intelligence', status: 'ok' },
  { event: 'step', step: 'morph_bootstrap', status: 'ok', valid_combinations: 24 },
  { event: 'step', step: 'monitors', status: 'ok', count: 2 },
  {
    event: 'done',
    answer: {
      probability_pct: 38,
      possibility: 'possible',
      conclusions: ['Blocatge parcialment aixecat abans de l\'horitzó.'],
      reasoning: [{ conclusion: 'Tensió persistent', because: 'OSINT mock' }],
    },
  },
]

export const FULL_SSE_EVENTS: Record<string, unknown>[] = [
  { event: 'step', step: 'parse', status: 'ok' },
  { event: 'step', step: 'osint', status: 'ok' },
  { event: 'step', step: 'intelligence', status: 'ok' },
  { event: 'step', step: 'morph_bootstrap', status: 'ok', valid_combinations: 18 },
  {
    event: 'awaiting_godet',
    morph_bootstrap: { godet_preview: [{ name: 'Escenari Tensió' }] },
  },
]

type MockOptions = {
  inquiryMode?: 'lite' | 'full'
  dashboardItems?: Record<string, unknown>[]
}

function json(route: Route, data: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

function pathname(url: string): string {
  try {
    return new URL(url).pathname
  } catch {
    return url
  }
}

export async function installApiMocks(page: Page, options: MockOptions = {}) {
  const sseEvents = options.inquiryMode === 'full' ? FULL_SSE_EVENTS : LITE_SSE_EVENTS
  const dashboardItems =
    options.dashboardItems ??
    [
      {
        id: MOCK_INQUIRY_ID,
        case_id: MOCK_CASE.id,
        case_name: MOCK_CASE.name,
        question: SAMPLE_QUESTION,
        mode: 'lite',
        status: 'completed',
        run_count: 1,
        probability_pct: 38,
        wizard_project_id: 7,
        auto_rerun_enabled: false,
      },
    ]

  await page.route(/\/api\//, async (route) => {
    const { url, method } = route.request()
    const path = pathname(url)

    if (method === 'GET' && (path === '/api/cases' || path === '/api/cases/')) {
      return json(route, [MOCK_CASE])
    }

    if (method === 'GET' && path === `/api/intelligence/${MOCK_CASE.id}/status`) {
      return json(route, {
        case_name: MOCK_CASE.name,
        pipeline_ready: true,
        llm_configured: true,
        ready_steps: 6,
        total_steps: 6,
        steps: {
          osint: { label: 'OSINT', ready: true, count: 10, detail: 'ok' },
          extraction: { label: 'Extracció', ready: true, count: 5, detail: 'ok' },
          events: { label: 'Esdeveniments', ready: true, count: 3, detail: 'ok' },
          risks: { label: 'Riscos', ready: true, count: 2, detail: 'ok' },
          actor_impact: { label: 'Actors', ready: true, count: 1, detail: 'ok' },
          investment: { label: 'Inversions', ready: true, count: 0, detail: 'ok' },
        },
      })
    }

    if (method === 'GET' && path === `/api/intelligence/${MOCK_CASE.id}/actor-network`) {
      return json(route, { nodes: [], edges: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/intelligence/${MOCK_CASE.id}/policy-industry`)) {
      return json(route, { companies: [], contractors: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/intelligence/${MOCK_CASE.id}/actor-impact`)) {
      return json(route, { scenarios: [] })
    }

    if (method === 'GET' && path.startsWith('/api/dashboard/metrics')) {
      return json(route, { articles: 10, events: 3 })
    }

    if (method === 'GET' && path.startsWith('/api/dashboard/mentions')) {
      return json(route, { series: [] })
    }

    if (method === 'GET' && path === '/api/prospective/inquiries/dashboard') {
      return json(route, {
        items: dashboardItems,
        stats: {
          total: dashboardItems.length,
          completed: dashboardItems.filter((i) => i.status === 'completed').length,
          awaiting_godet: dashboardItems.filter((i) => i.status === 'awaiting_godet').length,
          scheduled_active: 0,
          scheduled_due: 0,
          failed: 0,
        },
      })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/case/${MOCK_CASE.id}/compare`) {
      return json(route, { inquiries: [], deltas: [] })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/case/${MOCK_CASE.id}`) {
      return json(route, dashboardItems)
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/${MOCK_INQUIRY_ID}`) {
      return json(route, {
        id: MOCK_INQUIRY_ID,
        question: SAMPLE_QUESTION,
        status: 'completed',
        mode: 'lite',
      })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/${MOCK_INQUIRY_ID}/wizard-link`) {
      return json(route, {
        wizard_paths: { morph: '/prospective/morph?project=7&inquiry=42' },
        project_id: 7,
      })
    }

    if (method === 'GET' && path.endsWith('/scope-audit')) {
      return json(route, { audit: { kept: 12, rejected: 3 }, rejected_samples: [] })
    }

    if (method === 'GET' && path.endsWith('/audit')) {
      return json(route, { events: [] })
    }

    if (method === 'GET' && path.endsWith('/godet-status')) {
      return json(route, { godet_ready: false, checklist: [] })
    }

    if (method === 'GET' && path === '/api/prospective/projects/7') {
      return json(route, {
        id: 7,
        title: 'Hormuz Project',
        hypothesis: SAMPLE_QUESTION,
        case_id: MOCK_CASE.id,
      })
    }

    if (method === 'GET' && path === '/api/prospective/projects/7/morph-space') {
      return json(route, { valid_combinations: 24, total_combinations: 32 })
    }

    if (method === 'GET' && path.startsWith('/api/prospective/projects/7/cca-suggestions')) {
      return json(route, { found: true, rules: [], methodology: 'e2e' })
    }

    if (method === 'GET' && path === '/api/prospective/inquiries/export/batch') {
      return route.fulfill({
        status: 200,
        contentType: 'application/zip',
        body: Buffer.from('PK mock zip'),
        headers: { 'Content-Disposition': 'attachment; filename="inquiries.zip"' },
      })
    }

    if (method === 'GET' && path.includes('/export/html')) {
      return route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>E2E export</body></html>',
      })
    }

    if (method === 'POST' && path === '/api/prospective/inquiries') {
      return json(route, {
        inquiry_id: MOCK_INQUIRY_ID,
        status: 'pending',
        parsed_trigger: { ok: true, llm_used: false },
      })
    }

    if (method === 'POST' && (path.endsWith('/run') || path.endsWith('/rerun'))) {
      return route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
        body: sseBody(sseEvents),
      })
    }

    if (method === 'GET' && path === `/api/cases/${MOCK_CASE.id}/intsum`) {
      return json(route, { summary: 'E2E mock' })
    }

    if (method === 'GET' && path.startsWith(`/api/cases/${MOCK_CASE.id}/alert-matches`)) {
      return json(route, [])
    }

    if (method === 'GET' && path === `/api/cases/${MOCK_CASE.id}/scope-profile`) {
      return json(route, { focus_label: 'Hormuz', themes: [] })
    }

    if (method === 'GET' && path.startsWith('/api/intelligence/')) {
      return json(route, {})
    }

    if (method === 'GET' && path.startsWith('/api/visualizations/')) {
      return json(route, { nodes: [], edges: [] })
    }

    if (method === 'GET' && path.startsWith('/api/financial-crossover/')) {
      return json(route, { items: [] })
    }

    if (method === 'GET' && path.startsWith('/api/prospective/projects/7')) {
      return json(route, { id: 7, title: 'Hormuz', hypothesis: SAMPLE_QUESTION })
    }

    return json(route, {})
  })
}
