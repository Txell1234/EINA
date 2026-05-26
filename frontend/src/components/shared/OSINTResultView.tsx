import { useState } from 'react'
import { ChevronDown, ChevronRight, ExternalLink, FileText, Filter } from 'lucide-react'
import { Link } from 'react-router-dom'
import { parseOsintPayload, queryTypeLabel } from '../../utils/osintDisplay'
import './OSINTResultView.css'

type OSINTResultViewProps = {
  data: Record<string, unknown>
  queryType?: string
  status?: string
  createdAt?: string
  resultId?: number | null
  compact?: boolean
}

export default function OSINTResultView({
  data,
  queryType = 'osint',
  status = 'completed',
  createdAt,
  resultId,
  compact = false,
}: OSINTResultViewProps) {
  const [showRaw, setShowRaw] = useState(false)
  const parsed = parseOsintPayload(data, queryType, status)

  return (
    <div className={`osint-result-view ${compact ? 'osint-result-view--compact' : ''}`}>
      <div className="osint-result-view__meta">
        <span className="osint-result-view__badge">{queryTypeLabel(parsed.queryType)}</span>
        {createdAt ? (
          <span className="osint-result-view__date">
            {new Date(createdAt).toLocaleString('ca-ES')}
          </span>
        ) : null}
        {resultId ? <span className="osint-result-view__id">#{resultId}</span> : null}
      </div>

      {parsed.error ? <p className="osint-result-view__error">{parsed.error}</p> : null}

      {parsed.scopeFilter ? (
        <p className="osint-result-view__scope">
          <Filter size={12} />
          Filtre d&apos;àmbit: {String(parsed.scopeFilter.kept ?? '?')} articles conservats
          {parsed.scopeFilter.removed_topic != null
            ? ` · ${parsed.scopeFilter.removed_topic} fora de tema`
            : ''}
        </p>
      ) : null}

      {parsed.researchReport ? (
        <div className="osint-result-view__research">
          <h4>
            <FileText size={14} /> Informe Tavily Research
            {parsed.researchReport.sourceCount > 0
              ? ` · ${parsed.researchReport.sourceCount} fonts`
              : ''}
          </h4>
          <p className="osint-result-view__research-text">{parsed.researchReport.excerpt}</p>
          <Link to="/prospective" className="osint-result-view__action">
            Analitzar a l&apos;extracció prospectiva →
          </Link>
        </div>
      ) : null}

      {parsed.articles.length > 0 ? (
        <ul className="osint-result-view__articles">
          {parsed.articles.slice(0, compact ? 5 : 20).map((a, i) => (
            <li key={`${a.url}-${i}`} className="osint-result-view__article">
              <div className="osint-result-view__article-head">
                <strong>{a.title}</strong>
                {a.frontpageScore > 0 ? (
                  <span className="osint-result-view__score" title="Score editorial GFG">
                    {Math.round(a.frontpageScore * 100)}%
                  </span>
                ) : null}
              </div>
              <p className="osint-result-view__article-meta">
                {a.domain || a.source}
                {a.date ? ` · ${a.date.slice(0, 10)}` : ''}
                {a.enriched ? ' · cos complet' : a.textLen < 200 ? ' · snippet curt' : ''}
              </p>
              {a.summary ? <p className="osint-result-view__summary">{a.summary}</p> : null}
              {a.url ? (
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="osint-result-view__link">
                  <ExternalLink size={12} /> Obrir font
                </a>
              ) : null}
            </li>
          ))}
          {parsed.articles.length > (compact ? 5 : 20) ? (
            <li className="osint-result-view__more">
              +{parsed.articles.length - (compact ? 5 : 20)} articles més guardats al cas
            </li>
          ) : null}
        </ul>
      ) : null}

      {!parsed.error && parsed.articles.length === 0 && !parsed.researchReport ? (
        <p className="osint-result-view__empty">Consulta completada sense articles recuperables.</p>
      ) : null}

      <button type="button" className="osint-result-view__raw-toggle" onClick={() => setShowRaw((v) => !v)}>
        {showRaw ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {showRaw ? 'Amagar JSON tècnic' : 'Veure JSON tècnic'}
      </button>
      {showRaw ? <pre className="osint-result-view__raw">{JSON.stringify(data, null, 2)}</pre> : null}
    </div>
  )
}
