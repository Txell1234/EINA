"""
Integration router - Análisis cross-módulo
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.config import settings, INTEGRATION_REQUIREMENTS
from services.integration_service import IntegrationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integration", tags=["Integration"])

def _is_configured(value: Optional[str]) -> bool:
    return bool(value and str(value).strip())

@router.get("/status")
async def get_integration_status():
    """Devuelve el estado de configuración de las integraciones"""
    services = []
    for service_key, metadata in INTEGRATION_REQUIREMENTS.items():
        required_keys = metadata.get("required_keys", [])
        missing_keys = [
            key for key in required_keys
            if not _is_configured(getattr(settings, key, ""))
        ]
        services.append({
            "service": metadata.get("label", service_key),
            "key": service_key,
            "configured": len(missing_keys) == 0,
            "required_keys": required_keys,
            "missing_keys": missing_keys,
            "features": metadata.get("features", []),
        })

    return {"services": services}

@router.post("/comprehensive-analysis")
async def comprehensive_analysis(
    case_id: int = Query(...),
    entity_name: Optional[str] = Query(None),
    countries: Optional[str] = Query(None, description="Comma-separated list of countries"),
    db: AsyncSession = Depends(get_db)
):
    """Genera análisis integral combinando todos los módulos"""
    try:
        service = IntegrationService(db)
        country_list = [c.strip() for c in countries.split(",")] if countries else None
        
        result = await service.generate_comprehensive_risk_assessment(
            case_id=case_id,
            entity_name=entity_name,
            countries=country_list
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
        logger.error(f"Error generating comprehensive analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analysis: {str(e)}"
        )

@router.get("/geopolitical-investment-impact")
async def get_geopolitical_investment_impact(
    case_id: int = Query(...),
    countries: str = Query(..., description="Comma-separated list of countries"),
    investment_type: str = Query("general", description="general, long_term, regulatory_sensitive"),
    db: AsyncSession = Depends(get_db)
):
    """Analiza impacto geopolítico en inversiones"""
    try:
        service = IntegrationService(db)
        country_list = [c.strip() for c in countries.split(",")]
        
        result = await service.analyze_geopolitical_impact_on_investments(
            case_id=case_id,
            countries=country_list,
            investment_type=investment_type
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
        logger.error(f"Error analyzing geopolitical investment impact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing impact: {str(e)}"
        )

@router.get("/reputation-geopolitical")
async def get_reputation_geopolitical_correlation(
    entity_name: str = Query(...),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Correlaciona reputación con eventos geopolíticos"""
    try:
        service = IntegrationService(db)
        result = await service.assess_reputation_impact_of_geopolitical_events(
            entity_name=entity_name,
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
        logger.error(f"Error correlating reputation with geopolitics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error correlating: {str(e)}"
        )

@router.get("/public-affairs-reputation")
async def get_public_affairs_reputation_correlation(
    entity_name: str = Query(...),
    case_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Correlaciona asuntos públicos con reputación"""
    try:
        service = IntegrationService(db)
        result = await service.correlate_public_affairs_with_reputation(
            entity_name=entity_name,
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
        logger.error(f"Error correlating public affairs with reputation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error correlating: {str(e)}"
        )
