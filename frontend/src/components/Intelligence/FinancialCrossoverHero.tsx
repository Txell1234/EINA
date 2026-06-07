import './FinancialCrossoverHero.css'

type FinalNumbers = {
  external_return_index?: number
  external_risk_index?: number
  eina_investment_confidence_avg?: number
  geopolitical_confidence_index?: number
  case_geopolitical_confidence_index?: number
  entity_geopolitical_confidence_index?: number
  entity_icg_delta?: number
  blended_return_index?: number
  blended_risk_index?: number
  crossover_score_10?: number
}

type Props = {
  entity?: string | null
  externalSignal?: string | null
  einaRecommendation?: string | null
  entityRecommendation?: string | null
  privateAction?: string | null
  finalNumbers?: FinalNumbers
  synthesisParagraphs?: string[]
  alignments?: Array<{ summary?: string; because?: string }>
  divergences?: Array<{ summary?: string; because?: string }>
  confidenceSource?: string | null
  confidenceDetail?: string | null
  geopoliticalConfidenceIndex?: number | null
  caseGeopoliticalConfidenceIndex?: number | null
  entityGeopoliticalConfidenceIndex?: number | null
  entityIcgDelta?: number | null
  investmentPostureSource?: string | null
}

function scoreFromBlend(blended?: number, explicit?: number): number | null {
  if (explicit != null && !Number.isNaN(explicit)) return explicit
  if (blended == null || Number.isNaN(blended)) return null
  return Math.round((blended / 10) * 10) / 10
}

function clampPct(value: number): number {
  return Math.max(0, Math.min(100, value))
}

function IcgDualBars({
  caseIcg,
  entityIce,
  entityLabel,
  delta,
}: {
  caseIcg: number
  entityIce: number
  entityLabel?: string | null
  delta?: number | null
}) {
  return (
    <div className="crossover-hero__icg-bars" data-testid="icg-dual-bars">
      <div className="crossover-hero__icg-bar crossover-hero__icg-bar--case">
        <div className="crossover-hero__icg-bar-head">
          <span className="crossover-hero__icg-bar-label">ICG cas · context geopolític compartit</span>
          <strong>{caseIcg}%</strong>
        </div>
        <div
          className="crossover-hero__icg-bar-track"
          role="progressbar"
          aria-valuenow={clampPct(caseIcg)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`ICG cas ${caseIcg} per cent`}
        >
          <div className="crossover-hero__icg-bar-fill" style={{ width: `${clampPct(caseIcg)}%` }} />
        </div>
      </div>
      <div className="crossover-hero__icg-bar crossover-hero__icg-bar--entity">
        <div className="crossover-hero__icg-bar-head">
          <span className="crossover-hero__icg-bar-label">
            ICE entitat{entityLabel ? ` · ${entityLabel}` : ''}
          </span>
          <strong>
            {entityIce}%
            {delta != null ? (
              <span className="crossover-hero__delta">
                {' '}
                ({delta >= 0 ? '+' : ''}
                {delta} pp)
              </span>
            ) : null}
          </strong>
        </div>
        <div
          className="crossover-hero__icg-bar-track"
          role="progressbar"
          aria-valuenow={clampPct(entityIce)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`ICE entitat ${entityIce} per cent`}
        >
          <div className="crossover-hero__icg-bar-fill" style={{ width: `${clampPct(entityIce)}%` }} />
        </div>
      </div>
    </div>
  )
}

