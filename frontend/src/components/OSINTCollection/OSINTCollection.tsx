import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCase } from '../../contexts/CaseContext'
import { casesService, osintService } from '../../services/api'
import './OSINTCollection.css'

interface OSINTResult {
  id: number
  query_type: string
  status: string
  data: Record<string, unknown>
  created_at: string
}

interface SourceConfig {
  id: string
  label: string
  category: 'geopolitica' | 'notícies' | 'infraestructura'
  description: string
  requiresKey: boolean
  fields: Array<{ name: string; label: string; placeholder: string; type?: string }>
  endpoint: string
  buildParams: (vals: Record<string, string>, caseId: number | null) => Record<string, unknown>
}

const SOURCES: SourceConfig[] = [
  {
    id: 'gdelt',
    label: 'GDELT',
    category: 'geopolitica',
    description:
      'Events geopolítics globals en temps real. Cobreix 250+ països, 100+ idiomes. Gratuït.',
    requiresKey: false,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: China BRI Indo-Pacific' },
      { name: 'days', label: 'Dies enrere', placeholder: '7', type: 'number' },
    ],
    endpoint: 'gdelt',
    buildParams: (v, caseId) => ({
      query: v.query,
      days: parseInt(v.days || '7', 10),
      case_id: caseId,
    }),
  },
  {
    id: 'rss',
    label: 'Think-tanks i governs (RSS)',
    category: 'geopolitica',
    description:
      'IISS, Chatham House, RAND, CFR, CSIS, ICG, Brookings, Elcano, Foreign Affairs, ECFR. Gratuït.',
    requiresKey: false,
    fields: [{ name: 'source', label: 'Font', placeholder: 'cfr', type: 'select' }],
    endpoint: 'rss',
    buildParams: (v, caseId) => ({ source: v.source || 'cfr', case_id: caseId }),
  },
  {
    id: 'rss_all',
    label: 'Tots els think-tanks (RSS)',
    category: 'geopolitica',
    description: 'Agrega IISS, CFR, CSIS, Brookings, Elcano i la resta en una sola consulta.',
    requiresKey: false,
    fields: [{ name: 'max_items', label: 'Màx. per font', placeholder: '10', type: 'number' }],
    endpoint: 'rss/all',
    buildParams: (v, caseId) => ({
      max_items: parseInt(v.max_items || '10', 10),
      case_id: caseId,
    }),
  },
  {
    id: 'opensanctions',
    label: 'OpenSanctions',
    category: 'geopolitica',
    description: 'Sancions de 100+ governs (OFAC, UE, ONU, OFSI). Gratuït ús no comercial.',
    requiresKey: false,
    fields: [{ name: 'query', label: 'Entitat o persona', placeholder: 'Ex.: Rosneft' }],
    endpoint: 'opensanctions',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'google_news',
    label: 'Google News',
    category: 'notícies',
    description: 'Articles de premsa en temps real via NewsAPI.',
    requiresKey: true,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: India China trade' }],
    endpoint: 'google-news',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'reddit',
    label: 'Reddit',
    category: 'notícies',
    description: 'Posts i discussions. Sense API key.',
    requiresKey: false,
    fields: [
      { name: 'query', label: 'Cerca', placeholder: 'Ex.: geopolitics BRI' },
      { name: 'subreddit', label: 'Subreddit', placeholder: 'worldnews (opcional)' },
    ],
    endpoint: 'reddit',
    buildParams: (v, caseId) => ({
      query: v.query,
      subreddit: v.subreddit || undefined,
      case_id: caseId,
    }),
  },
  {
    id: 'github',
    label: 'GitHub',
    category: 'infraestructura',
    description: 'Repositoris, codi i organitzacions. Útil per a actors tècnics.',
    requiresKey: false,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: chinese military AI' }],
    endpoint: 'github',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'shodan',
    label: 'Shodan',
    category: 'infraestructura',
    description: 'Dispositius i serveis exposats a Internet. Requereix SHODAN_API_KEY.',
    requiresKey: true,
    fields: [{ name: 'query', label: 'Cerca', placeholder: 'Ex.: apache country:ES' }],
    endpoint: 'shodan',
    buildParams: (v, caseId) => ({ query: v.query, case_id: caseId }),
  },
  {
    id: 'ip_geolocation',
    label: 'Geolocalització IP',
    category: 'infraestructura',
    description: 'Ubicació i dades de seguretat d\'una adreça IP via ipstack.',
    requiresKey: true,
    fields: [{ name: 'ip', label: 'Adreça IP', placeholder: 'Ex.: 8.8.8.8' }],
    endpoint: 'ip-geolocation',
    buildParams: (v, caseId) => ({ ip_address: v.ip, case_id: caseId }),
  },
  {
    id: 'dns',
    label: 'DNS Lookup',
    category: 'infraestructura',
    description: 'Resolució de noms de domini. Sense API key.',
    requiresKey: false,
    fields: [{ name: 'domain', label: 'Domini', placeholder: 'Ex.: example.com' }],
    endpoint: 'dns',
    buildParams: (v, caseId) => ({ domain: v.domain, case_id: caseId }),
  },
  {
    id: 'whois',
    label: 'WHOIS',
    category: 'infraestructura',
    description: 'Informació de registre de domini. Sense API key.',
    requiresKey: false,
    fields: [{ name: 'domain', label: 'Domini', placeholder: 'Ex.: example.com' }],
    endpoint: 'whois',
    buildParams: (v, caseId) => ({ domain: v.domain, case_id: caseId }),
  },
  {
    id: 'wayback',
    label: 'Wayback Machine',
    category: 'infraestructura',
    description: 'Historial web. Veu contingut eliminat i canvis. Gratuït.',
    requiresKey: false,
    fields: [{ name: 'url', label: 'URL', placeholder: 'https://example.com' }],
    endpoint: 'wayback',
    buildParams: (v, caseId) => ({ url: v.url, case_id: caseId }),
  },
]

