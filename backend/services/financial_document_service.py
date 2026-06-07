"""Parse external financial/research documents (PRAAMS InvestWatch, reports, paste)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SCORE_1_7 = re.compile(
    r"(?P<label>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 \-/]{2,50}?)\s*[:\-]?\s*(?P<score>[1-7])\s*/\s*7",
    re.I,
)
_PROB = re.compile(
    r"(?:(?P<label>probability|prob\.|probabilitat)[^0-9]{0,20})"
    r"(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
    re.I,
)
_PRIMARY_REC = re.compile(
    r"(?:(?:recommendation|rating|investwatch|consensus|verdict|signal)\s*[:\-]\s*)"
    r"(?P<rec>BUY|HOLD|SELL|STRONG BUY|OUTPERFORM|UNDERPERFORM|NEUTRAL)",
    re.I,
)
_COMPANY_HEADER = re.compile(
    r"(?:InvestWatch|PRAAMS)[^\n—\-]{0,40}[—\-]\s*(?P<name>[^(|\n]{3,80})"
    r"(?:\((?P<ticker>[A-Z0-9.\-]{2,12})\))?",
    re.I,
)
_JP_TICKER = re.compile(r"\b(?P<ticker>\d{4}\.[A-Z]{1,3})\b")
_EXCHANGE_TICKER = re.compile(
    r"\b(?:NYSE|NASDAQ|TSE|LON|OTC)\s*[:\-]?\s*(?P<ticker>[A-Z]{1,5})\b",
    re.I,
)
_PARENS_TICKER = re.compile(r"\(([A-Z]{2,5})\)")

_KEY_METRIC_LINE = re.compile(
    r"(?i)\b("
    r"revenue|profit|profits|ebitda|eps|earnings|roa|roce|margin|dividend|"
    r"attributable profit|net income|operating profit|sales|"
    r"expenditure|benefici|ingressos|creixement|growth"
    r")\b[^%\n]{0,100}?(\d{1,3}(?:\.\d+)?)\s*%"
)

_FINANCIAL_LABEL_KEYWORDS = (
    "revenue",
    "profit",
    "ebitda",
    "eps",
    "margin",
    "roa",
    "roce",
    "return",
    "retorn",
    "growth",
    "creixement",
    "yield",
    "dividend",
    "risk",
    "risc",
    "forecast",
    "sales",
    "earnings",
    "benefici",
    "attributable",
    "expenditure",
    "capex",
    "ingressos",
)

_GARBAGE_COMPANY_FRAGMENTS = (
    "metric",
    "ratio",
    "sharpe",
    "tells how",
    " like ",
    "amounted to",
    "analysts predict",
    "return the",
    "and it ",
    "return on",
    "capital employed",
    "how much",
)

_RATIO_METRIC_WORDS = frozenset({"roa", "roce", "roe", "ebitda", "margin"})
_GROWTH_METRIC_WORDS = frozenset({"revenue", "eps", "earnings", "profit", "sales", "growth", "ingressos"})


def is_valid_company_name(name: str | None) -> bool:
    """Reject prose fragments misparsed as company names."""
    if not name or len(name.strip()) < 3:
        return False
    n = name.strip()
    low = n.lower()
    if any(g in low for g in _GARBAGE_COMPANY_FRAGMENTS):
        return False
    if len(n.split()) > 8 and not any(
        kw in low for kw in ("industries", "industry", "corporation", "corp", "heavy", "systems")
    ):
        return False
    from services.policy_industry_profiles import all_reference_names, looks_like_company

    if looks_like_company(n):
        return True
    for prof in all_reference_names().values():
        pn = prof["name"].lower()
        if low == pn or pn in low or low in pn:
            return True
        for alias in prof.get("aliases") or []:
            if alias.lower() in low:
                return True
    if re.search(r"\b(kawasaki|mitsubishi|lockheed|boeing|ihi|nec)\b", low):
        return True
    return False


def _metric_kind(label: str, snippet: str) -> str:
    l = (label or "").lower()
    sn = (snippet or "").lower()
    if any(x in l for x in ("nikkei", "225", "index", "forecast")):
        return "exclude"
    if any(x in l for x in _RATIO_METRIC_WORDS):
        return "ratio"
    if any(
        w in sn
        for w in (
            " up ",
            "upside",
            "growth",
            " rose ",
            " jumped ",
            " fell ",
            "from fy",
            "predict",
            "requiring",
            "reported revenue",
        )
    ):
        return "growth"
    if any(x in l for x in _GROWTH_METRIC_WORDS):
        return "growth"
    return "other"


def _snippet_quality(snippet: str) -> int:
    sn = (snippet or "").lower()
    score = 0
    if sn.lstrip().startswith(","):
        score -= 5
    for w in ("fy26", "fy25", "predict", "upside", "reported", "amounted", "7012"):
        if w in sn:
            score += 2
    if len(sn) > 30:
        score += 1
    return score


def _verdict_score(verdict: str) -> float:
    """Map PRAAMS textual verdicts to 1-7 proxy scores."""
    v = (verdict or "").lower().strip()
    if "very low" in v:
        return 6.0
    if any(w in v for w in ("poor", "unfavourable", "unfavorable", "overvalued", "weak")):
        return 2.5
    if any(w in v for w in ("somewhat favourable", "somewhat favorable", "decent")):
        return 5.0
    if any(w in v for w in ("fairly valued", "fair", "average", "mixed", "moderate", "modest")):
        return 4.0
    if any(w in v for w in ("favourable", "favorable", "undervalued", "good")):
        return 5.5
    return 4.0


def _bullet_score(line: str) -> float:
    low = (line or "").lower()
    if "poor" in low or "unfavourable" in low or "unfavorable" in low:
        return 2.5
    if "somewhat" in low or "decent" in low or "moderate" in low:
        return 4.5
    if any(w in low for w in ("good", "favourable", "favorable", "sufficiently", "resilient")):
        return 5.5
    return 4.0


_PRAAMS_BODY_HEADER = re.compile(
    r"(?P<company>[A-Za-z][^\n]{3,90}?),?\s*(?:Ltd\.?|Inc\.?|Corp\.?)?\s*"
    r"(?P<ticker>\d{4}\.[A-Z]{1,3})\s+(?P<ratio>[1-7])\s*\n",
    re.M,
)
_PRAAMS_VERDICT = re.compile(
    r"(Valuation|Performance|Analyst view|Profitability|Growth|Dividends|"
    r"Default risk|Volatility|Stress-test|Selling difficulty|Country risk|Country|ESG)"
    r"\s*:\s*(?P<verdict>[A-Za-z][A-Za-z \-/]+?)(?:\n|\.(?=\s|$)|$)",
    re.I | re.M,
)
_PRAAMS_BUY_PROSE = re.compile(r"means a\s+(BUY|HOLD|SELL)\s+recommendation", re.I)
_PRAAMS_ANALYST_UPSIDE = re.compile(
    r"suggests\s+(?P<pct>\d{1,2}(?:\.\d+)?)\s*%\s*upside potential",
    re.I,
)


def _praams_analysis_window(text: str) -> str:
    """Core InvestWatch pages — skip methodology intro and legal/news tail."""
    start = text.find("Key risks factors")
    if start < 0:
        start = 0
    end_markers = (
        "Profit Jumps",
        "Terms of service",
        "PLEASE READ CAREFULLY",
        "Counterparties",
    )
    end = len(text)
    for marker in end_markers:
        idx = text.find(marker, start + 200 if start else 0)
        if 0 <= idx < end:
            end = idx
    return text[start:end]


def parse_praams_investwatch_pdf(text: str) -> dict[str, Any] | None:
    """
    Structured extract for PRAAMS InvestWatch PDF exports.
    The 12-sector clock is graphical — scores come from ratio header + textual verdicts.
    """
    intro = text[:4000]
    if "Key risks factors" not in text:
        return None

    window = _praams_analysis_window(text)
    header = _PRAAMS_BODY_HEADER.search(window) or _PRAAMS_BODY_HEADER.search(text)
    if not header:
        return None
    if "InvestWatch" not in intro and "PRAAMS Ratio" not in intro and "Key return factors" not in text:
        return None

    company_raw = header.group("company").strip().rstrip(",")
    ticker = header.group("ticker")
    praams_ratio = int(header.group("ratio"))

    risk_lines: list[str] = []
    return_lines: list[str] = []
    section = None
    for line in window.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "Key risks factors":
            section = "risk"
            continue
        if stripped == "Key return factors":
            section = "return"
            continue
        if stripped in ("Information", "Company profile", "Risk Return", "Calendar & expectations"):
            section = None
            continue
        if section == "risk" and not stripped.startswith("Page"):
            risk_lines.append(stripped)
        elif section == "return" and not stripped.startswith("Page"):
            return_lines.append(stripped)

    verdicts: dict[str, str] = {}
    for m in _PRAAMS_VERDICT.finditer(window):
        key = m.group(1).strip()
        val = m.group("verdict").strip()
        if len(val) > 2:
            verdicts[key] = val

    rec = None
    buy_m = _PRAAMS_BUY_PROSE.search(window)
    if buy_m:
        rec = buy_m.group(1).upper()

    upside = None
    up_m = _PRAAMS_ANALYST_UPSIDE.search(window)
    if up_m:
        upside = float(up_m.group("pct"))

    return_scores = [_bullet_score(x) for x in return_lines[:6]]
    risk_scores = [_bullet_score(x) for x in risk_lines[:6]]
    verdict_return = [
        _verdict_score(v)
        for k, v in verdicts.items()
        if k.lower() in ("growth", "dividends", "profitability", "analyst view", "performance", "valuation")
    ]
    verdict_risk = [
        _verdict_score(v)
        for k, v in verdicts.items()
        if k.lower()
        in ("default risk", "volatility", "stress-test", "selling difficulty", "country", "country risk")
    ]
    avg_ret_vals = return_scores + verdict_return
    avg_risk_vals = risk_scores + verdict_risk
    avg_ret = round(sum(avg_ret_vals) / len(avg_ret_vals), 2) if avg_ret_vals else float(praams_ratio)
    avg_risk = round(sum(avg_risk_vals) / len(avg_risk_vals), 2) if avg_risk_vals else float(praams_ratio)

    return {
        "company_name": company_raw.replace(", Ltd.", "").replace(", Ltd", "").strip(),
        "primary_ticker": ticker,
        "praams_ratio": praams_ratio,
        "key_risk_summaries": risk_lines[:6],
        "key_return_summaries": return_lines[:6],
        "factor_verdicts": verdicts,
        "primary_recommendation": rec,
        "analyst_upside_pct": upside,
        "investwatch_summary": {
            "praams_ratio": praams_ratio,
            "avg_return_score": avg_ret,
            "avg_risk_score": avg_risk,
            "signal": (
                "more_return_than_risk"
                if avg_ret > avg_risk
                else "more_risk_than_return"
                if avg_risk > avg_ret
                else "neutral"
            ),
            "note": "PRAAMS InvestWatch PDF — rellotge gràfic; scores proxy des de ratio i verdicts textuals.",
        },
        "return_factors": [
            {"label": line[:60], "score": _bullet_score(line)} for line in return_lines[:6]
        ],
        "risk_factors": [{"label": line[:60], "score": _bullet_score(line)} for line in risk_lines[:6]],
    }


def derive_external_signal(metrics: dict[str, Any], text: str = "") -> str | None:
    """Infer BUY/HOLD/SELL from news prose when no explicit Recommendation line."""
    rec = metrics.get("primary_recommendation")
    if rec:
        return rec
    upside = metrics.get("fair_value_upside_pct")
    if isinstance(upside, (int, float)) and upside >= 10:
        return "BUY"
    blob = (text or "").lower()
    if re.search(r"shares?\s+jumped\s+(?:more\s+than\s+)?\d+\s*%", blob):
        return "BUY"
    if re.search(r"shares?\s+(?:fell|dropped|declined)\s+\d+\s*%", blob):
        return "SELL"
    growth = [k for k in (metrics.get("key_metrics") or []) if k.get("metric_kind") == "growth"]
    if growth:
        vals = [float(k["value_pct"]) for k in growth[:4]]
        avg = sum(vals) / len(vals)
        if avg >= 8:
            return "BUY"
        if avg <= -2:
            return "SELL"
        return "HOLD"
    return None


def build_report_narrative(
    company: str | None,
    *,
    title: str = "",
    eina_link: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> str:
    """Human-readable report summary — never uses garbage parsed company strings."""
    eina_link = eina_link or {}
    metrics = metrics or {}
    if not company or not is_valid_company_name(company):
        return (
            "No s'ha identificat l'empresa de l'informe. "
            "Selecciona-la al registre EINA o posa un títol clar (p.ex. Kawasaki — InvestWatch)."
        )

    parts = [f"Informe financer / notícia sobre **{company}**."]
    if metrics.get("parse_mode") == "praams_investwatch":
        ticker = metrics.get("primary_ticker") or metrics.get("suggested_ticker") or ""
        ratio = metrics.get("praams_ratio") or (metrics.get("investwatch_summary") or {}).get("praams_ratio")
        parts = [f"Informe **PRAAMS InvestWatch** sobre **{company}**" + (f" ({ticker})" if ticker else "") + "."]
        if ratio is not None:
            parts.append(f"PRAAMS Ratio: {ratio}/7 (retorn-risc global).")
        ret_sum = metrics.get("key_return_summaries") or []
        risk_sum = metrics.get("key_risk_summaries") or []
        if ret_sum:
            parts.append("Retorn: " + "; ".join(ret_sum[:3]) + ".")
        if risk_sum:
            parts.append("Risc: " + "; ".join(risk_sum[:3]) + ".")
        verdicts = metrics.get("factor_verdicts") or {}
        highlights = [
            f"{k}: {verdicts[k]}"
            for k in ("Analyst view", "Growth", "Valuation", "Profitability", "Performance")
            if k in verdicts
        ]
        if highlights:
            parts.append("Verdicts: " + ", ".join(highlights) + ".")
        upside = metrics.get("fair_value_upside_pct") or metrics.get("analyst_upside_pct")
        if upside:
            parts.append(f"Upside consens analistes: {upside}%.")
    elif title and title.strip().lower() not in company.lower():
        parts.append(f"Títol registrat: «{title.strip()[:100]}».")

    km = metrics.get("key_metrics") or []
    ratios = [k for k in km if k.get("metric_kind") == "ratio"][:4]
    growth = [k for k in km if k.get("metric_kind") == "growth"][:4]
    if ratios:
        parts.append(
            "Ratios extrets: "
            + ", ".join(f"{k['label']} {k['value_pct']}%" for k in ratios)
            + "."
        )
    if growth:
        parts.append(
            "Creixement / marge dinàmic: "
            + ", ".join(f"{k['label']} {k['value_pct']}%" for k in growth)
            + "."
        )
    derived = metrics.get("derived_signal")
    if metrics.get("primary_recommendation"):
        parts.append(f"Recomanació PRAAMS/analistes: {metrics['primary_recommendation']}.")
    elif derived:
        parts.append(f"Senyal inferit del text (sense línia Recommendation explícita): {derived}.")

    if metrics.get("parse_quality") == "weak":
        parts.append(
            "Qualitat de parseig baixa — les xifres s'han filtrat; "
            "complementa amb resum PRAAMS 1-7 si en tens."
        )

    if eina_link.get("found"):
        origins = ", ".join(eina_link.get("origins") or ["policy"])
        parts.append(f"EINA la vincula al cas ({origins}).")
        if eina_link.get("beneficiary_rationale"):
            parts.append(str(eina_link["beneficiary_rationale"])[:200] + ".")
    else:
        parts.append("Encara sense entrada al registre viu del cas — selecciona l'entitat manualment.")

    return " ".join(parts).replace("**", "")


def sanitize_parsed_metrics(
    metrics: dict[str, Any],
    *,
    text: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Fix bad company names, classify metrics, derive signals and parse quality."""
    if metrics.get("company_name") and not is_valid_company_name(metrics["company_name"]):
        metrics["company_name"] = None

    ref = metrics.get("reference_entity")
    if ref and is_valid_company_name(ref):
        metrics["company_name"] = ref

    if not metrics.get("company_name"):
        for d in metrics.get("detected_companies") or []:
            if is_valid_company_name(d.get("name")):
                metrics["company_name"] = d["name"]
                break

    if not metrics.get("company_name") and title:
        for d in detect_companies_in_text(text, title=title):
            metrics["company_name"] = d["name"]
            break

    m_up = None
    if not metrics.get("fair_value_upside_pct"):
        m_up = re.search(
            r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:upside|upside to|upside from)",
            text,
            re.I,
        )
    if m_up:
        metrics["fair_value_upside_pct"] = float(m_up.group(1))

    clean_metrics: list[dict[str, Any]] = []
    by_label: dict[str, dict[str, Any]] = {}
    for km in metrics.get("key_metrics") or []:
        kind = _metric_kind(km.get("label", ""), km.get("snippet", ""))
        if kind == "exclude":
            continue
        entry = {**km, "metric_kind": kind}
        label_key = (km.get("label") or "").lower()
        prev = by_label.get(label_key)
        if not prev or _snippet_quality(entry.get("snippet", "")) > _snippet_quality(prev.get("snippet", "")):
            by_label[label_key] = entry
    clean_metrics = list(by_label.values())[:10]
    metrics["key_metrics"] = clean_metrics
    metrics["percentages"] = list(clean_metrics)

    derived = derive_external_signal(metrics, text)
    if derived:
        metrics["derived_signal"] = derived
        if not metrics.get("primary_recommendation"):
            metrics["inferred_recommendation"] = derived

    has_iw = bool((metrics.get("investwatch_summary") or {}).get("avg_return_score") is not None)
    has_valid_co = is_valid_company_name(metrics.get("company_name"))
    has_rec = bool(metrics.get("primary_recommendation") or metrics.get("derived_signal"))
    has_clean = bool(clean_metrics)

    if has_iw and has_valid_co:
        metrics["parse_quality"] = "good"
    elif has_valid_co and has_rec and has_clean:
        metrics["parse_quality"] = "good"
    elif has_valid_co and (has_rec or has_clean):
        metrics["parse_quality"] = "partial"
    else:
        metrics["parse_quality"] = "weak"

    if metrics["parse_quality"] == "weak" and not metrics.get("parse_warning"):
        metrics["parse_warning"] = (
            "Parseig de notícia/informe amb soroll. Selecciona l'empresa al desplegable "
            "i contrasta amb dades PRAAMS 1-7 si cal."
        )
    return metrics

