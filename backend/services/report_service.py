"""
Report Service - Generate comprehensive reports
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.reports import Report, ReportStatus
from models.case import Case
from models.osint import OSINTQuery, OSINTResult
from models.ai_analysis import AIAnalysis
from models.qualitative import QualitativeAnalysis
from models.predictions import Prediction
from models.investments import InvestmentRecommendation
from models.qualitative import Premise
import json
from pathlib import Path

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
        """Generate PDF report (JSON fallback until Phase 4)."""
        file_path = f"reports/report_{report_id}.json"
        Path("reports").mkdir(exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {
            "status": "not_implemented",
            "message": "Exportació a PDF pendent d'implementació. Disponible a la Fase 4.",
            "format": "json",
            "file_path": file_path,
        }

    async def _generate_excel(self, report_id: int, data: dict) -> dict:
        """Generate Excel report (JSON fallback until Phase 4)."""
        file_path = f"reports/report_{report_id}.json"
        Path("reports").mkdir(exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {
            "status": "not_implemented",
            "message": "Exportació a Excel pendent d'implementació. Disponible a la Fase 4.",
            "format": "json",
            "file_path": file_path,
        }








