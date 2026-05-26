"""
Morphological space (Zwicky) — cartesian product, compatibility filter,
scenario selection and SMIC probability cross-impact.
"""
from itertools import product
from typing import Any

SCENARIO_TEMPLATES = [
    {
        "index": 0,
        "name": "Escenari Infern",
        "scenario_type": "infern",
        "default_probability": "BAIXA-MITJA",
    },
    {
        "index": 1,
        "name": "Escenari Tensió Crònica",
        "scenario_type": "tensio",
        "default_probability": "ALTA",
    },
    {
        "index": 2,
        "name": "Escenari Equilibri Dinàmic",
        "scenario_type": "equilibri",
        "default_probability": "MITJA",
    },
    {
        "index": 3,
        "name": "Escenari Cel",
        "scenario_type": "cel",
        "default_probability": "BAIXA",
    },
]

DEFAULT_SMIC_INITIAL = [0.20, 0.35, 0.30, 0.15]
DEFAULT_SMIC_CROSS = [[0.0] * 4 for _ in range(4)]

ComboEntry = tuple[str, str, str, int]


def _config_labels(component: dict) -> list[str]:
    configs = component.get("configs") or component.get("configurations") or []
    labels: list[str] = []
    for c in configs:
        if isinstance(c, str):
            labels.append(c)
        elif isinstance(c, dict):
            labels.append(str(c.get("label", "?")))
    return labels or ["?"]