_GARBAGE_LABEL_ENDINGS = (
    " from",
    " to",
    " of",
    " a",
    " the",
    " up",
    " down",
    " into",
    " that",
    " is",
    " be",
    " rose",
    " fell",
    " gained",
    " less than",
    " requiring",
    " representing",
    " amounted",
    " declined",
    " equalled",
    " suggests",
    " jumped",
    " climbed",
)

_TICKER_STOP = frozenset(
    {
        "A",
        "I",
        "B",
        "AI",
        "OR",
        "AND",
        "THE",
        "EU",
        "US",
        "UK",
        "FY",
        "EPS",
        "EBITDA",
        "ROA",
        "ROCE",
        "CEO",
        "CFO",
        "IPO",
        "ETF",
        "GDP",
        "PRAAMS",
        "BUY",
        "SELL",
        "HOLD",
        "NYSE",
        "NASDAQ",
        "TSE",
        "LON",
        "OTC",
        "PE",
        "PB",
        "RSI",
        "ROE",
        "YOY",
        "QOQ",
        "FOR",
        "JPY",
        "USD",
        "EUR",
        "GBP",
        "JP",
        "IT",
        "AT",
        "BE",
        "IS",
        "AS",
        "ON",
        "IN",
        "TO",
        "OF",
        "IF",
        "MY",
        "WE",
        "HE",
        "SE",
        "NO",
        "SO",
        "GO",
        "DO",
        "BY",
        "AN",
        "AT",
        "VS",
        "PM",
        "AM",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "FY26",
        "FY25",
    }
)


