"""Geographic entity extraction from free text (keywords + patterns)."""
from __future__ import annotations

from services.geo_keywords import GEO_KEYWORD_COORDS, find_geo_hits

REGION_PHRASES: dict[str, tuple[float, float, str]] = {
    "south china sea": (15.0, 115.0, "Mar de la Xina Meridional"),
    "mar de la xina meridional": (15.0, 115.0, "Mar de la Xina Meridional"),
    "taiwan strait": (24.0, 119.5, "Estret de Taiwan"),
    "estret de taiwan": (24.0, 119.5, "Estret de Taiwan"),
    "red sea": (20.0, 38.0, "Mar Roig"),
    "mar roig": (20.0, 38.0, "Mar Roig"),
    "persian gulf": (26.0, 52.0, "Golf Pèrsic"),
    "middle east": (29.0, 42.0, "Orient Mitjà"),
    "orient mitjà": (29.0, 42.0, "Orient Mitjà"),
    "indo-pacific": (10.0, 130.0, "Indopacífic"),
    "indopacific": (10.0, 130.0, "Indopacífic"),
    "korean peninsula": (37.5, 127.0, "Península Coreana"),
}

_EXTRA_KEYWORDS: dict[str, tuple[float, float, str]] = {
    "singapore": (1.3521, 103.8198, "Singapur"),
    "singapur": (1.3521, 103.8198, "Singapur"),
    "vietnam": (14.0583, 108.2772, "Vietnam"),
    "philippines": (12.8797, 121.774, "Filipines"),
    "pakistan": (30.3753, 69.3451, "Pakistan"),
    "syria": (34.8021, 38.9968, "Síria"),
    "lebanon": (33.8547, 35.8623, "Líban"),
    "poland": (51.9194, 19.1451, "Polònia"),
    "kyiv": (50.4501, 30.5234, "Kíiv"),
    "seoul": (37.5665, 126.978, "Seül"),
    "okinawa": (26.2124, 127.6809, "Okinawa"),
    "indonesia": (-0.7893, 113.9213, "Indonèsia"),
    "malaysia": (4.2105, 101.9758, "Malàisia"),
    "thailand": (15.87, 100.9925, "Tailàndia"),
}

_MERGED_KEYWORDS = {**GEO_KEYWORD_COORDS, **_EXTRA_KEYWORDS}
_SORTED_ALL = sorted(_MERGED_KEYWORDS.keys(), key=len, reverse=True)
_SORTED_PHRASES = sorted(REGION_PHRASES.keys(), key=len, reverse=True)


def extract_geo_entities(text: str) -> list[dict[str, float | str]]:
    """Return [{label, lat, lng, match_type}] from text."""
    if not text or not str(text).strip():
        return []

    lower = str(text).lower()
    out: list[dict[str, float | str]] = []
    seen: set[str] = set()

    def _add(label: str, lat: float, lng: float, match_type: str) -> None:
        if label in seen:
            return
        seen.add(label)
        out.append({"label": label, "lat": lat, "lng": lng, "match_type": match_type})

    for phrase in _SORTED_PHRASES:
        if phrase in lower:
            lat, lng, label = REGION_PHRASES[phrase]
            _add(label, lat, lng, "region_phrase")

    for keyword in _SORTED_ALL:
        if keyword not in lower:
            continue
        lat, lng, label = _MERGED_KEYWORDS[keyword]
        _add(label, lat, lng, "keyword")

    for label, lat, lng in find_geo_hits(text):
        _add(label, lat, lng, "keyword")

    return out
