import './FinancialInvestWatchReport.css'

export type InvestWatchSector = {
  label: string
  verdict: string
  score: number | null
  band: string
  kind?: string
}

export type InvestWatchKeyMetric = {
  label: string
  value: string
  kind?: string
}

export type InvestWatchEinaOverlay = {
  linked?: boolean
  policy_link?: string
  beneficiary_rationale?: string
  sectors?: string[]
  external_signal?: string
  private_action?: string
  blended_return_index?: number
  external_return_index?: number
  eina_confidence_avg?: number
}

export type InvestWatchReport = {
  layout?: string
  company?: string | null
  ticker?: string | null
  title?: string
  parse_mode?: string
  praams_ratio?: number | null
  recommendation?: string | null
  recommendation_class?: string
  analyst_upside_pct?: number | null
  headline?: string
  narrative?: string
  narrative_source?: string
  signal?: string
  has_clock?: boolean
  risk_sectors?: InvestWatchSector[]
  return_sectors?: InvestWatchSector[]
  key_risk_summaries?: string[]
  key_return_summaries?: string[]
  key_metrics?: InvestWatchKeyMetric[]
  eina_overlay?: InvestWatchEinaOverlay
}

type Props = {
  report: InvestWatchReport
  compact?: boolean
  showNarrative?: boolean
  /** external = PRAAMS/informe only; crossover = legacy combined card */
  variant?: 'external' | 'crossover'
}

function scorePct(score: number | null | undefined): number {
  if (score == null || Number.isNaN(score)) return 0
  return Math.min(100, Math.max(8, (score / 7) * 100))
}

function SectorCell({ sector, variant }: { sector: InvestWatchSector; variant: 'risk' | 'return' }) {
  const pct = scorePct(sector.score)
  return (
    <div
      className={`iw-sector iw-sector--${variant} iw-sector--${sector.band || 'unknown'}`}
      title={sector.score != null ? `${sector.label}: ${sector.score}/7` : sector.label}
    >
      <div className="iw-sector__bar-track">
        <div className="iw-sector__bar-fill" style={{ height: `${pct}%` }} />
      </div>
      <div className="iw-sector__body">
        <span className="iw-sector__label">{sector.label}</span>
        <span className="iw-sector__verdict">{sector.verdict}</span>
        {sector.score != null ? (
          <span className="iw-sector__score">{sector.score}/7</span>
        ) : null}
      </div>
    </div>
  )
}

function signalLabel(signal: string | undefined): string | null {
  if (!signal) return null
  if (signal === 'more_return_than_risk') return 'Retorn > risc'
  if (signal === 'more_risk_than_return') return 'Risc > retorn'
  if (signal === 'neutral') return 'Equilibrat'
  return signal
}

