"""Risk analysis: rule-based (no IA) and AI-based."""
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from models import Case, OSINTData, RiskConcept, RiskAnalysis


def _extract_text_from_osint(osint_list: List[OSINTData]) -> str:
    """Extract concatenated text from all OSINT data for analysis."""
    texts = []
    for item in osint_list:
        if not item.raw_data:
            continue
        rd = item.raw_data
        if isinstance(rd, dict):
            for k, v in rd.items():
                if isinstance(v, str):
                    texts.append(v)
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, dict):
                            texts.append(" ".join(str(y) for y in x.values() if y))
                        elif isinstance(x, str):
                            texts.append(x)
                elif isinstance(v, (int, float)):
                    texts.append(str(v))
        elif isinstance(rd, str):
            texts.append(rd)
    return " ".join(texts).lower()


def _get_keywords_for_concept(concept: RiskConcept, rule_config: Optional[dict]) -> List[str]:
    """Get keywords to search for a concept (from concept or rule_config)."""
    if rule_config and isinstance(rule_config.get(concept.name), list):
        return [str(k).lower() for k in rule_config[concept.name]]
    if concept.keywords:
        return [str(k).lower() for k in concept.keywords]
    return [concept.name.lower()]


def analyze_risk_rule_based(db: Session, case_id: int, rule_config: Optional[dict] = None) -> Dict[str, Any]:
    """Rule-based risk analysis: search keywords, count matches, apply weights."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {"concepts": [], "dimensions": {}, "overall_score": 0}


    osint_list = db.query(OSINTData).filter(OSINTData.case_id == case_id).all()
    concepts = db.query(RiskConcept).filter(RiskConcept.case_id == case_id).all()

    if not concepts:
        return {"concepts": [], "dimensions": {}, "overall_score": 0}

    full_text = _extract_text_from_osint(osint_list)
    results = []
    dim_scores = {}

    for concept in concepts:
        keywords = _get_keywords_for_concept(concept, rule_config)
        count = 0
        for kw in keywords:
            count += len(re.findall(re.escape(kw), full_text))
        score = min(1.0, (count * concept.weight) / 10.0) if count else 0
        results.append({
            "concept": concept.name,
            "score": round(score, 2),
            "evidence_count": count,
            "dimension": concept.dimension,
        })
        if concept.dimension:
            dim_scores[concept.dimension] = dim_scores.get(concept.dimension, 0) + score

    for k in dim_scores:
        dim_scores[k] = round(dim_scores[k] / max(1, sum(1 for r in results if r.get("dimension") == k)), 2)

    overall = round(sum(r["score"] for r in results) / max(1, len(results)), 2)

    analysis = RiskAnalysis(
        case_id=case_id,
        mode="rule_based",
        parameters_snapshot=rule_config,
        results={"concepts": results, "dimensions": dim_scores, "overall_score": overall},
    )
    db.add(analysis)
    db.commit()

    return {"concepts": results, "dimensions": dim_scores, "overall_score": overall}


def analyze_risk_ai(db: Session, case_id: int, params: Optional[dict] = None) -> Dict[str, Any]:
    """AI-based risk analysis (simulated with rule-based + reasoning)."""
    rule_result = analyze_risk_rule_based(db, case_id, params.get("rule_config") if params else None)
    if not rule_result.get("concepts"):
        analysis = RiskAnalysis(case_id=case_id, mode="ai", parameters_snapshot=params, results=rule_result)
        db.add(analysis)
        db.commit()
        return rule_result
    concepts = rule_result.get("concepts", [])
    for c in concepts:
        c["reasoning"] = f"Detectat a partir de {c.get('evidence_count', 0)} coincidències en les dades OSINT."
    analysis = RiskAnalysis(
        case_id=case_id,
        mode="ai",
        parameters_snapshot=params,
        results={
            "concepts": concepts,
            "dimensions": rule_result.get("dimensions", {}),
            "overall_score": rule_result.get("overall_score", 0),
            "reasoning": "Anàlisi de risc per conceptes parametritzada (mode IA simulat).",
        },
    )
    db.add(analysis)
    db.commit()
    return rule_result
