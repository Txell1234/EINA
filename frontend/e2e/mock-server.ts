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
      const url = new URL(req.url ?? '/', 'http://127.0.0.1')
      const q = (url.searchParams.get('q') || '').toLowerCase()
      const caseFilter = url.searchParams.get('case_id')
      const baseItem = {
        id: MOCK_INQUIRY_ID,
        case_id: MOCK_CASE.id,
        case_name: MOCK_CASE.name,
        question: SAMPLE_QUESTION,
        mode: 'lite',
        status: 'completed',
        run_count: 2,
        probability_pct: 38,
        probability_delta: 3,
        probability_history: [
          { probability_pct: 35, run_number: 1 },
          { probability_pct: 38, run_number: 2 },
        ],
        wizard_project_id: 7,
        auto_rerun_enabled: false,
        parse_confidence: 0.91,
        llm_used: false,
      }
      let items = [baseItem]
      if (q && !SAMPLE_QUESTION.toLowerCase().includes(q)) {
        items = []
      }
      if (caseFilter && Number(caseFilter) !== MOCK_CASE.id) {
        items = []
      }
      return sendJson(res, {
        items,
        stats: {
          total: items.length,
          completed: items.length ? 1 : 0,
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

    if (
      method === 'GET' &&
      (path === `/api/osint/coverage/${MOCK_CASE.id}` ||
        path === `/api/extract/coverage/${MOCK_CASE.id}`)
    ) {
      return sendJson(res, {
        case_id: MOCK_CASE.id,
        coverage_percent: 42,
        articles: {
          articles_total: 10,
          extractable: 8,
          enriched: 5,
          needs_enrichment: 3,
          extracted_urls: 4,
          pending_extraction: 2,
          pending_thin: 1,
          top_domains: [{ domain: 'reuters.com', count: 3 }],
        },
        statements: { total: 0, by_decision: {} },
        osint: { orphan_queries_global: 0, error_results: 0 },
        alerts: { pending_extraction: 0, short_excerpt: 0 },
        recommendations: [],
      })
    }

    if (method === 'GET' && path === `/api/osint/inventory/${MOCK_CASE.id}`) {
      return sendJson(res, { items: [], total: 0 })
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

    if (method === 'PATCH' && path === '/api/prospective/inquiries/batch-schedule') {
      let body = ''
      req.on('data', (chunk) => {
        body += chunk
      })
      req.on('end', () => {
        try {
          const parsed = JSON.parse(body)
          const ids = parsed.ids || []
          sendJson(res, {
            ok_count: ids.length,
            failed_count: 0,
            processed: ids.length,
            interval_hours: parsed.interval_hours ?? 24,
          })
        } catch {
          sendJson(res, { ok_count: 0, failed_count: 1, processed: 0 }, 400)
        }
      })
      return
    }

    if (method === 'GET' && path === '/api/prospective/inquiries/export/executive') {
      res.writeHead(200, {
        'Content-Type': 'text/html',
        'Content-Disposition': 'attachment; filename="executive.html"',
        'Access-Control-Allow-Origin': '*',
      })
      res.end('<html><body>E2E executive report</body></html>')
      return
    }

    if (method === 'GET' && path === '/health') {
      return sendJson(res, {
        services: { export: { weasyprint: { available: false } } },
      })
    }

    if (method === 'GET' && path === '/api/prospective/projects/7/morph-space') {
      return sendJson(res, {
        valid_combinations: 3,
        total_combinations: 4,
        filtered_out: 1,
      })
    }

    if (method === 'GET' && path === '/api/prospective/projects/7/compatibilities') {
      return sendJson(res, [
        { component_a: 'C1', config_a: 'Opció A', component_b: 'C2', config_b: 'Opció B' },
      ])
    }

    if (method === 'GET' && path.startsWith('/api/prospective/projects/7/cca-suggestions')) {
      return sendJson(res, { found: true, rules: [], existing_incompatibilities: [] })
    }

    if (method === 'POST' && path === '/api/prospective/projects/7/cca-suggestions/preview') {
      return sendJson(res, {
        after: { valid_combinations: 3, total_combinations: 4, filtered_out: 1 },
      })
    }

    if (method === 'GET' && path.startsWith('/api/prospective/projects/7')) {
      return sendJson(res, { id: 7, title: 'Hormuz', hypothesis: SAMPLE_QUESTION })
    }

    if (method === 'GET' && path.endsWith('/scope-audit')) {
      return sendJson(res, { audit: { kept: 12, rejected: 3 }, rejected_samples: [] })
    }

    if (method === 'GET' && path.endsWith('/godet-status')) {
      return sendJson(res, {
        found: true,
        inquiry_id: MOCK_INQUIRY_ID,
        status: inquiryMode === 'full' ? 'awaiting_godet' : 'completed',
        project_id: 7,
        godet_ready: false,
        can_synthesize: false,
        checklist: {
          project: true,
          variables: false,
          micmac: false,
          actors: false,
          mactor: false,
          morph: false,
          smic: false,
          scenarios: false,
        },
        missing_steps: ['variables', 'micmac', 'actors', 'mactor', 'morph', 'smic', 'scenarios'],
      })
    }

    if (method === 'GET' && path === '/api/integration/status') {
      return sendJson(res, {
        osint_apis: {
          ensembledata: { configured: true, status: 'configured' },
          tavily: { configured: true, status: 'configured' },
        },
      })
    }

    if (method === 'POST' && path === '/api/osint/collect') {
      let body: { query_type?: string } = {}
      const chunks: Buffer[] = []
      req.on('data', (c) => chunks.push(c))
      req.on('end', () => {
        try {
          body = JSON.parse(Buffer.concat(chunks).toString('utf8'))
        } catch {
          body = {}
        }
        sendJson(res, {
          query_id: 901,
          result_id: 902,
          status: 'completed',
          data: {
            status: 'success',
            query_type: body.query_type,
            data: [{ id: 1, text: 'mock social post' }],
          },
        })
      })
      return
    }

    if (method === 'GET' && path === '/api/osint/recent-searches') {
      return sendJson(res, [])
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
