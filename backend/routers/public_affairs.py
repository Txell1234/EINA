"""
Public Affairs router - Análisis de políticas, stakeholders y advocacy
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.public_affairs_service import PublicAffairsService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public-affairs", tags=["Public Affairs"])

@router.get("/policies")
async def list_policies(
    case_id: Optional[int] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista análisis de políticas"""
    try:
        from sqlalchemy import select, and_
        from models.public_affairs import PolicyAnalysis
        
        query = select(PolicyAnalysis)
        conditions = []
        
        if case_id:
            conditions.append(PolicyAnalysis.case_id == case_id)
        if jurisdiction:
            conditions.append(PolicyAnalysis.jurisdiction == jurisdiction)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(PolicyAnalysis.impact_score.desc()))
        policies = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "policy_topic": p.policy_topic,
                "jurisdiction": p.jurisdiction,
                "impact_score": p.impact_score,
                "impact_level": p.impact_level.value
            }
            for p in policies
        ]
    except Exception as e:
        logger.error(f"Error listing policies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing policies: {str(e)}"
        )

@router.get("/stakeholders")
async def get_stakeholders(
    case_id: int = Query(...),
    policy_topic: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene stakeholders identificados"""
    try:
        service = PublicAffairsService(db)
        result = await service.identify_stakeholders(case_id, policy_topic)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stakeholders: {str(e)}"
        )

@router.post("/analyze-impact")
async def analyze_policy_impact(
    policy_topic: str = Query(...),
    jurisdiction: str = Query(...),
    case_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Analiza impacto de una política"""
    try:
        service = PublicAffairsService(db)
        result = await service.analyze_policy_impact(policy_topic, jurisdiction, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing policy impact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing impact: {str(e)}"
        )

@router.get("/advocacy-opportunities")
async def get_advocacy_opportunities(
    case_id: int = Query(...),
    policy_topic: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene oportunidades de advocacy"""
    try:
        service = PublicAffairsService(db)
        result = await service.track_advocacy_opportunities(case_id, policy_topic)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting advocacy opportunities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting opportunities: {str(e)}"
        )

@router.post("/campaigns")
async def create_campaign(
    campaign_name: str = Query(...),
    case_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Crea una campaña de advocacy"""
    try:
        from models.public_affairs import AdvocacyCampaign, CampaignStatus
        
        campaign = AdvocacyCampaign(
            case_id=case_id,
            campaign_name=campaign_name,
            status=CampaignStatus.PLANNING
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        
        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.campaign_name,
            "status": campaign.status.value
        }
    except Exception as e:
        logger.error(f"Error creating campaign: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating campaign: {str(e)}"
        )

@router.get("/campaigns/{campaign_id}/effectiveness")
async def get_campaign_effectiveness(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mide efectividad de una campaña"""
    try:
        service = PublicAffairsService(db)
        result = await service.measure_campaign_effectiveness(campaign_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error measuring campaign effectiveness: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error measuring effectiveness: {str(e)}"
        )
