"""Analytics Lab — async-friendly sensitivity, Monte Carlo, market correlations (Phase C).

Not on the financial crossover sync hot path. Uses numpy when available; pure-Python fallback otherwise.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

_lab_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 3600


def _cache_key(case_id: int, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return f"lab:{case_id}:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _get_cached(key: str) -> dict[str, Any] | None:
    entry = _lab_cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("_ts", 0) > _CACHE_TTL:
        _lab_cache.pop(key, None)
        return None
    return entry.get("result")


def _set_cache(key: str, result: dict[str, Any]) -> None:
    _lab_cache[key] = {"_ts": time.time(), "result": result}


def _icg_from_components(components: list[dict[str, Any]]) -> float | None:
    if not components:
        return None
    total_w = sum(float(c.get("weight") or c.get("base_weight") or 0) for c in components)
    if total_w <= 0:
        return None
    return round(
        sum(float(c["value"]) * float(c.get("weight") or c.get("base_weight") or 0) for c in components)
        / total_w,
        1,
    )


def resolve_lab_confidence(
    confidence_bundle: dict[str, Any],
    *,
    scope: str = "auto",
) -> tuple[list[dict[str, Any]], float | None, str]:
    """Pick case (ICG_cas) or entity (ICE) components for analytics experiments."""
    has_entity = confidence_bundle.get("entity_confidence_index") is not None
    use_entity = scope == "entity" or (scope == "auto" and has_entity and confidence_bundle.get("focus_company"))
    if use_entity and has_entity:
        components = confidence_bundle.get("entity_confidence_components") or []
        base = confidence_bundle.get("entity_confidence_index")
        if components and base is not None:
            return components, float(base), "entity"
    components = confidence_bundle.get("geopolitical_confidence_components") or confidence_bundle.get(
        "components"
    ) or []
    base = confidence_bundle.get("case_geopolitical_confidence_index")
    if base is None:
        base = confidence_bundle.get("geopolitical_confidence_index")
    return components, float(base) if base is not None else None, "case"


def run_tornado_sensitivity(
    components: list[dict[str, Any]],
    *,
    perturb_pct: float = 20.0,
    base_icg: float | None = None,
) -> list[dict[str, Any]]:
    """±perturb_pct one-at-a-time sensitivity on each ICG component."""
    base = base_icg if base_icg is not None else _icg_from_components(components)
    if base is None:
        return []
    out: list[dict[str, Any]] = []
    for c in components:
        name = c.get("name") or c.get("label")
        val = float(c["value"])
        w = float(c.get("weight") or c.get("base_weight") or 0)
        low_val = max(0.0, val * (1 - perturb_pct / 100))
        high_val = min(100.0, val * (1 + perturb_pct / 100))
        modified_low = []
        for comp in components:
            entry = dict(comp)
            if entry.get("name") == c.get("name") or entry.get("label") == c.get("label"):
                entry["value"] = low_val
            modified_low.append(entry)
        icg_low = _icg_from_components(modified_low)
        modified_high = []
        for comp in components:
            entry = dict(comp)
            if entry.get("name") == c.get("name") or entry.get("label") == c.get("label"):
                entry["value"] = high_val
            modified_high.append(entry)
        icg_high = _icg_from_components(modified_high)
        out.append(
            {
                "component": name,
                "label": c.get("label") or name,
                "base_value": val,
                "weight": round(w, 4),
                "icg_at_low": icg_low,
                "icg_at_high": icg_high,
                "delta_low": round((icg_low or base) - base, 2) if icg_low is not None else None,
                "delta_high": round((icg_high or base) - base, 2) if icg_high is not None else None,
                "swing": round(abs((icg_high or base) - (icg_low or base)), 2),
            }
        )
    return sorted(out, key=lambda x: x.get("swing") or 0, reverse=True)


def run_monte_carlo_icg(
    components: list[dict[str, Any]],
    *,
    n_samples: int = 500,
    noise_pct: float = 12.0,
    seed: int = 42,
) -> dict[str, Any]:
    """Monte Carlo distribution of ICG with Gaussian noise on component values."""
    base = _icg_from_components(components)
    if base is None:
        return {"samples": [], "mean": None, "p5": None, "p95": None, "n": 0}
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_samples):
        perturbed = []
        for c in components:
            val = float(c["value"])
            noise = rng.gauss(0, noise_pct / 100 * val)
            perturbed.append(
                {
                    **c,
                    "value": max(0.0, min(100.0, val + noise)),
                }
            )
        icg = _icg_from_components(perturbed)
        if icg is not None:
            samples.append(icg)
    if _HAS_NUMPY and samples:
        arr = np.array(samples)
        hist = _histogram_bins([float(x) for x in arr], n_bins=12)
        return {
            "samples": [round(float(x), 2) for x in arr[:: max(1, len(arr) // 50)]],
            "histogram": hist,
            "mean": round(float(np.mean(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "p5": round(float(np.percentile(arr, 5)), 2),
            "p50": round(float(np.percentile(arr, 50)), 2),
            "p95": round(float(np.percentile(arr, 95)), 2),
            "n": n_samples,
            "base_icg": base,
        }
    samples.sort()
    n = len(samples)
    hist = _histogram_bins(samples, n_bins=12)
    return {
        "samples": samples[:: max(1, n // 50)],
        "histogram": hist,
        "mean": round(sum(samples) / n, 2) if n else None,
        "p5": samples[int(n * 0.05)] if n else None,
        "p50": samples[int(n * 0.5)] if n else None,
        "p95": samples[int(n * 0.95)] if n else None,
        "n": n_samples,
        "base_icg": base,
    }


def run_shap_like_attribution(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Linear attribution of ICG to components (weight × value / sum).
    SHAP-like without model — exact for weighted average.
    """
    base = _icg_from_components(components)
    if base is None:
        return []
    total_w = sum(float(c.get("weight") or c.get("base_weight") or 0) for c in components)
    out = []
    for c in components:
        w = float(c.get("weight") or c.get("base_weight") or 0)
        val = float(c["value"])
        contrib = (val * w) / total_w if total_w else 0
        out.append(
            {
                "component": c.get("name") or c.get("label"),
                "label": c.get("label"),
                "contribution": round(contrib, 2),
                "share_pct": round(100 * contrib / base, 1) if base else 0,
                "value": val,
                "weight": round(w, 4),
            }
        )
    return sorted(out, key=lambda x: abs(x["contribution"]), reverse=True)


