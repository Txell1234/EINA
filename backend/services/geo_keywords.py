"""Keyword → coordinates for geopolitical OSINT (actors, headlines, case text)."""
from __future__ import annotations

# keyword -> (lat, lng, display label)
GEO_KEYWORD_COORDS: dict[str, tuple[float, float, str]] = {
    "japó": (36.2048, 138.2529, "Japó"),
    "japo": (36.2048, 138.2529, "Japó"),
    "japan": (36.2048, 138.2529, "Japó"),
    "tokyo": (35.6762, 139.6503, "Tòquio"),
    "tòquio": (35.6762, 139.6503, "Tòquio"),
    "xina": (35.8617, 104.1954, "Xina"),
    "china": (35.8617, 104.1954, "Xina"),
    "beijing": (39.9042, 116.4074, "Pequín"),
    "pekin": (39.9042, 116.4074, "Pequín"),
    "pequín": (39.9042, 116.4074, "Pequín"),
    "taiwan": (25.033, 121.565, "Taiwan"),
    "taipei": (25.033, 121.565, "Taiwan"),
    "corea del sud": (37.5665, 126.978, "Corea del Sud"),
    "south korea": (37.5665, 126.978, "Corea del Sud"),
    "corea del nord": (39.0392, 125.7625, "Corea del Nord"),
    "north korea": (39.0392, 125.7625, "Corea del Nord"),
    "eua": (38.9072, -77.0369, "EUA"),
    "usa": (38.9072, -77.0369, "EUA"),
    "united states": (38.9072, -77.0369, "EUA"),
    "washington": (38.9072, -77.0369, "Washington"),
    "europa": (50.1109, 8.6821, "Europa"),
    "europe": (50.1109, 8.6821, "Europa"),
    "eu": (50.8466, 4.3528, "Unió Europea"),
    "brussel": (50.8466, 4.3528, "Brussel·les"),
    "brussels": (50.8466, 4.3528, "Brussel·les"),
    "espanya": (40.4637, -3.7492, "Espanya"),
    "spain": (40.4637, -3.7492, "Espanya"),
    "frança": (46.2276, 2.2137, "França"),
    "france": (46.2276, 2.2137, "França"),
    "alemanya": (51.1657, 10.4515, "Alemanya"),
    "germany": (51.1657, 10.4515, "Alemanya"),
    "regne unit": (51.5074, -0.1278, "Regne Unit"),
    "united kingdom": (51.5074, -0.1278, "Regne Unit"),
    "uk": (51.5074, -0.1278, "Regne Unit"),
    "london": (51.5074, -0.1278, "Londres"),
    "rússia": (61.524, 105.3188, "Rússia"),
    "russia": (61.524, 105.3188, "Rússia"),
    "ucraïna": (48.3794, 31.1656, "Ucraïna"),
    "ukraine": (48.3794, 31.1656, "Ucraïna"),
    "india": (20.5937, 78.9629, "Índia"),
    "iran": (32.4279, 53.688, "Iran"),
    "israel": (31.0461, 34.8516, "Israel"),
    "gaza": (31.5, 34.4667, "Gaza"),
    "brasil": (-14.235, -51.9253, "Brasil"),
    "brazil": (-14.235, -51.9253, "Brasil"),
    "indopacific": (10.0, 130.0, "Indopacífic"),
    "indo-pacific": (10.0, 130.0, "Indopacífic"),
    "hormuz": (26.5, 56.5, "Estret d'Hormuz"),
    "taiwan strait": (24.0, 119.5, "Estret de Taiwan"),
}

# Longer phrases first to avoid partial false positives
_SORTED_KEYWORDS = sorted(GEO_KEYWORD_COORDS.keys(), key=len, reverse=True)


def find_geo_hits(text: str) -> list[tuple[str, float, float]]:
    """Return unique (label, lat, lng) matches found in free text."""
    if not text or not str(text).strip():
        return []
    lower = str(text).lower()
    hits: list[tuple[str, float, float]] = []
    seen_labels: set[str] = set()
    for keyword in _SORTED_KEYWORDS:
        if keyword not in lower:
            continue
        lat, lng, label = GEO_KEYWORD_COORDS[keyword]
        if label in seen_labels:
            continue
        seen_labels.add(label)
        hits.append((label, lat, lng))
    return hits
