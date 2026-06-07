import './GeopoliticalConfidencePanel.css'

export type ConfidenceComponent = {
  name?: string
  label?: string
  value?: number
  weight?: number
  base_weight?: number
  because?: string
}

export type OsintSignals = {
  avg_geopolitical_risk?: number
  hostility_ratio?: number
  conflict_events?: number
  countries_at_risk?: number
}

export type GeopoliticalCaseSummary = {
  geopolitical_confidence_index?: number | null
  case_geopolitical_confidence_index?: number | null
  entity_confidence_index?: number | null
  entity_icg_delta?: number | null
  focus_company?: string | null
  geopolitical_confidence_components?: ConfidenceComponent[]
  entity_confidence_components?: ConfidenceComponent[]
  geopolitical_confidence_formula?: string
  entity_confidence_formula?: string
  entity_confidence_detail?: string | null
  confidence_detail?: string | null
  gpr_case_level?: number | null
  gpr_multiplier_applied?: number | null
  eina_gma?: number | null
  eina_gma_formula?: string
  eina_gma_components?: Record<string, number>
  sanction_impact_score?: number | null
  sanction_drivers?: Array<{ type?: string; excerpt?: string; weight?: number }>
  sanction_entity_impacts?: Array<{
    entity?: string
    entity_type?: string
    score?: number
    prob_adjust_pp?: number
    because?: string
  }>
  sanction_scenario_adjustments?: Record<string, number>
  sanction_trend_signals?: string[]
  driver_interactions?: Array<{
    pair?: string
    direction?: string
    score?: number
    because?: string
  }>
  eina_confidence_pct?: number | null
  eina_confidence_source?: string | null
  eina_confidence_detail?: string | null
  investment_recommendation?: string | null
  investment_confidence_pct?: number | null
  investment_posture_source?: string | null
  investment_posture_detail?: string | null
  investment_rationale?: string
  osint_signals?: OsintSignals
}

type Props = {
  summary?: GeopoliticalCaseSummary | null
}

function ComponentList({ components }: { components: ConfidenceComponent[] }) {
  return (
    <ul className="geo-confidence-panel__component-list">
      {components.map((c) => (
        <li key={c.name ?? c.label} className="geo-confidence-panel__component-row">
          <div className="geo-confidence-panel__component-head">
            <span className="geo-confidence-panel__component-label">{c.label ?? c.name}</span>
            <span className="geo-confidence-panel__component-value">{c.value}%</span>
            {c.weight != null ? (
              <span className="geo-confidence-panel__component-weight">pes {Math.round(c.weight * 100)}%</span>
            ) : null}
          </div>
          <div
            className="geo-confidence-panel__component-bar"
            role="presentation"
            style={{ width: `${Math.min(100, c.value ?? 0)}%` }}
          />
          {c.because ? <p className="geo-confidence-panel__component-because">{c.because}</p> : null}
        </li>
      ))}
    </ul>
  )
}