def _is_valid_metric_label(label: str) -> bool:
    l = (label or "").strip().lower()
    if len(l) < 5:
        return False
    if any(l.endswith(e.strip()) or l.endswith(e) for e in _GARBAGE_LABEL_ENDINGS):
        return False
    if not any(kw in l for kw in _FINANCIAL_LABEL_KEYWORDS):
        return False
    return True


def _normalize_rec(raw: str) -> str:
    r = raw.upper().strip()
    if "STRONG BUY" in r or r == "OUTPERFORM":
        return "BUY"
    if r == "UNDERPERFORM":
        return "SELL"
    if r == "NEUTRAL":
        return "HOLD"
    return r


def _extract_primary_recommendation(text: str) -> str | None:
    for m in _PRIMARY_REC.finditer(text):
        return _normalize_rec(m.group("rec"))
    return None


def _extract_tickers(text: str) -> list[str]:
    found: set[str] = set()
    for m in _JP_TICKER.finditer(text):
        found.add(m.group("ticker"))
    for m in _EXCHANGE_TICKER.finditer(text):
        t = m.group("ticker")
        if t not in _TICKER_STOP and len(t) >= 2:
            found.add(t)
    for m in _PARENS_TICKER.finditer(text[:1200]):
        t = m.group(1)
        if t not in _TICKER_STOP and len(t) >= 2:
            found.add(t)
    return sorted(found)[:12]


