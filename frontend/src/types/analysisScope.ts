// @refresh reset

export type PeriodPreset = '7' | '30' | '90' | '180' | '365' | 'custom'
export interface AnalysisScope {
  periodDays: number | null
  startDate: string
  endDate: string
  periodPreset: PeriodPreset
  applyTopicFilter: boolean
  domains: string
  sources: string
  minRelevance: number
}

export interface AnalyticalProfile {
  analysis_lenses?: string[]
  lens_labels?: Record<string, string>
  actor_classes_focus?: string[]
  institution_subtypes_focus?: string[]
  institution_subtype_labels?: Record<string, string>
  scenario_types?: string[]
  scenario_profiles?: Record<string, { label?: string; risk_profile?: string; reversibility?: string }>
  theme_labels?: Record<string, string>
  horizon_public_months?: [number, number]
  horizon_private_months?: [number, number]
  case_type?: string
}

export interface CaseScopeProfile {
  case_id: number
  focus_label: string
  suggested_query: string
  suggested_queries?: string[]
  keywords: string[]
  primary_geos: string[]
  themes: string[]
  case_type?: string
  analytical_profile?: AnalyticalProfile | null
  default_scope: Partial<AnalysisScope>
}

export const DEFAULT_SCOPE: AnalysisScope = {
  periodDays: 90,
  startDate: '',
  endDate: '',
  periodPreset: '90',
  applyTopicFilter: true,
  domains: '',
  sources: '',
  minRelevance: 0.28,
}

export function resolveOsintSearchQuery(profile: CaseScopeProfile): string {
  const raw = profile.suggested_query?.trim() ?? ''
  const words = raw.split(/\s+/).filter(Boolean)
  const looksFocused =
    words.length > 0 &&
    words.length <= 6 &&
    /rearmament|geoeconomic|sanction|diplomatic|military|defense|indo-/i.test(raw)

  if (looksFocused) return raw

  const themePriority = ['rearmament', 'indo_pacific', 'sanctions', 'diplomacy'] as const
  const themeLabels: Record<string, string> = {
    rearmament: 'rearmament',
    indo_pacific: 'indo-pacific',
    sanctions: 'sanctions',
    diplomacy: 'diplomatic',
  }
  const theme =
    themePriority.find((t) => profile.themes?.includes(t)) ?? profile.themes?.[0]
  const themeWord = theme ? themeLabels[theme] ?? theme.replace(/_/g, ' ') : 'geopolitical'

  const geoRank = ['japan', 'japó', 'japon', 'japo', 'xina', 'china', 'corea', 'korea']
  let geoEn = 'Japan'
  for (const rank of geoRank) {
    const hit = profile.primary_geos?.find((g) => g.toLowerCase().includes(rank))
    if (hit) {
      if (rank.includes('jap')) geoEn = 'Japan'
      else if (rank.includes('xin') || rank.includes('chin')) geoEn = 'China'
      else if (rank.includes('cor') || rank.includes('kor')) geoEn = 'Korea'
      break
    }
  }

  return `${geoEn} ${themeWord}`.trim()
}

export function isGenericGeoQuery(query: string): boolean {
  const words = query.trim().split(/\s+/).filter(Boolean)
  return (
    words.length > 5 &&
    !/rearmament|geoeconomic|sanction|diplomatic|military|defense|indo-/i.test(query)
  )
}

export function scopeToTimeRange(scope: AnalysisScope): { start: string; end: string } | undefined {
  if (scope.periodPreset === 'custom' && scope.startDate && scope.endDate) {
    return { start: scope.startDate, end: scope.endDate }
  }
  const days = scope.periodDays ?? (parseInt(scope.periodPreset, 10) || 90)
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days)
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  }
}

export function scopeDomainsList(scope: AnalysisScope): string[] {
  return scope.domains
    .split(/[,;\s]+/)
    .map((d) => d.trim().toLowerCase())
    .filter(Boolean)
}

export function scopeSourcesList(scope: AnalysisScope): string[] {
  return scope.sources
    .split(/[,;\s]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
}

export function scopeToExtractQuery(scope: AnalysisScope, applyScope: boolean): string {
  if (!applyScope) return ''
  const tr = scopeToTimeRange(scope)
  const params = new URLSearchParams()
  params.set('apply_scope', 'true')
  params.set('apply_topic_filter', String(scope.applyTopicFilter))
  if (scope.periodDays) params.set('period_days', String(scope.periodDays))
  if (tr?.start) params.set('start_date', tr.start)
  if (tr?.end) params.set('end_date', tr.end)
  if (scope.domains.trim()) params.set('domains', scope.domains.trim())
  params.set('min_relevance', String(scope.minRelevance))
  return params.toString()
}

export function scopeToOsintParams(scope: AnalysisScope): Record<string, unknown> {
  const tr = scopeToTimeRange(scope)
  return {
    apply_topic_filter: scope.applyTopicFilter,
    scope_min_relevance: scope.minRelevance,
    scope_domains: scopeDomainsList(scope),
    scope_start_date: tr?.start,
    scope_end_date: tr?.end,
    days: scope.periodDays ?? (parseInt(scope.periodPreset, 10) || 90),
    _analysis_scope: {
      period_days: scope.periodDays ?? (parseInt(scope.periodPreset, 10) || null),
      start_date: tr?.start,
      end_date: tr?.end,
      apply_topic_filter: scope.applyTopicFilter,
      domains: scopeDomainsList(scope),
      sources: scopeSourcesList(scope),
      min_relevance: scope.minRelevance,
    },
  }
}
