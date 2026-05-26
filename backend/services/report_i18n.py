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
    ),
}


def normalize_lang(lang: str | None) -> ReportLang:
    code = (lang or "ca").lower().strip()[:2]
    if code not in _STRINGS:
        return "ca"
    return code  # type: ignore[return-value]


def get_report_strings(lang: str | None) -> ReportStrings:
    return _STRINGS[normalize_lang(lang)]