def _extract_company_header(text: str) -> tuple[str | None, str | None]:
    m = _COMPANY_HEADER.search(text[:800])
    if m:
        name = (m.group("name") or "").strip(" -—\t")
        ticker = m.group("ticker")
        return name or None, ticker
    return None, None


def detect_companies_in_text(text: str, *, title: str = "") -> list[dict[str, Any]]:
    """Find companies mentioned in report text using EINA reference profiles + title."""
    from services.policy_industry_profiles import all_reference_names

    ref = all_reference_names()
    combined = f"{title}\n{text[:12000]}"
    blob = combined.lower()
    hits: dict[str, dict[str, Any]] = {}

    entries = sorted(ref.items(), key=lambda x: len(x[0]), reverse=True)
    for _key, prof in entries:
        name = prof["name"]
        terms = [name.lower(), *[a.lower() for a in (prof.get("aliases") or [])]]
        for pat in terms:
            if len(pat) < 3:
                continue
            if len(pat) <= 4:
                if not re.search(rf"\b{re.escape(pat)}\b", blob):
                    continue
            elif pat not in blob:
                continue
            score = len(pat) + (20 if pat == name.lower() else 5)
            if title and pat in title.lower():
                score += 30
            prev = hits.get(name.lower())
            if not prev or prev["score"] < score:
                hits[name.lower()] = {
                    "name": name,
                    "country": prof.get("country"),
                    "region": prof.get("region"),
                    "match_kind": "reference_profile",
                    "matched_term": pat,
                    "score": score,
                    "beneficiary_rationale": (prof.get("beneficiary_rationale") or "")[:240],
                    "policy_link": prof.get("policy_link", ""),
                }

    for m in re.finditer(
        r"\b(Kawasaki|Mitsubishi|Lockheed|Boeing|Hyundai|Rheinmetall|BAE|NEC|IHI)\b"
        r"(?:\'s|\s+(?:Heavy|Electric|Industries|Corporation|Corp))?",
        combined[:6000],
        re.I,
    ):
        token = m.group(1).lower()
        for _key, prof in ref.items():
            if token in prof["name"].lower() or any(token in a.lower() for a in (prof.get("aliases") or [])):
                name = prof["name"]
                if name.lower() not in hits:
                    hits[name.lower()] = {
                        "name": name,
                        "country": prof.get("country"),
                        "region": prof.get("region"),
                        "match_kind": "news_mention",
                        "matched_term": m.group(0),
                        "score": 15,
                        "beneficiary_rationale": (prof.get("beneficiary_rationale") or "")[:240],
                        "policy_link": prof.get("policy_link", ""),
                    }

    return sorted(hits.values(), key=lambda x: -x["score"])[:6]


