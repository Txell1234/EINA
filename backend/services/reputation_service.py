"""
Reputation Service - Gestión de reputación, cálculo de scores, detección de crisis y análisis de stakeholders
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.reputation import ReputationProfile, ReputationHistory, StakeholderAnalysis, EntityType, SentimentTrend, StakeholderType
from models.osint import OSINTResult, OSINTQuery
from models.ai_classification import AIClassification
from services.ai_service import AIService
from services.data_extraction_service import DataExtractionService
from integrations.news_api import NewsAPIService
from integrations.reddit_api import RedditAPIService
import logging

logger = logging.getLogger(__name__)

class ReputationService:
    """Servicio para gestión de reputación"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.extraction_service = DataExtractionService()
        self.news_api = NewsAPIService()
        self.reddit_api = RedditAPIService()
    
    async def calculate_reputation_score(
        self,
        entity_name: str,
        entity_type: EntityType,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calcula score de reputación agregado desde datos OSINT"""
        try:
            # Obtener o crear perfil
            profile = await self._get_or_create_profile(entity_name, entity_type, case_id)
            
            # Obtener datos OSINT relacionados
            osint_data = await self._get_osint_data_for_entity(entity_name, case_id)
            
            # Calcular score basado en sentimiento
            sentiment_score = await self._calculate_sentiment_score(osint_data)
            
            # Calcular score basado en engagement
            engagement_score = await self._calculate_engagement_score(osint_data)
            
            # Calcular score basado en menciones
            mentions_score = await self._calculate_mentions_score(osint_data)
            
            # Score agregado (ponderado)
            reputation_score = (
                sentiment_score * 0.5 +
                engagement_score * 0.3 +
                mentions_score * 0.2
            )
            
            # Limitar entre 0 y 100
            reputation_score = max(0.0, min(100.0, reputation_score))
            
            # Actualizar perfil
            old_score = profile.reputation_score
            profile.reputation_score = reputation_score
            profile.last_calculated = datetime.now()
            
            # Determinar tendencia
            if reputation_score > old_score + 5:
                profile.sentiment_trend = SentimentTrend.IMPROVING
            elif reputation_score < old_score - 5:
                profile.sentiment_trend = SentimentTrend.DETERIORATING
            else:
                profile.sentiment_trend = SentimentTrend.STABLE
            
            # Guardar histórico
            await self._save_history(profile, old_score, reputation_score, osint_data)
            
            await self.db.commit()
            
            return {
                "profile_id": profile.id,
                "reputation_score": reputation_score,
                "sentiment_trend": profile.sentiment_trend.value,
                "change": reputation_score - old_score
            }
            
        except Exception as e:
            logger.error(f"Error calculating reputation score: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def detect_crisis_indicators(
        self,
        entity_name: str,
        case_id: Optional[int] = None,
        fetch_fresh_data: bool = True
    ) -> Dict[str, Any]:
        """Detecta indicadores de crisis reputacional
        
        Args:
            entity_name: Nombre de la entidad
            case_id: ID del caso (opcional)
            fetch_fresh_data: Si True, obtiene datos frescos de APIs sociales cuando es necesario
        """
        try:
            profile = await self._get_profile_by_name(entity_name)
            if not profile:
                return {"crisis_indicators": [], "crisis_level": "none"}
            
            # Obtener datos recientes (últimas 24 horas)
            recent_data = await self._get_recent_osint_data(entity_name, case_id, hours=24)
            
            # Si fetch_fresh_data es True y hay pocos datos, obtener datos frescos de APIs
            if fetch_fresh_data and len(recent_data) < 5:
                fresh_data = await self._fetch_fresh_social_data(entity_name)
                recent_data.extend(fresh_data)
            
            crisis_indicators = []
            crisis_level = "none"
            
            # Detectar picos negativos de sentimiento
            negative_sentiment = await self._detect_negative_sentiment_spike(recent_data)
            if negative_sentiment:
                crisis_indicators.append({
                    "type": "negative_sentiment_spike",
                    "severity": negative_sentiment["severity"],
                    "description": negative_sentiment["description"]
                })
            
            # Detectar aumento de menciones negativas
            negative_mentions = await self._detect_negative_mentions_increase(recent_data)
            if negative_mentions:
                crisis_indicators.append({
                    "type": "negative_mentions_increase",
                    "severity": negative_mentions["severity"],
                    "description": negative_mentions["description"]
                })
            
            # Detectar influencers negativos
            negative_influencers = await self._detect_negative_influencers(recent_data)
            if negative_influencers:
                crisis_indicators.append({
                    "type": "negative_influencers",
                    "severity": negative_influencers["severity"],
                    "description": negative_influencers["description"]
                })
            
            # Determinar nivel de crisis
            if len(crisis_indicators) >= 3:
                crisis_level = "critical"
            elif len(crisis_indicators) >= 2:
                crisis_level = "high"
            elif len(crisis_indicators) >= 1:
                crisis_level = "medium"
            
            # Actualizar perfil
            profile.crisis_indicators = crisis_indicators
            if crisis_level in ["critical", "high"]:
                profile.sentiment_trend = SentimentTrend.CRISIS
            
            await self.db.commit()
            
            return {
                "crisis_indicators": crisis_indicators,
                "crisis_level": crisis_level,
                "profile_id": profile.id
            }
            
        except Exception as e:
            logger.error(f"Error detecting crisis indicators: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def analyze_stakeholder_sentiment(
        self,
        entity_name: str,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Análisis de sentimiento por stakeholder"""
        try:
            profile = await self._get_profile_by_name(entity_name)
            if not profile:
                return {"error": "Profile not found"}
            
            # Obtener datos OSINT
            osint_data = await self._get_osint_data_for_entity(entity_name, case_id)
            
            # Agrupar por tipo de stakeholder
            stakeholder_sentiment = {}
            
            for data_item in osint_data:
                # Detectar tipo de stakeholder desde los datos
                stakeholder_type = self._detect_stakeholder_type(data_item)
                
                if stakeholder_type not in stakeholder_sentiment:
                    stakeholder_sentiment[stakeholder_type] = {
                        "sentiment_scores": [],
                        "mentions": 0,
                        "engagement": 0
                    }
                
                # Extraer métricas
                metrics = self.extraction_service.extract_social_metrics(data_item)
                sentiment = metrics.get("sentiment", 0.0)
                
                stakeholder_sentiment[stakeholder_type]["sentiment_scores"].append(sentiment)
                stakeholder_sentiment[stakeholder_type]["mentions"] += 1
                stakeholder_sentiment[stakeholder_type]["engagement"] += metrics.get("engagement", 0)
            
            # Calcular promedios
            for st_type, data in stakeholder_sentiment.items():
                if data["sentiment_scores"]:
                    avg_sentiment = sum(data["sentiment_scores"]) / len(data["sentiment_scores"])
                    data["average_sentiment"] = avg_sentiment
                else:
                    data["average_sentiment"] = 0.0
            
            # Actualizar perfil
            profile.stakeholder_sentiment = stakeholder_sentiment
            
            await self.db.commit()
            
            return {
                "stakeholder_sentiment": stakeholder_sentiment,
                "profile_id": profile.id
            }
            
        except Exception as e:
            logger.error(f"Error analyzing stakeholder sentiment: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}
    
    async def track_reputation_trend(
        self,
        entity_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Seguimiento de tendencias de reputación"""
        try:
            profile = await self._get_profile_by_name(entity_name)
            if not profile:
                return {"error": "Profile not found"}
            
            # Obtener histórico
            cutoff_date = datetime.now() - timedelta(days=days)
            result = await self.db.execute(
                select(ReputationHistory)
                .where(
                    and_(
                        ReputationHistory.profile_id == profile.id,
                        ReputationHistory.timestamp >= cutoff_date
                    )
                )
                .order_by(ReputationHistory.timestamp.asc())
            )
            history = result.scalars().all()
            
            # Calcular tendencia
            if len(history) < 2:
                trend = "insufficient_data"
            else:
                first_score = history[0].score
                last_score = history[-1].score
                change = last_score - first_score
                
                if change > 10:
                    trend = "strongly_improving"
                elif change > 5:
                    trend = "improving"
                elif change < -10:
                    trend = "strongly_deteriorating"
                elif change < -5:
                    trend = "deteriorating"
                else:
                    trend = "stable"
            
            return {
                "trend": trend,
                "current_score": profile.reputation_score,
                "history": [
                    {
                        "timestamp": h.timestamp.isoformat(),
                        "score": h.score,
                        "change": h.score_change
                    }
                    for h in history
                ]
            }
            
        except Exception as e:
            logger.error(f"Error tracking reputation trend: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def generate_reputation_report(
        self,
        entity_name: str,
        case_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Genera informe completo de reputación"""
        try:
            profile = await self._get_profile_by_name(entity_name)
            if not profile:
                return {"error": "Profile not found"}
            
            # Calcular score actual
            score_data = await self.calculate_reputation_score(
                entity_name,
                profile.entity_type,
                case_id
            )
            
            # Detectar crisis
            crisis_data = await self.detect_crisis_indicators(entity_name, case_id)
            
            # Análisis de stakeholders
            stakeholder_data = await self.analyze_stakeholder_sentiment(entity_name, case_id)
            
            # Tendencias
            trend_data = await self.track_reputation_trend(entity_name)
            
            return {
                "entity_name": entity_name,
                "entity_type": profile.entity_type.value,
                "reputation_score": score_data.get("reputation_score", profile.reputation_score),
                "sentiment_trend": profile.sentiment_trend.value,
                "crisis_indicators": crisis_data.get("crisis_indicators", []),
                "crisis_level": crisis_data.get("crisis_level", "none"),
                "stakeholder_sentiment": stakeholder_data.get("stakeholder_sentiment", {}),
                "trend": trend_data.get("trend", "unknown"),
                "recommendations": await self._generate_recommendations(profile, crisis_data, stakeholder_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating reputation report: {e}", exc_info=True)
            return {"error": str(e)}
    
    # Métodos privados
    
    async def _get_or_create_profile(
        self,
        entity_name: str,
        entity_type: EntityType,
        case_id: Optional[int]
    ) -> ReputationProfile:
        """Obtiene o crea un perfil de reputación"""
        result = await self.db.execute(
            select(ReputationProfile)
            .where(
                and_(
                    ReputationProfile.entity_name == entity_name,
                    ReputationProfile.entity_type == entity_type
                )
            )
            .limit(1)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = ReputationProfile(
                entity_name=entity_name,
                entity_type=entity_type,
                case_id=case_id,
                reputation_score=50.0,
                sentiment_trend=SentimentTrend.STABLE
            )
            self.db.add(profile)
            await self.db.flush()
        
        return profile
    
    async def _get_profile_by_name(self, entity_name: str) -> Optional[ReputationProfile]:
        """Obtiene perfil por nombre"""
        result = await self.db.execute(
            select(ReputationProfile)
            .where(ReputationProfile.entity_name == entity_name)
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_osint_data_for_entity(
        self,
        entity_name: str,
        case_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Obtiene datos OSINT relacionados con la entidad"""
        query = select(OSINTResult).join(OSINTQuery)
        if case_id:
            query = query.where(OSINTQuery.case_id == case_id)
        
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        # Filtrar por nombre de entidad en los datos
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if entity_name.lower() in text.lower():
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _get_recent_osint_data(
        self,
        entity_name: str,
        case_id: Optional[int],
        hours: int
    ) -> List[Dict[str, Any]]:
        """Obtiene datos OSINT recientes"""
        cutoff = datetime.now() - timedelta(hours=hours)
        query = select(OSINTResult).join(OSINTQuery).where(OSINTResult.created_at >= cutoff)
        if case_id:
            query = query.where(OSINTQuery.case_id == case_id)
        
        result = await self.db.execute(query)
        osint_results = result.scalars().all()
        
        relevant_data = []
        for osint_result in osint_results:
            if osint_result.data:
                text = self._extract_text_from_osint(osint_result.data)
                if entity_name.lower() in text.lower():
                    relevant_data.append(osint_result.data)
        
        return relevant_data
    
    async def _calculate_sentiment_score(self, osint_data: List[Dict]) -> float:
        """Calcula score de sentimiento (0-100)"""
        if not osint_data:
            return 50.0
        
        sentiment_scores = []
        for data in osint_data:
            metrics = self.extraction_service.extract_sentiment_metrics(data)
            sentiment = metrics.get("sentiment", 0.0)
            # Convertir de -1 a 1 a 0 a 100
            score = (sentiment + 1) * 50
            sentiment_scores.append(score)
        
        if sentiment_scores:
            return sum(sentiment_scores) / len(sentiment_scores)
        return 50.0
    
    async def _calculate_engagement_score(self, osint_data: List[Dict]) -> float:
        """Calcula score de engagement (0-100)"""
        if not osint_data:
            return 50.0
        
        total_engagement = 0
        count = 0
        
        for data in osint_data:
            metrics = self.extraction_service.extract_social_media_metrics(data)
            engagement = metrics.get("total_engagement", 0)
            total_engagement += engagement
            count += 1
        
        if count == 0:
            return 50.0
        
        # Normalizar engagement (asumiendo que 10000+ es alto engagement)
        avg_engagement = total_engagement / count
        score = min(100.0, (avg_engagement / 10000) * 100)
        return score
    
    async def _calculate_mentions_score(self, osint_data: List[Dict]) -> float:
        """Calcula score basado en número de menciones"""
        mention_count = len(osint_data)
        # Normalizar (asumiendo que 100+ menciones es bueno)
        score = min(100.0, (mention_count / 100) * 100)
        return score
    
    async def _save_history(
        self,
        profile: ReputationProfile,
        old_score: float,
        new_score: float,
        osint_data: List[Dict]
    ):
        """Guarda histórico de cambios"""
        history = ReputationHistory(
            profile_id=profile.id,
            score=new_score,
            score_change=new_score - old_score,
            change_reason=f"Calculated from {len(osint_data)} OSINT sources"
        )
        self.db.add(history)
        await self.db.flush()
    
    async def _detect_negative_sentiment_spike(self, recent_data: List[Dict]) -> Optional[Dict]:
        """Detecta picos negativos de sentimiento"""
        if not recent_data:
            return None
        
        negative_count = 0
        for data in recent_data:
            metrics = self.extraction_service.extract_sentiment_metrics(data)
            sentiment = metrics.get("sentiment", 0.0)
            if sentiment < -0.5:
                negative_count += 1
        
        if negative_count > len(recent_data) * 0.3:  # Más del 30% negativo
            return {
                "severity": "high" if negative_count > len(recent_data) * 0.5 else "medium",
                "description": f"{negative_count} negative mentions detected in last 24h"
            }
        return None
    
    async def _detect_negative_mentions_increase(self, recent_data: List[Dict]) -> Optional[Dict]:
        """Detecta aumento de menciones negativas"""
        # Implementación simplificada
        return None
    
    async def _detect_negative_influencers(self, recent_data: List[Dict]) -> Optional[Dict]:
        """Detecta influencers con sentimiento negativo"""
        # Implementación simplificada
        return None
    
    def _detect_stakeholder_type(self, data: Dict) -> str:
        """Detecta tipo de stakeholder desde los datos"""
        # Implementación simplificada
        if isinstance(data, dict):
            source = data.get("source", "").lower()
            if "news" in source or "media" in source:
                return StakeholderType.MEDIA.value
            elif "twitter" in source or "instagram" in source:
                return StakeholderType.INFLUENCER.value
        
        return StakeholderType.COMMUNITY.value
    
    async def _fetch_fresh_social_data(self, entity_name: str) -> List[Dict[str, Any]]:
        """Obtiene datos frescos de APIs sociales (News API, Reddit)"""
        fresh_data = []
        
        try:
            # Obtener noticias recientes de News API
            news_result = await self.news_api.search(
                query=entity_name,
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
        
        try:
            # Obtener posts recientes de Reddit
            reddit_result = await self.reddit_api.search(
                query=entity_name,
                limit=10
            )
            
            if "data" in reddit_result and "children" in reddit_result["data"]:
                for post in reddit_result["data"]["children"][:10]:
                    post_data = post.get("data", {})
                    fresh_data.append({
                        "source": "reddit",
                        "title": post_data.get("title", ""),
                        "selftext": post_data.get("selftext", ""),
                        "score": post_data.get("score", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "created_utc": post_data.get("created_utc", 0),
                        "url": post_data.get("url", "")
                    })
        except Exception as e:
            logger.warning(f"Error fetching fresh Reddit data: {e}")
        
        return fresh_data
    
    def _extract_text_from_osint(self, data: Any) -> str:
        """Extrae texto de datos OSINT"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            text_parts = []
            for key in ["text", "content", "description", "title", "caption", "selftext"]:
                if key in data and isinstance(data[key], str):
                    text_parts.append(data[key])
            return " ".join(text_parts)
        return ""
    
    async def _generate_recommendations(
        self,
        profile: ReputationProfile,
        crisis_data: Dict,
        stakeholder_data: Dict
    ) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        if crisis_data.get("crisis_level") in ["critical", "high"]:
            recommendations.append("Activar protocolo de crisis inmediatamente")
            recommendations.append("Preparar comunicación de respuesta")
        
        if profile.reputation_score < 40:
            recommendations.append("Implementar estrategia de recuperación de reputación")
        
        stakeholder_sentiment = stakeholder_data.get("stakeholder_sentiment", {})
        for st_type, data in stakeholder_sentiment.items():
            if data.get("average_sentiment", 0) < -0.3:
                recommendations.append(f"Mejorar engagement con stakeholders tipo {st_type}")
        
        return recommendations

