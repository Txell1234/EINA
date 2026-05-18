"""
Dashboard Service - Aggregate metrics from all cases and classifications
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from models.case import Case
from models.osint import OSINTQuery, OSINTResult
from models.ai_classification import AIClassification
from models.ai_analysis import Concept
from services.data_extraction_service import DataExtractionService
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    """Service to aggregate dashboard metrics from all cases"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.extraction_service = DataExtractionService()
    
    async def get_total_mentions(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get total mentions count with change percentage"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)
            
            # Count OSINT results in current period
            current_query = (
                select(func.count(OSINTResult.id))
                .join(OSINTQuery)
                .where(OSINTResult.created_at >= cutoff_date)
            )
            if case_id:
                current_query = current_query.where(OSINTQuery.case_id == case_id)
            current_result = await self.db.execute(current_query)
            current_count = current_result.scalar() or 0
            
            # Count OSINT results in previous period
            previous_query = (
                select(func.count(OSINTResult.id))
                .join(OSINTQuery)
                .where(
                    and_(
                        OSINTResult.created_at >= previous_cutoff,
                        OSINTResult.created_at < cutoff_date
                    )
                )
            )
            if case_id:
                previous_query = previous_query.where(OSINTQuery.case_id == case_id)
            previous_result = await self.db.execute(previous_query)
            previous_count = previous_result.scalar() or 0
            
            # Calculate change percentage
            change_percent = 0
            if previous_count > 0:
                change_percent = ((current_count - previous_count) / previous_count) * 100
            elif current_count > 0:
                change_percent = 100  # New data
            
            return {
                "total_mentions": current_count,
                "change_percent": round(change_percent, 1),
                "previous_period": previous_count
            }
        except Exception as e:
            logger.error(f"Error getting total mentions: {e}", exc_info=True)
            return {"total_mentions": 0, "change_percent": 0, "previous_period": 0}
    
    async def get_sentiment_score(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get average sentiment score with change"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)
            
            # Get classifications in current period
            current_query = (
                select(
                    func.avg(AIClassification.sentiment_score).label("avg_score"),
                    func.count(AIClassification.id).label("count")
                )
                .where(AIClassification.created_at >= cutoff_date)
            )
            if case_id:
                current_query = current_query.where(AIClassification.case_id == case_id)
            current_result = await self.db.execute(current_query)
            current_row = current_result.first()
            current_avg = (current_row.avg_score or 0.0) if current_row else 0.0
            current_count = current_row.count or 0 if current_row else 0
            
            # Get classifications in previous period
            previous_query = (
                select(
                    func.avg(AIClassification.sentiment_score).label("avg_score")
                )
                .where(
                    and_(
                        AIClassification.created_at >= previous_cutoff,
                        AIClassification.created_at < cutoff_date
                    )
                )
            )
            if case_id:
                previous_query = previous_query.where(AIClassification.case_id == case_id)
            previous_result = await self.db.execute(previous_query)
            previous_row = previous_result.first()
            previous_avg = (previous_row.avg_score or 0.0) if previous_row else 0.0
            
            # Convert to 0-100 scale (from -1 to 1)
            current_score = ((current_avg + 1) / 2) * 100
            previous_score = ((previous_avg + 1) / 2) * 100
            
            # Calculate change in points
            change_points = current_score - previous_score
            
            return {
                "sentiment_score": round(current_score, 1),
                "change_points": round(change_points, 1),
                "total_classifications": current_count
            }
        except Exception as e:
            logger.error(f"Error getting sentiment score: {e}", exc_info=True)
            return {"sentiment_score": 0, "change_points": 0, "total_classifications": 0}
    
    async def get_estimated_reach(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get estimated reach (sum of views + followers)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)
            
            # Get OSINT results with view counts
            results_query = (
                select(OSINTResult)
                .join(OSINTQuery)
                .where(OSINTResult.created_at >= cutoff_date)
            )
            if case_id:
                results_query = results_query.where(OSINTQuery.case_id == case_id)
            results_result = await self.db.execute(results_query)
            results = results_result.scalars().all()
            
            current_reach = 0
            for result in results:
                if result.data and isinstance(result.data, dict):
                    # Extract view_count from data
                    data = result.data
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            if isinstance(item, dict):
                                view_count = item.get("view_count", 0) or 0
                                follower_count = 0
                                if "user" in item and isinstance(item["user"], dict):
                                    follower_count = item["user"].get("follower_count", 0) or 0
                                current_reach += view_count + follower_count
            
            # Previous period
            previous_results_query = (
                select(OSINTResult)
                .join(OSINTQuery)
                .where(
                    and_(
                        OSINTResult.created_at >= previous_cutoff,
                        OSINTResult.created_at < cutoff_date
                    )
                )
            )
            if case_id:
                previous_results_query = previous_results_query.where(OSINTQuery.case_id == case_id)
            previous_results_result = await self.db.execute(previous_results_query)
            previous_results = previous_results_result.scalars().all()
            
            previous_reach = 0
            for result in previous_results:
                if result.data and isinstance(result.data, dict):
                    data = result.data
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            if isinstance(item, dict):
                                view_count = item.get("view_count", 0) or 0
                                follower_count = 0
                                if "user" in item and isinstance(item["user"], dict):
                                    follower_count = item["user"].get("follower_count", 0) or 0
                                previous_reach += view_count + follower_count
            
            # Calculate change
            change_percent = 0
            if previous_reach > 0:
                change_percent = ((current_reach - previous_reach) / previous_reach) * 100
            elif current_reach > 0:
                change_percent = 100
            
            # Format as millions/thousands
            if current_reach >= 1000000:
                formatted_reach = f"{current_reach / 1000000:.1f}M"
            elif current_reach >= 1000:
                formatted_reach = f"{current_reach / 1000:.1f}K"
            else:
                formatted_reach = str(current_reach)
            
            return {
                "estimated_reach": current_reach,
                "formatted_reach": formatted_reach,
                "change_percent": round(change_percent, 1)
            }
        except Exception as e:
            logger.error(f"Error getting estimated reach: {e}", exc_info=True)
            return {"estimated_reach": 0, "formatted_reach": "0", "change_percent": 0}
    
    async def get_engagement_rate(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get average engagement rate"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get OSINT results
            results_query = (
                select(OSINTResult)
                .join(OSINTQuery)
                .where(OSINTResult.created_at >= cutoff_date)
            )
            if case_id:
                results_query = results_query.where(OSINTQuery.case_id == case_id)
            results_result = await self.db.execute(results_query)
            results = results_result.scalars().all()
            
            total_engagement = 0
            total_views = 0
            
            for result in results:
                if result.data and isinstance(result.data, dict):
                    data = result.data
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            if isinstance(item, dict):
                                likes = item.get("like_count", 0) or 0
                                comments = item.get("comment_count", 0) or 0
                                shares = item.get("share_count", 0) or 0
                                views = item.get("view_count", 0) or 0
                                
                                total_engagement += likes + comments + shares
                                total_views += views
            
            # Calculate engagement rate
            engagement_rate = 0
            if total_views > 0:
                engagement_rate = (total_engagement / total_views) * 100
            
            return {
                "engagement_rate": round(engagement_rate, 2),
                "total_engagement": total_engagement,
                "total_views": total_views
            }
        except Exception as e:
            logger.error(f"Error getting engagement rate: {e}", exc_info=True)
            return {"engagement_rate": 0, "total_engagement": 0, "total_views": 0}
    
    async def get_critical_alerts(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get count of critical alerts (high-risk predictions)"""
        try:
            from models.ai_analysis import AIPrediction
            
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)
            
            # Count high-confidence risk predictions
            current_query = (
                select(func.count(AIPrediction.id))
                .join(AIAnalysis, AIPrediction.analysis_id == AIAnalysis.id)
                .where(
                    and_(
                        AIPrediction.prediction_type == "risk",
                        AIPrediction.confidence_percentage >= 70,
                        AIPrediction.created_at >= cutoff_date
                    )
                )
            )
            if case_id:
                current_query = current_query.where(AIAnalysis.case_id == case_id)
            current_result = await self.db.execute(current_query)
            current_count = current_result.scalar() or 0
            
            # Previous period
            previous_query = (
                select(func.count(AIPrediction.id))
                .join(AIAnalysis, AIPrediction.analysis_id == AIAnalysis.id)
                .where(
                    and_(
                        AIPrediction.prediction_type == "risk",
                        AIPrediction.confidence_percentage >= 70,
                        AIPrediction.created_at >= previous_cutoff,
                        AIPrediction.created_at < cutoff_date
                    )
                )
            )
            if case_id:
                previous_query = previous_query.where(AIAnalysis.case_id == case_id)
            previous_result = await self.db.execute(previous_query)
            previous_count = previous_result.scalar() or 0
            
            change = current_count - previous_count
            
            return {
                "critical_alerts": current_count,
                "change": change,
                "previous_period": previous_count
            }
        except Exception as e:
            logger.error(f"Error getting critical alerts: {e}", exc_info=True)
            return {"critical_alerts": 0, "change": 0, "previous_period": 0}
    
    async def get_trending_topics(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get count of unique trending topics"""
        try:
            from models.ai_analysis import Concept
            
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)
            
            from models.ai_analysis import AIAnalysis
            
            from models.ai_analysis import AIAnalysis
            
            from models.ai_analysis import AIAnalysis
            
            # Count unique concepts (Concept model uses 'concept_name' field)
            current_query = (
                select(func.count(func.distinct(Concept.concept_name)))
                .join(AIAnalysis, Concept.analysis_id == AIAnalysis.id)
                .where(Concept.created_at >= cutoff_date)
            )
            if case_id:
                current_query = current_query.where(AIAnalysis.case_id == case_id)
            current_result = await self.db.execute(current_query)
            current_count = current_result.scalar() or 0
            
            # Previous period
            previous_query = (
                select(func.count(func.distinct(Concept.concept_name)))
                .join(AIAnalysis, Concept.analysis_id == AIAnalysis.id)
                .where(
                    and_(
                        Concept.created_at >= previous_cutoff,
                        Concept.created_at < cutoff_date
                    )
                )
            )
            if case_id:
                previous_query = previous_query.where(AIAnalysis.case_id == case_id)
            previous_result = await self.db.execute(previous_query)
            previous_count = previous_result.scalar() or 0
            
            change = current_count - previous_count
            
            return {
                "trending_topics": current_count,
                "change": change,
                "previous_period": previous_count
            }
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}", exc_info=True)
            return {"trending_topics": 0, "change": 0, "previous_period": 0}
    
    async def get_data_sources(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get data sources with mention counts"""
        try:
            # Group OSINT queries by type
            sources_query = (
                select(
                    OSINTQuery.query_type,
                    func.count(OSINTResult.id).label("mentions")
                )
                .join(OSINTResult)
                .group_by(OSINTQuery.query_type)
                .order_by(func.count(OSINTResult.id).desc())
            )
            if case_id:
                sources_query = sources_query.where(OSINTQuery.case_id == case_id)
            result = await self.db.execute(sources_query)
            
            sources = []
            source_mapping = {
                "ensembledata_instagram": "Xarxes Socials",
                "ensembledata_tiktok": "Xarxes Socials",
                "ensembledata_youtube": "Xarxes Socials",
                "ensembledata_threads": "Xarxes Socials",
                "ensembledata_twitter": "Xarxes Socials",
                "ensembledata_reddit": "Fòrums i Blogs",
                "google_news": "Mitjans Digitals",
                "reddit": "Fòrums i Blogs",
                "github": "Fòrums i Blogs"
            }
            
            for row in result.all():
                query_type = row.query_type
                mentions = row.mentions
                
                # Determine source category
                source_category = "Altres"
                for key, category in source_mapping.items():
                    if key in query_type.lower():
                        source_category = category
                        break
                
                sources.append({
                    "name": query_type,
                    "category": source_category,
                    "mentions": mentions,
                    "is_active": True
                })
            
            # Aggregate by category
            aggregated = {}
            for source in sources:
                category = source["category"]
                if category not in aggregated:
                    aggregated[category] = {
                        "name": category,
                        "mentions": 0,
                        "is_active": True
                    }
                aggregated[category]["mentions"] += source["mentions"]
            
            return list(aggregated.values())
        except Exception as e:
            logger.error(f"Error getting data sources: {e}", exc_info=True)
            return []
    
    async def get_all_metrics(self, days: int = 7, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get all dashboard metrics at once"""
        try:
            mentions = await self.get_total_mentions(days, case_id=case_id)
            sentiment = await self.get_sentiment_score(days, case_id=case_id)
            reach = await self.get_estimated_reach(days, case_id=case_id)
            engagement = await self.get_engagement_rate(days, case_id=case_id)
            alerts = await self.get_critical_alerts(days, case_id=case_id)
            topics = await self.get_trending_topics(days, case_id=case_id)
            sources = await self.get_data_sources(case_id=case_id)
            
            return {
                "total_mentions": mentions,
                "sentiment_score": sentiment,
                "estimated_reach": reach,
                "engagement_rate": engagement,
                "critical_alerts": alerts,
                "trending_topics": topics,
                "data_sources": sources,
                "period_days": days,
                "case_id": case_id
            }
        except Exception as e:
            logger.error(f"Error getting all metrics: {e}", exc_info=True)
            return {}

    async def get_alerts_feed(
        self,
        days: int = 7,
        case_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent critical alerts with context"""
        try:
            from models.ai_analysis import AIPrediction, AIAnalysis

            cutoff_date = datetime.now() - timedelta(days=days)
            alerts_query = (
                select(AIPrediction, AIAnalysis)
                .join(AIAnalysis, AIPrediction.analysis_id == AIAnalysis.id)
                .where(
                    and_(
                        AIPrediction.prediction_type == "risk",
                        AIPrediction.created_at >= cutoff_date
                    )
                )
                .order_by(AIPrediction.created_at.desc())
                .limit(limit)
            )
            if case_id:
                alerts_query = alerts_query.where(AIAnalysis.case_id == case_id)

            result = await self.db.execute(alerts_query)
            alerts = []
            for prediction, analysis in result.all():
                confidence = prediction.confidence_percentage or 0
                level = "high" if confidence >= 80 else "medium" if confidence >= 60 else "low"
                alerts.append({
                    "id": prediction.id,
                    "title": prediction.prediction_text[:120],
                    "confidence": confidence,
                    "level": level,
                    "prediction_type": prediction.prediction_type,
                    "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
                    "case_id": analysis.case_id
                })
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts feed: {e}", exc_info=True)
            return []

    async def get_trending_topics_list(
        self,
        days: int = 7,
        case_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top trending topics with change over previous period"""
        try:
            from models.ai_analysis import AIAnalysis
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days * 2)

            current_query = (
                select(Concept.concept_name, func.count(Concept.id).label("mentions"))
                .join(AIAnalysis, Concept.analysis_id == AIAnalysis.id)
                .where(Concept.created_at >= cutoff_date)
                .group_by(Concept.concept_name)
                .order_by(func.count(Concept.id).desc())
                .limit(limit)
            )
            if case_id:
                current_query = current_query.where(AIAnalysis.case_id == case_id)
            current_result = await self.db.execute(current_query)
            current_topics = current_result.all()

            previous_query = (
                select(Concept.concept_name, func.count(Concept.id).label("mentions"))
                .join(AIAnalysis, Concept.analysis_id == AIAnalysis.id)
                .where(
                    and_(
                        Concept.created_at >= previous_cutoff,
                        Concept.created_at < cutoff_date
                    )
                )
                .group_by(Concept.concept_name)
            )
            if case_id:
                previous_query = previous_query.where(AIAnalysis.case_id == case_id)
            previous_result = await self.db.execute(previous_query)
            previous_counts = {row.concept_name: row.mentions for row in previous_result.all()}

            topics = []
            for row in current_topics:
                previous_mentions = previous_counts.get(row.concept_name, 0)
                change_percent = 0.0
                if previous_mentions > 0:
                    change_percent = ((row.mentions - previous_mentions) / previous_mentions) * 100
                elif row.mentions > 0:
                    change_percent = 100.0
                topics.append({
                    "topic": row.concept_name,
                    "mentions": row.mentions,
                    "change_percent": round(change_percent, 1)
                })
            return topics
        except Exception as e:
            logger.error(f"Error getting trending topics list: {e}", exc_info=True)
            return []