def run_sobol_first_order(
    components: list[dict[str, Any]],
    *,
    n_samples: int = 256,
    seed: int = 7,
) -> list[dict[str, Any]]:
    """First-order Sobol-style indices via one-at-a-time variance (no scipy)."""
    base = _icg_from_components(components)
    if base is None or not components:
        return []
    rng = random.Random(seed)
    matrix_samples: list[float] = []
    for _ in range(n_samples):
        perturbed = []
        for c in components:
            val = float(c["value"])
            perturbed.append({**c, "value": max(0.0, min(100.0, val + rng.uniform(-15, 15)))})
        icg = _icg_from_components(perturbed)
        if icg is not None:
            matrix_samples.append(icg)
    if len(matrix_samples) < 10:
        return []
    total_var = sum((x - sum(matrix_samples) / len(matrix_samples)) ** 2 for x in matrix_samples) / len(
        matrix_samples
    )
    if total_var <= 0:
        return []
    indices = []
    for c in components:
        cond_samples: list[float] = []
        for _ in range(n_samples // 2):
            perturbed = []
            for comp in components:
                val = float(comp["value"])
                if comp.get("name") == c.get("name"):
                    perturbed.append({**comp, "value": max(0.0, min(100.0, rng.uniform(0, 100)))})
                else:
                    perturbed.append(comp)
            icg = _icg_from_components(perturbed)
            if icg is not None:
                cond_samples.append(icg)
        if len(cond_samples) < 5:
            continue
        mean = sum(matrix_samples) / len(matrix_samples)
        cond_mean = sum(cond_samples) / len(cond_samples)
        var_i = sum((x - cond_mean) ** 2 for x in cond_samples) / len(cond_samples)
        s1 = min(1.0, var_i / total_var) if total_var else 0
        indices.append(
            {
                "component": c.get("name") or c.get("label"),
                "label": c.get("label"),
                "sobol_first_order": round(s1, 4),
            }
        )
    return sorted(indices, key=lambda x: x["sobol_first_order"], reverse=True)


def _histogram_bins(samples: list[float], *, n_bins: int = 12) -> list[dict[str, Any]]:
    if not samples:
        return []
    lo, hi = min(samples), max(samples)
    if hi <= lo:
        return [{"bin": f"{lo:.1f}", "count": len(samples)}]
    width = (hi - lo) / n_bins
    bins = [0] * n_bins
    for s in samples:
        idx = min(n_bins - 1, int((s - lo) / width) if width else 0)
        bins[idx] += 1
    out = []
    for i, count in enumerate(bins):
        start = lo + i * width
        end = start + width
        out.append({"bin": f"{start:.0f}-{end:.0f}", "count": count, "mid": round((start + end) / 2, 1)})
    return out


def _fetch_commodity_correlation_matrix(*, period: str = "6mo") -> dict[str, Any]:
    """Cross-asset return correlations (optional yfinance — analytics lab only)."""
    try:
        import yfinance as yf
    except ImportError:
        return {"available": False, "reason": "yfinance no instal·lat"}
    symbols = {
        "CL=F": "Oil WTI",
        "NG=F": "NatGas",
        "TTF=F": "LNG TTF",
        "GC=F": "Gold",
        "SI=F": "Silver",
        "^VIX": "VIX",
        "^GSPC": "S&P500",
        "BTC-USD": "BTC",
    }
    try:
        raw = yf.download(list(symbols.keys()), period=period, progress=False)["Close"]
        if raw.empty or len(raw) < 25:
            return {"available": False, "reason": "dades insuficients"}
        rets = raw.pct_change().dropna(how="all")
        labels = [symbols.get(c, c) for c in rets.columns]
        matrix: list[dict[str, Any]] = []
        for i, col_a in enumerate(rets.columns):
            row: dict[str, Any] = {"asset": labels[i]}
            for j, col_b in enumerate(rets.columns):
                aligned = rets[col_a].align(rets[col_b], join="inner")
                xs, ys = aligned[0].dropna(), aligned[1].dropna()
                common = xs.index.intersection(ys.index)
                if len(common) < 15:
                    row[labels[j]] = None
                    continue
                xa, ya = xs.loc[common], ys.loc[common]
                if _HAS_NUMPY:
                    corr = float(np.corrcoef(xa, ya)[0, 1])
                else:
                    xv, yv = list(xa), list(ya)
                    mx, my = sum(xv) / len(xv), sum(yv) / len(yv)
                    num = sum((x - mx) * (y - my) for x, y in zip(xv, yv))
                    den = (sum((x - mx) ** 2 for x in xv) * sum((y - my) ** 2 for y in yv)) ** 0.5
                    corr = num / den if den else 0.0
                row[labels[j]] = round(corr, 3)
            matrix.append(row)
        return {
            "available": True,
            "period": period,
            "matrix": matrix,
            "labels": labels,
            "interpretation": (
                "Correlacions de rendiments diaris. Valors >0.6 indiquen co-moviment fort "
                "(ex. energia en risc geo). Negatius: possible safe-haven."
            ),
        }
    except Exception as exc:
        logger.warning("commodity matrix failed: %s", exc)
        return {"available": False, "reason": str(exc)}


def _fetch_market_correlations(ticker: str, *, period: str = "6mo") -> dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError:
        return {
            "available": False,
            "reason": "yfinance no instal·lat — pip install yfinance",
            "ticker": ticker,
        }
    try:
        sym = ticker.strip().upper()
        stock = yf.Ticker(sym)
        hist = stock.history(period=period)
        if hist.empty or len(hist) < 20:
            return {"available": False, "reason": "dades insuficients", "ticker": sym}
        ret = hist["Close"].pct_change().dropna()
        benchmarks = {"^GSPC": "S&P500", "^N225": "Nikkei225", "CL=F": "WTI Oil"}
        correlations: list[dict[str, Any]] = []
        for bench, label in benchmarks.items():
            try:
                bhist = yf.Ticker(bench).history(period=period)
                if bhist.empty:
                    continue
                bret = bhist["Close"].pct_change().dropna()
                aligned = ret.align(bret, join="inner")
                if len(aligned[0]) < 15:
                    continue
                if _HAS_NUMPY:
                    corr = float(np.corrcoef(aligned[0], aligned[1])[0, 1])
                else:
                    xs, ys = list(aligned[0]), list(aligned[1])
                    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
                    corr = num / den if den else 0.0
                correlations.append(
                    {"benchmark": label, "symbol": bench, "correlation": round(corr, 3), "n": len(aligned[0])}
                )
            except Exception as exc:
                logger.debug("benchmark %s skip: %s", bench, exc)
        return {
            "available": True,
            "ticker": sym,
            "period": period,
            "correlations": correlations,
        }
    except Exception as exc:
        logger.warning("market correlations failed: %s", exc)
        return {"available": False, "reason": str(exc), "ticker": ticker}


class AnalyticsLabService:
    """Run analytics experiments for a case ICG / crossover context."""

    async def run(
        self,
        case_id: int,
        *,
        confidence_bundle: dict[str, Any],
        ticker: str | None = None,
        experiments: list[str] | None = None,
        monte_carlo_samples: int = 500,
        confidence_scope: str = "auto",
    ) -> dict[str, Any]:
        experiments = experiments or ["tornado", "monte_carlo", "shap_attribution", "sobol"]
        components, base_icg, resolved_scope = resolve_lab_confidence(
            confidence_bundle, scope=confidence_scope
        )

        cache_payload = {
            "case_id": case_id,
            "experiments": experiments,
            "base_icg": base_icg,
            "ticker": ticker,
            "n_components": len(components),
            "confidence_scope": resolved_scope,
            "focus_company": confidence_bundle.get("focus_company"),
        }
        key = _cache_key(case_id, cache_payload)
        cached = _get_cached(key)
        if cached:
            return {**cached, "cached": True}

        result: dict[str, Any] = {
            "case_id": case_id,
            "base_icg": base_icg,
            "confidence_scope": resolved_scope,
            "focus_company": confidence_bundle.get("focus_company"),
            "case_icg_baseline": confidence_bundle.get("case_geopolitical_confidence_index")
            or confidence_bundle.get("geopolitical_confidence_index"),
            "entity_icg_delta": confidence_bundle.get("entity_icg_delta"),
            "component_count": len(components),
            "experiments_run": [],
            "cached": False,
        }

        if "tornado" in experiments:
            result["tornado"] = run_tornado_sensitivity(components, base_icg=base_icg)
            result["experiments_run"].append("tornado")

        if "monte_carlo" in experiments:
            result["monte_carlo"] = run_monte_carlo_icg(components, n_samples=monte_carlo_samples)
            result["experiments_run"].append("monte_carlo")

        if "shap_attribution" in experiments:
            result["shap_attribution"] = run_shap_like_attribution(components)
            result["experiments_run"].append("shap_attribution")

        if "sobol" in experiments:
            result["sobol_first_order"] = run_sobol_first_order(components)
            result["experiments_run"].append("sobol")

        if "market_correlations" in experiments and ticker:
            result["market_correlations"] = _fetch_market_correlations(ticker)
            result["experiments_run"].append("market_correlations")

        if "commodity_matrix" in experiments:
            result["commodity_matrix"] = _fetch_commodity_correlation_matrix()
            result["experiments_run"].append("commodity_matrix")

        result["driver_interactions"] = confidence_bundle.get("driver_interactions") or []
        result["sanction_context"] = {
            "sis": confidence_bundle.get("sanction_impact_score"),
            "entity_impacts": (confidence_bundle.get("sanction_entity_impacts") or [])[:6],
        }
        result["gma"] = confidence_bundle.get("eina_gma")

        _set_cache(key, result)
        return result

    def get_latest(
        self,
        case_id: int,
        *,
        focus_company: str | None = None,
        confidence_scope: str | None = None,
    ) -> dict[str, Any] | None:
        prefix = f"lab:{case_id}:"
        best: dict[str, Any] | None = None
        best_ts = 0.0
        for key, entry in _lab_cache.items():
            if not key.startswith(prefix) or time.time() - entry.get("_ts", 0) > _CACHE_TTL:
                continue
            result = entry.get("result") or {}
            if focus_company and result.get("focus_company") != focus_company:
                continue
            if confidence_scope and result.get("confidence_scope") != confidence_scope:
                continue
            if entry.get("_ts", 0) > best_ts:
                best_ts = entry["_ts"]
                best = result
        return best