def resolve_suggested_ticker(company_name: str | None, text_tickers: list[str] | None = None) -> str | None:
    """Prefer ticker from reference profile, then parsed text."""
    from services.policy_industry_profiles import ticker_for_company

    if company_name:
        profile_ticker = ticker_for_company(company_name)
        if profile_ticker:
            return profile_ticker
    for t in text_tickers or []:
        if t and len(t) >= 3:
            return t
    return None


def needs_llm_narrative(
    text: str,
    metrics: dict[str, Any],
    *,
    title: str = "",
) -> tuple[bool, str]:
    """
    Decide if optional LLM narrative is warranted.
    InvestWatch / structured parses never need LLM — rules cover numbers and actions.
    """
    parse_mode = metrics.get("parse_mode") or "unknown"
    if parse_mode in ("investwatch", "praams_investwatch"):
        if metrics.get("return_factors") or metrics.get("risk_factors") or metrics.get("praams_ratio"):
            return False, "investwatch_structured"

    has_rec = bool(metrics.get("primary_recommendation"))
    has_iw = bool((metrics.get("investwatch_summary") or {}).get("avg_return_score") is not None)
    has_key = bool(metrics.get("key_metrics"))
    has_company = bool(metrics.get("company_name") or metrics.get("detected_companies"))

    if has_company and has_rec and (has_iw or has_key):
        return False, "rules_sufficient"

    blob_len = len(f"{title}\n{text}".strip())
    if blob_len < 150:
        return False, "text_too_short"

    if not has_company:
        return True, "no_company_detected"
    if metrics.get("parse_warning"):
        return True, "parse_partial"
    if parse_mode in ("partial", "unknown", "financial_news") and not has_rec and blob_len > 350:
        return True, "prose_without_recommendation"
    if not has_rec and not has_iw and not has_key and blob_len > 300:
        return True, "unstructured_prose"

    return False, "rules_sufficient"


