"""
Reputation router - Gestión de reputación, scores, histórico y crisis
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.database import get_db
from services.reputation_service import ReputationService
from models.reputation import ReputationProfile, ReputationHistory, StakeholderAnalysis, EntityType
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reputation", tags=["Reputation"])

# Schemas
class ReputationProfileResponse(BaseModel):
    id: int
    entity_type: str
    entity_name: str
    reputation_score: float
    sentiment_trend: str
    
    class Config:
        from_attributes = True

class ReputationHistoryResponse(BaseModel):
    id: int
    timestamp: str
    score: float
    score_change: float
    change_reason: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/profiles")
async def list_reputation_profiles(
    case_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista perfiles de reputación"""
    try:
        from sqlalchemy import select, and_
        
        query = select(ReputationProfile)
        conditions = []
        
        if case_id:
            conditions.append(ReputationProfile.case_id == case_id)
        if entity_type:
            try:
                conditions.append(ReputationProfile.entity_type == EntityType(entity_type))
            except ValueError:
                pass
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(ReputationProfile.reputation_score.desc()))
        profiles = result.scalars().all()
        
        return [ReputationProfileResponse.model_validate(p) for p in profiles]
    except Exception as e:
        logger.error(f"Error listing reputation profiles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing profiles: {str(e)}"
        )

@router.get("/{entity_name}/score")
async def get_reputation_score(
    entity_name: str,
    entity_type: str = Query("company"),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene score de reputación"""
    try:
        service = ReputationService(db)
        try:
            entity_type_enum = EntityType(entity_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity_type: {entity_type}"
            )
        
        result = await service.calculate_reputation_score(
            entity_name=entity_name,
            entity_type=entity_type_enum,
            case_id=case_id
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reputation score: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting score: {str(e)}"
        )

@router.get("/{entity_name}/history")
async def get_reputation_history(
    entity_name: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene histórico de reputación"""
    try:
        service = ReputationService(db)
        result = await service.track_reputation_trend(entity_name, days)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reputation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting history: {str(e)}"
        )

@router.get("/{entity_name}/crisis-indicators")
async def get_crisis_indicators(
    entity_name: str,
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene indicadores de crisis"""
    try:
        service = ReputationService(db)
        result = await service.detect_crisis_indicators(entity_name, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting crisis indicators: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting crisis indicators: {str(e)}"
        )

@router.post("/analyze")
async def analyze_reputation(
    entity_name: str = Query(...),
    entity_type: str = Query("company"),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Analiza reputación completa"""
    try:
        service = ReputationService(db)
        try:
            entity_type_enum = EntityType(entity_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity_type: {entity_type}"
            )
        
        result = await service.generate_reputation_report(entity_name, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing reputation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing reputation: {str(e)}"
        )

@router.get("/stakeholders")
async def get_stakeholder_analysis(
    entity_name: str = Query(...),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene análisis de stakeholders"""
    try:
        service = ReputationService(db)
        result = await service.analyze_stakeholder_sentiment(entity_name, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholder analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stakeholder analysis: {str(e)}"
        )
