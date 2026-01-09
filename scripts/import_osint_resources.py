import json
import re
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

RAW_URL = "https://raw.githubusercontent.com/OldBonhart/Osint-Resources/master/README.md"
OUTPUT_JSON = "data/osint_sources.json"
OUTPUT_RANKINGS = "data/osint_rankings.json"
OUTPUT_DOC = "docs/OSINT_CATALOG.md"

HEADING_RE = re.compile(r"^(#{2,4})\s+(.*)")
URL_RE = re.compile(r"(https?://[^\s)]+)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")

CATEGORY_KEYWORDS = {
    "noticies": ["news", "notici", "новост", "newspapers", "media", "press"],
    "socials": ["social", "соц", "социаль", "messenger", "мессендж", "forum", "форум", "twitter", "facebook", "instagram", "tiktok", "vk", "reddit"],
    "registres_publics": ["registry", "register", "реестр", "registro", "public", "gov", "government", "cadastre", "cadastral", "офиц"],
    "empreses": ["company", "business", "empresa", "corporate", "компан", "организац", "crunchbase"],
    "geolocalitzacio": ["geo", "map", "карты", "mapa", "maps", "geocode", "geolocation"],
    "imatges": ["image", "photo", "foto", "фото", "reverse image", "face"],
    "video": ["video", "youtube", "vimeo"],
    "dominis_i_infra": ["whois", "dns", "ip", "domain", "shodan", "censys"],
    "emails_i_telefon": ["email", "mail", "phone", "телефон"],
}

TYPE_KEYWORDS = {
    "eina": ["tool", "инструмент", "instrument", "utilit", "analysis"],
    "directori": ["directory", "list", "каталог", "compilation"],
    "cerca": ["search", "поиск", "busc"],
}

FREQUENCY_BY_CATEGORY = {
    "socials": "alta",
    "noticies": "alta",
    "registres_publics": "baixa",
    "empreses": "mitjana",
    "geolocalitzacio": "mitjana",
    "imatges": "mitjana",
    "video": "alta",
    "dominis_i_infra": "alta",
    "emails_i_telefon": "mitjana",
}

CATEGORY_DEFAULT = "altres"

@dataclass
class Source:
    font: str
    url: str
    tipus: str
    categoria: str
    cobertura: str
    acces: str
    cost: str
    quota: str
    frequencia: str
    scoring: dict


def normalize_heading(heading: str) -> str:
    return heading.strip().lower()


def infer_category(heading: str, label: str) -> str:
    text = f"{heading} {label}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return CATEGORY_DEFAULT


def infer_type(heading: str, label: str) -> str:
    text = f"{heading} {label}".lower()
    for type_name, keywords in TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return type_name
    return "font"


def infer_coverage(url: str) -> str:
    host = urlparse(url).hostname or ""
    parts = host.split(".")
    tld = parts[-1] if parts else ""
    if len(tld) == 2 and tld not in {"io", "ai"}:
        return f"regional ({tld})"
    return "global"


def score_source(category: str, cost: str, acces: str, frequencia: str) -> dict:
    reliability = 3
    coverage = 3
    latency = 3
    cost_score = 5 if cost == "gratis" else 3
    access_score = 5 if acces == "public" else 3

    if category == "noticies":
        reliability += 1
        coverage += 1
        latency += 1
    elif category == "socials":
        coverage += 1
        latency += 1
    elif category == "registres_publics":
        reliability += 2
        latency -= 1
    elif category == "empreses":
        reliability += 1
    elif category == "geolocalitzacio":
        reliability += 1
    elif category == "dominis_i_infra":
        reliability += 1
        latency += 1

    if frequencia == "alta":
        latency += 1
    elif frequencia == "baixa":
        latency -= 1

    def clamp(value: int) -> int:
        return max(1, min(5, value))

    reliability = clamp(reliability)
    coverage = clamp(coverage)
    latency = clamp(latency)

    total = round((reliability + coverage + latency + cost_score + access_score) / 5, 2)
    return {
        "fiabilitat": reliability,
        "cobertura": coverage,
        "latencia": latency,
        "cost": cost_score,
        "accessibilitat": access_score,
        "total": total,
    }


def is_media_url(url: str) -> bool:
    return url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg"))


def clean_label(label: str, url: str) -> str:
    label = label.strip("-+•\t ").strip()
    label = label.strip("[]()")
    if not label or label.startswith("@") or "bot" in label.lower():
        return urlparse(url).hostname or url
    if label.lower().startswith("http"):
        return urlparse(url).hostname or url
    if not re.sub(r"[\\W_]+", "", label):
        return urlparse(url).hostname or url
    return label


