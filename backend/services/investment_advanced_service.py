"""
Investment Advanced Service - Análisis ESG, riesgo regulatorio y análisis comparativo
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.investments import InvestmentRecommendation, RiskAnalysis
from models.geopolitical import GeopoliticalRisk, SupplyChainRisk
from services.ai_service import AIService
from services.geopolitical_advanced_service import GeopoliticalAdvancedService
from integrations.alphavantage_api import AlphaVantageAPIService
from integrations.finnhub_api import FinnhubAPIService
import logging

logger = logging.getLogger(__name__)

class InvestmentAdvancedService:
    """Servicio para análisis avanzado de inversiones"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.alphavantage = AlphaVantageAPIService()
        self.finnhub = FinnhubAPIService()
        self.geo_advanced = GeopoliticalAdvancedService(db)
    
    async def analyze_esg_factors(
        self,
        case_id: int,
        company_symbol: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analiza factores ESG (Environmental, Social, Governance)"""
        try:
            # Obtener datos OSINT del caso
            from models.osint import OSINTResult, OSINTQuery
            query = select(OSINTResult).join(OSINTQuery).where(OSINTQuery.case_id == case_id)
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            osint_data = [r.data for r in osint_results if r.data]
            
            # Analizar factores ESG con IA
            esg_analysis = await self._analyze_esg_with_ai(osint_data, company_symbol, country)
            
            # Calcular scores ESG
            environmental_score = esg_analysis.get("environmental_score", 50.0)
            social_score = esg_analysis.get("social_score", 50.0)
            governance_score = esg_analysis.get("governance_score", 50.0)
            
            # Score ESG agregado
            esg_score = (environmental_score + social_score + governance_score) / 3.0
            
            return {
                "esg_score": esg_score,
                "environmental_score": environmental_score,
                "social_score": social_score,
                "governance_score": governance_score,
                "factors": esg_analysis.get("factors", {}),
                "recommendations": esg_analysis.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing ESG factors: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def assess_regulatory_risk(
        self,
        case_id: int,
        country: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evalúa riesgo regulatorio para inversiones"""
        try:
            # Usar servicio geopolítico avanzado
            regulatory_risk = await self.geo_advanced.assess_regulatory_risk(
                country=country,
                industry=industry,
                case_id=case_id
            )
            
            # Obtener riesgos geopolíticos
            from models.geopolitical import GeopoliticalRisk
            result = await self.db.execute(
                select(GeopoliticalRisk)
                .where(GeopoliticalRisk.country == country)
                .order_by(GeopoliticalRisk.calculated_at.desc())
                .limit(1)
            )
            geo_risk = result.scalar_one_or_none()
            
            # Combinar análisis
            combined_risk = {
                "regulatory_risk": regulatory_risk.get("regulatory_risk", {}),
                "geopolitical_risk": {
                    "overall": geo_risk.overall_risk_score if geo_risk else 50.0,
                    "regulatory": geo_risk.regulatory_risk if geo_risk else 50.0
                } if geo_risk else None,
                "recommendation": self._generate_regulatory_recommendation(regulatory_risk, geo_risk)
            }
            
            return combined_risk
            
        except Exception as e:
            logger.error(f"Error assessing regulatory risk: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def compare_market_opportunities(
        self,
        case_id: int,
        countries: List[str],
        industries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compara oportunidades de mercado entre países/industrias"""
        try:
            opportunities = []
            
            for country in countries:
                # Obtener riesgos geopolíticos
                from models.geopolitical import GeopoliticalRisk
                result = await self.db.execute(
                    select(GeopoliticalRisk)
                    .where(GeopoliticalRisk.country == country)
                    .order_by(GeopoliticalRisk.calculated_at.desc())
                    .limit(1)
                )
                geo_risk = result.scalar_one_or_none()
                
                # Calcular oportunidad (inversa del riesgo)
                risk_score = geo_risk.overall_risk_score if geo_risk else 50.0
                opportunity_score = 100.0 - risk_score
                
                # Analizar por industria si se especifica
                industry_analysis = {}
                if industries:
                    for industry in industries:
                        supply_chain = await self.geo_advanced.analyze_supply_chain_risks(
                            country=country,
                            industry=industry,
                            case_id=case_id
                        )
                        industry_analysis[industry] = {
                            "supply_chain_risk": supply_chain.get("dependency_score", 50.0),
                            "opportunity": 100.0 - supply_chain.get("dependency_score", 50.0)
                        }
                
                opportunities.append({
                    "country": country,
                    "opportunity_score": opportunity_score,
                    "geopolitical_risk": risk_score,
                    "industry_analysis": industry_analysis if industries else None
                })
            
            # Ordenar por oportunidad
            opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
            
            return {
                "opportunities": opportunities,
                "best_opportunity": opportunities[0] if opportunities else None,
                "comparison_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing market opportunities: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def calculate_geopolitical_impact_on_investments(
        self,
        case_id: int,
        countries: List[str],
        investment_type: str = "general",
        fetch_fresh_data: bool = True
    ) -> Dict[str, Any]:
        """Calcula impacto geopolítico en inversiones
        
        Args:
            case_id: ID del caso
            countries: Lista de países a analizar
            investment_type: Tipo de inversión (general, long_term, regulatory_sensitive)
            fetch_fresh_data: Si True, obtiene datos frescos de APIs geopolíticas cuando es necesario
        """
        try:
            # Obtener contexto del caso
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await self.db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if not case:
                return {"error": f"Case {case_id} not found"}
            
            from models.geopolitical import GeopoliticalRisk
            
            impacts = []
            
            for country in countries:
                # Obtener riesgo geopolítico
                result = await self.db.execute(
                    select(GeopoliticalRisk)
                    .where(GeopoliticalRisk.country == country)
                    .order_by(GeopoliticalRisk.calculated_at.desc())
                    .limit(1)
                )
                geo_risk = result.scalar_one_or_none()
                
                # Si fetch_fresh_data es True y no hay riesgo geopolítico reciente, obtener datos frescos
                if fetch_fresh_data and (not geo_risk or geo_risk.calculated_at < datetime.now() - timedelta(days=1)):
                    try:
                        from integrations.permutable_api import PermutableAPIService
                        permutable = PermutableAPIService()
                        
                        events_result = await permutable.get_geopolitical_events(
                            location=country,
                            limit=10
                        )
                        if events_result.get("status") == "success" and events_result.get("events"):
                            # Actualizar o crear riesgo geopolítico con datos frescos
                            # Esto es una simplificación - en producción, se debería procesar los eventos
                            logger.info(f"Fetched {len(events_result.get('events', []))} fresh geopolitical events for {country}")
                    except Exception as e:
                        logger.warning(f"Error fetching fresh geopolitical data for {country}: {e}")
                
                if not geo_risk:
                    # Crear riesgo geopolítico por defecto si no existe
                    geo_risk = GeopoliticalRisk(
                        case_id=case_id,
                        country=country,
                        overall_risk_score=50.0,
                        political_stability_risk=50.0,
                        conflict_risk=50.0,
                        economic_risk=50.0,
                        regulatory_risk=50.0
                    )
                    self.db.add(geo_risk)
                    await self.db.flush()
                    continue
                
                # Calcular impacto en inversiones
                impact_score = self._calculate_investment_impact(geo_risk, investment_type)
                
                # Factores de impacto
                impact_factors = {
                    "political_stability": geo_risk.political_stability_risk,
                    "conflict_risk": geo_risk.conflict_risk,
                    "economic_risk": geo_risk.economic_risk,
                    "regulatory_risk": geo_risk.regulatory_risk
                }
                
                impacts.append({
                    "country": country,
                    "impact_score": impact_score,
                    "impact_level": self._determine_impact_level(impact_score),
                    "factors": impact_factors,
                    "recommendation": self._generate_investment_recommendation(impact_score, impact_factors)
                })
            
            return {
                "impacts": impacts,
                "overall_assessment": self._assess_overall_impact(impacts),
                "investment_type": investment_type
            }
            
        except Exception as e:
            logger.error(f"Error calculating geopolitical impact: {e}", exc_info=True)
            return {"error": str(e)}
    
    # Métodos privados
    
    async def _analyze_esg_with_ai(
        self,
        osint_data: List[Dict],
        company_symbol: Optional[str],
        country: Optional[str]
    ) -> Dict[str, Any]:
        """Analiza factores ESG usando IA"""
        try:
            if not self.ai_service.client:
                return self._esg_fallback()
            
            context = f"OSINT data points: {len(osint_data)}\n"
            if company_symbol:
                context += f"Company: {company_symbol}\n"
            if country:
                context += f"Country: {country}\n"
            
            prompt = f"""Analyze ESG (Environmental, Social, Governance) factors:
{context}

Return JSON with:
- environmental_score: 0-100
- social_score: 0-100
- governance_score: 0-100
- factors: {{"environmental": [...], "social": [...], "governance": [...]}}
- recommendations: list of recommendations

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are an ESG analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            import json
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return self._esg_fallback()
        except Exception as e:
            logger.error(f"Error in ESG AI analysis: {e}")
            return self._esg_fallback()
    
    def _esg_fallback(self) -> Dict[str, Any]:
        """Fallback para análisis ESG"""
        return {
            "environmental_score": 50.0,
            "social_score": 50.0,
            "governance_score": 50.0,
            "factors": {
                "environmental": [],
                "social": [],
                "governance": []
            },
            "recommendations": []
        }
    
    def _generate_regulatory_recommendation(
        self,
        regulatory_risk: Dict,
        geo_risk: Optional[Any]
    ) -> str:
        """Genera recomendación basada en riesgo regulatorio"""
        risk_level = regulatory_risk.get("regulatory_risk", {}).get("risk_level", "medium")
        
        if risk_level == "high":
            return "High regulatory risk - consider alternative jurisdictions"
        elif risk_level == "medium":
            return "Moderate regulatory risk - monitor developments closely"
        else:
            return "Low regulatory risk - proceed with standard due diligence"
    
    def _calculate_investment_impact(
        self,
        geo_risk: Any,
        investment_type: str
    ) -> float:
        """Calcula impacto en inversiones (0-100, donde 100 es máximo impacto negativo)"""
        # Ponderar según tipo de inversión
        if investment_type == "long_term":
            # Inversiones a largo plazo más sensibles a estabilidad política
            weights = {"political_stability_risk": 0.4, "conflict_risk": 0.3, "economic_risk": 0.2, "regulatory_risk": 0.1}
        elif investment_type == "regulatory_sensitive":
            # Inversiones sensibles a regulación
            weights = {"political_stability_risk": 0.2, "conflict_risk": 0.2, "economic_risk": 0.2, "regulatory_risk": 0.4}
        else:
            # General
            weights = {"political_stability_risk": 0.25, "conflict_risk": 0.25, "economic_risk": 0.25, "regulatory_risk": 0.25}
        
        impact = (
            geo_risk.political_stability_risk * weights["political_stability_risk"] +
            geo_risk.conflict_risk * weights["conflict_risk"] +
            geo_risk.economic_risk * weights["economic_risk"] +
            geo_risk.regulatory_risk * weights["regulatory_risk"]
        )
        
        return impact
    
    def _determine_impact_level(self, impact_score: float) -> str:
        """Determina nivel de impacto"""
        if impact_score >= 70:
            return "high"
        elif impact_score >= 40:
            return "medium"
        else:
            return "low"
    
    def _generate_investment_recommendation(
        self,
        impact_score: float,
        impact_factors: Dict
    ) -> str:
        """Genera recomendación de inversión"""
        if impact_score >= 70:
            return "Avoid or reduce exposure - high geopolitical risk"
        elif impact_score >= 40:
            return "Proceed with caution - implement risk mitigation strategies"
        else:
            return "Favorable conditions - standard due diligence recommended"
    
    def _assess_overall_impact(self, impacts: List[Dict]) -> Dict[str, Any]:
        """Evalúa impacto general"""
        if not impacts:
            return {"assessment": "insufficient_data"}
        
        avg_impact = sum(i["impact_score"] for i in impacts) / len(impacts)
        
        return {
            "average_impact": avg_impact,
            "overall_level": self._determine_impact_level(avg_impact),
            "countries_analyzed": len(impacts)
        }

