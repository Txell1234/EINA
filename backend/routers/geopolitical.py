"""
Geopolitical router - Relacions bilaterals, tractats, esdeveniments i riscos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.geopolitical_relation_service import GeopoliticalRelationService
from services.geopolitical_risk_service import GeopoliticalRiskService
from services.diplomatic_event_service import DiplomaticEventService
from pydantic import BaseModel, ConfigDict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["Geopolitical"])

# Schemas
class BilateralRelationResponse(BaseModel):
    id: int
    country1: str
    country2: str
    relation_type: str
    status: str
    relation_score: float
    political_cooperation: float
    economic_cooperation: float
    security_cooperation: float
    
    model_config = ConfigDict(from_attributes=True)

class TreatyResponse(BaseModel):
    id: int
    name: str
    treaty_type: Optional[str]
    signing_date: Optional[str]
    status: str
    countries: List[str]
    impact_score: float
    
    model_config = ConfigDict(from_attributes=True)

class DiplomaticEventResponse(BaseModel):
    id: int
    event_type: str
    importance: str
    title: str
    description: Optional[str]
    event_date: str
    countries: List[str]
    impact_score: float
    sentiment_score: Optional[float]
    location: Optional[str] = None
    location_coordinates: Optional[Any] = None
    source_references: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

class GeopoliticalRiskResponse(BaseModel):
    id: int
    country: str
    region: Optional[str]
    overall_risk_score: float
    political_stability_risk: float
    conflict_risk: float
    economic_risk: float
    security_risk: float
    risk_change_7d: float
    risk_change_30d: float
    alert_triggered: bool
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/relations/extract")
async def extract_relations(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Extreu relacions bilaterals des de dades OSINT"""
    try:
        service = GeopoliticalRelationService(db)
        relations = await service.extract_relations_from_osint(case_id)
        return {
            "status": "success",
            "relations_found": len(relations),
            "relations": relations
        }
    except Exception as e:
        logger.error(f"Error extracting relations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting relations: {str(e)}"
        )

@router.get("/relations/timeline")
async def get_relation_timeline(
    country1: str = Query(..., description="First country"),
    country2: str = Query(..., description="Second country"),
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Obté timeline de relació entre dos països"""
    try:
        service = GeopoliticalRelationService(db)
        timeline = await service.get_relation_timeline(country1, country2, days)
        return timeline
    except Exception as e:
        logger.error(f"Error getting relation timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting timeline: {str(e)}"
        )

@router.get("/relations/matrix")
async def get_bilateral_matrix(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Genera matriu de relacions bilaterals"""
    try:
        service = GeopoliticalRelationService(db)
        matrix = await service.get_bilateral_matrix(case_id)
        return matrix
    except Exception as e:
        logger.error(f"Error generating bilateral matrix: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating matrix: {str(e)}"
        )

@router.get("/relations")
async def list_relations(
    case_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Llista relacions bilaterals"""
    try:
        from sqlalchemy import select, and_, or_
        from models.geopolitical import BilateralRelation
        
        query = select(BilateralRelation)
        conditions = []
        
        if case_id:
            conditions.append(BilateralRelation.case_id == case_id)
        if country:
            conditions.append(
                or_(
                    BilateralRelation.country1.ilike(f"%{country}%"),
                    BilateralRelation.country2.ilike(f"%{country}%")
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(BilateralRelation.last_updated.desc()))
        relations = result.scalars().all()
        
        return [BilateralRelationResponse.model_validate(r) for r in relations]
    except Exception as e:
        logger.error(f"Error listing relations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing relations: {str(e)}"
        )

@router.post("/treaties/extract")
async def extract_treaties(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Extreu tractats des de dades OSINT"""
    try:
        service = GeopoliticalRelationService(db)
        treaties = await service.extract_treaties_from_osint(case_id)
        return {
            "status": "success",
            "treaties_found": len(treaties),
            "treaties": treaties
        }
    except Exception as e:
        logger.error(f"Error extracting treaties: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting treaties: {str(e)}"
        )

@router.get("/treaties")
async def list_treaties(
    case_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Llista tractats"""
    try:
        from sqlalchemy import select, and_, or_
        from models.geopolitical import Treaty
        
        query = select(Treaty)
        conditions = []
        
        if case_id:
            conditions.append(Treaty.case_id == case_id)
        if country:
            # Buscar en el camp JSON de countries
            conditions.append(Treaty.countries.contains([country]))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(Treaty.signing_date.desc()))
        treaties = result.scalars().all()
        
        return [TreatyResponse.model_validate(t) for t in treaties]
    except Exception as e:
        logger.error(f"Error listing treaties: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing treaties: {str(e)}"
        )

@router.get("/events")
async def list_diplomatic_events(
    case_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Llista esdeveniments diplomàtics"""
    try:
        from sqlalchemy import select, and_
        from models.geopolitical import DiplomaticEvent, EventType, EventImportance
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(DiplomaticEvent).where(DiplomaticEvent.event_date >= cutoff_date)
        conditions = []
        
        if case_id:
            conditions.append(DiplomaticEvent.case_id == case_id)
        if country:
            conditions.append(DiplomaticEvent.countries.contains([country]))
        if event_type:
            try:
                conditions.append(DiplomaticEvent.event_type == EventType(event_type))
            except ValueError:
                pass
        if importance:
            try:
                conditions.append(DiplomaticEvent.importance == EventImportance(importance))
            except ValueError:
                pass
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(DiplomaticEvent.event_date.desc()))
        events = result.scalars().all()
        
        return [DiplomaticEventResponse.model_validate(e) for e in events]
    except Exception as e:
        logger.error(f"Error listing events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing events: {str(e)}"
        )

@router.get("/risks")
async def get_geopolitical_risks(
    case_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Obté riscos geopolítics"""
    try:
        service = GeopoliticalRiskService(db)
        risks = await service.get_risks(case_id, country, region)
        return risks
    except Exception as e:
        logger.error(f"Error getting risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting risks: {str(e)}"
        )

@router.post("/risks/calculate")
async def calculate_risks(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Calcula riscos geopolítics des de dades OSINT"""
    try:
        service = GeopoliticalRiskService(db)
        result = await service.calculate_risks_from_osint(case_id)
        return result
    except Exception as e:
        logger.error(f"Error calculating risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating risks: {str(e)}"
        )

@router.get("/risks/comparison")
async def compare_risks(
    countries: str = Query(..., description="Comma-separated list of countries"),
    db: AsyncSession = Depends(get_db)
):
    """Compara riscos entre múltiples països"""
    try:
        service = GeopoliticalRiskService(db)
        country_list = [c.strip() for c in countries.split(",")]
        comparison = await service.compare_country_risks(country_list)
        return comparison
    except Exception as e:
        logger.error(f"Error comparing risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing risks: {str(e)}"
        )

@router.post("/events/extract")
async def extract_diplomatic_events(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Extreu esdeveniments diplomàtics des de dades OSINT"""
    try:
        service = DiplomaticEventService(db)
        events = await service.extract_events_from_osint(case_id)
        return {
            "status": "success",
            "events_found": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"Error extracting events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting events: {str(e)}"
        )
