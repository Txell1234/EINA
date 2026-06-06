import { useCallback, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { extractService, osintService } from '../../services/api'
import './ExtractionCoverage.css'

export interface ExtractionCoverageData {
  case_id: number
  coverage_percent: number
  articles: {
    articles_total: number
    extractable: number
    enriched: number
    needs_enrichment: number
    extracted_urls: number
    pending_extraction: number
    pending_thin: number
    top_domains: Array<{ domain: string; count: number }>
  }
  statements: {
    total: number
    by_decision: Record<string, number>
  }
  osint: {
    orphan_queries_global: number
    error_results: number
  }
  alerts: {
    pending_extraction: number
    short_excerpt: number
  }
  recommendations: string[]
}

interface ExtractionCoveragePanelProps {
  caseId: number
  compact?: boolean
  showExtractButton?: boolean
  showRepairOrphans?: boolean
  scope?: import('../../types/analysisScope').AnalysisScope
  applyScopeToExtraction?: boolean
}

export default function ExtractionCoveragePanel({
  caseId,
  compact = false,
  showExtractButton = true,
  showRepairOrphans = true,
  scope,
  applyScopeToExtraction = false,
}: ExtractionCoveragePanelProps) {
  const queryClient = useQueryClient()
  const [extractRunning, setExtractRunning] = useState(false)
  const [extractProgress, setExtractProgress] = useState<string | null>(null)
  const [repairBusy, setRepairBusy] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['extraction-coverage', caseId],
    queryFn: () => extractService.getCoverage(caseId),
    enabled: caseId > 0,
    staleTime: 20_000,
  })

  const cov = data as ExtractionCoverageData | undefined

  const startExtractPending = useCallback(() => {
    if (extractRunning) return
    setExtractRunning(true)
    setExtractProgress('Iniciant…')
    esRef.current?.close()
    const es = new EventSource(
      extractService.getPendingStreamUrl(caseId, {
        applyScope: applyScopeToExtraction,
        scope,
      }),
    )
    esRef.current = es
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as {
          event?: string
          current?: number
          total?: number
          total_extracted?: number
          message?: string
        }
        if (payload.event === 'start') {
          setExtractProgress(`0 / ${payload.total ?? 0} articles`)
        }
        if (payload.event === 'progress') {
          setExtractProgress(`${payload.current ?? 0} / ${payload.total ?? 0} articles`)
        }
        if (payload.event === 'done') {
          setExtractProgress(`Fet — ${payload.total_extracted ?? 0} declaracions`)
          setExtractRunning(false)
          es.close()
          void refetch()
          void queryClient.invalidateQueries({ queryKey: ['extract-statements', caseId] })
        }
        if (payload.event === 'error') {
          setExtractProgress(payload.message ?? 'Error')
          setExtractRunning(false)
          es.close()
        }
      } catch {
        /* ignore */
      }
    }
    es.onerror = () => {
      setExtractRunning(false)
      es.close()
    }
  }, [caseId, extractRunning, queryClient, refetch, applyScopeToExtraction, scope])

  const repairOrphans = async () => {
    setRepairBusy(true)
    try {
      const res = await osintService.repairOrphans(caseId)
      await refetch()
      setExtractProgress(`${res.repaired ?? 0} consultes assignades al cas #${caseId}`)
    } finally {
      setRepairBusy(false)
    }
  }

  if (isLoading || !cov) {
    return (
      <div className={`extraction-coverage ${compact ? 'extraction-coverage--compact' : ''}`}>
        <p className="extraction-coverage-loading">Carregant cobertura d&apos;extracció…</p>
      </div>
    )
  }

  const a = cov.articles ?? {
    articles_total: 0,
    extractable: 0,
    enriched: 0,
    needs_enrichment: 0,
    extracted_urls: 0,
    pending_extraction: 0,
    pending_thin: 0,
    top_domains: [],
  }
  const pct = cov.coverage_percent ?? 0

  return (
    <div className={`extraction-coverage ${compact ? 'extraction-coverage--compact' : ''}`}>
      <div className="extraction-coverage-header">
        <h4>Cobertura fonts → extracció</h4>
        <span className={`extraction-coverage-pct ${pct >= 50 ? 'ok' : pct >= 20 ? 'mid' : 'low'}`}>
          {pct}%
        </span>
      </div>

      <div className="extraction-coverage-bars">
        <div className="extraction-coverage-row">
          <span>Articles recollits</span>
          <strong>{a?.articles_total ?? 0}</strong>
        </div>
        <div className="extraction-coverage-row">
          <span>Extractables</span>
          <strong>{a.extractable}</strong>
        </div>
        <div className="extraction-coverage-row">
          <span>Enriqueïts (cos complet)</span>
          <strong>{a.enriched}</strong>
        </div>
        <div className="extraction-coverage-row highlight">
          <span>Pendents d&apos;extracció</span>
          <strong>{a.pending_extraction}</strong>
        </div>
        <div className="extraction-coverage-row">
          <span>URLs ja extretes</span>
          <strong>{a.extracted_urls}</strong>
        </div>
        <div className="extraction-coverage-row">
          <span>Declaracions totals</span>
          <strong>{cov.statements?.total ?? 0}</strong>
        </div>
        {cov.alerts.pending_extraction > 0 && (
          <div className="extraction-coverage-row warn">
            <span>Alertes pendents</span>
            <strong>{cov.alerts.pending_extraction}</strong>
          </div>
        )}
      </div>

      {!compact && cov.recommendations.length > 0 && (
        <ul className="extraction-coverage-recs">
          {cov.recommendations.slice(0, 4).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}

      <div className="extraction-coverage-actions">
        {showExtractButton && a.pending_extraction > 0 && (
          <button
            type="button"
            className="btn btn-primary"
            disabled={extractRunning}
            onClick={startExtractPending}
          >
            {extractRunning ? 'Extraint…' : 'Extreure tot el pendent'}
          </button>
        )}
        {showRepairOrphans && cov.osint.orphan_queries_global > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={repairBusy}
            onClick={repairOrphans}
          >
            {repairBusy ? 'Reparant…' : `Reparar ${cov.osint.orphan_queries_global} consultes orfes`}
          </button>
        )}
        <button type="button" className="btn btn-ghost" onClick={() => refetch()}>
          Actualitzar
        </button>
      </div>

      {extractProgress && <p className="extraction-coverage-progress">{extractProgress}</p>}
    </div>
  )
}