export function FinancialInvestWatchReport({
  report,
  compact = false,
  showNarrative = true,
  variant = 'crossover',
}: Props) {
  const isExternal = variant === 'external'
  const risk = report.risk_sectors ?? []
  const ret = report.return_sectors ?? []
  const rec = report.recommendation
  const recClass = report.recommendation_class || 'neutral'
  const overlay = report.eina_overlay ?? {}
  const ratio = report.praams_ratio

  return (
    <article
      className={`iw-report${compact ? ' iw-report--compact' : ''}`}
      data-testid="investwatch-report"
      data-parse-mode={report.parse_mode}
    >
      <header className="iw-report__header">
        <div className="iw-report__header-top">
          <span className="iw-report__brand">
            {isExternal ? 'Informe extern' : 'EINA · Informe creuat'}
          </span>
          {report.parse_mode === 'praams_investwatch' ? (
            <span className="iw-report__source-tag">PRAAMS InvestWatch</span>
          ) : report.parse_mode === 'investwatch' ? (
            <span className="iw-report__source-tag">InvestWatch</span>
          ) : report.parse_mode ? (
            <span className="iw-report__source-tag">{report.parse_mode}</span>
          ) : null}
        </div>
        <div className="iw-report__header-main">
          <div className="iw-report__identity">
            <h3 className="iw-report__company">{report.company || 'Empresa no identificada'}</h3>
            <div className="iw-report__meta">
              {report.ticker ? <span className="iw-report__ticker">{report.ticker}</span> : null}
              {report.title ? (
                <span className="iw-report__doc-title" title={report.title}>
                  {report.title.length > 48 ? `${report.title.slice(0, 48)}…` : report.title}
                </span>
              ) : null}
            </div>
            {report.headline ? <p className="iw-report__headline">{report.headline}</p> : null}
          </div>
          {ratio != null ? (
            <div className="iw-report__ratio" aria-label={`PRAAMS Ratio ${ratio} de 7`}>
              <span className="iw-report__ratio-value">{ratio}</span>
              <span className="iw-report__ratio-scale">/7</span>
              <span className="iw-report__ratio-label">PRAAMS Ratio</span>
            </div>
          ) : null}
        </div>
      </header>

      {(risk.length > 0 || ret.length > 0) && (
        <div className="iw-report__clock">
          <section className="iw-report__half iw-report__half--risk" aria-label="Factors de risc">
            <h4 className="iw-report__half-title">
              <span className="iw-report__half-dot iw-report__half-dot--risk" />
              Risc
            </h4>
            <div className="iw-report__sectors">
              {risk.length > 0 ? (
                risk.map((s) => <SectorCell key={`risk-${s.label}`} sector={s} variant="risk" />)
              ) : (
                <p className="iw-report__empty-half">Sense factors de risc estructurats</p>
              )}
            </div>
            {!compact && (report.key_risk_summaries?.length ?? 0) > 0 ? (
              <ul className="iw-report__bullets iw-report__bullets--risk">
                {report.key_risk_summaries!.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <div className="iw-report__clock-divider" aria-hidden />

          <section className="iw-report__half iw-report__half--return" aria-label="Factors de retorn">
            <h4 className="iw-report__half-title">
              <span className="iw-report__half-dot iw-report__half-dot--return" />
              Retorn
            </h4>
            <div className="iw-report__sectors">
              {ret.length > 0 ? (
                ret.map((s) => <SectorCell key={`ret-${s.label}`} sector={s} variant="return" />)
              ) : (
                <p className="iw-report__empty-half">Sense factors de retorn estructurats</p>
              )}
            </div>
            {!compact && (report.key_return_summaries?.length ?? 0) > 0 ? (
              <ul className="iw-report__bullets iw-report__bullets--return">
                {report.key_return_summaries!.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            ) : null}
          </section>
        </div>
      )}

      {(rec || report.analyst_upside_pct != null) && (
        <div className={`iw-report__rec iw-report__rec--${recClass}`}>
          {rec ? <strong className="iw-report__rec-action">{rec}</strong> : null}
          {report.analyst_upside_pct != null ? (
            <span className="iw-report__rec-upside">Upside consens {report.analyst_upside_pct}%</span>
          ) : null}
          {signalLabel(report.signal) ? (
            <span className="iw-report__rec-signal">{signalLabel(report.signal)}</span>
          ) : null}
        </div>
      )}

      {(report.key_metrics?.length ?? 0) > 0 && (
        <div className="iw-report__metrics">
          {report.key_metrics!.map((m) => (
            <div
              key={m.label}
              className={`iw-report__metric iw-report__metric--${m.kind || 'other'}`}
            >
              <span className="iw-report__metric-label">{m.label}</span>
              <span className="iw-report__metric-value">{m.value}</span>
            </div>
          ))}
        </div>
      )}

      {showNarrative && report.narrative ? (
        <div className="iw-report__narrative">
          <span className="iw-report__narrative-badge">
            {isExternal
              ? 'Síntesi informe extern'
              : report.narrative_source === 'llm'
                ? 'Resum IA'
                : 'Síntesi per regles'}
          </span>
          <p>{report.narrative}</p>
        </div>
      ) : null}

      {!isExternal ? (
      <footer className="iw-report__eina">
        <div className="iw-report__eina-header">
          <span className="iw-report__eina-label">Creuament EINA</span>
          {overlay.linked ? (
            <span className="iw-report__eina-badge iw-report__eina-badge--linked">Vinculat al cas</span>
          ) : (
            <span className="iw-report__eina-badge">Sense vincle registre</span>
          )}
        </div>
        <div className="iw-report__eina-grid">
          {overlay.external_signal ? (
            <div className="iw-report__eina-stat">
              <span className="iw-report__eina-stat-label">Senyal extern</span>
              <strong>{overlay.external_signal}</strong>
            </div>
          ) : null}
          {overlay.private_action ? (
            <div className="iw-report__eina-stat">
              <span className="iw-report__eina-stat-label">Acció privada</span>
              <strong>{overlay.private_action}</strong>
            </div>
          ) : null}
          {overlay.external_return_index != null ? (
            <div className="iw-report__eina-stat">
              <span className="iw-report__eina-stat-label">Índex retorn extern</span>
              <strong>{overlay.external_return_index}</strong>
            </div>
          ) : null}
          {overlay.blended_return_index != null ? (
            <div className="iw-report__eina-stat">
              <span className="iw-report__eina-stat-label">Índex combinat</span>
              <strong>{overlay.blended_return_index}</strong>
            </div>
          ) : null}
          {overlay.eina_confidence_avg != null ? (
            <div className="iw-report__eina-stat">
              <span className="iw-report__eina-stat-label">Confiança EINA</span>
              <strong>{overlay.eina_confidence_avg}%</strong>
            </div>
          ) : null}
        </div>
        {overlay.policy_link ? (
          <p className="iw-report__eina-policy">
            <strong>Policy×Indústria:</strong> {overlay.policy_link}
          </p>
        ) : null}
        {overlay.beneficiary_rationale ? (
          <p className="iw-report__eina-rationale">{overlay.beneficiary_rationale}</p>
        ) : null}
        {(overlay.sectors?.length ?? 0) > 0 ? (
          <div className="iw-report__eina-sectors">
            {overlay.sectors!.map((s) => (
              <span key={s} className="iw-report__sector-chip">
                {s}
              </span>
            ))}
          </div>
        ) : null}
      </footer>
      ) : null}
    </article>
  )
}
