import http from 'node:http'
import { MOCK_CASE, MOCK_INQUIRY_ID, SAMPLE_QUESTION } from './fixtures/auth'
import { FULL_SSE_EVENTS, LITE_SSE_EVENTS, sseBody } from './fixtures/mock-api'

const PORT = Number(process.env.E2E_MOCK_PORT ?? 9321)

let inquiryMode: 'lite' | 'full' = 'lite'

function sendJson(res: http.ServerResponse, data: unknown, status = 200) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  })
  res.end(JSON.stringify(data))
}

function parsePath(url: string): string {
  try {
    return new URL(url, 'http://127.0.0.1').pathname
  } catch {
    return url
  }
}

export function startE2eMockServer(): Promise<() => Promise<void>> {
  const server = http.createServer((req, res) => {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      })
      res.end()
      return
    }

    const path = parsePath(req.url ?? '/')
    const method = req.method ?? 'GET'

    if (path === '/__e2e/mode' && method === 'POST') {
      let body = ''
      req.on('data', (chunk) => {
        body += chunk
      })
      req.on('end', () => {
        try {
          inquiryMode = (JSON.parse(body).mode as 'lite' | 'full') ?? 'lite'
        } catch {
          inquiryMode = 'lite'
        }
        sendJson(res, { ok: true, mode: inquiryMode })
      })
      return
    }

    if (method === 'GET' && (path === '/api/cases' || path === '/api/cases/')) {
      return sendJson(res, [MOCK_CASE])
    }

    if (method === 'GET' && path === '/api/prospective/inquiries/dashboard') {
      const items = [
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
      return sendJson(res, {
        items,
        stats: {
          total: items.length,
          completed: 1,
          awaiting_godet: 0,
          scheduled_active: 0,
          scheduled_due: 0,
          failed: 0,
        },
      })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/case/${MOCK_CASE.id}`) {
      return sendJson(res, [])
    }

    if (method === 'GET' && path === `/api/intelligence/${MOCK_CASE.id}/status`) {
      return sendJson(res, {
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

    if (method === 'GET' && path.startsWith('/api/dashboard/')) {
      return sendJson(res, { articles: 0, series: [] })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/case/${MOCK_CASE.id}/compare`) {
      return sendJson(res, { inquiries: [], deltas: [] })
    }

    if (method === 'GET' && path === `/api/intelligence/${MOCK_CASE.id}/actor-network`) {
      return sendJson(res, { nodes: [], edges: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/intelligence/${MOCK_CASE.id}/policy-industry`)) {
      return sendJson(res, { companies: [], contractors: [], beneficiaries: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/intelligence/${MOCK_CASE.id}/actor-impact`)) {
      return sendJson(res, { scenarios: [] })
    }

    if (method === 'GET' && path.startsWith('/api/visualizations/')) {
      return sendJson(res, { nodes: [], edges: [] })
    }

    if (method === 'GET' && path.startsWith('/api/financial-crossover/')) {
      return sendJson(res, { items: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/cases/${MOCK_CASE.id}/`)) {
      if (path.includes('financial-reports')) {
        return sendJson(res, [])
      }
      if (path.includes('financial-crossover')) {
        return sendJson(res, { rows: [], conclusions: [] })
      }
      if (path.includes('intsum')) {
        return sendJson(res, { summary: 'E2E mock' })
      }
      if (path.includes('alert-matches')) {
        return sendJson(res, [])
      }
      if (path.includes('scope-profile')) {
        return sendJson(res, { focus_label: 'Hormuz', themes: [] })
      }
      return sendJson(res, {})
    }

    if (method === 'GET' && path === `/api/visualizations/network/${MOCK_CASE.id}`) {
      return sendJson(res, { nodes: [], edges: [] })
    }

    if (method === 'GET' && path.startsWith(`/api/visualizations/trends/${MOCK_CASE.id}`)) {
      return sendJson(res, { points: [], series: [] })
    }

    if (method === 'GET' && path === `/api/geographic/locations/${MOCK_CASE.id}`) {
      return sendJson(res, { locations: [] })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/${MOCK_INQUIRY_ID}`) {
      return sendJson(res, {
        id: MOCK_INQUIRY_ID,
        question: SAMPLE_QUESTION,
        status: 'completed',
      })
    }

    if (method === 'GET' && path === `/api/prospective/inquiries/${MOCK_INQUIRY_ID}/wizard-link`) {
      return sendJson(res, {
        wizard_paths: { morph: '/prospective/morph?project=7&inquiry=42' },
        project_id: 7,
      })
    }

    if (method === 'GET' && path.startsWith('/api/prospective/projects/7')) {
      return sendJson(res, { id: 7, title: 'Hormuz', hypothesis: SAMPLE_QUESTION })
    }

    if (method === 'GET' && path.endsWith('/scope-audit')) {
      return sendJson(res, { audit: { kept: 12, rejected: 3 }, rejected_samples: [] })
    }

    if (method === 'GET' && path.endsWith('/godet-status')) {
      return sendJson(res, { godet_ready: false, checklist: [] })
    }

    if (method === 'GET' && path.endsWith('/audit')) {
      return sendJson(res, { events: [] })
    }

    if (method === 'GET' && path === '/api/prospective/inquiries/export/batch') {
      res.writeHead(200, {
        'Content-Type': 'application/zip',
        'Content-Disposition': 'attachment; filename="inquiries.zip"',
        'Access-Control-Allow-Origin': '*',
      })
      res.end(Buffer.from('PK mock zip'))
      return
    }

    if (method === 'POST' && path === '/api/prospective/inquiries/rerun/batch') {
      return sendJson(res, {
        processed: 1,
        ok_count: 1,
        failed_count: 0,
        results: [{ inquiry_id: MOCK_INQUIRY_ID, ok: true, status: 'completed', event: 'done' }],
      })
    }

    if (method === 'POST' && path === '/api/prospective/inquiries/parse-preview') {
      return sendJson(res, {
        ok: true,
        confidence: 0.91,
        llm_used: false,
        event_type: 'geopolitical',
        horizon_label: '2026-12',
      })
    }

    if (method === 'POST' && path === '/api/prospective/inquiries') {
      return sendJson(res, {
        inquiry_id: MOCK_INQUIRY_ID,
        status: 'pending',
        parsed_trigger: { ok: true },
      })
    }

    if (method === 'POST' && (path.endsWith('/run') || path.endsWith('/rerun'))) {
      const events = inquiryMode === 'full' ? FULL_SSE_EVENTS : LITE_SSE_EVENTS
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Access-Control-Allow-Origin': '*',
      })
      res.end(sseBody(events))
      return
    }

    if (path.startsWith('/api/')) {
      return sendJson(res, {})
    }

    res.writeHead(404)
    res.end()
  })

  return new Promise((resolve) => {
    server.listen(PORT, '127.0.0.1', () => {
      process.env.E2E_MOCK_PORT = String(PORT)
      resolve(
        () =>
          new Promise<void>((res) => {
            server.close(() => res())
          }),
      )
    })
  })
}

export const E2E_MOCK_API_URL = `http://127.0.0.1:${PORT}`
