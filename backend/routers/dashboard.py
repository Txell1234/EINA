"""
Dashboard router - Aggregated metrics and statistics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from app.database import get_db
from services.dashboard_service import DashboardService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/metrics")
async def get_dashboard_metrics(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all dashboard metrics"""
    try:
        service = DashboardService(db)
        metrics = await service.get_all_metrics(days, case_id=case_id)
        return metrics
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting dashboard metrics: {str(e)}"
        )

@router.get("/mentions")
async def get_total_mentions(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get total mentions count"""
    try:
        service = DashboardService(db)
        return await service.get_total_mentions(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting total mentions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting total mentions: {str(e)}"
        )

@router.get("/sentiment")
async def get_sentiment_score(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get sentiment score"""
    try:
        service = DashboardService(db)
        return await service.get_sentiment_score(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting sentiment score: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sentiment score: {str(e)}"
        )

@router.get("/reach")
async def get_estimated_reach(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get estimated reach"""
    try:
        service = DashboardService(db)
        return await service.get_estimated_reach(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting estimated reach: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting estimated reach: {str(e)}"
        )

@router.get("/engagement")
async def get_engagement_rate(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get engagement rate"""
    try:
        service = DashboardService(db)
        return await service.get_engagement_rate(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting engagement rate: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting engagement rate: {str(e)}"
        )

@router.get("/alerts")
async def get_critical_alerts(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get critical alerts count"""
    try:
        service = DashboardService(db)
        return await service.get_critical_alerts(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting critical alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting critical alerts: {str(e)}"
        )

@router.get("/trending-topics")
async def get_trending_topics(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics count"""
    try:
        service = DashboardService(db)
        return await service.get_trending_topics(days, case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trending topics: {str(e)}"
        )

@router.get("/sources")
async def get_data_sources(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get data sources with mention counts"""
    try:
        service = DashboardService(db)
        return await service.get_data_sources(case_id=case_id)
    except Exception as e:
        logger.error(f"Error getting data sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data sources: {str(e)}"
        )

@router.get("/alerts/feed")
async def get_alerts_feed(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recent critical alerts with details"""
    try:
        service = DashboardService(db)
        return await service.get_alerts_feed(days=days, case_id=case_id, limit=limit)
    except Exception as e:
        logger.error(f"Error getting alerts feed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting alerts feed: {str(e)}"
        )

@router.get("/trending-topics/list")
async def get_trending_topics_list(
    days: int = Query(7, ge=1, le=365),
    case_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get list of trending topics with counts and change"""
    try:
        service = DashboardService(db)
        return await service.get_trending_topics_list(days=days, case_id=case_id, limit=limit)
    except Exception as e:
        logger.error(f"Error getting trending topics list: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trending topics list: {str(e)}"
        )

