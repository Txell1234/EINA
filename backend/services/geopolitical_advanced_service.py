"""
Geopolitical Advanced Service - Análisis avanzado de cadenas de suministro, interdependencias y escenarios
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.geopolitical import SupplyChainRisk, EconomicInterdependence, GeopoliticalRisk
from models.osint import OSINTResult, OSINTQuery
from services.ai_service import AIService
from integrations.ensembledata_api import EnsembleDataAPIService
from integrations.news_api import NewsAPIService
import logging

logger = logging.getLogger(__name__)

class GeopoliticalAdvancedService:
    """Servicio para análisis geopolítico avanzado"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.ensembledata = EnsembleDataAPIService()
        self.news_api = NewsAPIService()
    
    async def analyze_supply_chain_risks(
        self,
        country: str,
        industry: str,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Analiza riesgos en cadenas de suministro"""
        try:
            # Buscar riesgo existente o crear nuevo
            result = await self.db.execute(
                select(SupplyChainRisk)
                .where(
                    and_(
                        SupplyChainRisk.country == country,
                        SupplyChainRisk.industry == industry
                    )
                )
                .limit(1)
            )
            risk = result.scalar_one_or_none()
            
            if not risk:
                risk = SupplyChainRisk(
                    case_id=case_id,
                    country=country,
                    industry=industry,
                    dependency_score=0.0
                )
                self.db.add(risk)
                await self.db.flush()
            
            # Obtener datos OSINT relacionados
            osint_data = await self._get_osint_data_for_supply_chain(country, industry, case_id)
            
            # Obtener riesgos geopolíticos del país
            geo_risks = await self._get_geopolitical_risks(country)
            
            # Calcular score de dependencia
            dependency_score = await self._calculate_dependency_score(country, industry, osint_data, geo_risks)
            
            # Identificar factores de vulnerabilidad
            vulnerability_factors = await self._identify_vulnerability_factors(country, industry, geo_risks, osint_data)
            
            # Análisis de riesgo detallado
            risk_assessment = await self._assess_supply_chain_risk(country, industry, dependency_score, vulnerability_factors)
            
            # Estrategias de mitigación
            mitigation_strategies = await self._suggest_mitigation_strategies(risk_assessment, vulnerability_factors)
            
            # Actualizar riesgo
            risk.dependency_score = dependency_score
            risk.vulnerability_factors = vulnerability_factors
            risk.risk_assessment = risk_assessment
            risk.mitigation_strategies = mitigation_strategies
            
            await self.db.commit()
            
            return {
                "risk_id": risk.id,
                "country": country,
                "industry": industry,
                "dependency_score": dependency_score,
                "vulnerability_factors": vulnerability_factors,
                "risk_assessment": risk_assessment,
                "mitigation_strategies": mitigation_strategies
            }
            
        except Exception as e:
            logger.error(f"Error analyzing supply chain risks: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def calculate_economic_interdependence(
        self,
        country1: str,
        country2: str,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calcula interdependencias económicas entre países"""
        try:
            # Normalizar orden de países
            if country1 > country2:
                country1, country2 = country2, country1
            
            # Buscar interdependencia existente o crear nueva
            result = await self.db.execute(
                select(EconomicInterdependence)
                .where(
                    and_(
                        EconomicInterdependence.country1 == country1,
                        EconomicInterdependence.country2 == country2
                    )
                )
                .limit(1)
            )
            interdependence = result.scalar_one_or_none()
            
            if not interdependence:
                interdependence = EconomicInterdependence(
                    case_id=case_id,
                    country1=country1,
                    country2=country2,
                    trade_volume=0.0,
                    dependency_ratio=0.0
                )
                self.db.add(interdependence)
                await self.db.flush()
            
            # Obtener datos OSINT relacionados
            osint_data = await self._get_osint_data_for_trade(country1, country2, case_id)
            
            # Calcular volumen de comercio (simplificado - en producción usar APIs de comercio)
            trade_volume = await self._estimate_trade_volume(country1, country2, osint_data)
            
            # Calcular ratio de dependencia
            dependency_ratio = await self._calculate_dependency_ratio(country1, country2, trade_volume, osint_data)
            
            # Identificar sectores involucrados
            sectors = await self._identify_trade_sectors(country1, country2, osint_data)
            
            # Análisis por sector
            sector_analysis = await self._analyze_sectors(sectors, osint_data)
            
            # Dirección de dependencia
            dependency_direction = await self._determine_dependency_direction(country1, country2, dependency_ratio, sector_analysis)
            
            # Actualizar interdependencia
            interdependence.trade_volume = trade_volume
            interdependence.dependency_ratio = dependency_ratio
            interdependence.sectors = sectors
            interdependence.sector_analysis = sector_analysis
            interdependence.dependency_direction = dependency_direction
            
            await self.db.commit()
            
            return {
                "interdependence_id": interdependence.id,
                "country1": country1,
                "country2": country2,
                "trade_volume": trade_volume,
                "dependency_ratio": dependency_ratio,
                "sectors": sectors,
                "sector_analysis": sector_analysis,
                "dependency_direction": dependency_direction
            }
            
        except Exception as e:
            logger.error(f"Error calculating economic interdependence: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def generate_scenario_analysis(
        self,
        case_id: int,
        countries: List[str],
        time_horizon: str = "12_months"
    ) -> Dict[str, Any]:
        """Genera análisis de escenarios (best case, worst case, base case)"""
        try:
            # Obtener riesgos geopolíticos para los países
            geo_risks = {}
            for country in countries:
                result = await self.db.execute(
                    select(GeopoliticalRisk)
                    .where(GeopoliticalRisk.country == country)
                    .order_by(GeopoliticalRisk.calculated_at.desc())
                    .limit(1)
                )
                risk = result.scalar_one_or_none()
                if risk:
                    geo_risks[country] = risk
            
            # Obtener datos OSINT
            osint_data = await self._get_osint_data_for_countries(countries, case_id)
            
            # Generar escenarios con IA
            scenarios = await self._generate_scenarios_with_ai(countries, geo_risks, osint_data, time_horizon)
            
            return {
                "scenarios": scenarios,
                "countries": countries,
                "time_horizon": time_horizon
            }
            
        except Exception as e:
            logger.error(f"Error generating scenario analysis: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def assess_regulatory_risk(
        self,
        country: str,
        industry: Optional[str] = None,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Evalúa riesgo regulatorio por jurisdicción"""
        try:
            # Obtener riesgos geopolíticos
            geo_risk = await self._get_geopolitical_risks(country)
            
            # Obtener datos OSINT sobre regulaciones
            osint_data = await self._get_osint_data_for_regulations(country, industry, case_id)
            
            # Analizar riesgo regulatorio con IA
            regulatory_risk = await self._analyze_regulatory_risk_with_ai(country, industry, geo_risk, osint_data)
            
            return {
                "country": country,
                "industry": industry,
                "regulatory_risk": regulatory_risk
            }
            
        except Exception as e:
            logger.error(f"Error assessing regulatory risk: {e}", exc_info=True)
            return {"error": str(e)}
    
    # Métodos privados
    
    async def _get_osint_data_for_supply_chain(
        self,
        country: str,
        industry: str,
        case_id: Optional[int]
    ) -> List[Dict]:
        """Obtiene datos OSINT relacionados con cadena de suministro"""
        query = select(OSINTResult).join(OSINTQuery)
        if case_id:
            query = query.where(OSINTQuery.case_id == case_id)
        
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if country.lower() in text.lower() and industry.lower() in text.lower():
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _get_geopolitical_risks(self, country: str) -> Optional[GeopoliticalRisk]:
        """Obtiene riesgos geopolíticos del país"""
        result = await self.db.execute(
            select(GeopoliticalRisk)
            .where(GeopoliticalRisk.country == country)
            .order_by(GeopoliticalRisk.calculated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _calculate_dependency_score(
        self,
        country: str,
        industry: str,
        osint_data: List[Dict],
        geo_risk: Optional[GeopoliticalRisk]
    ) -> float:
        """Calcula score de dependencia (0-100)"""
        base_score = 50.0
        
        # Ajustar según riesgo geopolítico
        if geo_risk:
            base_score += geo_risk.overall_risk_score * 0.3
        
        # Ajustar según menciones en OSINT
        if osint_data:
            base_score += min(30.0, len(osint_data) * 2)
        
        return min(100.0, base_score)
    
    async def _identify_vulnerability_factors(
        self,
        country: str,
        industry: str,
        geo_risk: Optional[GeopoliticalRisk],
        osint_data: List[Dict]
    ) -> List[str]:
        """Identifica factores de vulnerabilidad"""
        factors = []
        
        if geo_risk:
            if geo_risk.political_stability_risk > 50:
                factors.append("political_instability")
            if geo_risk.conflict_risk > 50:
                factors.append("conflict_risk")
            if geo_risk.economic_risk > 50:
                factors.append("economic_instability")
            if geo_risk.regulatory_risk > 50:
                factors.append("regulatory_uncertainty")
        
        return factors
    
    async def _assess_supply_chain_risk(
        self,
        country: str,
        industry: str,
        dependency_score: float,
        vulnerability_factors: List[str]
    ) -> Dict[str, Any]:
        """Evalúa riesgo de cadena de suministro"""
        risk_level = "low"
        if dependency_score > 70:
            risk_level = "high"
        elif dependency_score > 40:
            risk_level = "medium"
        
        return {
            "risk_level": risk_level,
            "dependency_score": dependency_score,
            "vulnerability_factors": vulnerability_factors,
            "recommendation": "diversify" if risk_level == "high" else "monitor"
        }
    
    async def _suggest_mitigation_strategies(
        self,
        risk_assessment: Dict,
        vulnerability_factors: List[str]
    ) -> List[str]:
        """Sugiere estrategias de mitigación"""
        strategies = []
        
        if "political_instability" in vulnerability_factors:
            strategies.append("Diversify supply chain to stable countries")
        
        if "regulatory_uncertainty" in vulnerability_factors:
            strategies.append("Engage with regulatory bodies early")
        
        if risk_assessment.get("risk_level") == "high":
            strategies.append("Develop alternative suppliers")
            strategies.append("Increase inventory buffers")
        
        return strategies
    
    async def _get_osint_data_for_trade(
        self,
        country1: str,
        country2: str,
        case_id: Optional[int]
    ) -> List[Dict]:
        """Obtiene datos OSINT relacionados con comercio"""
        query = select(OSINTResult).join(OSINTQuery)
        if case_id:
            query = query.where(OSINTQuery.case_id == case_id)
        
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if (country1.lower() in text.lower() and country2.lower() in text.lower()) or \
                   ("trade" in text.lower() and (country1.lower() in text.lower() or country2.lower() in text.lower())):
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _estimate_trade_volume(
        self,
        country1: str,
        country2: str,
        osint_data: List[Dict]
    ) -> float:
        """Estima volumen de comercio (simplificado)"""
        # En producción, usar APIs de comercio internacional
        # Por ahora, estimación basada en menciones
        return len(osint_data) * 1000.0  # Millones USD
    
    async def _calculate_dependency_ratio(
        self,
        country1: str,
        country2: str,
        trade_volume: float,
        osint_data: List[Dict]
    ) -> float:
        """Calcula ratio de dependencia (0-1)"""
        # Simplificado - en producción usar datos económicos reales
        if trade_volume > 0:
            return min(1.0, trade_volume / 100000.0)  # Normalizar
        return 0.0
    
    async def _identify_trade_sectors(
        self,
        country1: str,
        country2: str,
        osint_data: List[Dict]
    ) -> List[str]:
        """Identifica sectores involucrados en el comercio"""
        sectors = set()
        
        sector_keywords = {
            "technology": ["tech", "software", "electronics", "semiconductor"],
            "energy": ["oil", "gas", "energy", "petroleum"],
            "manufacturing": ["manufacturing", "production", "factory"],
            "agriculture": ["agriculture", "food", "crops", "grain"]
        }
        
        for data in osint_data:
            text = self._extract_text_from_osint(data).lower()
            for sector, keywords in sector_keywords.items():
                if any(keyword in text for keyword in keywords):
                    sectors.add(sector)
        
        return list(sectors) if sectors else ["general"]
    
    async def _analyze_sectors(
        self,
        sectors: List[str],
        osint_data: List[Dict]
    ) -> Dict[str, Any]:
        """Analiza sectores en detalle"""
        analysis = {}
        for sector in sectors:
            analysis[sector] = {
                "importance": "high",  # Simplificado
                "trade_volume_estimate": len(osint_data) * 100
            }
        return analysis
    
    async def _determine_dependency_direction(
        self,
        country1: str,
        country2: str,
        dependency_ratio: float,
        sector_analysis: Dict
    ) -> str:
        """Determina dirección de dependencia"""
        if dependency_ratio > 0.7:
            return "mutual"
        elif dependency_ratio > 0.4:
            return f"{country1}_to_{country2}"
        else:
            return "low"
    
    async def _get_osint_data_for_countries(
        self,
        countries: List[str],
        case_id: int
    ) -> List[Dict]:
        """Obtiene datos OSINT para países"""
        query = select(OSINTResult).join(OSINTQuery).where(OSINTQuery.case_id == case_id)
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if any(country.lower() in text.lower() for country in countries):
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _generate_scenarios_with_ai(
        self,
        countries: List[str],
        geo_risks: Dict[str, GeopoliticalRisk],
        osint_data: List[Dict],
        time_horizon: str
    ) -> Dict[str, Dict]:
        """Genera escenarios usando IA"""
        try:
            if not self.ai_service.client:
                return self._generate_scenarios_fallback(countries, geo_risks)
            
            context = f"Countries: {', '.join(countries)}\n"
            context += f"Time horizon: {time_horizon}\n"
            for country, risk in geo_risks.items():
                context += f"{country} risk score: {risk.overall_risk_score}\n"
            
            prompt = f"""Generate geopolitical scenarios for these countries:
{context}

Return JSON with three scenarios:
- best_case: optimistic scenario
- worst_case: pessimistic scenario
- base_case: most likely scenario

Each scenario should have:
- description: scenario description
- probability: probability percentage (0-100)
- key_events: list of key events
- impact: impact assessment

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are a geopolitical analyst. Generate scenarios and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            import json
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return self._generate_scenarios_fallback(countries, geo_risks)
        except Exception as e:
            logger.error(f"Error generating scenarios with AI: {e}")
            return self._generate_scenarios_fallback(countries, geo_risks)
    
    def _generate_scenarios_fallback(
        self,
        countries: List[str],
        geo_risks: Dict[str, GeopoliticalRisk]
    ) -> Dict[str, Dict]:
        """Genera escenarios sin IA (fallback)"""
        avg_risk = sum(r.overall_risk_score for r in geo_risks.values()) / len(geo_risks) if geo_risks else 50.0
        
        return {
            "best_case": {
                "description": "Stable relations and economic growth",
                "probability": 30,
                "key_events": ["Diplomatic engagement", "Trade agreements"],
                "impact": "positive"
            },
            "worst_case": {
                "description": "Escalation of tensions and economic disruption",
                "probability": 20,
                "key_events": ["Sanctions", "Trade restrictions"],
                "impact": "negative"
            },
            "base_case": {
                "description": "Continued current trends",
                "probability": 50,
                "key_events": ["Status quo maintained"],
                "impact": "neutral"
            }
        }
    
    async def _get_osint_data_for_regulations(
        self,
        country: str,
        industry: Optional[str],
        case_id: Optional[int]
    ) -> List[Dict]:
        """Obtiene datos OSINT sobre regulaciones"""
        query = select(OSINTResult).join(OSINTQuery)
        if case_id:
            query = query.where(OSINTQuery.case_id == case_id)
        
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if country.lower() in text.lower() and \
                   ("regulation" in text.lower() or "regulatory" in text.lower() or "policy" in text.lower()):
                    if not industry or industry.lower() in text.lower():
                        relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _analyze_regulatory_risk_with_ai(
        self,
        country: str,
        industry: Optional[str],
        geo_risk: Optional[GeopoliticalRisk],
        osint_data: List[Dict]
    ) -> Dict[str, Any]:
        """Analiza riesgo regulatorio con IA"""
        try:
            if not self.ai_service.client:
                return {"risk_level": "medium", "factors": []}
            
            context = f"Country: {country}\n"
            if industry:
                context += f"Industry: {industry}\n"
            if geo_risk:
                context += f"Geopolitical risk: {geo_risk.overall_risk_score}\n"
            
            prompt = f"""Analyze regulatory risk:
{context}

Return JSON with:
- risk_level: "low", "medium", or "high"
- factors: list of risk factors
- recommendations: list of recommendations

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are a regulatory risk analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            import json
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {"risk_level": "medium", "factors": []}
        except Exception as e:
            logger.error(f"Error analyzing regulatory risk with AI: {e}")
            return {"risk_level": "medium", "factors": []}
    
    def _extract_text_from_osint(self, data: Any) -> str:
        """Extrae texto de datos OSINT"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            text_parts = []
            for key in ["text", "content", "description", "title", "caption"]:
                if key in data and isinstance(data[key], str):
                    text_parts.append(data[key])
            return " ".join(text_parts)
        return ""