def normalize_components(raw: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(raw):
        code = str(c.get("code") or c.get("id") or f"C{i + 1}")
        name = str(c.get("name") or code)
        labels = _config_labels(c)
        out.append({"code": code, "name": name, "configs": labels})
    return out


def build_cartesian(components: list[dict]) -> list[list[ComboEntry]]:
    if not components:
        return []
    option_lists: list[list[ComboEntry]] = []
    for comp in components:
        entries = [
            (comp["code"], comp["name"], label, idx)
            for idx, label in enumerate(comp["configs"])
        ]
        option_lists.append(entries)
    return [list(combo) for combo in product(*option_lists)]


def _pair_incompatible(
    comp_a: str,
    cfg_a: str,
    comp_b: str,
    cfg_b: str,
    incompatibilities: list[dict],
) -> bool:
    for inc in incompatibilities:
        a, ca = inc.get("component_a"), inc.get("config_a")
        b, cb = inc.get("component_b"), inc.get("config_b")
        if not all([a, ca, b, cb]):
            continue
        if (a == comp_a and ca == cfg_a and b == comp_b and cb == cfg_b) or (
            a == comp_b and ca == cfg_b and b == comp_a and cb == cfg_a
        ):
            return True
    return False


def is_combo_valid(combo: list[ComboEntry], incompatibilities: list[dict]) -> bool:
    for i in range(len(combo)):
        for j in range(i + 1, len(combo)):
            comp_a, _, cfg_a, _ = combo[i]
            comp_b, _, cfg_b, _ = combo[j]
            if _pair_incompatible(comp_a, cfg_a, comp_b, cfg_b, incompatibilities):
                return False
    return True


def filter_valid_combinations(
    components: list[dict],
    incompatibilities: list[dict] | None = None,
) -> list[list[ComboEntry]]:
    incompatibilities = incompatibilities or []
    normalized = normalize_components(components)
    return [c for c in build_cartesian(normalized) if is_combo_valid(c, incompatibilities)]


def combo_score(combo: list[ComboEntry], config_counts: list[int] | None = None) -> float:
    """0 = worst combo, 1 = best (first config = worst, last = best per component)."""
    if not combo:
        return 0.0
    scores: list[float] = []
    for i, (_, _, _, idx) in enumerate(combo):
        n = config_counts[i] if config_counts and i < len(config_counts) else max(idx + 1, 1)
        scores.append(idx / max(n - 1, 1))
    return sum(scores) / len(scores)


def format_morph_config(combo: list[ComboEntry]) -> str:
    if not combo:
        return ""
    return " | ".join(label for _, _, label, _ in combo)


def morph_space_stats(
    components: list[dict],
    incompatibilities: list[dict] | None = None,
) -> dict[str, Any]:
    normalized = normalize_components(components)
    total = 1
    for comp in normalized:
        total *= max(len(comp["configs"]), 1)
    valid = filter_valid_combinations(normalized, incompatibilities)
    return {
        "total_combinations": total,
        "valid_combinations": len(valid),
        "filtered_out": total - len(valid),
        "components": normalized,
    }


def _pick_by_percentile(
    combos: list[list[ComboEntry]],
    percentile: float,
    config_counts: list[int] | None = None,
) -> list[ComboEntry]:
    if not combos:
        return []
    sorted_combos = sorted(combos, key=lambda c: combo_score(c, config_counts))
    idx = int(round(percentile * (len(sorted_combos) - 1)))
    idx = max(0, min(idx, len(sorted_combos) - 1))
    return sorted_combos[idx]


def select_scenario_combos(
    components: list[dict],
    incompatibilities: list[dict] | None = None,
) -> dict[str, list[ComboEntry]]:
    normalized = normalize_components(components)
    config_counts = [len(c["configs"]) for c in normalized]
    all_combos = build_cartesian(normalized)[:64]
    valid = [c for c in all_combos if is_combo_valid(c, incompatibilities or [])]
    if not valid:
        valid = all_combos
    return {
        "infern": _pick_by_percentile(valid, 0.0, config_counts),
        "tensio": _pick_by_percentile(valid, 0.35, config_counts),
        "equilibri": _pick_by_percentile(valid, 0.65, config_counts),
        "cel": _pick_by_percentile(valid, 1.0, config_counts),
    }


def prob_to_label(p: float) -> str:
    if p >= 0.50:
        return "ALTA"
    if p >= 0.35:
        return "MITJA"
    if p >= 0.20:
        return "BAIXA-MITJA"
    return "BAIXA"


def compute_smic_bayesian(
    prior: list[float],
    conditional_matrix: list[list[float]],
) -> tuple[list[float], list[str]]:
    """Bayesian cross-impact: P(j|i) adjusts prior P(j), normalized."""
    n = len(prior)
    adjusted = list(prior)
    for j in range(n):
        weighted = 0.0
        total_w = 0.0
        for i in range(n):
            if i == j:
                continue
            p_i = prior[i]
            cond = (
                conditional_matrix[i][j]
                if i < len(conditional_matrix) and j < len(conditional_matrix[i])
                else prior[j]
            )
            weighted += p_i * cond
            total_w += p_i
        if total_w > 0:
            adjusted[j] = (prior[j] + weighted / total_w) / 2
    total = sum(adjusted)
    if total > 0:
        adjusted = [round(a / total, 3) for a in adjusted]
    labels = [prob_to_label(p) for p in adjusted]
    return adjusted, labels


def compute_smic_final(
    initial: list[float],
    cross: list[list[float]],
) -> tuple[list[float], list[str]]:
    n = 4
    init = (initial + DEFAULT_SMIC_INITIAL)[:n]
    total_init = sum(init) or 1.0
    init = [p / total_init for p in init]

    adjusted = list(init)
    for j in range(n):
        for i in range(n):
            if i != j:
                adjusted[j] += cross[i][j] * init[i] * 0.075
        adjusted[j] = max(0.01, adjusted[j])

    total = sum(adjusted)
    final = [a / total for a in adjusted]
    labels = [prob_to_label(p) for p in final]
    return final, labels


def assess_scenario_possibility(
    combo: list[ComboEntry],
    incompatibilities: list[dict] | None,
    components: list[dict] | None,
    scenario_type: str,
) -> dict[str, str]:
    """Possibilitat lògica (Zwicky): l'escenari pot existir dins l'espai morfològic?

    Distint de probabilitat (likelihood SMIC/OSINT).
    """
    normalized = normalize_components(components or [])
    if not combo:
        return {
            "possibility": "PLAUSIBLE",
            "possibility_rationale": (
                "Sense configuració morfològica explícita; escenari qualitatiu per defecte."
            ),
        }
    if not is_combo_valid(combo, incompatibilities or []):
        return {
            "possibility": "EXCLOS",
            "possibility_rationale": (
                "La combinació viola incompatibilitats Zwicky i queda fora de l'espai possible."
            ),
        }
    config_counts = [len(c["configs"]) for c in normalized] if normalized else None
    score = combo_score(combo, config_counts)
    config_str = format_morph_config(combo)
    if scenario_type in ("infern", "cel") or score <= 0.15 or score >= 0.85:
        return {
            "possibility": "CONDICIONAL",
            "possibility_rationale": (
                f"Combinació vàlida però extrema ({config_str}). "
                "Possibilitat lògica verificada; la realització depèn de condicions concretes simultànies."
            ),
        }
    return {
        "possibility": "PLAUSIBLE",
        "possibility_rationale": (
            f"Combinació vàlida dins l'espai morfològic ({config_str}). "
            "Sense incompatibilitats Zwicky; l'estat futur és estructuralment assolible."
        ),
    }


def build_scenario_specs(
    components: list[dict],
    incompatibilities: list[dict] | None = None,
    probability_labels: list[str] | None = None,
) -> list[dict]:
    combos = select_scenario_combos(components, incompatibilities)
    specs: list[dict] = []
    for tpl in SCENARIO_TEMPLATES:
        st = tpl["scenario_type"]
        combo = combos.get(st, [])
        idx = tpl["index"]
        prob = (
            probability_labels[idx]
            if probability_labels and idx < len(probability_labels)
            else tpl["default_probability"]
        )
        config_str = format_morph_config(combo) if combo else ""
        poss = assess_scenario_possibility(combo, incompatibilities, components, st)
        specs.append(
            {
                "index": idx,
                "name": tpl["name"],
                "scenario_type": st,
                "possibility": poss["possibility"],
                "possibility_rationale": poss["possibility_rationale"],
                "probability": prob,
                "config": config_str or f"Configuració {st}",
                "combo": combo,
            }
        )
    return specs
