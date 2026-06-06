"""Morphological box bootstrap from inquiry trigger — components + CCA suggestions."""
from __future__ import annotations

from typing import Any

from services.morph_space import (
    _get_pair_consistency,
    backtrack_valid_combinations,
    filter_valid_combinations,
    morph_space_stats,
    normalize_components,
    reduce_to_godet_four,
)

_EVENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "security_maritime": [
        {
            "code": "C1",
            "name": "Postura actor principal",
            "configurations": [
                {"label": "Escalada", "desc": "Enduriment / bloqueig"},
                {"label": "Modulació", "desc": "Pressió sense ruptura"},
                {"label": "Alleujament", "desc": "Desescalada parcial"},
                {"label": "Retirada", "desc": "Normalització"},
            ],
        },
        {
            "code": "C2",
            "name": "Resposta contrapart",
            "configurations": [
                {"label": "Hostil", "desc": "Amenaça / acció directa"},
                {"label": "Resistent", "desc": "Retòrica dura, poc acció"},
                {"label": "Negociador", "desc": "Via diplomàtica"},
                {"label": "Cooperatiu", "desc": "Acord explícit"},
            ],
        },
        {
            "code": "C3",
            "name": "Estat via / estret",
            "configurations": [
                {"label": "Bloquejat", "desc": "Trànsit severament limitat"},
                {"label": "Tens", "desc": "Interrupcions puntuals"},
                {"label": "Obert", "desc": "Trànsit normal"},
            ],
        },
    ],
    "bilateral_relations": [
        {
            "code": "C1",
            "name": "Vol polític bilateral",
            "configurations": [
                {"label": "Normalització plena", "desc": ""},
                {"label": "Acords sectorials", "desc": ""},
                {"label": "Gel", "desc": ""},
                {"label": "Ruptura", "desc": ""},
            ],
        },
        {
            "code": "C2",
            "name": "Mediació externa",
            "configurations": [
                {"label": "Activa", "desc": ""},
                {"label": "Latent", "desc": ""},
                {"label": "Absència", "desc": ""},
            ],
        },
        {
            "code": "C3",
            "name": "Impacte mercat",
            "configurations": [
                {"label": "Positiu", "desc": ""},
                {"label": "Neutre", "desc": ""},
                {"label": "Negatiu", "desc": ""},
            ],
        },
    ],
    "political_transition": [
        {
            "code": "C1",
            "name": "Estabilitat règim",
            "configurations": [
                {"label": "Consolidat", "desc": ""},
                {"label": "Tens", "desc": ""},
                {"label": "Fragile", "desc": ""},
                {"label": "Transició oberta", "desc": ""},
            ],
        },
        {
            "code": "C2",
            "name": "Elite / successió",
            "configurations": [
                {"label": "Continuïtat", "desc": ""},
                {"label": "Reforma", "desc": ""},
                {"label": "Canvi", "desc": ""},
            ],
        },
    ],
    "geopolitical": [
        {
            "code": "C1",
            "name": "Dinàmica del sistema",
            "configurations": [
                {"label": "Cooperació", "desc": ""},
                {"label": "Competició", "desc": ""},
                {"label": "Conflicte", "desc": ""},
            ],
        },
        {
            "code": "C2",
            "name": "Resposta multilateral",
            "configurations": [
                {"label": "Coordinada", "desc": ""},
                {"label": "Fragmentada", "desc": ""},
                {"label": "Absent", "desc": ""},
            ],
        },
    ],
}


def _default_cca_rules(components: list[dict]) -> list[dict[str, Any]]:
    """Domain heuristics for common incompatible pairs."""
    rules: list[dict[str, Any]] = []
    by_code = {c["code"]: c for c in normalize_components(components)}

    def add(a: str, ca: str, b: str, cb: str, justification: str) -> None:
        if a in by_code and b in by_code:
            rules.append(
                {
                    "component_a": a,
                    "config_a": ca,
                    "component_b": b,
                    "config_b": cb,
                    "consistency": -1,
                    "justification": justification,
                    "source": "domain_rule",
                }
            )

    if "C1" in by_code and "C2" in by_code:
        add("C1", "Retirada", "C2", "Hostil", "Alleujament unilateral incompatible amb resposta hostil simultània")
        add("C1", "Escalada", "C2", "Cooperatiu", "Escalada incompatible amb resposta cooperativa")
    if "C1" in by_code and "C3" in by_code:
        add("C1", "Retirada", "C3", "Bloquejat", "Retirada política incompatible amb bloqueig físic mantingut")
        add("C1", "Escalada", "C3", "Obert", "Escalada incompatible amb trànsit obert sense fricció")
    return rules


class MorphBootstrapService:
    """Suggest Zwicky box components and CCA rules from inquiry parse (no LLM)."""

    def bootstrap(
        self,
        *,
        question: str,
        event_type: str = "geopolitical",
        actors: list[str] | None = None,
    ) -> dict[str, Any]:
        templates = _EVENT_TEMPLATES.get(event_type) or _EVENT_TEMPLATES["geopolitical"]
        components = templates[:5]
        incompatibilities = _default_cca_rules(components)
        stats = morph_space_stats(components, incompatibilities)
        valid = filter_valid_combinations(components, incompatibilities)
        godet_four = reduce_to_godet_four(valid[:500] if len(valid) > 500 else valid, components)

        return {
            "question": question,
            "event_type": event_type,
            "actors": actors or [],
            "suggested_components": components,
            "suggested_cca_rules": incompatibilities,
            "morph_stats": stats,
            "valid_combinations_count": len(valid),
            "godet_preview": godet_four,
            "cca_heatmap": self.build_cca_heatmap(components, incompatibilities),
            "methodology": "rule_based_morph_bootstrap",
            "llm_used": False,
            "note": (
                "Suggeriment per iniciar el pas morfològic al wizard. "
                "Valida i ajusta manualment abans de generar escenaris."
            ),
        }

    def build_cca_heatmap(
        self,
        components: list[dict],
        incompatibilities: list[dict],
    ) -> dict[str, Any]:
        """Pairwise CCA matrix for UI heat-map (deterministic)."""
        normalized = normalize_components(components)
        codes = [c["code"] for c in normalized]
        cells: list[dict[str, Any]] = []
        for i, ca in enumerate(codes):
            for j, cb in enumerate(codes):
                if j <= i:
                    continue
                comp_a = next(c for c in normalized if c["code"] == ca)
                comp_b = next(c for c in normalized if c["code"] == cb)
                for cfg_a in comp_a["configs"]:
                    for cfg_b in comp_b["configs"]:
                        val = _get_pair_consistency(ca, cfg_a, cb, cfg_b, incompatibilities)
                        if val != 0:
                            cells.append(
                                {
                                    "param_a": ca,
                                    "state_a": cfg_a,
                                    "param_b": cb,
                                    "state_b": cfg_b,
                                    "value": val,
                                }
                            )
        return {
            "parameters": [{"code": c["code"], "name": c["name"], "states": c["configs"]} for c in normalized],
            "cells": cells,
            "inconsistent_count": sum(1 for x in cells if x["value"] == -1),
            "neutral_count": sum(1 for x in cells if x["value"] == 0),
        }
