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
_PCT = re.compile(r"(?P<label>[A-Za-zÀ-ÿ][\w\s\-]{2,40}?)\s*[:\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*%")
_PROB = re.compile(
    r"(?P<label>probability|prob\.|probabilitat|risk|risks?|return|score)[^0-9]{0,20}(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
    re.I,
)
_TICKER = re.compile(r"\b([A-Z]{1,5})\b")
_RECOMMEND = re.compile(r"\b(BUY|HOLD|SELL|STRONG BUY|OUTPERFORM|UNDERPERFORM)\b", re.I)


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

    # Fallback: try utf-8 decode
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def parse_financial_document(text: str, *, source: str = "custom") -> dict[str, Any]:
    """Rule-based extraction of scores, percentages and recommendations."""
    if not (text or "").strip():
        return {"parse_status": "failed", "error": "Text buit", "metrics": {}}

    metrics: dict[str, Any] = {
        "source": source,
        "return_factors": [],
        "risk_factors": [],
        "percentages": [],
        "probabilities": [],
        "recommendations": [],
        "tickers_mentioned": [],
        "raw_snippets": [],
    }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    in_risk_section = False
    in_return_section = False

    for ln in lines[:500]:
        low = ln.lower()
        if any(k in low for k in ("risk", "risc", "red sector", "core risk")):
            in_risk_section = True
            in_return_section = False
        if any(k in low for k in ("return", "retorn", "green sector", "key return")):
            in_return_section = True
            in_risk_section = False

        for m in _SCORE_1_7.finditer(ln):
            entry = {"label": m.group("label").strip(), "score": int(m.group("score")), "scale": "1-7"}
            if in_risk_section:
                metrics["risk_factors"].append(entry)
            elif in_return_section:
                metrics["return_factors"].append(entry)
            else:
                metrics["return_factors"].append(entry)

        for m in _PCT.finditer(ln):
            metrics["percentages"].append(
                {"label": m.group("label").strip(), "value_pct": float(m.group("value"))}
            )
        for m in _PROB.finditer(ln):
            metrics["probabilities"].append(
                {"label": m.group("label").strip(), "value_pct": float(m.group("value"))}
            )
        for m in _RECOMMEND.finditer(ln):
            metrics["recommendations"].append(m.group(1).upper())

    # InvestWatch heuristic: count greens vs reds from 1-7 scores
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
            "note": "Patró tipus PRAAMS InvestWatch (1-7) detectat" if source == "praams" else "",
        }

    tickers = sorted(set(_TICKER.findall(text)) - {"A", "I", "OR", "AND", "THE", "EU", "US", "UK"})
    metrics["tickers_mentioned"] = tickers[:30]

    status = "ok" if (ret_scores or risk_scores or metrics["percentages"] or metrics["probabilities"]) else "partial"
    if len(text) > 200 and status == "partial":
        metrics["raw_snippets"] = [text[:400], text[-400:] if len(text) > 800 else ""]

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
