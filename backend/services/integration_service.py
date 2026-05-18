"""
Integration Service - Conecta análisis entre módulos (geopolítica, inversiones, reputación, asuntos públicos)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.reputation_service import ReputationService
from services.public_affairs_service import PublicAffairsService
from services.geopolitical_advanced_service import GeopoliticalAdvancedService
from services.investment_advanced_service import InvestmentAdvancedService
from services.geopolitical_risk_service import GeopoliticalRiskService
import logging

logger = logging.getLogger(__name__)

class IntegrationService:
    """Servicio para integrar análisis entre módulos"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.reputation_service = ReputationService(db)
        self.public_affairs_service = PublicAffairsService(db)
        self.geo_advanced_service = GeopoliticalAdvancedService(db)
        self.investment_advanced_service = InvestmentAdvancedService(db)
        self.geo_risk_service = GeopoliticalRiskService(db)
    
    async def analyze_geopolitical_impact_on_investments(
        self,
        case_id: int,
        countries: List[str],
        investment_type: str = "general",
        fetch_fresh_data: bool = True
    ) -> Dict[str, Any]:
        """Analiza cómo eventos geopolíticos afectan inversiones
        
        Args:
            case_id: ID del caso
            countries: Lista de países a analizar
            investment_type: Tipo de inversión (general, long_term, regulatory_sensitive)
            fetch_fresh_data: Si True, obtiene datos frescos de APIs cuando es necesario
        """
        try:
            # Obtener contexto del caso
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await self.db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if not case:
                return {"error": f"Case {case_id} not found"}
            
            # Usar servicio de inversiones avanzado
            impact_analysis = await self.investment_advanced_service.calculate_geopolitical_impact_on_investments(
                case_id=case_id,
                countries=countries,
                investment_type=investment_type
            )
            
            # Obtener eventos geopolíticos recientes
            from models.geopolitical import DiplomaticEvent
            from sqlalchemy import select, and_
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=90)
            result = await self.db.execute(
                select(DiplomaticEvent)
                .where(
                    and_(
                        DiplomaticEvent.case_id == case_id,
                        DiplomaticEvent.event_date >= cutoff_date
                    )
                )
                .order_by(DiplomaticEvent.event_date.desc())
            )
            events = result.scalars().all()
            
            # Correlacionar eventos con impacto
            event_impacts = []
            for event in events:
                event_countries = event.countries or []
                if any(c in countries for c in event_countries):
                    event_impacts.append({
                        "event_type": event.event_type.value,
                        "title": event.title,
                        "date": event.event_date.isoformat() if event.event_date else None,
                        "impact_score": event.impact_score,
                        "sentiment": event.sentiment_score
                    })
            
            return {
                "investment_impact": impact_analysis,
                "recent_events": event_impacts,
                "correlation": self._correlate_events_with_impact(event_impacts, impact_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing geopolitical impact on investments: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def assess_reputation_impact_of_geopolitical_events(
        self,
        entity_name: str,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Evalúa impacto reputacional de eventos geopolíticos"""
        try:
            # Obtener perfil de reputación
            profile = await self.reputation_service._get_profile_by_name(entity_name)
            if not profile:
                return {"error": "Reputation profile not found"}
            
            # Obtener eventos geopolíticos relacionados
            from models.geopolitical import DiplomaticEvent
            from sqlalchemy import select, and_
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=30)
            query = select(DiplomaticEvent).where(DiplomaticEvent.event_date >= cutoff_date)
            if case_id:
                query = query.where(DiplomaticEvent.case_id == case_id)
            
            result = await self.db.execute(query.order_by(DiplomaticEvent.event_date.desc()))
            events = result.scalars().all()
            
            # Filtrar eventos relevantes
            relevant_events = []
            for event in events:
                event_text = f"{event.title} {event.description or ''}"
                if entity_name.lower() in event_text.lower():
                    relevant_events.append(event)
            
            # Calcular impacto en reputación
            reputation_impact = self._calculate_reputation_impact_from_events(relevant_events, profile)
            
            return {
                "entity_name": entity_name,
                "current_reputation_score": profile.reputation_score,
                "relevant_events": [
                    {
                        "type": e.event_type.value,
                        "title": e.title,
                        "date": e.event_date.isoformat() if e.event_date else None,
                        "impact_score": e.impact_score,
                        "sentiment": e.sentiment_score
                    }
                    for e in relevant_events
                ],
                "reputation_impact": reputation_impact
            }
            
        except Exception as e:
            logger.error(f"Error assessing reputation impact: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def correlate_public_affairs_with_reputation(
        self,
        entity_name: str,
        case_id: int
    ) -> Dict[str, Any]:
        """Correlaciona asuntos públicos con reputación"""
        try:
            # Obtener análisis de políticas
            from models.public_affairs import PolicyAnalysis
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(PolicyAnalysis).where(PolicyAnalysis.case_id == case_id)
            )
            policies = result.scalars().all()
            
            # Obtener perfil de reputación
            profile = await self.reputation_service._get_profile_by_name(entity_name)
            
            # Correlacionar políticas con reputación
            correlations = []
            for policy in policies:
                # Verificar si la política afecta a la entidad
                policy_text = f"{policy.policy_topic} {policy.policy_description or ''}"
                if entity_name.lower() in policy_text.lower():
                    correlation = {
                        "policy_topic": policy.policy_topic,
                        "jurisdiction": policy.jurisdiction,
                        "impact_score": policy.impact_score,
                        "reputation_impact": self._estimate_reputation_impact_from_policy(policy, profile)
                    }
                    correlations.append(correlation)
            
            return {
                "entity_name": entity_name,
                "current_reputation": profile.reputation_score if profile else None,
                "policy_correlations": correlations,
                "overall_assessment": self._assess_public_affairs_impact(correlations)
            }
            
        except Exception as e:
            logger.error(f"Error correlating public affairs with reputation: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def generate_comprehensive_risk_assessment(
        self,
        case_id: int,
        entity_name: Optional[str] = None,
        countries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Genera evaluación de riesgo integral combinando todos los módulos"""
        try:
            assessment = {
                "case_id": case_id,
                "assessment_date": datetime.now().isoformat(),
                "risks": {}
            }
            
            # Riesgo geopolítico
            if countries:
                geo_risks = []
                for country in countries:
                    risks = await self.geo_risk_service.get_risks(case_id=case_id, country=country)
                    if risks:
                        geo_risks.extend(risks)
                
                assessment["risks"]["geopolitical"] = {
                    "countries": countries,
                    "risks": geo_risks,
                    "overall_level": self._determine_overall_risk_level(geo_risks)
                }
            
            # Riesgo de reputación
            if entity_name:
                reputation_data = await self.reputation_service.generate_reputation_report(
                    entity_name=entity_name,
                    case_id=case_id
                )
                
                reputation_risk = 100.0 - reputation_data.get("reputation_score", 50.0)
                assessment["risks"]["reputation"] = {
                    "entity_name": entity_name,
                    "reputation_score": reputation_data.get("reputation_score", 50.0),
                    "reputation_risk": reputation_risk,
                    "crisis_level": reputation_data.get("crisis_level", "none"),
                    "trend": reputation_data.get("trend", "unknown")
                }
            
            # Riesgo regulatorio (asuntos públicos)
            if countries:
                regulatory_risks = []
                for country in countries:
                    risk = await self.geo_advanced_service.assess_regulatory_risk(
                        country=country,
                        case_id=case_id
                    )
                    regulatory_risks.append({
                        "country": country,
                        "risk": risk
                    })
                
                assessment["risks"]["regulatory"] = {
                    "countries": countries,
                    "risks": regulatory_risks
                }
            
            # Riesgo de inversión
            if countries:
                investment_impacts = await self.investment_advanced_service.calculate_geopolitical_impact_on_investments(
                    case_id=case_id,
                    countries=countries
                )
                
                assessment["risks"]["investment"] = investment_impacts
            
            # Calcular riesgo agregado
            assessment["overall_risk"] = self._calculate_overall_risk(assessment["risks"])
            
            # Recomendaciones
            assessment["recommendations"] = self._generate_comprehensive_recommendations(assessment)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error generating comprehensive risk assessment: {e}", exc_info=True)
            return {"error": str(e)}
    
    # Métodos privados
    
    def _correlate_events_with_impact(
        self,
        events: List[Dict],
        impact_analysis: Dict
    ) -> Dict[str, Any]:
        """Correlaciona eventos con impacto en inversiones"""
        if not events:
            return {"correlation": "no_events"}
        
        # Calcular correlación básica
        negative_events = sum(1 for e in events if e.get("sentiment", 0) < -0.3)
        positive_events = sum(1 for e in events if e.get("sentiment", 0) > 0.3)
        
        return {
            "total_events": len(events),
            "negative_events": negative_events,
            "positive_events": positive_events,
            "correlation_strength": "strong" if len(events) > 5 else "moderate"
        }
    
    def _calculate_reputation_impact_from_events(
        self,
        events: List[Any],
        profile: Any
    ) -> Dict[str, Any]:
        """Calcula impacto en reputación desde eventos"""
        if not events:
            return {"impact": "none", "change": 0.0}
        
        total_impact = 0.0
        for event in events:
            # Impacto basado en score de sentimiento y importancia
            sentiment = event.sentiment_score or 0.0
            importance = 1.0 if event.importance.value == "high" else 0.5
            total_impact += sentiment * importance * 10
        
        # Normalizar
        avg_impact = total_impact / len(events)
        
        return {
            "impact": "positive" if avg_impact > 0 else "negative" if avg_impact < 0 else "neutral",
            "estimated_change": avg_impact,
            "events_count": len(events)
        }
    
    def _estimate_reputation_impact_from_policy(
        self,
        policy: Any,
        profile: Optional[Any]
    ) -> Dict[str, Any]:
        """Estima impacto reputacional desde política"""
        impact_score = policy.impact_score
        
        # Convertir score de impacto de política a cambio en reputación
        # Políticas de alto impacto pueden afectar reputación significativamente
        if impact_score >= 75:
            reputation_change = -15.0  # Alto impacto negativo
        elif impact_score >= 50:
            reputation_change = -8.0
        elif impact_score >= 25:
            reputation_change = -3.0
        else:
            reputation_change = 0.0
        
        return {
            "estimated_change": reputation_change,
            "impact_level": policy.impact_level.value
        }
    
    def _assess_public_affairs_impact(self, correlations: List[Dict]) -> Dict[str, Any]:
        """Evalúa impacto general de asuntos públicos"""
        if not correlations:
            return {"assessment": "no_correlations"}
        
        total_impact = sum(c.get("reputation_impact", {}).get("estimated_change", 0) for c in correlations)
        avg_impact = total_impact / len(correlations)
        
        return {
            "policies_affecting": len(correlations),
            "average_impact": avg_impact,
            "overall_assessment": "high_risk" if avg_impact < -10 else "moderate_risk" if avg_impact < -5 else "low_risk"
        }
    
    def _determine_overall_risk_level(self, risks: List[Dict]) -> str:
        """Determina nivel de riesgo general"""
        if not risks:
            return "unknown"
        
        avg_risk = sum(r.get("overall_risk_score", 50.0) for r in risks) / len(risks)
        
        if avg_risk >= 70:
            return "high"
        elif avg_risk >= 40:
            return "medium"
        else:
            return "low"
    
    def _calculate_overall_risk(self, risks: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula riesgo agregado de todos los módulos"""
        risk_scores = []
        
        # Geopolítico
        if "geopolitical" in risks:
            geo_level = risks["geopolitical"].get("overall_level", "medium")
            risk_scores.append(self._level_to_score(geo_level))
        
        # Reputación
        if "reputation" in risks:
            rep_risk = risks["reputation"].get("reputation_risk", 50.0)
            risk_scores.append(rep_risk)
        
        # Regulatorio
        if "regulatory" in risks:
            reg_risks = risks["regulatory"].get("risks", [])
            if reg_risks:
                reg_scores = [
                    self._level_to_score(
                        str(r.get("risk", {}).get("regulatory_risk", {}).get("risk_level", "medium"))
                    )
                    for r in reg_risks
                ]
                avg_reg = sum(reg_scores) / len(reg_scores)
                risk_scores.append(avg_reg)
        
        # Inversión
        if "investment" in risks:
            inv_assessment = risks["investment"].get("overall_assessment", {})
            avg_impact = inv_assessment.get("average_impact", 50.0)
            risk_scores.append(avg_impact)
        
        if not risk_scores:
            return {"overall_score": 50.0, "level": "medium"}
        
        overall_score = sum(risk_scores) / len(risk_scores)
        
        return {
            "overall_score": overall_score,
            "level": "high" if overall_score >= 70 else "medium" if overall_score >= 40 else "low",
            "components": len(risk_scores)
        }
    
    def _level_to_score(self, level: str) -> float:
        """Convierte nivel de riesgo a score"""
        if level == "high" or level == "critical":
            return 75.0
        elif level == "medium":
            return 50.0
        else:
            return 25.0
    
    def _generate_comprehensive_recommendations(self, assessment: Dict) -> List[str]:
        """Genera recomendaciones comprehensivas"""
        recommendations = []
        
        overall_risk = assessment.get("overall_risk", {})
        risk_level = overall_risk.get("level", "medium")
        
        if risk_level == "high":
            recommendations.append("Implement immediate risk mitigation measures")
            recommendations.append("Diversify operations and investments")
        
        if "reputation" in assessment.get("risks", {}):
            rep_risk = assessment["risks"]["reputation"]
            if rep_risk.get("crisis_level") in ["critical", "high"]:
                recommendations.append("Activate crisis communication protocol")
        
        if "geopolitical" in assessment.get("risks", {}):
            geo_risk = assessment["risks"]["geopolitical"]
            if geo_risk.get("overall_level") == "high":
                recommendations.append("Monitor geopolitical developments closely")
                recommendations.append("Develop contingency plans for high-risk countries")
        
        return recommendations