const RSS_SOURCES = [
  { value: 'cfr', label: 'Council on Foreign Relations' },
  { value: 'iiss', label: 'IISS' },
  { value: 'chatham_house', label: 'Chatham House' },
  { value: 'rand', label: 'RAND Corporation' },
  { value: 'csis', label: 'CSIS' },
  { value: 'icg', label: 'International Crisis Group' },
  { value: 'brookings', label: 'Brookings Institution' },
  { value: 'elcano', label: 'Real Instituto Elcano' },
  { value: 'foreign_affairs', label: 'Foreign Affairs' },
  { value: 'ecfr', label: 'ECFR' },
]

const CATEGORIES = [
  { id: 'geopolitica', label: '◈ Geopolítica' },
  { id: 'notícies', label: '○ Notícies' },
  { id: 'infraestructura', label: '⊞ Infraestructura' },
] as const

export default function OSINTCollection() {
  const { activeCase, setActiveCase } = useCase()
  const [selectedCategory, setSelectedCategory] = useState<string>('geopolitica')
  const [selectedSource, setSelectedSource] = useState<string>('gdelt')
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})
  const [results, setResults] = useState<OSINTResult[]>([])
  const [resultError, setResultError] = useState<string | null>(null)

  const source = SOURCES.find((s) => s.id === selectedSource) || SOURCES[0]

  const { data: cases } = useQuery({
    queryKey: ['cases-list'],
    queryFn: () => casesService.list(),
  })

  const searchMutation = useMutation({
    mutationFn: async () => {
      setResultError(null)
      const params = source.buildParams(fieldValues, activeCase?.id ?? null)
      return osintService.search(source.endpoint, params)
    },
    onSuccess: (data) => {
      setResults((prev) => [data as OSINTResult, ...prev].slice(0, 50))
    },
    onError: (err: Error) => {
      setResultError(err.message)
    },
  })

  const sourcesInCategory = SOURCES.filter((s) => s.category === selectedCategory)

  return (
    <div className="osint-layout">
      <aside className="osint-sidebar">
        <div className="osint-case-selector">
          <label className="osint-field-label">Cas actiu</label>
          <select
            className="osint-select"
            value={activeCase?.id ?? ''}
            onChange={(e) => {
              const id = Number(e.target.value)
              const c = (cases as { id: number; name: string }[])?.find((x) => x.id === id)
              if (c) setActiveCase({ id: c.id, name: c.name, case_type: '', status: 'actiu' })
            }}
          >
            <option value="">— Sense cas —</option>
            {((cases as { id: number; name: string }[]) ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>
          {activeCase && (
            <div className="osint-case-badge">
              Cas: <strong>{activeCase.name}</strong>
            </div>
          )}
        </div>

        <div className="osint-categories">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`osint-category-btn ${selectedCategory === cat.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedCategory(cat.id)
                const first = SOURCES.find((s) => s.category === cat.id)
                if (first) {
                  setSelectedSource(first.id)
                  setFieldValues({})
                }
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="osint-source-list">
          {sourcesInCategory.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`osint-source-btn ${selectedSource === s.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedSource(s.id)
                setFieldValues({})
              }}
            >
              <span className="osint-source-name">{s.label}</span>
              {s.requiresKey && <span className="osint-key-badge">clau API</span>}
            </button>
          ))}
        </div>
      </aside>

      <main className="osint-main">
        <div className="card osint-form-card">
          <h2 className="osint-source-title">{source.label}</h2>
          <p className="osint-source-desc">{source.description}</p>

          <div className="osint-fields">
            {source.fields.map((field) => (
              <div key={field.name} className="osint-field">
                <label className="osint-field-label" htmlFor={`field-${field.name}`}>
                  {field.label}
                </label>
                {field.type === 'select' && field.name === 'source' ? (
                  <select
                    id={`field-${field.name}`}
                    className="osint-select"
                    value={fieldValues[field.name] ?? 'cfr'}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                  >
                    {RSS_SOURCES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`field-${field.name}`}
                    className="osint-input"
                    type={field.type || 'text'}
                    placeholder={field.placeholder}
                    value={fieldValues[field.name] ?? ''}
                    onChange={(e) =>
                      setFieldValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') searchMutation.mutate()
                    }}
                  />
                )}
              </div>
            ))}
          </div>

          <div className="osint-form-actions">
            <button
              type="button"
              className="btn btn-accent"
              disabled={searchMutation.isPending}
              onClick={() => searchMutation.mutate()}
            >
              {searchMutation.isPending ? 'Cercant...' : `Cercar amb ${source.label}`}
            </button>
            {results.length > 0 && (
              <button type="button" className="btn" onClick={() => setResults([])}>
                Netejar resultats
              </button>
            )}
          </div>

          {resultError && <div className="osint-alert osint-alert--error">{resultError}</div>}
        </div>

        {results.length > 0 && (
          <div className="osint-results">
            <h3 className="osint-results-title">
              {results.length} resultat{results.length !== 1 ? 's' : ''}
            </h3>
            {results.map((r, i) => (
              <div key={i} className="card osint-result-card">
                <div className="osint-result-header">
                  <span className="status-badge neutral">{r.query_type}</span>
                  <span className="osint-result-date">
                    {new Date(r.created_at).toLocaleString('ca-ES')}
                  </span>
                </div>
                <pre className="osint-result-data">{JSON.stringify(r.data, null, 2)}</pre>
              </div>
            ))}
          </div>
        )}

        {results.length === 0 && !searchMutation.isPending && (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">◎</div>
              <h3 className="empty-state-title">Cap resultat encara</h3>
              <p className="empty-state-desc">
                Selecciona una font OSINT, omple els camps i executa la cerca.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
