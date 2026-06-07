import type { GeopoliticalCaseSummary } from './GeopoliticalConfidencePanel'

/** Map API geopolitical-confidence bundle to panel summary shape. */
export function mapGeoBundleToSummary(data: Record<string, unknown> | null | undefined): GeopoliticalCaseSummary | null {
  if (!data || data.found === false) return null
  const caseIcg = data.case_icg as { index?: number } | undefined
  return {
    geopolitical_confidence_index: (data.geopolitical_confidence_index ?? caseIcg?.index) as number | null,
    case_geopolitical_confidence_index: (data.case_geopolitical_confidence_index ?? caseIcg?.index) as number | null,
    entity_confidence_index: data.entity_confidence_index as number | null,
    entity_icg_delta: data.entity_icg_delta as number | null,
    focus_company: data.focus_company as string | null,
    geopolitical_confidence_components: (data.geopolitical_confidence_components ?? data.components) as GeopoliticalCaseSummary['geopolitical_confidence_components'],
    entity_confidence_components: data.entity_confidence_components as GeopoliticalCaseSummary['entity_confidence_components'],
    geopolitical_confidence_formula: data.geopolitical_confidence_formula as string,
    entity_confidence_formula: data.entity_confidence_formula as string,
    entity_confidence_detail: data.entity_confidence_detail as string | null,
    confidence_detail: data.confidence_detail as string | null,
    gpr_case_level: data.gpr_case_level as number | null,
    gpr_multiplier_applied: data.gpr_multiplier_applied as number | null,
    eina_gma: data.eina_gma as number | null,
    eina_gma_formula: data.eina_gma_formula as string,
    eina_gma_components: data.eina_gma_components as Record<string, number>,
    sanction_impact_score: data.sanction_impact_score as number | null,
    sanction_drivers: data.sanction_drivers as GeopoliticalCaseSummary['sanction_drivers'],
    sanction_entity_impacts: data.sanction_entity_impacts as GeopoliticalCaseSummary['sanction_entity_impacts'],
    sanction_scenario_adjustments: data.sanction_scenario_adjustments as Record<string, number>,
    sanction_trend_signals: data.sanction_trend_signals as string[],
    driver_interactions: data.driver_interactions as GeopoliticalCaseSummary['driver_interactions'],
    eina_confidence_source: data.confidence_source as string | null,
    investment_recommendation: (data.investment_posture as { recommendation?: string } | undefined)?.recommendation,
    investment_confidence_pct: (data.investment_posture as { confidence_pct?: number } | undefined)?.confidence_pct,
    investment_posture_source: (data.investment_posture as { source?: string } | undefined)?.source,
    investment_rationale: (data.investment_posture as { rationale?: string } | undefined)?.rationale,
    entity_investment_recommendation: (data.entity_investment_posture as { recommendation?: string } | undefined)
      ?.recommendation,
    entity_investment_confidence_pct: (data.entity_investment_posture as { confidence_pct?: number } | undefined)
      ?.confidence_pct,
    entity_investment_posture_source: (data.entity_investment_posture as { source?: string } | undefined)?.source,
    entity_investment_rationale: (data.entity_investment_posture as { rationale?: string } | undefined)?.rationale,
    osint_signals: (data.actor_impact_snapshot as { osint_signals?: GeopoliticalCaseSummary['osint_signals'] } | undefined)?.osint_signals,
  }
}
