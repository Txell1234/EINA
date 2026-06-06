"""Reference profiles linking policy themes to industrial/defense stakeholders (additive hints)."""
from __future__ import annotations

from typing import Any

# theme -> list of company reference records (not exhaustive; enriched by OSINT + LLM)
_THEME_COMPANY_PROFILES: dict[str, list[dict[str, Any]]] = {
    "rearmament": [
        {
            "name": "Mitsubishi Heavy Industries",
            "aliases": ["MHI", "Mitsubishi Heavy"],
            "country": "JP",
            "region": "domestic",
            "roles": ["prime_contractor", "integrator"],
            "sectors": ["naval", "missiles", "aircraft", "space"],
            "beneficiary_rationale": (
                "Principal integrador naval i de sistemes de míssils del JSDF; "
                "s'beneficia d'incrementos pressupostaris en destructors, submarins i defensa antí-míssil."
            ),
            "policy_link": "Pressupost de defensa >2% PIB · modernització JMSDF · Article 9 reinterpretat",
            "contractor_relationships": [
                {"partner": "Lockheed Martin", "type": "license/offset", "region": "overseas"},
                {"partner": "Raytheon", "type": "component_supply", "region": "overseas"},
            ],
        },
        {
            "name": "Kawasaki Heavy Industries",
            "aliases": ["KHI", "Kawasaki Heavy"],
            "country": "JP",
            "region": "domestic",
            "roles": ["prime_contractor"],
            "sectors": ["submarines", "aircraft", "transport"],
            "beneficiary_rationale": (
                "Constructor de submarins Sōryū/Taigei i avions de patrulla; "
                "el rearmament amplia comandes de renovació de flota submarina."
            ),
            "policy_link": "Expansió capacitat submarina Indo-Pacífic",
            "contractor_relationships": [],
        },
        {
            "name": "IHI Corporation",
            "aliases": ["IHI"],
            "country": "JP",
            "region": "domestic",
            "roles": ["supplier", "integrator"],
            "sectors": ["engines", "aerospace", "land_systems"],
            "beneficiary_rationale": "Motors i components per plataformes aeris i terrestres del JSDF.",
            "policy_link": "Modernització logística i mobilitat",
            "contractor_relationships": [],
        },
        {
            "name": "Mitsubishi Electric",
            "aliases": ["MELCO defense"],
            "country": "JP",
            "region": "domestic",
            "roles": ["supplier", "integrator"],
            "sectors": ["radar", "electronic_warfare", "C4ISR"],
            "beneficiary_rationale": "Radars, sistemes EW i C4ISR per plataformes navals i terrestres.",
            "policy_link": "Inversió en dominis espai i cibernètic",
            "contractor_relationships": [],
        },
        {
            "name": "NEC",
            "aliases": ["NEC Corporation"],
            "country": "JP",
            "region": "domestic",
            "roles": ["supplier"],
            "sectors": ["cyber", "C4ISR", "communications"],
            "beneficiary_rationale": "Comunicacions segures i ciberdefensa per forces japoneses.",
            "policy_link": "Prioritat ciber i xarxa de comandament",
            "contractor_relationships": [],
        },
        {
            "name": "Lockheed Martin",
            "aliases": ["Lockheed"],
            "country": "US",
            "region": "overseas",
            "roles": ["prime_contractor", "offset_partner"],
            "sectors": ["aircraft", "missiles", "space"],
            "beneficiary_rationale": (
                "F-35, Aegis, sistemes de míssils: principal beneficiari de compres d'armament "
                "japonès als EUA i acords d'offset."
            ),
            "policy_link": "Aquisició F-35 · SM-3 · interoperabilitat aliat",
            "contractor_relationships": [
                {"partner": "Mitsubishi Heavy Industries", "type": "offset/MRO", "region": "domestic"},
            ],
        },
        {
            "name": "RTX",
            "aliases": ["Raytheon", "RTX Corporation"],
            "country": "US",
            "region": "overseas",
            "roles": ["prime_contractor", "supplier"],
            "sectors": ["missiles", "air_defense", "sensors"],
            "beneficiary_rationale": "Patriot, SM-3, radars: vendes vinculades a amenaça regional i pressió per capacitat antí-míssil.",
            "policy_link": "Defensa antí-míssil i deterrencia regional",
            "contractor_relationships": [],
        },
        {
            "name": "Boeing",
            "aliases": ["Boeing Defense"],
            "country": "US",
            "region": "overseas",
            "roles": ["prime_contractor"],
            "sectors": ["aircraft", "helicopters", "refueling"],
            "beneficiary_rationale": "Helicòpters, avions de reabastiment i plataformes de vigilància.",
            "policy_link": "Projecció de poder aeri i logística",
            "contractor_relationships": [],
        },
        {
            "name": "BAE Systems",
            "aliases": ["BAE"],
            "country": "GB",
            "region": "overseas",
            "roles": ["subcontractor", "offset_partner"],
            "sectors": ["naval", "electronic_systems"],
            "beneficiary_rationale": "Cooperació tècnica i subsystems en programes navals i electrònics.",
            "policy_link": "Aliances de seguretat i transferència tecnològica",
            "contractor_relationships": [],
        },
        {
            "name": "Northrop Grumman",
            "aliases": ["Northrop"],
            "country": "US",
            "region": "overseas",
            "roles": ["supplier"],
            "sectors": ["space", "C4ISR", "drones"],
            "beneficiary_rationale": "Sensors, UAV i capacitats espai per vigilància Indo-Pacífic.",
            "policy_link": "Dominis espai i ISR",
            "contractor_relationships": [],
        },
    ],
    "defense_procurement": [
        {
            "name": "General Dynamics",
            "aliases": ["GD", "General Dynamics Land Systems"],
            "country": "US",
            "region": "overseas",
            "roles": ["prime_contractor"],
            "sectors": ["land_systems", "submarines"],
            "beneficiary_rationale": "Sistemes terrestres i components per submarins en programes d'exportació.",
            "policy_link": "Compres internacionals i offsets",
            "contractor_relationships": [],
        },
        {
            "name": "Thales",
            "aliases": [],
            "country": "FR",
            "region": "overseas",
            "roles": ["supplier", "integrator"],
            "sectors": ["C4ISR", "naval_systems"],
            "beneficiary_rationale": "Electrònica naval i sistemes de combat en mercats indo-pacífics.",
            "policy_link": "Exportació de defensa europea",
            "contractor_relationships": [],
        },
    ],
    "indo_pacific": [
        {
            "name": "Hyundai Heavy Industries",
            "aliases": ["HHI"],
            "country": "KR",
            "region": "overseas",
            "roles": ["prime_contractor"],
            "sectors": ["naval"],
            "beneficiary_rationale": "Competidor/regional en construcció naval; indirectament afectat per dinàmica d'armament regional.",
            "policy_link": "Carrera armamentista regional Indo-Pacífic",
            "contractor_relationships": [],
        },
    ],
    "supply_chain": [
        {
            "name": "Tokyo Electron",
            "aliases": ["TEL"],
            "country": "JP",
            "region": "domestic",
            "roles": ["supplier"],
            "sectors": ["semiconductors", "dual_use"],
            "beneficiary_rationale": "Equipament de semiconductors amb implicacions dual-use i resiliència supply chain.",
            "policy_link": "Control d'exportacions i resiliència industrial",
            "contractor_relationships": [],
        },
    ],
}

_CORPORATE_KEYWORDS = (
    "industries",
    "industry",
    "corp",
    "corporation",
    "inc",
    "ltd",
    "group",
    "systems",
    "heavy",
    "electric",
    "aerospace",
    "defense",
    "defence",
    "lockheed",
    "boeing",
    "raytheon",
    "mitsubishi",
    "kawasaki",
    "bae",
    "thales",
    "northrop",
)


def profiles_for_themes(themes: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for theme in themes:
        for row in _THEME_COMPANY_PROFILES.get(theme, []):
            key = row["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({**row, "matched_themes": [theme]})
    return out


def all_reference_names() -> dict[str, dict[str, Any]]:
    """Normalized name -> profile."""
    index: dict[str, dict[str, Any]] = {}
    for profiles in _THEME_COMPANY_PROFILES.values():
        for p in profiles:
            index[p["name"].lower()] = p
            for alias in p.get("aliases") or []:
                index[alias.lower()] = p
    return index


def looks_like_company(name: str) -> bool:
    n = (name or "").lower()
    if not n or len(n) < 3:
        return False
    return any(k in n for k in _CORPORATE_KEYWORDS)
