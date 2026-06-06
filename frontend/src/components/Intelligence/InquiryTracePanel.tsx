import './InquiryTracePanel.css'

export type ScopeAuditData = {
  required_terms?: string[]
  min_required_matches?: number
  negative_terms?: string[]
  osint_queries?: string[]
  audit?: Record<string, number | string>
  rejected_samples?: Array<{
    title?: string
    url?: string
    score?: number
    reasons?: string[]
    required_hits?: number
  }>
}

export type AuditTrailEntry = {
  at?: string
  event?: string
  detail?: Record<string, unknown>
}

type InquiryTracePanelProps = {
  scopeAudit?: ScopeAuditData | null
  auditTrail?: AuditTrailEntry[]
  evidence?: Array<Record<string, unknown>>
  reasoning?: Array<{ conclusion?: string; because?: string; sources?: Array<{ origin?: string }> }>
  godetStatus?: {
    godet_ready?: boolean
    project_id?: number | null
    checklist?: Record<string, boolean>
    missing_steps?: string[]
    can_synthesize?: boolean
  } | null
  onSynthesize?: () => void
  synthesizePending?: boolean
}

export default function InquiryTracePanel({
  scopeAudit,
  auditTrail = [],
  evidence = [],
  reasoning = [],
  godetStatus,
  onSynthesize,
  synthesizePending,
}: InquiryTracePanelProps) {
  const audit = scopeAudit?.audit ?? {}
  const rejected = scopeAudit?.rejected_samples ?? []

  return (
    <div className="inquiry-trace">
      {godetStatus && (
        <section className="inquiry-trace__section">
          <h4>Estat Godet</h4>
          <p>
            {godetStatus.godet_ready ? 'Complet — llest per síntesi' : 'Incomplet — completa el wizard'}
            {godetStatus.project_id ? ` · Projecte #${godetStatus.project_id}` : ''}
          </p>
          {godetStatus.checklist && (
            <ul className="inquiry-trace__checklist">
              {Object.entries(godetStatus.checklist).map(([key, ok]) => (
                <li key={key} className={ok ? 'inquiry-trace__ok' : 'inquiry-trace__missing'}>
                  {ok ? '✓' : '○'} {key}
                </li>
              ))}
            </ul>
          )}
          {godetStatus.can_synthesize && onSynthesize && (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={synthesizePending}
              onClick={onSynthesize}
            >
              {synthesizePending ? 'Sintetitzant…' : 'Executar síntesi final'}
            </button>
          )}
        </section>
      )}

      {scopeAudit && (
        <section className="inquiry-trace__section">
          <h4>Auditoria scope OSINT</h4>
          {scopeAudit.required_terms && scopeAudit.required_terms.length > 0 && (
            <p className="inquiry-trace__terms">
              Termes obligatoris ({scopeAudit.min_required_matches ?? 2} mín.):{' '}
              {scopeAudit.required_terms.slice(0, 8).join(', ')}
            </p>
          )}
          <ul className="inquiry-trace__stats">
            {['input', 'kept', 'removed_topic', 'removed_must_match', 'queries_run'].map((k) =>
              audit[k] != null ? (
                <li key={k}>
                  {k}: {String(audit[k])}
                </li>
              ) : null,
            )}
          </ul>
          {rejected.length > 0 && (
            <details open>
              <summary>Articles descartats ({rejected.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Títol</th>
                    <th>Score</th>
                    <th>Motiu</th>
                  </tr>
                </thead>
                <tbody>
                  {rejected.map((row) => (
                    <tr key={`${row.url ?? row.title}`}>
                      <td>
                        {row.url ? (
                          <a href={row.url} target="_blank" rel="noreferrer">
                            {(row.title ?? row.url).slice(0, 70)}
                          </a>
                        ) : (
                          (row.title ?? '—').slice(0, 70)
                        )}
                      </td>
                      <td>{row.score != null ? row.score.toFixed?.(2) ?? row.score : '—'}</td>
                      <td>{(row.reasons ?? []).slice(0, 2).join('; ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}
        </section>
      )}

      {evidence.length > 0 && (
        <section className="inquiry-trace__section">
          <h4>Evidències traçables</h4>
          <ul>
            {evidence.map((ev) => (
              <li key={`${ev.kind}-${ev.label}`}>
                [{String(ev.kind ?? 'item')}] {String(ev.label ?? '')}
                {ev.value != null ? `: ${String(ev.value)}` : ''}
                {ev.origin ? ` (${String(ev.origin)})` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}

      {reasoning.some((r) => r.sources?.length) && (
        <section className="inquiry-trace__section">
          <h4>Fonts del raonament</h4>
          <ul>
            {reasoning.map((r) =>
              (r.sources ?? []).map((s) => (
                <li key={`${r.conclusion}-${s.origin}`}>
                  {r.conclusion?.slice(0, 60)}… → {s.origin}
                  {s.field ? `.${s.field}` : ''}
                </li>
              )),
            )}
          </ul>
        </section>
      )}

      {auditTrail.length > 0 && (
        <section className="inquiry-trace__section">
          <h4>Audit trail ({auditTrail.length})</h4>
          <ol className="inquiry-trace__trail">
            {auditTrail.map((entry, i) => (
              <li key={`${entry.at}-${entry.event}-${i}`}>
                <time>{entry.at ?? '—'}</time> — {entry.event ?? 'event'}
                {entry.detail && Object.keys(entry.detail).length > 0
                  ? `: ${JSON.stringify(entry.detail).slice(0, 120)}`
                  : ''}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}
