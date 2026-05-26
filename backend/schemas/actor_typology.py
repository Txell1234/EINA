"""Unified actor, institution, scenario and analysis lens typology (EINA-native, JPA-inspired)."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActorClass(str, Enum):
    STATE = "state"
    INSTITUTION = "institution"
    COMPANY = "company"
    INDIVIDUAL = "individual"
    ALLIANCE = "alliance"
    MULTILATERAL = "multilateral"


class InstitutionSubtype(str, Enum):
    GOVERNMENT = "government"
    MINISTRY = "ministry"
    MULTILATERAL_ORG = "multilateral_org"
    DEFENSE_AGENCY = "defense_agency"
    THINK_TANK = "think_tank"
    TRADE_AGENCY = "trade_agency"
    NGO = "ngo"
    REGULATOR = "regulator"
    POLITICAL_PARTY = "political_party"
    FINANCIAL_INSTITUTION = "financial_institution"
    CORPORATE = "corporate"
    UNKNOWN = "unknown"


class AnalysisLens(str, Enum):
    """Analytical frames inspired by public/private sector intelligence (not JPA trademarks)."""
    PUBLIC_SECTOR = "public_sector"
    PRIVATE_SECTOR = "private_sector"
    REGULATORY = "regulatory"
    SUPPLY_CHAIN = "supply_chain"
    MARKET_ENTRY = "market_entry"
    STAKEHOLDER_MAPPING = "stakeholder_mapping"
    EARLY_WARNING = "early_warning"
    BOARD_DECISION = "board_decision"


class SignalType(str, Enum):
    STRUCTURAL = "structural"
    EPISODIC = "episodic"


THEME_LABELS: dict[str, str] = {
    "rearmament": "Rearmament i defensa",
    "indo_pacific": "Indo-Pacífic",
    "sanctions": "Sancions i control d'exportacions",
    "diplomacy": "Diplomàcia i relacions bilaterals",
    "regulatory": "Risc regulatori",
    "supply_chain": "Cadena de subministrament",
    "market_entry": "Entrada a mercat",
    "energy": "Energia i recursos",
    "defense_procurement": "Compres de defensa",
}

LENS_LABELS: dict[str, str] = {
    AnalysisLens.PUBLIC_SECTOR.value: "Sector públic (horitzó 3–12 mesos)",
    AnalysisLens.PRIVATE_SECTOR.value: "Sector privat (horitzó 6–18 mesos)",
    AnalysisLens.REGULATORY.value: "Risc regulatori",
    AnalysisLens.SUPPLY_CHAIN.value: "Dependències industrials",
    AnalysisLens.MARKET_ENTRY.value: "Entrada / sortida de mercat",
    AnalysisLens.STAKEHOLDER_MAPPING.value: "Mapatge d'stakeholders",
    AnalysisLens.EARLY_WARNING.value: "Alerta primerenca",
    AnalysisLens.BOARD_DECISION.value: "Decisions de consell / CAPEX",
}

SCENARIO_PROFILES: dict[str, dict[str, Any]] = {
    "infern": {
        "label": "Escenari Infern",
        "valence": -1.0,
        "risk_profile": "crisis",
        "reversibility": "low",
        "horizon_months": (0, 12),
    },
    "tensio": {
        "label": "Escenari Tensió Crònica",
        "valence": -0.4,
        "risk_profile": "structural_tension",
        "reversibility": "medium",
        "horizon_months": (6, 24),
    },
    "equilibri": {
        "label": "Escenari Equilibri Dinàmic",
        "valence": 0.0,
        "risk_profile": "managed_balance",
        "reversibility": "high",
        "horizon_months": (12, 36),
    },
    "cel": {
        "label": "Escenari Cel",
        "valence": 0.7,
        "risk_profile": "opportunity",
        "reversibility": "high",
        "horizon_months": (18, 60),
    },
}

_CASE_TYPE_DEFAULT_LENSES: dict[str, list[str]] = {
    "geopolitical": [
        AnalysisLens.PUBLIC_SECTOR.value,
        AnalysisLens.EARLY_WARNING.value,
        AnalysisLens.STAKEHOLDER_MAPPING.value,
    ],
    "political": [
        AnalysisLens.PUBLIC_SECTOR.value,
        AnalysisLens.STAKEHOLDER_MAPPING.value,
    ],
    "business": [
        AnalysisLens.PRIVATE_SECTOR.value,
        AnalysisLens.MARKET_ENTRY.value,
        AnalysisLens.REGULATORY.value,
    ],
    "general": [AnalysisLens.STAKEHOLDER_MAPPING.value, AnalysisLens.EARLY_WARNING.value],
    "social": [AnalysisLens.STAKEHOLDER_MAPPING.value],
    "investigation": [AnalysisLens.EARLY_WARNING.value, AnalysisLens.STAKEHOLDER_MAPPING.value],
}

_THEME_LENSES: dict[str, list[str]] = {
    "rearmament": [AnalysisLens.PUBLIC_SECTOR.value, AnalysisLens.EARLY_WARNING.value],
    "indo_pacific": [AnalysisLens.PUBLIC_SECTOR.value, AnalysisLens.STAKEHOLDER_MAPPING.value],
    "sanctions": [AnalysisLens.REGULATORY.value, AnalysisLens.SUPPLY_CHAIN.value],
    "diplomacy": [AnalysisLens.STAKEHOLDER_MAPPING.value, AnalysisLens.PUBLIC_SECTOR.value],
    "regulatory": [AnalysisLens.REGULATORY.value, AnalysisLens.PRIVATE_SECTOR.value],
    "supply_chain": [AnalysisLens.SUPPLY_CHAIN.value, AnalysisLens.PRIVATE_SECTOR.value],
    "market_entry": [AnalysisLens.MARKET_ENTRY.value, AnalysisLens.PRIVATE_SECTOR.value],
}

_THEME_INSTITUTION_FOCUS: dict[str, list[str]] = {
    "rearmament": [
        InstitutionSubtype.DEFENSE_AGENCY.value,
        InstitutionSubtype.GOVERNMENT.value,
        InstitutionSubtype.MULTILATERAL_ORG.value,
    ],
    "indo_pacific": [
        InstitutionSubtype.GOVERNMENT.value,
        InstitutionSubtype.MULTILATERAL_ORG.value,
        InstitutionSubtype.THINK_TANK.value,
    ],
    "sanctions": [
        InstitutionSubtype.REGULATOR.value,
        InstitutionSubtype.GOVERNMENT.value,
        InstitutionSubtype.FINANCIAL_INSTITUTION.value,
    ],
    "diplomacy": [
        InstitutionSubtype.GOVERNMENT.value,
        InstitutionSubtype.MINISTRY.value,
        InstitutionSubtype.MULTILATERAL_ORG.value,
    ],
    "regulatory": [InstitutionSubtype.REGULATOR.value, InstitutionSubtype.GOVERNMENT.value],
    "supply_chain": [InstitutionSubtype.CORPORATE.value, InstitutionSubtype.TRADE_AGENCY.value],
    "market_entry": [
        InstitutionSubtype.TRADE_AGENCY.value,
        InstitutionSubtype.FINANCIAL_INSTITUTION.value,
        InstitutionSubtype.CORPORATE.value,
    ],
}

_INSTITUTION_HINTS: list[tuple[str, InstitutionSubtype]] = [
    (r"\b(nato|otan|united nations|onu|eu commission|european union|asean|quad|aukus)\b", InstitutionSubtype.MULTILATERAL_ORG),
    (r"\b(ministry|minister|ministre|foreign office|state department|defense department|pentagon)\b", InstitutionSubtype.MINISTRY),
    (r"\b(jsdf|self-defense force|armed forces|military|defense agency|dod)\b", InstitutionSubtype.DEFENSE_AGENCY),
    (r"\b(brookings|rand|chatham|csis|think tank|institute for)\b", InstitutionSubtype.THINK_TANK),
    (r"\b(sec|regulator|regulatory|central bank|fed |ecb)\b", InstitutionSubtype.REGULATOR),
    (r"\b(ngo|nonprofit|human rights watch|amnesty)\b", InstitutionSubtype.NGO),
    (r"\b(trade promotion|export agency|chamber of commerce)\b", InstitutionSubtype.TRADE_AGENCY),
    (r"\b(party|parliament|congress|senate|diet)\b", InstitutionSubtype.POLITICAL_PARTY),
    (r"\b(inc\.|corp\.|ltd\.|holdings|industries)\b", InstitutionSubtype.CORPORATE),
    (r"\b(bank|fund|capital|investment)\b", InstitutionSubtype.FINANCIAL_INSTITUTION),
]


class AnalyticalProfile(BaseModel):
    """Thematic and institutional framing for a case — additive metadata, no behavior change."""

    analysis_lenses: list[str] = Field(default_factory=list)
    lens_labels: dict[str, str] = Field(default_factory=dict)
    actor_classes_focus: list[str] = Field(default_factory=list)
    institution_subtypes_focus: list[str] = Field(default_factory=list)
    institution_subtype_labels: dict[str, str] = Field(default_factory=dict)
    scenario_types: list[str] = Field(default_factory=lambda: list(SCENARIO_PROFILES.keys()))
    scenario_profiles: dict[str, dict[str, Any]] = Field(default_factory=lambda: dict(SCENARIO_PROFILES))
    theme_labels: dict[str, str] = Field(default_factory=dict)
    horizon_public_months: tuple[int, int] = (3, 12)
    horizon_private_months: tuple[int, int] = (6, 18)
    case_type: str = "general"


def normalize_actor_class(raw: str | None) -> str:
    val = (raw or "state").lower().strip()
    aliases = {
        "country": ActorClass.STATE.value,
        "nation": ActorClass.STATE.value,
        "org": ActorClass.INSTITUTION.value,
        "organization": ActorClass.INSTITUTION.value,
        "organisation": ActorClass.INSTITUTION.value,
        "entity": ActorClass.INSTITUTION.value,
        "strategic": ActorClass.STATE.value,
        "corporation": ActorClass.COMPANY.value,
        "firm": ActorClass.COMPANY.value,
        "person": ActorClass.INDIVIDUAL.value,
        "io": ActorClass.MULTILATERAL.value,
    }
    if val in {e.value for e in ActorClass}:
        return val
    return aliases.get(val, ActorClass.STATE.value)


def infer_institution_subtype(actor_name: str, actor_type: str | None = None) -> str:
    """Heuristic subtype from actor label — used when DB column is null."""
    blob = (actor_name or "").lower()
    at = normalize_actor_class(actor_type)
    if at == ActorClass.STATE.value:
        return InstitutionSubtype.GOVERNMENT.value
    if at == ActorClass.COMPANY.value:
        return InstitutionSubtype.CORPORATE.value
    if at == ActorClass.INDIVIDUAL.value:
        return InstitutionSubtype.UNKNOWN.value
    if at == ActorClass.ALLIANCE.value or at == ActorClass.MULTILATERAL.value:
        return InstitutionSubtype.MULTILATERAL_ORG.value

    for pattern, subtype in _INSTITUTION_HINTS:
        if re.search(pattern, blob, re.I):
            return subtype.value
    if at == ActorClass.INSTITUTION.value:
        return InstitutionSubtype.GOVERNMENT.value
    return InstitutionSubtype.UNKNOWN.value


def resolve_analysis_lenses(case_type: str | None, themes: set[str] | list[str]) -> list[str]:
    lenses: list[str] = []
    seen: set[str] = set()
    ct = (case_type or "general").lower()
    for lens in _CASE_TYPE_DEFAULT_LENSES.get(ct, _CASE_TYPE_DEFAULT_LENSES["general"]):
        if lens not in seen:
            seen.add(lens)
            lenses.append(lens)
    for theme in themes:
        for lens in _THEME_LENSES.get(theme, []):
            if lens not in seen:
                seen.add(lens)
                lenses.append(lens)
    return lenses


def resolve_institution_focus(themes: set[str] | list[str]) -> list[str]:
    focus: list[str] = []
    seen: set[str] = set()
    for theme in themes:
        for sub in _THEME_INSTITUTION_FOCUS.get(theme, []):
            if sub not in seen:
                seen.add(sub)
                focus.append(sub)
    if not focus:
        focus = [
            InstitutionSubtype.GOVERNMENT.value,
            InstitutionSubtype.MULTILATERAL_ORG.value,
            InstitutionSubtype.THINK_TANK.value,
        ]
    return focus


def resolve_actor_classes_focus(themes: set[str] | list[str], case_type: str | None) -> list[str]:
    classes = [ActorClass.STATE.value, ActorClass.INSTITUTION.value]
    theme_set = set(themes)
    if theme_set & {"sanctions", "supply_chain", "market_entry"} or (case_type or "").lower() == "business":
        classes.extend([ActorClass.COMPANY.value, ActorClass.MULTILATERAL.value])
    if "diplomacy" in theme_set:
        classes.append(ActorClass.INDIVIDUAL.value)
    out: list[str] = []
    seen: set[str] = set()
    for c in classes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_analytical_profile(
    *,
    case_type: str | None,
    themes: set[str] | list[str],
) -> AnalyticalProfile:
    theme_list = sorted(set(themes))
    lenses = resolve_analysis_lenses(case_type, theme_list)
    inst_focus = resolve_institution_focus(theme_list)
    return AnalyticalProfile(
        analysis_lenses=lenses,
        lens_labels={k: LENS_LABELS.get(k, k) for k in lenses},
        actor_classes_focus=resolve_actor_classes_focus(theme_list, case_type),
        institution_subtypes_focus=inst_focus,
        institution_subtype_labels={
            k: k.replace("_", " ").title() for k in inst_focus
        },
        scenario_types=list(SCENARIO_PROFILES.keys()),
        scenario_profiles=dict(SCENARIO_PROFILES),
        theme_labels={t: THEME_LABELS.get(t, t.replace("_", " ").title()) for t in theme_list},
        case_type=(case_type or "general").lower(),
    )


def classify_signal_type(statement: str, topic: str = "", actor_type: str = "") -> str | None:
    """Optional structural vs episodic — returns None if uncertain (keeps legacy behavior)."""
    blob = f"{statement} {topic}".lower()
    structural_markers = (
        "budget", "law", "treaty", "strategy", "doctrine", "reform", "procurement",
        "constitution", "alliance", "sanctions regime", "structural", "long-term",
    )
    episodic_markers = (
        "summit", "meeting", "statement", "comment", "tweet", "speech", "visit",
        "incident", "skirmish", "protest", "announcement today",
    )
    s_hits = sum(1 for m in structural_markers if m in blob)
    e_hits = sum(1 for m in episodic_markers if m in blob)
    if s_hits >= 2 and s_hits > e_hits:
        return SignalType.STRUCTURAL.value
    if e_hits >= 2 and e_hits > s_hits:
        return SignalType.EPISODIC.value
    return None