export function FinancialCrossoverHero({
  entity,
  externalSignal,
  einaRecommendation,
  entityRecommendation,
  privateAction,
  finalNumbers,
  synthesisParagraphs,
  alignments,
  divergences,
  confidenceSource,
  confidenceDetail,
  geopoliticalConfidenceIndex,
  caseGeopoliticalConfidenceIndex,
  entityGeopoliticalConfidenceIndex,
  entityIcgDelta,
  investmentPostureSource,
}: Props) {
  const fn = finalNumbers ?? {}
  const score10 = scoreFromBlend(fn.blended_return_index, fn.crossover_score_10)
  const iceDisplay =
    entityGeopoliticalConfidenceIndex ??
    fn.entity_geopolitical_confidence_index ??
    geopoliticalConfidenceIndex ??
    fn.geopolitical_confidence_index ??
    (confidenceSource !== 'default_fallback' && confidenceSource !== 'missing'
      ? fn.eina_investment_confidence_avg
      : null)
  const caseIcgDisplay =
    caseGeopoliticalConfidenceIndex ??
    fn.case_geopolitical_confidence_index ??
    geopoliticalConfidenceIndex ??
    fn.geopolitical_confidence_index
  const deltaDisplay = entityIcgDelta ?? fn.entity_icg_delta
  const showDualIcgBars =
    caseIcgDisplay != null &&
    iceDisplay != null &&
    (entityGeopoliticalConfidenceIndex != null ||
      fn.entity_geopolitical_confidence_index != null ||
      Boolean(entity))

  return (
    <article className="crossover-hero" data-testid="crossover-hero">
      <header className="crossover-hero__header">
        <span className="crossover-hero__eyebrow">Resultat del creuament</span>
        <h4 className="crossover-hero__title">
          EINA + informe extern
          {entity ? (
            <>
              {' · '}
              <strong>{entity}</strong>
            </>
          ) : null}
        </h4>
        <p className="crossover-hero__lead">
          Anàlisi combinada: dades PRAAMS/informe extern per empresa, ponderades amb escenaris Godet,
          Policy×Indústria i confiança geo (ICG_cas + ICE entitat quan hi ha focus).
        </p>
      </header>

      <div className="crossover-hero__score-row">
        {score10 != null ? (
          <div className="crossover-hero__score-main" aria-label={`Puntuació creuament ${score10} sobre 10`}>
            <span className="crossover-hero__score-value">{score10}</span>
            <span className="crossover-hero__score-denom">/10</span>
            <span className="crossover-hero__score-label">Índex creuament (retorn blend)</span>
          </div>
        ) : null}
        <div className="crossover-hero__kpis">
          {externalSignal ? (
            <div className="crossover-hero__kpi crossover-hero__kpi--external">
              <span className="crossover-hero__kpi-label">Informe extern</span>
              <strong>{externalSignal}</strong>
            </div>
          ) : null}
          {einaRecommendation ? (
            <div className="crossover-hero__kpi crossover-hero__kpi--eina">
              <span className="crossover-hero__kpi-label">EINA cas</span>
              <strong>{einaRecommendation}</strong>
            </div>
          ) : null}
          {entityRecommendation ? (
            <div className="crossover-hero__kpi crossover-hero__kpi--entity">
              <span className="crossover-hero__kpi-label">Entitat</span>
              <strong>{entityRecommendation}</strong>
            </div>
          ) : null}
          {privateAction ? (
            <div className="crossover-hero__kpi">
              <span className="crossover-hero__kpi-label">Acció privada</span>
              <strong>{privateAction}</strong>
            </div>
          ) : null}
          {fn.blended_return_index != null ? (
            <div className="crossover-hero__kpi">
              <span className="crossover-hero__kpi-label">Retorn combinat</span>
              <strong>{fn.blended_return_index}</strong>
            </div>
          ) : null}
          {fn.blended_risk_index != null ? (
            <div className="crossover-hero__kpi">
              <span className="crossover-hero__kpi-label">Risc combinat</span>
              <strong>{fn.blended_risk_index}</strong>
            </div>
          ) : null}
          {!showDualIcgBars && iceDisplay != null ? (
            <div className="crossover-hero__kpi crossover-hero__kpi--eina">
              <span className="crossover-hero__kpi-label">
                {entityGeopoliticalConfidenceIndex != null || fn.entity_geopolitical_confidence_index != null
                  ? 'ICE entitat'
                  : 'Confiança geo-estratègica'}
              </span>
              <strong>
                {iceDisplay}%
                {deltaDisplay != null ? (
                  <span className="crossover-hero__delta">
                    {' '}
                    ({deltaDisplay >= 0 ? '+' : ''}
                    {deltaDisplay} pp)
                  </span>
                ) : null}
              </strong>
            </div>
          ) : !showDualIcgBars && confidenceSource === 'missing' ? (
            <div className="crossover-hero__kpi crossover-hero__kpi--eina">
              <span className="crossover-hero__kpi-label">Confiança geo</span>
              <strong>Pendent</strong>
            </div>
          ) : null}
          {!showDualIcgBars &&
          caseIcgDisplay != null &&
          (entityGeopoliticalConfidenceIndex != null || fn.entity_geopolitical_confidence_index != null) ? (
            <div className="crossover-hero__kpi">
              <span className="crossover-hero__kpi-label">ICG cas</span>
              <strong>{caseIcgDisplay}%</strong>
            </div>
          ) : null}
        </div>
      </div>

      {showDualIcgBars ? (
        <IcgDualBars
          caseIcg={caseIcgDisplay!}
          entityIce={iceDisplay!}
          entityLabel={entity}
          delta={deltaDisplay}
        />
      ) : null}

      {confidenceSource === 'default_fallback' || investmentPostureSource === 'default_fallback' ? (
        <p className="crossover-hero__confidence-warn">
          ⚠ {confidenceDetail ||
            'Recomanació inversió HOLD 50% per defecte — no és confiança geo. Executa intel·ligència al cas.'}
        </p>
      ) : confidenceSource === 'missing' ? (
        <p className="crossover-hero__confidence-warn">
          Confiança geo pendent — executa intel·ligència o impacte actors al cas.
        </p>
      ) : confidenceDetail ? (
        <p className="crossover-hero__confidence-note">{confidenceDetail}</p>
      ) : null}

      {synthesisParagraphs && synthesisParagraphs.length > 0 ? (
        <div className="crossover-hero__synthesis">
          {synthesisParagraphs.map((p, i) => (
            <p key={`syn-${i}`}>{p}</p>
          ))}
        </div>
      ) : null}

      {(divergences?.length ?? 0) > 0 || (alignments?.length ?? 0) > 0 ? (
        <div className="crossover-hero__judgments">
          {divergences?.slice(0, 2).map((d) => (
            <p key={d.summary} className="crossover-hero__judgment crossover-hero__judgment--warn">
              <strong>Divergència:</strong> {d.summary}
            </p>
          ))}
          {alignments?.slice(0, 1).map((a) => (
            <p key={a.summary} className="crossover-hero__judgment crossover-hero__judgment--ok">
              <strong>Alineació:</strong> {a.summary}
            </p>
          ))}
        </div>
      ) : null}
    </article>
  )
}
