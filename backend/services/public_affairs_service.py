"""
Public Affairs Service - Análisis de políticas, stakeholders y advocacy
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.public_affairs import PolicyAnalysis, AdvocacyCampaign, PolicyImpactLevel, CampaignStatus
from models.osint import OSINTResult, OSINTQuery
from services.ai_service import AIService
from integrations.news_api import NewsAPIService
import logging

logger = logging.getLogger(__name__)

class PublicAffairsService:
    """Servicio para análisis de asuntos públicos"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.news_api = NewsAPIService()
    
    async def analyze_policy_impact(
        self,
        policy_topic: str,
        jurisdiction: str,
        case_id: int,
        fetch_fresh_data: bool = True
    ) -> Dict[str, Any]:
        """Analiza el impacto de una política
        
        Args:
            policy_topic: Tema de la política
            jurisdiction: Jurisdicción
            case_id: ID del caso
            fetch_fresh_data: Si True, obtiene datos frescos de APIs de noticias cuando es necesario
        """
        try:
            # Buscar política existente o crear nueva
            result = await self.db.execute(
                select(PolicyAnalysis)
                .where(
                    and_(
                        PolicyAnalysis.policy_topic.ilike(f"%{policy_topic}%"),
                        PolicyAnalysis.jurisdiction == jurisdiction,
                        PolicyAnalysis.case_id == case_id
                    )
                )
                .limit(1)
            )
            policy = result.scalar_one_or_none()
            
            if not policy:
                policy = PolicyAnalysis(
                    case_id=case_id,
                    policy_topic=policy_topic,
                    jurisdiction=jurisdiction,
                    impact_score=0.0
                )
                self.db.add(policy)
                await self.db.flush()
            
            # Obtener datos OSINT relacionados
            osint_data = await self._get_osint_data_for_policy(policy_topic, jurisdiction, case_id)
            
            # Si fetch_fresh_data es True y hay pocos datos, obtener datos frescos de APIs
            if fetch_fresh_data and len(osint_data) < 5:
                fresh_data = await self._fetch_fresh_news_data(policy_topic, jurisdiction)
                osint_data.extend(fresh_data)
            
            # Analizar impacto con IA
            impact_analysis = await self._analyze_impact_with_ai(policy_topic, jurisdiction, osint_data)
            
            # Calcular score de impacto
            impact_score = self._calculate_impact_score(impact_analysis)
            
            # Identificar posiciones de stakeholders
            stakeholder_positions = await self._identify_stakeholder_positions(osint_data, policy_topic)
            
            # Identificar oportunidades de advocacy
            advocacy_opportunities = await self._identify_advocacy_opportunities(stakeholder_positions, impact_analysis)
            
            # Actualizar política
            policy.impact_score = impact_score
            policy.impact_level = self._determine_impact_level(impact_score)
            policy.stakeholder_positions = stakeholder_positions
            policy.advocacy_opportunities = advocacy_opportunities
            policy.impact_analysis = impact_analysis
            
            await self.db.commit()
            
            return {
                "policy_id": policy.id,
                "policy_topic": policy_topic,
                "jurisdiction": jurisdiction,
                "impact_score": impact_score,
                "impact_level": policy.impact_level.value,
                "stakeholder_positions": stakeholder_positions,
                "advocacy_opportunities": advocacy_opportunities
            }
            
        except Exception as e:
            logger.error(f"Error analyzing policy impact: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def identify_stakeholders(
        self,
        case_id: int,
        policy_topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Identifica stakeholders clave"""
        try:
            # Obtener datos OSINT del caso
            query = select(OSINTResult).join(OSINTQuery).where(OSINTQuery.case_id == case_id)
            if policy_topic:
                # Filtrar por tema de política si se especifica
                pass  # Implementar filtrado si es necesario
            
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            stakeholders = {}
            
            for osint_result in osint_results:
                if not osint_result.data:
                    continue
                
                # Extraer información de stakeholders
                stakeholder_info = await self._extract_stakeholder_info(osint_result.data)
                
                for st_name, st_data in stakeholder_info.items():
                    if st_name not in stakeholders:
                        stakeholders[st_name] = {
                            "name": st_name,
                            "type": st_data.get("type", "unknown"),
                            "influence": st_data.get("influence", 0.0),
                            "sentiment": st_data.get("sentiment", 0.0),
                            "mentions": 0,
                            "platforms": set()
                        }
                    
                    stakeholders[st_name]["mentions"] += 1
                    if "platform" in st_data:
                        stakeholders[st_name]["platforms"].add(st_data["platform"])
            
            # Convertir sets a listas
            for st in stakeholders.values():
                st["platforms"] = list(st["platforms"])
            
            return {
                "stakeholders": list(stakeholders.values()),
                "total_identified": len(stakeholders)
            }
            
        except Exception as e:
            logger.error(f"Error identifying stakeholders: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def track_advocacy_opportunities(
        self,
        case_id: int,
        policy_topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rastrea oportunidades de advocacy"""
        try:
            # Obtener análisis de políticas
            query = select(PolicyAnalysis).where(PolicyAnalysis.case_id == case_id)
            if policy_topic:
                query = query.where(PolicyAnalysis.policy_topic.ilike(f"%{policy_topic}%"))
            
            result = await self.db.execute(query)
            policies = result.scalars().all()
            
            opportunities = []
            
            for policy in policies:
                if policy.advocacy_opportunities:
                    for opp in policy.advocacy_opportunities:
                        opportunities.append({
                            "policy_topic": policy.policy_topic,
                            "jurisdiction": policy.jurisdiction,
                            "opportunity": opp,
                            "impact_score": policy.impact_score
                        })
            
            return {
                "opportunities": opportunities,
                "total": len(opportunities)
            }
            
        except Exception as e:
            logger.error(f"Error tracking advocacy opportunities: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def measure_campaign_effectiveness(
        self,
        campaign_id: int
    ) -> Dict[str, Any]:
        """Mide la efectividad de una campaña de advocacy"""
        try:
            result = await self.db.execute(
                select(AdvocacyCampaign).where(AdvocacyCampaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                return {"error": "Campaign not found"}
            
            # Obtener métricas actuales desde OSINT
            osint_data = await self._get_osint_data_for_campaign(campaign)
            
            # Calcular métricas
            current_metrics = await self._calculate_campaign_metrics(osint_data, campaign)
            
            # Comparar con métricas objetivo
            effectiveness = self._calculate_effectiveness(campaign.success_metrics, current_metrics)
            
            # Actualizar campaña
            campaign.current_metrics = current_metrics
            await self.db.commit()
            
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.campaign_name,
                "current_metrics": current_metrics,
                "target_metrics": campaign.success_metrics,
                "effectiveness": effectiveness
            }
            
        except Exception as e:
            logger.error(f"Error measuring campaign effectiveness: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    # Métodos privados
    
    async def _get_osint_data_for_policy(
        self,
        policy_topic: str,
        jurisdiction: str,
        case_id: int
    ) -> List[Dict]:
        """Obtiene datos OSINT relacionados con la política"""
        query = select(OSINTResult).join(OSINTQuery).where(OSINTQuery.case_id == case_id)
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if policy_topic.lower() in text.lower() or jurisdiction.lower() in text.lower():
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _analyze_impact_with_ai(
        self,
        policy_topic: str,
        jurisdiction: str,
        osint_data: List[Dict]
    ) -> Dict[str, Any]:
        """Analiza impacto usando IA"""
        try:
            if not self.ai_service.client:
                return {"impact": "unknown", "factors": []}
            
            # Preparar contexto
            context = f"Policy topic: {policy_topic}\nJurisdiction: {jurisdiction}\n"
            context += f"OSINT data points: {len(osint_data)}\n"
            
            prompt = f"""Analyze the impact of this policy:
{context}

Return JSON with:
- impact: "high", "medium", or "low"
- factors: list of impact factors
- affected_groups: list of groups affected
- economic_impact: estimated economic impact
- social_impact: estimated social impact

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are a public affairs expert. Analyze policy impact and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            import json
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {"impact": "unknown", "factors": []}
        except Exception as e:
            logger.error(f"Error in AI impact analysis: {e}")
            return {"impact": "unknown", "factors": []}
    
    def _calculate_impact_score(self, impact_analysis: Dict) -> float:
        """Calcula score de impacto (0-100)"""
        impact_level = impact_analysis.get("impact", "low")
        if impact_level == "high":
            return 75.0
        elif impact_level == "medium":
            return 50.0
        else:
            return 25.0
    
    async def _identify_stakeholder_positions(
        self,
        osint_data: List[Dict],
        policy_topic: str
    ) -> Dict[str, Dict]:
        """Identifica posiciones de stakeholders"""
        positions = {}
        
        # Análisis simplificado - en producción usar IA
        for data in osint_data:
            # Extraer stakeholders y sus posiciones
            # Implementación simplificada
            pass
        
        return positions
    
    async def _identify_advocacy_opportunities(
        self,
        stakeholder_positions: Dict,
        impact_analysis: Dict
    ) -> List[Dict]:
        """Identifica oportunidades de advocacy"""
        opportunities = []
        
        # Si hay stakeholders con posiciones neutrales o positivas, hay oportunidad
        for st_name, position in stakeholder_positions.items():
            if position.get("position") in ["neutral", "support"]:
                opportunities.append({
                    "stakeholder": st_name,
                    "opportunity": "Engage for support",
                    "priority": "medium"
                })
        
        return opportunities
    
    def _determine_impact_level(self, impact_score: float) -> PolicyImpactLevel:
        """Determina nivel de impacto"""
        if impact_score >= 75:
            return PolicyImpactLevel.CRITICAL
        elif impact_score >= 50:
            return PolicyImpactLevel.HIGH
        elif impact_score >= 25:
            return PolicyImpactLevel.MEDIUM
        else:
            return PolicyImpactLevel.LOW
    
    async def _extract_stakeholder_info(self, data: Any) -> Dict[str, Dict]:
        """Extrae información de stakeholders desde datos OSINT"""
        stakeholders = {}
        
        # Implementación simplificada
        if isinstance(data, dict):
            author = data.get("author") or data.get("user") or data.get("source")
            if author:
                stakeholders[author] = {
                    "type": "influencer",
                    "influence": 0.5,
                    "sentiment": 0.0,
                    "platform": data.get("platform", "unknown")
                }
        
        return stakeholders
    
    async def _get_osint_data_for_campaign(self, campaign: AdvocacyCampaign) -> List[Dict]:
        """Obtiene datos OSINT relacionados con la campaña"""
        query = select(OSINTResult).join(OSINTQuery).where(OSINTQuery.case_id == campaign.case_id)
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if campaign.campaign_name.lower() in text.lower():
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _calculate_campaign_metrics(
        self,
        osint_data: List[Dict],
        campaign: AdvocacyCampaign
    ) -> Dict[str, Any]:
        """Calcula métricas de campaña"""
        return {
            "awareness": len(osint_data),
            "support": 0,  # Simplificado
            "engagement": 0  # Simplificado
        }
    
    def _calculate_effectiveness(
        self,
        target_metrics: Dict,
        current_metrics: Dict
    ) -> Dict[str, Any]:
        """Calcula efectividad comparando métricas"""
        effectiveness = {}
        
        for metric, target_value in target_metrics.items():
            current_value = current_metrics.get(metric, 0)
            if target_value > 0:
                effectiveness[metric] = {
                    "current": current_value,
                    "target": target_value,
                    "percentage": min(100, (current_value / target_value) * 100)
                }
        
        return effectiveness
    
    async def _fetch_fresh_news_data(self, policy_topic: str, jurisdiction: str) -> List[Dict]:
        """Obtiene datos frescos de APIs de noticias sobre la política"""
        fresh_data = []
        
        try:
            # Buscar noticias sobre el tema de política
            query = f"{policy_topic} {jurisdiction}"
            news_result = await self.news_api.search(
                query=query,
                language="es",
                sort_by="publishedAt"
            )
            
            if news_result.get("status") == "ok" and "articles" in news_result:
                for article in news_result["articles"][:10]:  # Limitar a 10 artículos
                    fresh_data.append({
                        "source": "news_api",
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "publishedAt": article.get("publishedAt", ""),
                        "url": article.get("url", "")
                    })
        except Exception as e:
            logger.warning(f"Error fetching fresh news data: {e}")
        
        return fresh_data
    
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

