"""
Qualitative Analysis Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from models.qualitative import Premise, ReasoningFramework, KPI, QualitativeAnalysis, QuantitativeAnalysis
from services.ai_service import AIService

class QualitativeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
    
    async def run_analysis(
        self,
        case_id: int,
        premise: str,
        framework: str = "deductive",
        kpi_ids: List[int] = None
    ) -> Dict[str, Any]:
        """Run qualitative/quantitative analysis"""
        # Get KPIs
        kpis = []
        if kpi_ids:
            from sqlalchemy import select
            result = await self.db.execute(
                select(KPI).where(KPI.id.in_(kpi_ids))
            )
            kpi_objs = result.scalars().all()
            kpis = [
                {"id": kpi.id, "name": kpi.name, "type": kpi.kpi_type.value if hasattr(kpi.kpi_type, 'value') else str(kpi.kpi_type)}
                for kpi in kpi_objs
            ]
        
        # Get framework
        framework_obj = await self._get_framework(framework)
        
        # Create premise
        premise_obj = Premise(
            case_id=case_id,
            premise_text=premise,
            framework_id=framework_obj.id if framework_obj else None
        )
        self.db.add(premise_obj)
        await self.db.commit()
        
        # Get OSINT data for this case to include in analysis
        osint_summary = ""
        try:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await self.db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            if queries:
                osint_findings = []
                for query in queries[:10]:  # Limit to 10 queries
                    results_result = await self.db.execute(
                        select(OSINTResult).where(OSINTResult.query_id == query.id)
                    )
                    results = results_result.scalars().all()
                    for result in results[:3]:  # First 3 results per query
                        if result.data and isinstance(result.data, dict):
                            # Extract meaningful data
                            for key in ['title', 'description', 'text', 'content', 'summary', 'name']:
                                if key in result.data:
                                    osint_findings.append(f"- {str(result.data[key])[:300]}")
                                    break
                
                if osint_findings:
                    osint_summary = "\nDATOS OSINT DEL CASO:\n" + "\n".join(osint_findings[:15])  # Limit to 15 findings
        except Exception as osint_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error obteniendo datos OSINT para análisis cualitativo: {osint_error}")
        
        # Run AI analysis based on framework, including OSINT data
        try:
            # Enhance premise with OSINT data
            enhanced_premise = premise
            if osint_summary:
                enhanced_premise = f"{premise}\n\n{osint_summary}"
            
            analysis_result = await self.ai_service.analyze_with_framework(
                premise=enhanced_premise,
                framework=framework,
                kpis=kpis
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en analyze_with_framework: {e}", exc_info=True)
            # Fallback analysis result
            analysis_result = {
                "conclusions": f"Anàlisi basada en la premisa: {premise[:200]}...",
                "evidence": [],
                "confidence": 0.5
            }
        
        # Create qualitative analysis
        # Convert conclusions to string if it's a list
        conclusions = analysis_result.get("conclusions", "")
        if isinstance(conclusions, list):
            import json
            conclusions = json.dumps(conclusions, ensure_ascii=False) if conclusions else ""
        elif not isinstance(conclusions, str):
            conclusions = str(conclusions)
        
        qual_analysis = QualitativeAnalysis(
            case_id=case_id,
            premise_id=premise_obj.id,
            framework_id=framework_obj.id if framework_obj else None,
            conclusions=conclusions,
            evidence=analysis_result.get("evidence", []),
            confidence_score=analysis_result.get("confidence", 0.5)
        )
        self.db.add(qual_analysis)
        await self.db.commit()
        
        return {
            "analysis_id": qual_analysis.id,
            "conclusions": analysis_result.get("conclusions", ""),
            "confidence": analysis_result.get("confidence", 0.5)
        }
    
    async def _get_framework(self, framework_name: str):
        """Get or create reasoning framework"""
        from sqlalchemy import select, func
        from models.qualitative import ReasoningFramework, ReasoningFrameworkType
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Normalize framework name for search
        normalized_name = framework_name.lower()
        
        # Try to find existing framework (case-insensitive search)
        result = await self.db.execute(
            select(ReasoningFramework)
            .where(func.lower(ReasoningFramework.name) == normalized_name)
        )
        framework = result.scalar_one_or_none()
        
        if framework:
            return framework
        
        # Also try to find by framework_type
        framework_type_map = {
            "deductive": ReasoningFrameworkType.DEDUCTIVE,
            "inductive": ReasoningFrameworkType.INDUCTIVE,
            "abductive": ReasoningFrameworkType.ABDUCTIVE,
            "causal": ReasoningFrameworkType.CAUSAL,
        }
        
        framework_type = framework_type_map.get(normalized_name, ReasoningFrameworkType.DEDUCTIVE)
        
        # Try to find by type
        result = await self.db.execute(
            select(ReasoningFramework)
            .where(ReasoningFramework.framework_type == framework_type)
            .where(ReasoningFramework.is_active == True)
        )
        framework = result.scalar_one_or_none()
        
        if framework:
            return framework
        
        # Create framework if it doesn't exist
        descriptions = {
            "deductive": "Raonament des de principis generals a conclusions específiques",
            "inductive": "Inferències basades en l'observació de patrons i tendències",
            "abductive": "Generació d'hipòtesis més probables a partir d'informació incompleta",
            "causal": "Identificació de relacions de causa i efecte entre variables",
        }
        
        description = descriptions.get(normalized_name, "")
        
        # Capitalize first letter for display name
        display_name = framework_name.capitalize()
        
        try:
            new_framework = ReasoningFramework(
                name=display_name,
                framework_type=framework_type,
                description=description,
                is_active=True
            )
            self.db.add(new_framework)
            await self.db.commit()
            await self.db.refresh(new_framework)
            
            return new_framework
        except Exception as e:
            # If UNIQUE constraint fails, try to find it again (race condition)
            await self.db.rollback()
            logger.warning(f"Error creando framework {display_name}, intentando buscar nuevamente: {e}")
            
            # Try to find again (might have been created by another request)
            result = await self.db.execute(
                select(ReasoningFramework)
                .where(func.lower(ReasoningFramework.name) == normalized_name)
            )
            framework = result.scalar_one_or_none()
            
            if framework:
                return framework
            
            # If still not found, try by type
            result = await self.db.execute(
                select(ReasoningFramework)
                .where(ReasoningFramework.framework_type == framework_type)
                .where(ReasoningFramework.is_active == True)
            )
            framework = result.scalar_one_or_none()
            
            if framework:
                return framework
            
            # If still not found, raise the error
            raise Exception(f"No se pudo crear ni encontrar el framework '{framework_name}': {str(e)}")

