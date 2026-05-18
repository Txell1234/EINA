"""
Report Service - Generate comprehensive reports
"""
import asyncio
import html as html_module
import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.reports import Report, ReportStatus
from models.case import Case
from models.osint import OSINTQuery
from models.ai_analysis import AIAnalysis
from models.qualitative import QualitativeAnalysis, Premise
from models.predictions import Prediction
from models.investments import InvestmentRecommendation

from services.export_backends import (
    ExportBackendError,
    render_pdf_from_html,
    write_case_report_excel,
)

logger = logging.getLogger(__name__)


def _case_report_html(data: dict) -> str:
    case = data.get("case") or {}
    sections = ""
    for key, title in [
        ("osint_data", "Dades OSINT"),
        ("ai_analyses", "Anàlisis IA"),
        ("qualitative_analyses", "Anàlisi qualitativa"),
        ("predictions", "Prediccions"),
        ("investment_recommendations", "Recomanacions"),
        ("premises", "Premisses"),
    ]:
        block = data.get(key) or []
        sections += (
            f"<h2>{title}</h2>"
            f"<pre>{html_module.escape(json.dumps(block, ensure_ascii=False, indent=2))}</pre>"
        )
    bias = data.get("bias_guidance") or {}
    return f"""<!DOCTYPE html><html lang="ca"><head><meta charset="UTF-8">
<style>
body{{font-family:Arial,sans-serif;font-size:11pt;color:#1a1a2e;margin:2cm}}
h1{{color:#1e3a5f}} h2{{color:#1e3a5f;border-bottom:1px solid #ccc;padding-bottom:4px}}
pre{{background:#f8f9fa;padding:12px;font-size:9pt;white-space:pre-wrap}}
</style></head><body>
<h1>Informe OSINT — {html_module.escape(str(case.get('name', '')))}</h1>
<p>{html_module.escape(str(case.get('description', '')))}</p>
{sections}
<h2>Guia de biaix</h2>
<pre>{html_module.escape(json.dumps(bias, ensure_ascii=False, indent=2))}</pre>
</body></html>"""


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_report(self, report_id: int):
        """Generate comprehensive report"""
        try:
            # Get report
            result = await self.db.execute(
                select(Report).where(Report.id == report_id)
            )
            report = result.scalar_one_or_none()
            
            if not report:
                return
            
            # Get case
            case_result = await self.db.execute(
                select(Case).where(Case.id == report.case_id)
            )
            case = case_result.scalar_one_or_none()
            
            # Collect all data
            report_data = {
                "case": {
                    "id": case.id if case else None,
                    "name": case.name if case else "",
                    "description": case.description if case else "",
                },
                "osint_data": await self._get_osint_data(report.case_id),
                "ai_analyses": await self._get_ai_analyses(report.case_id),
                "qualitative_analyses": await self._get_qualitative_analyses(report.case_id),
                "predictions": await self._get_predictions(report.case_id),
                "investment_recommendations": await self._get_investment_recommendations(report.case_id),
                "premises": await self._get_case_premises(report.case_id),
            }
            
            report_data["bias_guidance"] = self._build_bias_guidance(report_data["premises"])
            
            # Generate file based on format
            export_meta = None
            if report.format == "pdf":
                export_meta = await self._generate_pdf(report_id, report_data)
            elif report.format == "excel":
                export_meta = await self._generate_excel(report_id, report_data)
            else:
                file_path = None

            if export_meta is not None:
                file_path = export_meta.get("file_path")
                report_data["export"] = export_meta
            else:
                file_path = None

            # Update report
            report.content = report_data
            report.file_path = file_path
            report.status = ReportStatus.COMPLETED
            await self.db.commit()
            
        except Exception as e:
            # Update status to failed
            result = await self.db.execute(
                select(Report).where(Report.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.FAILED
                await self.db.commit()
            raise e
    
    async def _get_osint_data(self, case_id: int):
        """Get OSINT data for case"""
        result = await self.db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        )
        queries = result.scalars().all()
        
        return [{"id": q.id, "type": q.query_type, "status": q.status} for q in queries]
    
    async def _get_ai_analyses(self, case_id: int):
        """Get AI analyses for case"""
        result = await self.db.execute(
            select(AIAnalysis).where(AIAnalysis.case_id == case_id)
        )
        analyses = result.scalars().all()
        
        return [{"id": a.id, "type": a.analysis_type, "confidence": a.confidence_score} for a in analyses]
    
    async def _get_qualitative_analyses(self, case_id: int):
        """Get qualitative analyses for case"""
        result = await self.db.execute(
            select(QualitativeAnalysis).where(QualitativeAnalysis.case_id == case_id)
        )
        analyses = result.scalars().all()
        
        return [{"id": a.id, "conclusions": a.conclusions, "confidence": a.confidence_score} for a in analyses]
    
    async def _get_predictions(self, case_id: int):
        """Get predictions for case"""
        result = await self.db.execute(
            select(Prediction).where(Prediction.case_id == case_id)
        )
        predictions = result.scalars().all()
        
        return [{"id": p.id, "type": p.prediction_type, "confidence": p.confidence_percentage} for p in predictions]
    
    async def _get_investment_recommendations(self, case_id: int):
        """Get investment recommendations for case"""
        result = await self.db.execute(
            select(InvestmentRecommendation).where(InvestmentRecommendation.case_id == case_id)
        )
        recommendations = result.scalars().all()
        
        return [{"id": r.id, "type": r.recommendation_type, "confidence": r.confidence_percentage} for r in recommendations]

    async def _get_case_premises(self, case_id: int):
        """Get premises configured for a case"""
        result = await self.db.execute(
            select(Premise).where(Premise.case_id == case_id)
        )
        premises = result.scalars().all()
        
        return [
            {
                "id": premise.id,
                "premise_text": premise.premise_text,
                "framework_id": premise.framework_id,
                "created_at": premise.created_at.isoformat() if premise.created_at else None
            }
            for premise in premises
        ]

    def _build_bias_guidance(self, premises: list) -> dict:
        """Build report guidance to bias summaries according to premises."""
        if not premises:
            return {"enabled": False, "premise_count": 0, "notes": []}
        
        notes = [premise.get("premise_text") for premise in premises if premise.get("premise_text")]
        return {
            "enabled": True,
            "premise_count": len(premises),
            "notes": notes
        }
    
    async def _generate_pdf(self, report_id: int, data: dict) -> dict:
        """Generate PDF report via WeasyPrint, JSON fallback if unavailable."""
        Path("reports").mkdir(exist_ok=True)
        pdf_path = Path("reports") / f"report_{report_id}.pdf"
        try:
            html = _case_report_html(data)
            await asyncio.to_thread(
                render_pdf_from_html, html, pdf_path
            )
            return {
                "status": "completed",
                "format": "pdf",
                "file_path": str(pdf_path),
            }
        except ExportBackendError as exc:
            logger.warning("WeasyPrint no disponible per report %s: %s", report_id, exc)
        except Exception as exc:
            logger.warning("PDF generation failed for report %s: %s", report_id, exc)

        json_path = Path("reports") / f"report_{report_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {
            "status": "fallback_json",
            "message": "PDF no disponible (instal·la weasyprint + libpango). S'ha generat JSON.",
            "format": "json",
            "file_path": str(json_path),
        }

    async def _generate_excel(self, report_id: int, data: dict) -> dict:
        """Generate Excel (.xlsx) report via openpyxl, JSON fallback if unavailable."""
        Path("reports").mkdir(exist_ok=True)
        xlsx_path = Path("reports") / f"report_{report_id}.xlsx"
        try:
            await asyncio.to_thread(write_case_report_excel, data, xlsx_path)
            return {
                "status": "completed",
                "format": "excel",
                "file_path": str(xlsx_path),
            }
        except ExportBackendError as exc:
            logger.warning("openpyxl no disponible per report %s: %s", report_id, exc)
        except Exception as exc:
            logger.warning("Excel generation failed for report %s: %s", report_id, exc)

        json_path = Path("reports") / f"report_{report_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {
            "status": "fallback_json",
            "message": "Exportació Excel no disponible. S'ha generat JSON equivalent.",
            "format": "json",
            "file_path": str(json_path),
        }