async def interpret_report_narrative_llm(
    text: str,
    *,
    company: str | None,
    eina_context: dict[str, Any],
    structured_summary: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Optional LLM pass for narrative only — never mutates numeric metrics.
    Returns None when no provider or on failure.
    """
    from services.llm_service import LLMService, resolve_provider

    if not resolve_provider():
        return None

    llm = LLMService(mode="extract")
    prompt = json.dumps(
        {
            "company": company,
            "title": eina_context.get("title", ""),
            "text_excerpt": text[:5000],
            "structured_facts": structured_summary,
            "eina_link": eina_context.get("eina_link") or {},
            "instruction": (
                "Respon en català. Resumeix de què va l'informe (5-7 línies), "
                "indica senyal d'inversió qualitatiu (BUY/HOLD/SELL/MONITOR) "
                "basat només en el text i el context EINA. "
                "NO inventis percentatges ni puntuacions 1-7. "
                "Retorna JSON: {narrative_ca, action_hint, risks[] (màx 3)}"
            ),
        },
        ensure_ascii=False,
    )
    system = (
        "Analista financer. Usa només el text proporcionat. "
        "Retorna NOMÉS JSON vàlid, sense markdown."
    )
    try:
        raw = await asyncio.to_thread(llm.complete, prompt, system, 1200)
        if raw.strip().startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        narrative = (data.get("narrative_ca") or data.get("summary_ca") or "").strip()
        if not narrative:
            return None
        return {
            "narrative": narrative,
            "action_hint": (data.get("action_hint") or "").strip(),
            "risks": list(data.get("risks") or [])[:3],
            "llm_used": True,
        }
    except Exception as exc:
        logger.warning("LLM narrative interpretation failed: %s", exc)
        return None


def preview_parse(
    text: str,
    *,
    source: str = "custom",
    title: str = "",
    focus_company: str | None = None,
) -> dict[str, Any]:
    """Parse without persisting — for upload preview and LLM need detection."""
    parsed = parse_financial_document(text, source=source)
    metrics = parsed.get("metrics") or {}
    if title:
        for d in detect_companies_in_text(text, title=title):
            if d["name"] not in {x.get("name") for x in metrics.get("detected_companies") or []}:
                metrics.setdefault("detected_companies", []).insert(0, d)
        sanitize_parsed_metrics(metrics, text=text, title=title)

    if focus_company and not metrics.get("company_name"):
        apply_reference_entity(metrics, focus_company, source="preview_focus", text=text, title=title)

    company = metrics.get("company_name") or focus_company
    metrics["suggested_ticker"] = resolve_suggested_ticker(
        company, metrics.get("tickers_mentioned")
    )

    need_llm, llm_reason = needs_llm_narrative(text, metrics, title=title)
    from services.investwatch_report_view import build_investwatch_report_view

    investwatch_report = build_investwatch_report_view(metrics, title=title)
    if metrics.get("company_name") and is_valid_company_name(metrics.get("company_name")):
        investwatch_report["narrative"] = build_report_narrative(
            metrics["company_name"],
            title=title,
            metrics=metrics,
        )
    return {
        "parse_status": parsed.get("parse_status"),
        "parse_mode": metrics.get("parse_mode"),
        "company_name": metrics.get("company_name"),
        "reference_entity": metrics.get("reference_entity"),
        "primary_ticker": metrics.get("primary_ticker") or metrics.get("suggested_ticker"),
        "suggested_ticker": metrics.get("suggested_ticker"),
        "primary_recommendation": metrics.get("primary_recommendation"),
        "derived_signal": metrics.get("derived_signal"),
        "praams_ratio": metrics.get("praams_ratio"),
        "fair_value_upside_pct": metrics.get("fair_value_upside_pct"),
        "factor_verdicts": metrics.get("factor_verdicts"),
        "key_risk_summaries": metrics.get("key_risk_summaries"),
        "key_return_summaries": metrics.get("key_return_summaries"),
        "detected_companies": metrics.get("detected_companies") or [],
        "parse_warning": metrics.get("parse_warning"),
        "parse_quality": metrics.get("parse_quality"),
        "needs_llm_narrative": need_llm,
        "llm_narrative_reason": llm_reason,
        "investwatch_summary": metrics.get("investwatch_summary"),
        "return_factors_count": len(metrics.get("return_factors") or []),
        "risk_factors_count": len(metrics.get("risk_factors") or []),
        "investwatch_report": investwatch_report,
    }


def apply_reference_entity(
    metrics: dict[str, Any],
    reference_entity: str | None,
    *,
    source: str = "user",
    text: str = "",
    title: str = "",
) -> None:
    """Pin report metrics to a user-selected company or actor from the case registry."""
    if not reference_entity or not str(reference_entity).strip():
        return
    ref = str(reference_entity).strip()
    from services.policy_industry_profiles import ticker_for_company

    metrics["reference_entity"] = ref
    metrics["reference_entity_source"] = source
    metrics["company_name"] = ref
    ticker = ticker_for_company(ref)
    if ticker:
        metrics["suggested_ticker"] = ticker
        metrics["primary_ticker"] = ticker
    sanitize_parsed_metrics(metrics, text=text, title=title)


def _extract_key_metrics(text: str) -> list[dict[str, Any]]:
    by_label: dict[str, dict[str, Any]] = {}
    for m in _KEY_METRIC_LINE.finditer(text):
        label = m.group(1).strip()
        val = float(m.group(2))
        snippet = text[max(0, m.start() - 30) : m.end() + 20].replace("\n", " ").strip()
        if snippet.lstrip().startswith(","):
            continue
        kind = _metric_kind(label, snippet)
        if kind == "exclude":
            continue
        entry = {
            "label": label.upper() if len(label) <= 5 else label.title(),
            "value_pct": val,
            "snippet": snippet[:160],
            "metric_kind": kind,
        }
        label_key = label.lower()
        prev = by_label.get(label_key)
        if not prev or _snippet_quality(snippet) > _snippet_quality(prev.get("snippet", "")):
            by_label[label_key] = entry
        if len(by_label) >= 14:
            break
    return list(by_label.values())[:10]


def extract_text_from_bytes(data: bytes, filename: str = "") -> str:
    """Best-effort text extraction from upload."""
    name = (filename or "").lower()
    if name.endswith((".txt", ".md", ".html", ".htm", ".csv", ".json")):
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages[:40]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts).strip()
        except ImportError:
            raise ValueError(
                "PDF requereix pypdf. Instal·la amb: pip install pypdf — o enganxa el text manualment."
            )
        except Exception as exc:
            raise ValueError(f"No s'ha pogut llegir el PDF: {exc}") from exc

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def parse_financial_document(text: str, *, source: str = "custom", title: str = "") -> dict[str, Any]:
    """Structured extraction: InvestWatch 1-7 scores, key financial metrics, primary recommendation."""
    if not (text or "").strip():
        return {"parse_status": "failed", "error": "Text buit", "metrics": {}}

    metrics: dict[str, Any] = {
        "source": source,
        "parse_mode": "unknown",
        "company_name": None,
        "primary_ticker": None,
        "return_factors": [],
        "risk_factors": [],
        "key_metrics": [],
        "percentages": [],
        "probabilities": [],
        "primary_recommendation": None,
        "recommendations": [],
        "tickers_mentioned": [],
        "detected_companies": [],
        "raw_snippets": [],
    }

    company_name, header_ticker = _extract_company_header(text)
    if company_name and is_valid_company_name(company_name):
        metrics["company_name"] = company_name
        metrics["primary_ticker"] = header_ticker
    elif header_ticker:
        metrics["primary_ticker"] = header_ticker

    detected = detect_companies_in_text(text, title=title)
    metrics["detected_companies"] = detected
    if not metrics["company_name"] and detected:
        for d in detected:
            if is_valid_company_name(d.get("name")):
                metrics["company_name"] = d["name"]
                break
    if not metrics["primary_ticker"] and detected:
        for t in _extract_tickers(text):
            metrics["primary_ticker"] = t
            break

    praams_data = parse_praams_investwatch_pdf(text)
    metrics_window = _praams_analysis_window(text) if praams_data else text

    lines = [ln.strip() for ln in metrics_window.splitlines() if ln.strip()]
    in_risk_section = False
    in_return_section = False

    for ln in lines[:500]:
        low = ln.lower()
        if any(k in low for k in ("risk factor", "risc", "red sector", "core risk")):
            in_risk_section = True
            in_return_section = False
        if any(k in low for k in ("return factor", "retorn", "green sector", "key return")):
            in_return_section = True
            in_risk_section = False

        for m in _SCORE_1_7.finditer(ln):
            label = m.group("label").strip()
            if not _is_valid_metric_label(label) and not any(
                c.isalpha() for c in label if c not in " -/"
            ):
                continue
            entry = {"label": label, "score": int(m.group("score")), "scale": "1-7"}
            if in_risk_section:
                metrics["risk_factors"].append(entry)
            elif in_return_section:
                metrics["return_factors"].append(entry)
            else:
                if any(k in label.lower() for k in ("risk", "risc", "leverage", "liquidity")):
                    metrics["risk_factors"].append(entry)
                else:
                    metrics["return_factors"].append(entry)

        for m in _PROB.finditer(ln):
            metrics["probabilities"].append(
                {"label": m.group("label").strip(), "value_pct": float(m.group("value"))}
            )

    metrics["key_metrics"] = _extract_key_metrics(metrics_window)
    metrics["percentages"] = list(metrics["key_metrics"])

    primary_rec = _extract_primary_recommendation(metrics_window) or _extract_primary_recommendation(text)
    metrics["primary_recommendation"] = primary_rec
    if primary_rec:
        metrics["recommendations"] = [primary_rec]

    tickers = _extract_tickers(text)
    if header_ticker and header_ticker not in tickers:
        tickers.insert(0, header_ticker)
    metrics["tickers_mentioned"] = tickers
    metrics["suggested_ticker"] = resolve_suggested_ticker(
        metrics.get("company_name"), tickers
    )
    if not metrics["primary_ticker"] and metrics["suggested_ticker"]:
        metrics["primary_ticker"] = metrics["suggested_ticker"]

    ret_scores = [x["score"] for x in metrics["return_factors"]]
    risk_scores = [x["score"] for x in metrics["risk_factors"]]
    if ret_scores or risk_scores:
        avg_ret = sum(ret_scores) / len(ret_scores) if ret_scores else None
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else None
        metrics["investwatch_summary"] = {
            "avg_return_score": round(avg_ret, 2) if avg_ret is not None else None,
            "avg_risk_score": round(avg_risk, 2) if avg_risk is not None else None,
            "signal": (
                "more_return_than_risk"
                if avg_ret and avg_risk and avg_ret > avg_risk
                else "more_risk_than_return"
                if avg_ret and avg_risk and avg_risk > avg_ret
                else "neutral"
            ),
            "note": "Patró PRAAMS InvestWatch (puntuacions 1-7)" if source == "praams" else "",
        }
        metrics["parse_mode"] = "investwatch"
    elif praams_data:
        co = praams_data.get("company_name")
        if co and is_valid_company_name(co):
            metrics["company_name"] = co
        metrics["primary_ticker"] = praams_data.get("primary_ticker") or metrics.get("primary_ticker")
        metrics["praams_ratio"] = praams_data["praams_ratio"]
        metrics["key_risk_summaries"] = praams_data.get("key_risk_summaries") or []
        metrics["key_return_summaries"] = praams_data.get("key_return_summaries") or []
        metrics["factor_verdicts"] = praams_data.get("factor_verdicts") or {}
        metrics["return_factors"] = praams_data.get("return_factors") or metrics["return_factors"]
        metrics["risk_factors"] = praams_data.get("risk_factors") or metrics["risk_factors"]
        metrics["investwatch_summary"] = praams_data["investwatch_summary"]
        if praams_data.get("primary_recommendation"):
            metrics["primary_recommendation"] = praams_data["primary_recommendation"]
            metrics["recommendations"] = [praams_data["primary_recommendation"]]
        if praams_data.get("analyst_upside_pct") is not None:
            metrics["fair_value_upside_pct"] = praams_data["analyst_upside_pct"]
            metrics["analyst_upside_pct"] = praams_data["analyst_upside_pct"]
        metrics["parse_mode"] = "praams_investwatch"
    elif metrics["key_metrics"]:
        metrics["parse_mode"] = "financial_news"
    else:
        metrics["parse_mode"] = "partial"

    has_signal = bool(
        ret_scores
        or risk_scores
        or metrics["key_metrics"]
        or metrics["probabilities"]
        or primary_rec
        or praams_data
    )
    status = "ok" if has_signal else "partial"
    if len(text) > 200 and status == "partial":
        metrics["raw_snippets"] = [text[:400], text[-400:] if len(text) > 800 else ""]

    if status == "partial" and len(text) > 100:
        metrics["parse_warning"] = (
            "No s'han detectat puntuacions InvestWatch (X/7). "
            "Enganxa el resum PRAAMS amb factors retorn/risc 1-7, o un informe amb "
            "mètriques clares (Revenue +X%, Profit +Y%)."
        )

    sanitize_parsed_metrics(metrics, text=text, title=title)

    return {"parse_status": status, "metrics": metrics, "char_count": len(text)}


async def enrich_metrics_with_llm(text: str, source: str, base_metrics: dict[str, Any]) -> dict[str, Any]:
    from services.llm_service import LLMService, resolve_provider

    if not resolve_provider():
        return base_metrics

    llm = LLMService(mode="extract")
    prompt = json.dumps(
        {
            "source": source,
            "text_excerpt": text[:6000],
            "existing_metrics": base_metrics,
            "instruction": (
                "Extract structured financial intelligence: companies, risk scores 0-100, "
                "return potential, probabilities, BUY/HOLD/SELL, sector exposure. "
                "Return JSON with keys: companies[], risk_scores[], return_scores[], "
                "probabilities[], recommendation, summary_es or summary_ca."
            ),
        },
        ensure_ascii=False,
    )
    system = "You extract financial metrics from research reports. Return ONLY valid JSON."
    try:
        raw = await asyncio.to_thread(llm.complete, prompt, system, 3000)
        if raw.strip().startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw)
        extra = json.loads(raw)
        if isinstance(extra, dict):
            base_metrics["llm_extracted"] = extra
    except Exception as exc:
        logger.warning("LLM financial parse failed: %s", exc)
    return base_metrics
