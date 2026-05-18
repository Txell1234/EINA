"""FastAPI main application."""
import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Case, OSINTData, AIAnalysis, RiskConcept, RiskAnalysis, KPI, QualitativeAnalysis, UnifiedAnalysis, InvestmentRecommendation
from schemas import CaseCreate, CaseResponse, OSINTCollectRequest, RiskConceptCreate, RiskConceptResponse, RiskAnalyzeRequest
from osint_tools import collect_osint, _normalize_original_url
from risk_analysis import analyze_risk_rule_based, analyze_risk_ai

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OSINT Platform API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "OSINT Platform API", "docs": "/docs"}


# --- Cases ---
@app.get("/cases", response_model=list)
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).all()
    return [{"id": c.id, "name": c.name, "description": c.description, "country": c.country, "case_type": c.case_type, "thematics": c.thematics or [], "created_at": c.created_at} for c in cases]


@app.post("/cases", response_model=dict)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    case = Case(
        name=data.name,
        description=data.description,
        country=data.country,
        case_type=data.case_type,
        thematics=data.thematics,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "name": case.name, "description": case.description, "country": case.country, "case_type": case.case_type, "thematics": case.thematics or [], "created_at": case.created_at}


@app.put("/cases/{case_id}")
def update_case(case_id: int, data: CaseCreate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    case.name = data.name
    case.description = data.description
    case.country = data.country
    case.case_type = data.case_type
    case.thematics = data.thematics
    db.commit()
    db.refresh(case)
    return {"id": case.id, "name": case.name, "description": case.description, "country": case.country, "case_type": case.case_type, "thematics": case.thematics or [], "created_at": case.created_at}


@app.delete("/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    db.delete(case)
    db.commit()
    return {"status": "deleted"}


@app.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return {"id": case.id, "name": case.name, "description": case.description, "country": case.country, "case_type": case.case_type, "thematics": case.thematics or [], "created_at": case.created_at}


@app.get("/cases/{case_id}/full")
def get_full_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    osint = [{"id": o.id, "case_id": o.case_id, "source": o.source, "data_type": o.data_type, "query": o.query, "thematic": o.thematic, "raw_data": o.raw_data, "metadata_info": o.metadata_info, "collected_at": o.collected_at} for o in case.osint_data]
    ai = [{"id": a.id, "analysis_type": a.analysis_type, "confidence_score": a.confidence_score, "results": a.results, "created_at": a.created_at} for a in case.ai_analyses]
    risk = [{"id": r.id, "mode": r.mode, "results": r.results, "created_at": r.created_at} for r in case.risk_analyses]
    return {
        "id": case.id,
        "name": case.name,
        "description": case.description,
        "country": case.country,
        "case_type": case.case_type,
        "thematics": case.thematics or [],
        "osint_data": osint,
        "ai_analysis": ai,
        "risk_analyses": risk,
        "investment_recommendations": [{**({"id": ir.id, "created_at": ir.created_at} if ir.results else {}), **(ir.results or {})} for ir in case.investment_recommendations_rel],
        "unified_analysis": case.unified_analyses[-1].results if case.unified_analyses else None,
        "qualitative_analysis": [{"id": q.id, "premise": q.premise, "reasoning_framework": q.reasoning_framework, "analysis_result": q.analysis_result, "conclusion": q.conclusion, "created_at": q.created_at} for q in case.qualitative_analyses],
    }


@app.get("/cases/filtered")
def filtered_cases(
    thematic: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if thematic:
        cases_by_osint = db.query(Case).join(OSINTData).filter(OSINTData.thematic == thematic).distinct().all()
        all_cases = db.query(Case).all()
        cases_by_thematics = [c for c in all_cases if c.thematics and thematic in c.thematics]
        seen = set()
        cases = []
        for c in cases_by_thematics + cases_by_osint:
            if c.id not in seen:
                seen.add(c.id)
                cases.append(c)
    else:
        cases = db.query(Case).all()
    return [{"id": c.id, "name": c.name, "description": c.description, "country": c.country, "case_type": c.case_type, "thematics": c.thematics or [], "created_at": c.created_at} for c in cases]


# --- OSINT ---
@app.get("/osint/tools")
def osint_tools():
    return {"tools": ["username", "sherlock", "domain", "recon-ng", "news", "google_news", "reddit", "github", "whois", "dns", "wayback"]}


@app.post("/osint/collect")
def collect_osint_endpoint(data: OSINTCollectRequest, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == data.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    raw, source_name = collect_osint(data.source_type, data.query)
    original_url = _normalize_original_url(source_name, raw)
    metadata = {"original_url": original_url} if original_url else {}
    osint = OSINTData(
        case_id=data.case_id,
        source=source_name,
        data_type=data.source_type,
        query=data.query,
        thematic=data.thematic,
        raw_data=raw,
        metadata_info=metadata,
    )
    db.add(osint)
    db.commit()
    db.refresh(osint)
    return {"id": osint.id, "source": osint.source, "thematic": osint.thematic, "metadata_info": osint.metadata_info}


# --- AI ---
from ai_analysis import analyze_concepts as ai_analyze_concepts

@app.get("/ai/status")
def ai_status():
    return {"openai_configured": bool(os.getenv("OPENAI_API_KEY"))}

@app.post("/ai/analyze/{case_id}")
def analyze_ai(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    concepts, predictions, confidence = ai_analyze_concepts(case.osint_data)
    analysis = AIAnalysis(case_id=case_id, analysis_type="concepts", confidence_score=confidence, results={"concepts": concepts, "predictions": predictions})
    db.add(analysis)
    db.commit()
    return {"status": "ok", "concepts": concepts, "predictions": predictions}


# --- Risk ---
@app.get("/cases/{case_id}/risk-concepts", response_model=list)
def get_risk_concepts(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return [{"id": r.id, "case_id": r.case_id, "name": r.name, "weight": r.weight, "dimension": r.dimension, "keywords": r.keywords or []} for r in case.risk_concepts]


@app.post("/cases/{case_id}/risk-concepts", response_model=dict)
def create_risk_concept(case_id: int, data: RiskConceptCreate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    rc = RiskConcept(case_id=case_id, name=data.name, weight=data.weight or 1.0, dimension=data.dimension, keywords=data.keywords)
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return {"id": rc.id, "case_id": rc.case_id, "name": rc.name, "weight": rc.weight, "dimension": rc.dimension, "keywords": rc.keywords or []}


@app.delete("/cases/{case_id}/risk-concepts/{concept_id}")
def delete_risk_concept(case_id: int, concept_id: int, db: Session = Depends(get_db)):
    rc = db.query(RiskConcept).filter(RiskConcept.id == concept_id, RiskConcept.case_id == case_id).first()
    if not rc:
        raise HTTPException(404, "Risk concept not found")
    db.delete(rc)
    db.commit()
    return {"status": "deleted"}


@app.post("/risk/analyze/{case_id}")
def analyze_risk(case_id: int, body: Optional[RiskAnalyzeRequest] = Body(None), db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    result = analyze_risk_rule_based(db, case_id, body.rule_config if body else None)
    return result


@app.post("/risk/analyze-ai/{case_id}")
def analyze_risk_ai_endpoint(case_id: int, body: Optional[RiskAnalyzeRequest] = Body(None), db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    params = body.model_dump() if body else None
    result = analyze_risk_ai(db, case_id, params)
    return result


# --- KPIs i Qualitative ---
@app.get("/kpis/{case_id}")
def get_kpis(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return [{"id": k.id, "case_id": k.case_id, "name": k.name, "description": k.description, "variable_type": k.variable_type, "value": k.value, "qualitative_value": k.qualitative_value, "reasoning": k.reasoning} for k in case.kpis]


@app.post("/kpis")
def create_kpi(data: dict, db: Session = Depends(get_db)):
    case_id = data.get("case_id")
    if not case_id:
        raise HTTPException(400, "case_id required")
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    kpi = KPI(
        case_id=case_id,
        name=data.get("name", ""),
        description=data.get("description"),
        variable_type=data.get("variable_type", "quantitative"),
        value=data.get("value"),
        qualitative_value=data.get("qualitative_value"),
        reasoning=data.get("reasoning"),
    )
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    return {"id": kpi.id, "case_id": kpi.case_id, "name": kpi.name, "description": kpi.description, "variable_type": kpi.variable_type, "value": kpi.value, "qualitative_value": kpi.qualitative_value, "reasoning": kpi.reasoning}


@app.post("/qualitative/analyze")
def qualitative_analyze(data: dict, db: Session = Depends(get_db)):
    case_id = data.get("case_id")
    if not case_id:
        raise HTTPException(400, "case_id required")
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    kpi_ids = data.get("kpi_ids", [])
    kpis = db.query(KPI).filter(KPI.case_id == case_id, KPI.id.in_(kpi_ids)).all() if kpi_ids else []
    analysis_result = {"kpis_used": [{"id": k.id, "name": k.name, "value": k.value or k.qualitative_value} for k in kpis], "framework": data.get("reasoning_framework", "deductive")}
    conclusion = f"Anàlisi qualitativa basada en {len(kpis)} KPIs amb framework {data.get('reasoning_framework', 'deductive')}."
    qa = QualitativeAnalysis(
        case_id=case_id,
        premise=data.get("premise"),
        reasoning_framework=data.get("reasoning_framework"),
        kpi_ids=kpi_ids,
        analysis_result=analysis_result,
        conclusion=conclusion,
    )
    db.add(qa)
    db.commit()
    db.refresh(qa)
    return {"status": "ok", "id": qa.id, "analysis_result": analysis_result, "conclusion": conclusion}


@app.post("/investment/analyze/{case_id}")
def investment_analyze(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    n_osint = len(case.osint_data)
    risk_score = min(0.9, 0.3 + n_osint * 0.05)
    opp_score = max(0.2, 0.7 - n_osint * 0.03)
    rec_type = "hold" if risk_score < 0.5 else ("avoid" if risk_score > 0.7 else "hold")
    results = {
        "recommendation": rec_type,
        "risk_level": "high" if risk_score > 0.6 else ("medium" if risk_score > 0.4 else "low"),
        "visualization_data": {
            "risk_breakdown": {"geopolitic": risk_score * 0.4, "operational": risk_score * 0.3, "market": risk_score * 0.3},
            "opportunity_breakdown": {"growth": opp_score * 0.5, "stability": opp_score * 0.5},
            "scores": {"risk": risk_score, "opportunity": opp_score},
        },
    }
    ir = InvestmentRecommendation(case_id=case_id, results=results)
    db.add(ir)
    db.commit()
    return {"status": "ok", "recommendation": rec_type}


@app.post("/unified/analyze/{case_id}")
def unified_analyze(case_id: int, db: Session = Depends(get_db), country: Optional[str] = Query(None), actor: Optional[str] = Query(None)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    n_osint = len(case.osint_data)
    rec = "PROCEED" if n_osint < 5 else ("PROCEED_WITH_CAUTION" if n_osint < 10 else "HOLD")
    results = {
        "global_decision": {
            "recommendation": rec,
            "confidence": 0.75,
            "priority": "MEDIUM",
            "reasoning": f"Anàlisi basada en {n_osint} fonts OSINT. País: {country or 'N/A'}, Actor: {actor or 'N/A'}.",
        },
        "unified_visualization": {
            "risk_radar": {"geopolitic": 50, "social": 40, "economic": 60, "operational": 45},
        },
        "sources_analyzed": {"news": n_osint, "social": 0},
        "geopolitical_analysis": {"location": {"primary_country": country or case.country or "N/A"}, "geopolitical_index": 0.5, "tension_analysis": {"tension_level": "moderate"}},
        "social_analysis": {"social_sentiment": {"overall_sentiment": "neutral"}, "social_index": 0.5, "social_movements": {"total_movements": 0}},
    }
    ua = UnifiedAnalysis(case_id=case_id, country=country, actor=actor, results=results)
    db.add(ua)
    db.commit()
    return {"status": "ok", "global_decision": results["global_decision"]}


@app.get("/sync/status/{case_id}")
def sync_status(case_id: int):
    return {"status": "idle"}


@app.post("/sync/{case_id}")
def force_sync(case_id: int):
    return {"status": "ok"}
