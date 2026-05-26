export type OsintArticleView = {
  title: string
  url: string
  domain: string
  date: string
  source: string
  summary: string
  textLen: number
  enriched: boolean
  extracted: boolean
  frontpageScore: number
}

export type OsintParsedResult = {
  queryType: string
  status: string
  error: string | null
  articles: OsintArticleView[]
  researchReport: { excerpt: string; sourceCount: number; requestId?: string } | null
  scopeFilter: Record<string, unknown> | null
  rawFallback: boolean
}

const SOURCE_LABELS: Record<string, string> = {
  gdelt: 'GDELT',
  gdelt_gfg: 'GDELT Portades',
  tavily: 'Tavily',
  tavily_extract: 'Tavily Extract',
  tavily_crawl: 'Tavily Crawl',
  tavily_map: 'Tavily Map',
  tavily_research: 'Tavily Research',
  rss_feed: 'Think tank / RSS',
  rss_all: 'RSS (tots)',
  rss_url: 'RSS URL',
  bloomberg: 'Bloomberg',
  nikkei: 'Nikkei Asia',
  google_news: 'Google News',
}

export function queryTypeLabel(qt: string): string {
  return SOURCE_LABELS[qt] ?? qt.replace(/_/g, ' ')
}

function domainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function textLen(item: Record<string, unknown>): number {
  const parts = ['summary', 'description', 'content', 'snippet', 'text', 'body']
    .map((k) => String(item[k] ?? ''))
    .join(' ')
  return parts.trim().length
}

function normalizeArticle(raw: Record<string, unknown>, hint = ''): OsintArticleView | null {
  const title = String(raw.title ?? raw.name ?? raw.headline ?? '').trim()
  const url = String(raw.url ?? raw.link ?? raw.source_url ?? '').trim()
  const summary = String(raw.summary ?? raw.description ?? raw.content ?? raw.snippet ?? raw.text ?? '').trim()
  if (!title && !url && !summary) return null
  return {
    title: title || 'Sense titular',
    url,
    domain: domainFromUrl(url),
    date: String(raw.date ?? raw.publishedAt ?? raw.published ?? raw.seendate ?? '').slice(0, 19),
    source: String(raw.source ?? raw.domain ?? hint ?? ''),
    summary: summary.slice(0, 280),
    textLen: textLen(raw),
    enriched: Boolean(raw.enriched),
    extracted: false,
    frontpageScore: Number(raw.frontpage_score ?? raw.importance_score ?? 0),
  }
}

function flattenArticles(data: Record<string, unknown>): OsintArticleView[] {
  const out: OsintArticleView[] = []
  const hint = String(data.source ?? '')
  for (const key of ['articles', 'items', 'results']) {
    const list = data[key]
    if (!Array.isArray(list)) continue
    for (const item of list) {
      if (item && typeof item === 'object') {
        const row = normalizeArticle(item as Record<string, unknown>, hint)
        if (row) out.push(row)
      }
    }
  }
  if (!out.length && Array.isArray(data.urls)) {
    for (const u of data.urls.slice(0, 30)) {
      const url = String(u)
      out.push({
        title: url,
        url,
        domain: domainFromUrl(url),
        date: '',
        source: 'tavily_map',
        summary: '',
        textLen: 0,
        enriched: false,
        extracted: false,
        frontpageScore: 0,
      })
    }
  }
  return out
}

export function parseOsintPayload(
  data: Record<string, unknown> | undefined | null,
  queryType = 'osint',
  status = 'completed',
): OsintParsedResult {
  if (!data || typeof data !== 'object') {
    return {
      queryType,
      status,
      error: 'Sense dades',
      articles: [],
      researchReport: null,
      scopeFilter: null,
      rawFallback: true,
    }
  }

  const err =
    data.status === 'error' || data.error
      ? String(data.error ?? data.message ?? 'Error OSINT')
      : null

  const reportRaw = data.research_report
  const researchReport =
    typeof reportRaw === 'string' && reportRaw.trim()
      ? {
          excerpt: reportRaw.slice(0, 600) + (reportRaw.length > 600 ? '…' : ''),
          sourceCount: Array.isArray(data.sources) ? data.sources.length : 0,
          requestId: data.request_id ? String(data.request_id) : undefined,
        }
      : null

  const articles = flattenArticles(data)
  const scopeFilter =
    data._scope_filter && typeof data._scope_filter === 'object'
      ? (data._scope_filter as Record<string, unknown>)
      : null

  return {
    queryType,
    status,
    error: err,
    articles,
    researchReport,
    scopeFilter,
    rawFallback: !articles.length && !researchReport && !err,
  }
}

export type CaseInventory = {
  case_id: number
  summary: {
    total_queries: number
    total_articles: number
    unique_articles: number
    extracted_urls: number
    pending_extraction: number
    research_reports: number
    top_domains: Array<{ domain: string; count: number }>
  }
  source_groups: Array<{
    query_type: string
    label: string
    query_count: number
    article_count: number
    runs: Array<{
      query_id: number
      result_id: number | null
      created_at: string | null
      params_summary: string
      status: string
      error: string | null
      article_count: number
      articles: Array<{
        title: string
        url: string
        domain: string
        date: string
        summary: string
        extracted: boolean
        enriched: boolean
      }>
      research_report: { excerpt: string; source_count: number } | null
    }>
  }>
  research_briefs: Array<{ excerpt: string; source_count?: number; created_at?: string }>
  recommended_actions: string[]
}
