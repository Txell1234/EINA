"""
Load case-linked context for prospective report exports:
OSINT sources, extracted statements, retrospective, qualitative/quantitative analyses.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_analysis import AIAnalysis
from models.case import Case, CasePrompt
from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult
from models.prospective import MorphIncompatibility, SMICResult
from models.qualitative import KPI, Premise, QualitativeAnalysis, QuantitativeAnalysis, ReasoningFramework
from services.extract_service import ExtractService
from services.prospective_geopolitical_service import ProspectiveGeopoliticalService
from services.prospective_service import ProspectiveService
from services.osint_data_utils import flatten_osint_items, osint_has_error
    """Attach OSINT, extraction, retrospective and analysis context to export bundle."""
    project = bundle["project"]
    case_id: Optional[int] = project.case_id

    bundle["case"] = None
    bundle["case_prompt"] = None
    bundle["osint_sources"] = []
    bundle["osint_articles"] = []
    bundle["osint_query_errors"] = []
    bundle["statements"] = []
    bundle["retrospective"] = None
    bundle["qualitative_analyses"] = []
    bundle["quantitative_analyses"] = []
    bundle["ai_analyses"] = []
    bundle["incompatibilities"] = []
    bundle["smic"] = None
    bundle["morph_space"] = None
    bundle["suggested_variables"] = []
    bundle["suggested_actors"] = []
    bundle["micmac_suggestions"] = None

    svc = ProspectiveService(db)
    bundle["incompatibilities"] = await svc.get_incompatibilities(project.id)
    bundle["morph_space"] = await svc.get_morph_space(project.id)
    bundle["smic"] = await svc.get_smic(project.id)

    smic_r = await db.execute(select(SMICResult).where(SMICResult.project_id == project.id))
    bundle["smic_row"] = smic_r.scalar_one_or_none()

    incompat_r = await db.execute(
        select(MorphIncompatibility).where(MorphIncompatibility.project_id == project.id)
    )
    bundle["incompat_rows"] = list(incompat_r.scalars().all())

    if not case_id:
        return bundle

    case_r = await db.execute(select(Case).where(Case.id == case_id))
    bundle["case"] = case_r.scalar_one_or_none()

    prompt_r = await db.execute(
        select(CasePrompt)
        .where(CasePrompt.case_id == case_id)
        .order_by(CasePrompt.created_at.desc())
        .limit(1)
    )
    bundle["case_prompt"] = prompt_r.scalar_one_or_none()

    queries_r = await db.execute(
        select(OSINTQuery).where(OSINTQuery.case_id == case_id).order_by(OSINTQuery.created_at)
    )
    queries = list(queries_r.scalars().all())
    osint_sources: list[dict[str, Any]] = []
    osint_articles: list[dict[str, Any]] = []
    osint_query_errors: list[dict[str, Any]] = []

    for q in queries:
        results_r = await db.execute(select(OSINTResult).where(OSINTResult.query_id == q.id))
        for r in results_r.scalars().all():
            data = r.data if isinstance(r.data, dict) else {}
            query_meta = {
                "query_id": q.id,
                "query_type": q.query_type,
                "query_params": q.query_params or {},
                "query_status": q.status.value if hasattr(q.status, "value") else str(q.status),
                "result_id": r.id,
                "result_status": r.status,
                "error": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            osint_sources.append(query_meta)

            if r.status == "error" or osint_has_error(data):
                osint_query_errors.append(
                    {
                        **query_meta,
                        "error": r.error_message or data.get("error") or data.get("message") or "Error desconegut",
                    }
                )
                continue

            flat = flatten_osint_items(data)
            if flat:
                for article in flat:
                    osint_articles.append(
                        {
                            **query_meta,
                            "title": article.get("title") or "",
                            "url": article.get("url") or "",
                            "date": article.get("date") or "",
                            "source": article.get("source") or q.query_type,
                            "summary": article.get("summary") or "",
                        }
                    )
            else:
                osint_query_errors.append(
                    {
                        **query_meta,
                        "error": "Consulta completada però sense articles recuperables",
                    }
                )

    bundle["osint_sources"] = osint_sources
    bundle["osint_articles"] = osint_articles
    bundle["osint_query_errors"] = osint_query_errors

    stmts_r = await db.execute(
        select(ExtractedStatement)
        .where(ExtractedStatement.case_id == case_id)
        .order_by(ExtractedStatement.extracted_at.desc())
    )
    bundle["statements"] = list(stmts_r.scalars().all())

    retro = RetrospectiveService(db)
    bundle["retrospective"] = await retro.build_retrospective(case_id, project.id)

    extract_svc = ExtractService(db)
    bundle["suggested_variables"] = await extract_svc.get_suggested_variables(case_id)
    bundle["suggested_actors"] = await extract_svc.get_suggested_actors(case_id)

    qual_r = await db.execute(
        select(QualitativeAnalysis, Premise, ReasoningFramework)
        .join(Premise, QualitativeAnalysis.premise_id == Premise.id)
        .outerjoin(ReasoningFramework, QualitativeAnalysis.framework_id == ReasoningFramework.id)
        .where(QualitativeAnalysis.case_id == case_id)
        .order_by(QualitativeAnalysis.created_at.desc())
    )
    bundle["qualitative_analyses"] = [
        {
            "conclusions": qa.conclusions,
            "confidence_score": qa.confidence_score,
            "evidence": qa.evidence or [],
            "premise": prem.premise_text,
            "framework_name": fw.name if fw else None,
            "framework_type": fw.framework_type.value if fw and hasattr(fw.framework_type, "value") else None,
            "created_at": qa.created_at.isoformat() if qa.created_at else None,
        }
        for qa, prem, fw in qual_r.all()
    ]

    quant_r = await db.execute(
        select(QuantitativeAnalysis, KPI)
        .join(KPI, QuantitativeAnalysis.kpi_id == KPI.id)
        .where(QuantitativeAnalysis.case_id == case_id)
        .order_by(QuantitativeAnalysis.calculated_at.desc())
    )
    bundle["quantitative_analyses"] = [
        {
            "kpi_name": kpi.name,
            "kpi_type": kpi.kpi_type.value if hasattr(kpi.kpi_type, "value") else str(kpi.kpi_type),
            "metric_type": kpi.metric_type,
            "description": kpi.description,
            "value": qa.value,
            "unit": kpi.measurement_unit,
            "calculated_at": qa.calculated_at.isoformat() if qa.calculated_at else None,
        }
        for qa, kpi in quant_r.all()
    ]

    ai_r = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.case_id == case_id)
        .order_by(AIAnalysis.created_at.desc())
    )
    bundle["ai_analyses"] = [
        {
            "analysis_type": a.analysis_type,
            "confidence_score": a.confidence_score,
            "analysis_data": a.analysis_data,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in ai_r.scalars().all()
    ]

    if bundle["variables"]:
        vars_payload = [
            {
                "code": v.code,
                "name": v.name,
                "desc": v.description or "",
                "type": v.var_type or "I",
            }
            for v in bundle["variables"]
        ]
        try:
            bundle["micmac_suggestions"] = await ProspectiveGeopoliticalService(db).micmac_suggestions(
                case_id, vars_payload
            )
        except Exception:
            bundle["micmac_suggestions"] = None

    return bundle