def extract_sources(text: str) -> list[Source]:
    sources = []
    current_heading = ""
    seen_urls = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            current_heading = normalize_heading(heading_match.group(2))
            continue

        md_link_match = MD_LINK_RE.search(line)
        urls: list[tuple[str, str]] = []
        if md_link_match:
            label = md_link_match.group(1).strip()
            url = md_link_match.group(2).strip()
            urls.append((label, url))
        else:
            found_urls = URL_RE.findall(line)
            for url in found_urls:
                label = line.replace(url, " ").strip(" +-\t")
                label = re.sub(r"\s+", " ", label)
                if len(found_urls) > 1:
                    label = ""
                urls.append((label, url))

        for label, url in urls:
            if is_media_url(url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            label = clean_label(label, url)
            categoria = infer_category(current_heading, label)
            tipus = infer_type(current_heading, label)
            cobertura = infer_coverage(url)
            acces = "public"
            cost = "gratis"
            quota = "desconeguda"
            frequencia = FREQUENCY_BY_CATEGORY.get(categoria, "desconeguda")
            scoring = score_source(categoria, cost, acces, frequencia)

            sources.append(
                Source(
                    font=label,
                    url=url,
                    tipus=tipus,
                    categoria=categoria,
                    cobertura=cobertura,
                    acces=acces,
                    cost=cost,
                    quota=quota,
                    frequencia=frequencia,
                    scoring=scoring,
                )
            )
    return sources


def make_rankings(sources: list[Source]) -> dict:
    sorted_sources = sorted(
        sources,
        key=lambda s: (-s.scoring["total"], s.font.lower()),
    )
    top_global = sorted_sources[:20]
    categories: dict[str, list[Source]] = defaultdict(list)
    for source in sorted_sources:
        categories[source.categoria].append(source)

    top_by_category = {
        category: items[:5]
        for category, items in categories.items()
    }

    return {
        "top_global": top_global,
        "top_by_category": top_by_category,
    }


def write_outputs(sources: list[Source], rankings: dict) -> None:
    data = {
        "source": RAW_URL,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(sources),
        "sources": [
            {
                "font": s.font,
                "url": s.url,
                "tipus": s.tipus,
                "categoria": s.categoria,
                "cobertura": s.cobertura,
                "acces": s.acces,
                "cost": s.cost,
                "quota": s.quota,
                "frequencia": s.frequencia,
                "scoring": s.scoring,
            }
            for s in sources
        ],
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

    rankings_data = {
        "top_global": [
            {
                "font": s.font,
                "url": s.url,
                "categoria": s.categoria,
                "scoring_total": s.scoring["total"],
            }
            for s in rankings["top_global"]
        ],
        "top_by_category": {
            category: [
                {
                    "font": s.font,
                    "url": s.url,
                    "scoring_total": s.scoring["total"],
                }
                for s in items
            ]
            for category, items in rankings["top_by_category"].items()
        },
    }

    with open(OUTPUT_RANKINGS, "w", encoding="utf-8") as handle:
        json.dump(rankings_data, handle, ensure_ascii=False, indent=2)

    with open(OUTPUT_DOC, "w", encoding="utf-8") as handle:
        handle.write("# Catàleg de fonts OSINT normalitzat\n\n")
        handle.write(f"Font original: {RAW_URL}\n\n")
        handle.write("## Normalització\n\n")
        handle.write("Format: font, tipus, cobertura, accés, cost, quota, freqüència.\n")
        handle.write("Scoring: fiabilitat, cobertura, latència, cost, accessibilitat (1-5).\n\n")
        handle.write(f"Total de fonts: {len(sources)}\n\n")
        handle.write("## Top 20 global\n\n")
        handle.write("| # | Font | Categoria | Score | URL |\n")
        handle.write("| --- | --- | --- | --- | --- |\n")
        for idx, source in enumerate(rankings["top_global"], 1):
            handle.write(
                f"| {idx} | {source.font} | {source.categoria} | {source.scoring['total']} | {source.url} |\n"
            )
        handle.write("\n")

        handle.write("## Top 5 per categoria\n\n")
        for category, items in rankings["top_by_category"].items():
            handle.write(f"### {category}\n\n")
            handle.write("| # | Font | Score | URL |\n")
            handle.write("| --- | --- | --- | --- |\n")
            for idx, source in enumerate(items, 1):
                handle.write(
                    f"| {idx} | {source.font} | {source.scoring['total']} | {source.url} |\n"
                )
            handle.write("\n")


def main() -> None:
    with urllib.request.urlopen(RAW_URL) as response:
        text = response.read().decode("utf-8", errors="ignore")

    sources = extract_sources(text)
    rankings = make_rankings(sources)
    write_outputs(sources, rankings)


if __name__ == "__main__":
    main()