export function GeopoliticalConfidencePanel({ summary }: Props) {
  if (!summary) return null

  const caseIcg =
    summary.case_geopolitical_confidence_index ?? summary.geopolitical_confidence_index ?? null
  const entityIce = summary.entity_confidence_index ?? null
  const caseComponents = summary.geopolitical_confidence_components ?? []
  const entityComponents = summary.entity_confidence_components ?? []
  const source = summary.eina_confidence_source
  const postureSource = summary.investment_posture_source
  const signals = summary.osint_signals
  const delta = summary.entity_icg_delta
  const focusCompany = summary.focus_company

  return (
    <section className="geo-confidence-panel" data-testid="geo-confidence-panel">
      <div className="geo-confidence-panel__case-block" data-testid="geo-confidence-case">
        <header className="geo-confidence-panel__header">
          <h4>ICG del cas (marc compartit)</h4>
          {source ? (
            <span className={`geo-confidence-panel__badge geo-confidence-panel__badge--${source}`}>
              {source === 'computed' ? 'Calculat' : source === 'partial' ? 'Parcial' : source === 'missing' ? 'Pendent' : source}
            </span>
          ) : null}
        </header>

        {caseIcg != null ? (
          <div className="geo-confidence-panel__icg-main">
            <span className="geo-confidence-panel__icg-value">{caseIcg}%</span>
            <span className="geo-confidence-panel__icg-label">
              Confiança geo-estratègica del marc Hormuz / cas (sense focus empresa)
            </span>
          </div>
        ) : (
          <p className="geo-confidence-panel__missing">
            Confiança geo pendent — executa el pipeline d&apos;intel·ligència al cas (OSINT + impacte actors).
          </p>
        )}

        {summary.confidence_detail ? (
          <p className="geo-confidence-panel__detail">{summary.confidence_detail}</p>
        ) : null}

        {summary.geopolitical_confidence_formula ? (
          <details className="geo-confidence-panel__formula">
            <summary>Fórmula ICG_cas</summary>
            <p>{summary.geopolitical_confidence_formula}</p>
            {summary.gpr_case_level != null ? (
              <p className="geo-confidence-panel__formula-note">
                GPR cas: {summary.gpr_case_level}
                {summary.gpr_multiplier_applied != null
                  ? ` · multiplicador pes risc: ${summary.gpr_multiplier_applied}`
                  : null}
              </p>
            ) : null}
          </details>
        ) : null}

        {caseComponents.length > 0 ? (
          <div className="geo-confidence-panel__components">
            <h5>Desglossament ICG_cas</h5>
            <ComponentList components={caseComponents} />
          </div>
        ) : null}
      </div>

      {entityIce != null && focusCompany ? (
        <div className="geo-confidence-panel__entity-block" data-testid="geo-confidence-entity">
          <header className="geo-confidence-panel__header">
            <h4>ICE entitat · {focusCompany}</h4>
            {delta != null ? (
              <span
                className={`geo-confidence-panel__delta ${
                  delta >= 0 ? 'geo-confidence-panel__delta--up' : 'geo-confidence-panel__delta--down'
                }`}
              >
                {delta >= 0 ? '+' : ''}
                {delta} pp vs cas
              </span>
            ) : null}
          </header>

          <div className="geo-confidence-panel__icg-main geo-confidence-panel__icg-main--entity">
            <span className="geo-confidence-panel__icg-value">{entityIce}%</span>
            <span className="geo-confidence-panel__icg-label">
              Confiança geo-estratègica específica d&apos;aquesta empresa dins el cas
            </span>
          </div>

          {summary.entity_confidence_detail ? (
            <p className="geo-confidence-panel__detail">{summary.entity_confidence_detail}</p>
          ) : null}

          {summary.entity_confidence_formula ? (
            <details className="geo-confidence-panel__formula">
              <summary>Fórmula ICE</summary>
              <p>{summary.entity_confidence_formula}</p>
            </details>
          ) : null}

          {entityComponents.length > 0 ? (
            <div className="geo-confidence-panel__components">
              <h5>Desglossament ICE</h5>
              <ComponentList components={entityComponents} />
            </div>
          ) : null}
        </div>
      ) : null}

      {summary.eina_gma != null ? (
        <div className="geo-confidence-panel__gma">
          <h5>EINA-GMA (atenció geo del cas)</h5>
          <p>
            <strong>{summary.eina_gma}%</strong>
            {summary.eina_gma_formula ? (
              <span className="geo-confidence-panel__gma-formula"> · {summary.eina_gma_formula}</span>
            ) : null}
          </p>
        </div>
      ) : null}

      {summary.sanction_impact_score != null ? (
        <div className="geo-confidence-panel__sis">
          <h5>Impacte sancions (SIS) — informatiu</h5>
          <p className="geo-confidence-panel__sis-score">
            Score <strong>{summary.sanction_impact_score}</strong>/100
            {(summary.sanction_trend_signals?.length ?? 0) > 0 ? (
              <> · {summary.sanction_trend_signals!.join(' · ')}</>
            ) : null}
          </p>
          {(summary.sanction_drivers?.length ?? 0) > 0 ? (
            <ul className="geo-confidence-panel__sis-drivers">
              {summary.sanction_drivers!.slice(0, 5).map((d) => (
                <li key={`${d.type}-${d.excerpt?.slice(0, 20)}`}>
                  <strong>{d.type}</strong>: {d.excerpt}
                </li>
              ))}
            </ul>
          ) : null}
          {(summary.sanction_entity_impacts?.length ?? 0) > 0 ? (
            <table className="geo-confidence-panel__sis-table">
              <thead>
                <tr>
                  <th>Entitat</th>
                  <th>Tipus</th>
                  <th>Score</th>
                  <th>Δ prob.</th>
                </tr>
              </thead>
              <tbody>
                {summary.sanction_entity_impacts!.map((e) => (
                  <tr key={e.entity}>
                    <td>{e.entity}</td>
                    <td>{e.entity_type}</td>
                    <td>{e.score}</td>
                    <td>{e.prob_adjust_pp != null ? `${e.prob_adjust_pp} pp` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {summary.sanction_scenario_adjustments &&
          Object.keys(summary.sanction_scenario_adjustments).length > 0 ? (
            <p className="geo-confidence-panel__sis-adj">
              Ajust escenaris (informatiu):{' '}
              {Object.entries(summary.sanction_scenario_adjustments)
                .slice(0, 4)
                .map(([k, v]) => `${k} ${v > 0 ? '+' : ''}${v} pp`)
                .join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}

      {(summary.driver_interactions?.length ?? 0) > 0 ? (
        <div className="geo-confidence-panel__interactions">
          <h5>Interaccions de drivers (regles traçables)</h5>
          <ul>
            {summary.driver_interactions!.map((ix) => (
              <li key={ix.pair}>
                <strong>{ix.pair}</strong>
                {ix.score != null ? ` · score ${ix.score}` : ''}: {ix.because}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {(summary.investment_recommendation || summary.investment_confidence_pct != null) && (
        <div className="geo-confidence-panel__posture">
          <h5>Postura d&apos;inversió del cas (separada de l&apos;ICG)</h5>
          <p>
            <strong>{summary.investment_recommendation ?? '—'}</strong>
            {summary.investment_confidence_pct != null ? (
              <> · confiança {summary.investment_confidence_pct}%</>
            ) : null}
            {postureSource === 'default_fallback' ? (
              <span className="geo-confidence-panel__posture-warn"> (valor per defecte)</span>
            ) : null}
          </p>
          {summary.investment_posture_detail ? (
            <p className="geo-confidence-panel__posture-warn">{summary.investment_posture_detail}</p>
          ) : summary.investment_rationale ? (
            <p className="geo-confidence-panel__posture-rationale">{summary.investment_rationale}</p>
          ) : null}
        </div>
      )}

      {signals && Object.keys(signals).length > 0 ? (
        <div className="geo-confidence-panel__signals">
          <h5>Correlats del cas (OSINT)</h5>
          <table className="geo-confidence-panel__corr-table">
            <tbody>
              {signals.avg_geopolitical_risk != null ? (
                <tr>
                  <td>Risc geo mitjà</td>
                  <td>{signals.avg_geopolitical_risk}/100</td>
                </tr>
              ) : null}
              {signals.hostility_ratio != null ? (
                <tr>
                  <td>Hostilitat</td>
                  <td>{Math.round(signals.hostility_ratio * 100)}%</td>
                </tr>
              ) : null}
              {signals.conflict_events != null ? (
                <tr>
                  <td>Conflictes</td>
                  <td>{signals.conflict_events}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
