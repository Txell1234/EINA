"""
Geopolitical Advanced router - Análisis avanzado geopolítico
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.geopolitical_advanced_service import GeopoliticalAdvancedService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["Geopolitical Advanced"])

@router.get("/supply-chains")
async def get_supply_chain_risks(
    country: str = Query(...),
    industry: str = Query(...),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Analiza riesgos en cadenas de suministro"""
    try:
        service = GeopoliticalAdvancedService(db)
        result = await service.analyze_supply_chain_risks(country, industry, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing supply chain risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing supply chains: {str(e)}"
        )

@router.get("/interdependencies")
async def get_economic_interdependencies(
    country1: str = Query(...),
    country2: str = Query(...),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Calcula interdependencias económicas"""
    try:
        service = GeopoliticalAdvancedService(db)
        result = await service.calculate_economic_interdependence(country1, country2, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating interdependencies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating interdependencies: {str(e)}"
        )

@router.post("/scenarios")
async def generate_scenarios(
    case_id: int = Query(...),
    countries: str = Query(..., description="Comma-separated list of countries"),
    time_horizon: str = Query("12_months", description="3_months, 6_months, 12_months"),
    db: AsyncSession = Depends(get_db)
):
    """Genera análisis de escenarios"""
    try:
        service = GeopoliticalAdvancedService(db)
        country_list = [c.strip() for c in countries.split(",")]
        result = await service.generate_scenario_analysis(case_id, country_list, time_horizon)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating scenarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating scenarios: {str(e)}"
        )

@router.get("/regulatory-risks")
async def get_regulatory_risks(
    country: str = Query(...),
    industry: Optional[str] = Query(None),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Evalúa riesgo regulatorio"""
    try:
        service = GeopoliticalAdvancedService(db)
        result = await service.assess_regulatory_risk(country, industry, case_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing regulatory risk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assessing regulatory risk: {str(e)}"
        )
