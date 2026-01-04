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
    db: AsyncSession = Depends(get_db)
):
    """Get all dashboard metrics"""
    try:
        service = DashboardService(db)
        metrics = await service.get_all_metrics(days)
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
    db: AsyncSession = Depends(get_db)
):
    """Get total mentions count"""
    try:
        service = DashboardService(db)
        return await service.get_total_mentions(days)
    except Exception as e:
        logger.error(f"Error getting total mentions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting total mentions: {str(e)}"
        )

@router.get("/sentiment")
async def get_sentiment_score(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get sentiment score"""
    try:
        service = DashboardService(db)
        return await service.get_sentiment_score(days)
    except Exception as e:
        logger.error(f"Error getting sentiment score: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sentiment score: {str(e)}"
        )

@router.get("/reach")
async def get_estimated_reach(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get estimated reach"""
    try:
        service = DashboardService(db)
        return await service.get_estimated_reach(days)
    except Exception as e:
        logger.error(f"Error getting estimated reach: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting estimated reach: {str(e)}"
        )

@router.get("/engagement")
async def get_engagement_rate(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get engagement rate"""
    try:
        service = DashboardService(db)
        return await service.get_engagement_rate(days)
    except Exception as e:
        logger.error(f"Error getting engagement rate: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting engagement rate: {str(e)}"
        )

@router.get("/alerts")
async def get_critical_alerts(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get critical alerts count"""
    try:
        service = DashboardService(db)
        return await service.get_critical_alerts(days)
    except Exception as e:
        logger.error(f"Error getting critical alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting critical alerts: {str(e)}"
        )

@router.get("/trending-topics")
async def get_trending_topics(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics count"""
    try:
        service = DashboardService(db)
        return await service.get_trending_topics(days)
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trending topics: {str(e)}"
        )

@router.get("/sources")
async def get_data_sources(
    db: AsyncSession = Depends(get_db)
):
    """Get data sources with mention counts"""
    try:
        service = DashboardService(db)
        return await service.get_data_sources()
    except Exception as e:
        logger.error(f"Error getting data sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data sources: {str(e)}"
        )



