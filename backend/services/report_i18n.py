"""Traduccions per als informes prospectius (ca / es / en)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReportLang = Literal["ca", "es", "en"]


@dataclass(frozen=True)
class ReportStrings:
    report_title: str
    report_subtitle: str
    generated: str
    project_id: str
    toc: str
    executive_summary: str
    es_objective: str
    es_hypothesis: str
    es_context: str
    es_osint: str
    es_variables: str
    es_scenarios: str
    es_actors: str
    es_risks: str
    es_conclusions: str
    es_limitations: str
    key_factors: str
    variables_section: str
    var_profile: str
    var_type: str
    var_description: str
    var_motivation: str
    var_micmac: str
    var_sector: str
    var_motricity: str
    var_dependence: str
    var_osint_rationale: str
    var_relations: str
    var_evidence: str
    var_type_i: str
    var_type_e: str
    var_type_m: str
    no_data: str
    project_section: str
    hypothesis: str
    context: str
    articles: str
    statements: str
    scenarios: str
    possibility: str
    probability: str
    most_likely: str
    traceability_warning: str
    outlook_what_to_watch: str
    outlook_key_risks: str
    outlook_key_opportunities: str
    outlook_scenarios: str
    outlook_dominant_scenario: str
    outlook_motricity: str
    outlook_high_dependence: str
    outlook_risk: str
    outlook_risk_default: str
    outlook_confidence: str
    outlook_opportunity: str
    outlook_scenario_window: str
    report_variant_full: str
    report_variant_analytical: str
    outlook_source_note: str
    actor_map_title: str
    actor_map_lead: str
    actor_map_posture_worse: str
    actor_map_posture_better: str
    actor_map_geo_risk: str
    actor_map_no_detail: str
    actor_map_source_note: str
    actor_map_case_focus: str
    actor_map_statements: str
    actor_map_mactor: str
    actor_map_force: str
    actor_map_no_geo: str


_STRINGS: dict[str, ReportStrings] = {
    "ca": ReportStrings(
        report_title="Informe prospectiu · EINA",
        report_subtitle="Anàlisi estratègica OSINT · MIC-MAC · MACTOR · Escenaris",
        generated="Generat",
        project_id="ID projecte",
        toc="Índex de continguts",
        executive_summary="Resum executiu",
        es_objective="Objectiu de l'anàlisi",
        es_hypothesis="Hipòtesi central",
        es_context="Context estratègic",
        es_osint="Evidència OSINT",
        es_variables="Variables clau (MIC-MAC)",
        es_scenarios="Panorama d'escenaris",
        es_actors="Impacte sobre actors",
        es_risks="Factors de risc i oportunitats",
        es_conclusions="Conclusions principals",
        es_limitations="Limitacions i qualitat de dades",
        key_factors="Factors determinants",
        variables_section="Variables — perfil i motivació",
        var_profile="Perfil de variable",
        var_type="Tipus",
        var_description="Descripció",
        var_motivation="Motivació i rellevància",
        var_micmac="Classificació MIC-MAC",
        var_sector="Sector Godet",
        var_motricity="Motricitat",
        var_dependence="Dependència",
        var_osint_rationale="Raonament OSINT",
        var_relations="Relacions clau",
        var_evidence="Evidència documental",
        var_type_i="Influential (I) — variable que condiciona el sistema",
        var_type_e="Exogenous (E) — factor extern poc controlable",
        var_type_m="Motor (M) — variable amb alta motricitat",
        no_data="Sense dades disponibles per a aquesta secció.",
        project_section="Projecte",
        hypothesis="Hipòtesi",
        context="Context",
        articles="articles recollits",
        statements="declaracions extretes",
        scenarios="Escenaris",
        possibility="Possibilitat",
        probability="Probabilitat",
        most_likely="Escenari més probable",
        traceability_warning="Avís: algunes conclusions manquen citació verificable.",
        outlook_what_to_watch="Què cal vigilar",
        outlook_key_risks="Riscos clau",
        outlook_key_opportunities="Oportunitats clau",
        outlook_scenarios="Escenaris amb probabilitat",
        outlook_dominant_scenario="Escenari dominant",
        outlook_motricity="motricitat",
        outlook_high_dependence="alta dependència sistèmica",
        outlook_risk="Risc",
        outlook_risk_default="Riscos derivats de la incertesa del sistema i la traçabilitat OSINT",
        outlook_confidence="confiança global",
        outlook_opportunity="Oportunitat",
        outlook_scenario_window="Finestra d'escenari plausible:",
        report_variant_full="Informe complet (metodologia + annexos)",
        report_variant_analytical="Informe analític (estil outlook EIU)",
        outlook_source_note="Font: síntesi Godet · OSINT · Policy×Indústria",
        actor_map_title="Mapa d'actors principals",
        actor_map_lead="Actors del projecte Godet d'aquest cas, amb el que sabem d'OSINT i MACTOR.",
        actor_map_posture_worse="Postura OSINT empitjorant en declaracions recents del cas.",
        actor_map_posture_better="Postura OSINT millorant en declaracions recents del cas.",
        actor_map_geo_risk="Risc geo",
        actor_map_no_detail="Actor definit al Godet del cas; encara sense traçabilitat OSINT detallada.",
        actor_map_source_note="Font: actors del projecte · impacte OSINT · MACTOR",
        actor_map_case_focus="Focus del cas",
        actor_map_statements="declaracions al cas",
        actor_map_mactor="Mobilització MACTOR",
        actor_map_force="Força estratègica",
        actor_map_no_geo="Sense ubicació geogràfica al mapa (actor institucional o multilateral).",
    ),
    "es": ReportStrings(
        report_title="Informe prospectivo · EINA",
        report_subtitle="Análisis estratégico OSINT · MIC-MAC · MACTOR · Escenarios",
        generated="Generado",
        project_id="ID proyecto",
        toc="Índice de contenidos",
        executive_summary="Resumen ejecutivo",
        es_objective="Objetivo del análisis",
        es_hypothesis="Hipótesis central",
        es_context="Contexto estratégico",
        es_osint="Evidencia OSINT",
        es_variables="Variables clave (MIC-MAC)",
        es_scenarios="Panorama de escenarios",
        es_actors="Impacto sobre actores",
        es_risks="Factores de riesgo y oportunidades",
        es_conclusions="Conclusiones principales",
        es_limitations="Limitaciones y calidad de datos",
        key_factors="Factores determinantes",
        variables_section="Variables — perfil y motivación",
        var_profile="Perfil de variable",
        var_type="Tipo",
        var_description="Descripción",
        var_motivation="Motivación y relevancia",
        var_micmac="Clasificación MIC-MAC",
        var_sector="Sector Godet",
        var_motricity="Motricidad",
        var_dependence="Dependencia",
        var_osint_rationale="Razonamiento OSINT",
        var_relations="Relaciones clave",
        var_evidence="Evidencia documental",
        var_type_i="Influyente (I) — variable que condiciona el sistema",
        var_type_e="Exógena (E) — factor externo poco controlable",
        var_type_m="Motor (M) — variable con alta motricidad",
        no_data="Sin datos disponibles para esta sección.",
        project_section="Proyecto",
        hypothesis="Hipótesis",
        context="Contexto",
        articles="artículos recopilados",
        statements="declaraciones extraídas",
        scenarios="Escenarios",
        possibility="Posibilidad",
        probability="Probabilidad",
        most_likely="Escenario más probable",
        traceability_warning="Aviso: algunas conclusiones carecen de cita verificable.",
        outlook_what_to_watch="Qué vigilar",
        outlook_key_risks="Riesgos clave",
        outlook_key_opportunities="Oportunidades clave",
        outlook_scenarios="Escenarios con probabilidad",
        outlook_dominant_scenario="Escenario dominante",
        outlook_motricity="motricidad",
        outlook_high_dependence="alta dependencia sistémica",
        outlook_risk="Riesgo",
        outlook_risk_default="Riesgos derivados de la incertidumbre del sistema y la trazabilidad OSINT",
        outlook_confidence="confianza global",
        outlook_opportunity="Oportunidad",
        outlook_scenario_window="Ventana de escenario plausible:",
        report_variant_full="Informe completo (metodología + anexos)",
        report_variant_analytical="Informe analítico (estilo outlook EIU)",
        outlook_source_note="Fuente: síntesis Godet · OSINT · Policy×Industria",
        actor_map_title="Mapa de actores principales",
        actor_map_lead="Actores del proyecto Godet de este caso, con lo que sabemos de OSINT y MACTOR.",
        actor_map_posture_worse="Postura OSINT empeorando en declaraciones recientes del caso.",
        actor_map_posture_better="Postura OSINT mejorando en declaraciones recientes del caso.",
        actor_map_geo_risk="Riesgo geo",
        actor_map_no_detail="Actor definido en el Godet del caso; aún sin trazabilidad OSINT detallada.",
        actor_map_source_note="Fuente: actores del proyecto · impacto OSINT · MACTOR",
        actor_map_case_focus="Foco del caso",
        actor_map_statements="declaraciones en el caso",
        actor_map_mactor="Movilización MACTOR",
        actor_map_force="Fuerza estratégica",
        actor_map_no_geo="Sin ubicación geográfica en el mapa (actor institucional o multilateral).",
    ),
    "en": ReportStrings(
        report_title="Prospective Report · EINA",
        report_subtitle="Strategic OSINT · MIC-MAC · MACTOR · Scenarios",
        generated="Generated",
        project_id="Project ID",
        toc="Table of contents",
        executive_summary="Executive summary",
        es_objective="Analysis objective",
        es_hypothesis="Central hypothesis",
        es_context="Strategic context",
        es_osint="OSINT evidence",
        es_variables="Key variables (MIC-MAC)",
        es_scenarios="Scenario outlook",
        es_actors="Actor impact",
        es_risks="Risk factors and opportunities",
        es_conclusions="Main conclusions",
        es_limitations="Limitations and data quality",
        key_factors="Determining factors",
        variables_section="Variables — profile and rationale",
        var_profile="Variable profile",
        var_type="Type",
        var_description="Description",
        var_motivation="Rationale and relevance",
        var_micmac="MIC-MAC classification",
        var_sector="Godet sector",
        var_motricity="Motricity",
        var_dependence="Dependence",
        var_osint_rationale="OSINT rationale",
        var_relations="Key relations",
        var_evidence="Documentary evidence",
        var_type_i="Influential (I) — variable shaping the system",
        var_type_e="Exogenous (E) — external, less controllable factor",
        var_type_m="Motor (M) — high motricity variable",
        no_data="No data available for this section.",
        project_section="Project",
        hypothesis="Hypothesis",
        context="Context",
        articles="articles collected",
        statements="statements extracted",
        scenarios="Scenarios",
        possibility="Possibility",
        probability="Probability",
        most_likely="Most likely scenario",
        traceability_warning="Warning: some conclusions lack verifiable citations.",
        outlook_what_to_watch="What to watch",
        outlook_key_risks="Key risks",
        outlook_key_opportunities="Key opportunities",
        outlook_scenarios="Scenarios with likelihood",
        outlook_dominant_scenario="Dominant scenario",
        outlook_motricity="motricity",
        outlook_high_dependence="high systemic dependence",
        outlook_risk="Risk",
        outlook_risk_default="Risks from system uncertainty and OSINT traceability",
        outlook_confidence="overall confidence",
        outlook_opportunity="Opportunity",
        outlook_scenario_window="Plausible scenario window:",
        report_variant_full="Full report (methodology + annexes)",
        report_variant_analytical="Analytical report (EIU outlook style)",
        outlook_source_note="Source: Godet synthesis · OSINT · Policy×Industry",
        actor_map_title="Map of key actors",
        actor_map_lead="Actors from this case's Godet project, with OSINT and MACTOR findings.",
        actor_map_posture_worse="OSINT posture deteriorating in recent case statements.",
        actor_map_posture_better="OSINT posture improving in recent case statements.",
        actor_map_geo_risk="Geo risk",
        actor_map_no_detail="Actor defined in this case's Godet; no detailed OSINT traceability yet.",
        actor_map_source_note="Source: project actors · OSINT impact · MACTOR",
        actor_map_case_focus="Case focus",
        actor_map_statements="statements in case",
        actor_map_mactor="MACTOR mobilisation",
        actor_map_force="Strategic force",
        actor_map_no_geo="No geographic placement on map (institutional or multilateral actor).",
    ),
}


def normalize_lang(lang: str | None) -> ReportLang:
    code = (lang or "ca").lower().strip()[:2]
    if code not in _STRINGS:
        return "ca"
    return code  # type: ignore[return-value]


def get_report_strings(lang: str | None) -> ReportStrings:
    return _STRINGS[normalize_lang(lang)]
