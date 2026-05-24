"""
Case service - Business logic for cases
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.case import Case, CaseStatus, CasePrompt
from services.osint_service import OSINTService
from services.ai_service import AIService
from services.qualitative_service import QualitativeService
import logging

logger = logging.getLogger(__name__)

class CaseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.osint_service = OSINTService(db)
        self.ai_service = AIService()
        self.qualitative_service = QualitativeService(db)
    
    async def execute_case_analysis(self, case_id: int, analysis_plan: dict = None):
        """Execute complete analysis for a case"""
        try:
            # Get case
            result = await self.db.execute(
                select(Case).where(Case.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if not case:
                return
            
            # Update status
            case.status = CaseStatus.ANALYZING
            await self.db.commit()
            
            # If no plan provided, generate one
            if not analysis_plan:
                # Get prompt if exists
                prompt_result = await self.db.execute(
                    select(CasePrompt).where(CasePrompt.case_id == case_id).order_by(CasePrompt.created_at.desc())
                )
                prompt = prompt_result.scalar_one_or_none()
                
                if prompt and prompt.ai_analysis:
                    # Use existing plan from prompt
                    analysis_plan = prompt.ai_analysis
                    logger.info(f"Using existing analysis plan from prompt for case {case_id}")
                else:
                    # Generate plan from case description
                    logger.info(f"Generating new analysis plan for case {case_id}")
                    analysis_plan = await self.ai_service.analyze_case_prompt(
                        case.description or case.name
                    )
            
            # Execute OSINT collection
            osint_queries = analysis_plan.get("osint_queries", [])
            osint_results = []
            for query in osint_queries:
                result = await self.osint_service.execute_query(
                    query_type=query["type"],
                    query_params=query.get("params", {}),
                    case_id=case_id
                )
                osint_results.append(result)
            
            # IMPORTANT: Classify all OSINT results through AI
            # This ensures all collected data is classified before visualization
            try:
                from services.ai_classification_service import AIClassificationService
                classification_service = AIClassificationService(self.db)
                await classification_service.classify_all_case_osint(case_id)
                logger.info(f"Classified all OSINT results for case {case_id}")
            except Exception as e:
                logger.warning(f"Error classifying OSINT results for case {case_id}: {e}")
                # Don't fail the whole analysis if classification fails
            
            # Execute AI analysis - Pass db so it can fetch ALL OSINT data if needed
            ai_analyses = analysis_plan.get("ai_analyses", [])
            for ai_analysis_type in ai_analyses:
                await self.ai_service.analyze_data(
                    analysis_type=ai_analysis_type,
                    case_id=case_id,
                    osint_results=osint_results,
                    db=self.db  # Pass db to fetch ALL linked OSINT data
                )
            
            # Execute qualitative analysis if KPIs defined
            kpis = analysis_plan.get("kpis", [])
            if kpis:
                await self.qualitative_service.run_analysis(
                    case_id=case_id,
                    premise=analysis_plan.get("premise", ""),
                    framework=analysis_plan.get("framework", "deductive"),
                    kpi_ids=[kpi["id"] for kpi in kpis]
                )
            
            # Generate automatic predictions based on case data
            try:
                # Generate trend prediction
                trend_prediction = await self.ai_service.generate_prediction(
                    prediction_type="trend",
                    case_id=case_id,
                    db=self.db
                )
                
                # Generate risk prediction
                risk_prediction = await self.ai_service.generate_prediction(
                    prediction_type="risk",
                    case_id=case_id,
                    db=self.db
                )
                
                # Save predictions to database
                from models.ai_analysis import AIAnalysis, AIPrediction
                from sqlalchemy import select
                
                # Get or create AIAnalysis for this case
                analysis_result = await self.db.execute(
                    select(AIAnalysis).where(
                        AIAnalysis.case_id == case_id,
                        AIAnalysis.analysis_type == "predictions"
                    ).limit(1)
                )
                analysis = analysis_result.scalar_one_or_none()
                
                if not analysis:
                    analysis = AIAnalysis(
                        case_id=case_id,
                        analysis_type="predictions",
                        analysis_data={},
                        confidence_score=0.0
                    )
                    self.db.add(analysis)
                    await self.db.flush()
                
                # Save trend prediction
                if trend_prediction.get("text"):
                    trend_pred = AIPrediction(
                        analysis_id=analysis.id,
                        prediction_type="trend",
                        prediction_text=trend_prediction.get("text", ""),
                        confidence_percentage=trend_prediction.get("confidence", 0.0),
                        extra_data={
                            "explanation": trend_prediction.get("explanation", ""),
                            "supporting_data": trend_prediction.get("supporting_data", []),
                            "metadata": trend_prediction.get("metadata", {})
                        }
                    )
                    self.db.add(trend_pred)
                
                # Save risk prediction
                if risk_prediction.get("text"):
                    risk_pred = AIPrediction(
                        analysis_id=analysis.id,
                        prediction_type="risk",
                        prediction_text=risk_prediction.get("text", ""),
                        confidence_percentage=risk_prediction.get("confidence", 0.0),
                        extra_data={
                            "explanation": risk_prediction.get("explanation", ""),
                            "supporting_data": risk_prediction.get("supporting_data", []),
                            "metadata": risk_prediction.get("metadata", {})
                        }
                    )
                    self.db.add(risk_pred)
                
                await self.db.commit()
            except Exception as pred_error:
                logger.error(f"Error generando predicciones automáticas: {pred_error}", exc_info=True)
                # Don't fail the whole analysis if predictions fail
            
            # Update status to completed
            case.status = CaseStatus.COMPLETED
            await self.db.commit()
            
        except Exception as e:
            # Update status to failed
            result = await self.db.execute(
                select(Case).where(Case.id == case_id)
            )
            case = result.scalar_one_or_none()
            if case:
                case.status = CaseStatus.FAILED
                await self.db.commit()
            raise e

