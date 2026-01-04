"""
Investment Advanced router - Análisis ESG, riesgo regulatorio y comparación de mercados
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.investment_advanced_service import InvestmentAdvancedService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investment-advanced", tags=["Investment Advanced"])

@router.get("/esg")
async def analyze_esg(
    case_id: int = Query(...),
    company_symbol: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Analiza factores ESG (Environmental, Social, Governance)"""
    try:
        service = InvestmentAdvancedService(db)
        result = await service.analyze_esg_factors(
            case_id=case_id,
            company_symbol=company_symbol,
            country=country
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
        logger.error(f"Error analyzing ESG factors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing ESG: {str(e)}"
        )

@router.get("/regulatory-risk")
async def get_regulatory_risk(
    case_id: int = Query(...),
    country: str = Query(...),
    industry: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Evalúa riesgo regulatorio para inversiones"""
    try:
        service = InvestmentAdvancedService(db)
        result = await service.assess_regulatory_risk(
            case_id=case_id,
            country=country,
            industry=industry
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
        logger.error(f"Error assessing regulatory risk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assessing regulatory risk: {str(e)}"
        )

@router.get("/market-opportunities")
async def compare_market_opportunities(
    case_id: int = Query(...),
    countries: str = Query(..., description="Comma-separated list of countries"),
    industries: Optional[str] = Query(None, description="Comma-separated list of industries"),
    db: AsyncSession = Depends(get_db)
):
    """Compara oportunidades de mercado entre países/industrias"""
    try:
        service = InvestmentAdvancedService(db)
        country_list = [c.strip() for c in countries.split(",")]
        industry_list = [i.strip() for i in industries.split(",")] if industries else None
        
        result = await service.compare_market_opportunities(
            case_id=case_id,
            countries=country_list,
            industries=industry_list
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
        logger.error(f"Error comparing market opportunities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing opportunities: {str(e)}"
        )

@router.get("/geopolitical-impact")
async def get_geopolitical_impact(
    case_id: int = Query(...),
    countries: str = Query(..., description="Comma-separated list of countries"),
    investment_type: str = Query("general", description="general, long_term, regulatory_sensitive"),
    db: AsyncSession = Depends(get_db)
):
    """Calcula impacto geopolítico en inversiones"""
    try:
        service = InvestmentAdvancedService(db)
        country_list = [c.strip() for c in countries.split(",")]
        
        result = await service.calculate_geopolitical_impact_on_investments(
            case_id=case_id,
            countries=country_list,
            investment_type=investment_type,
            fetch_fresh_data=False
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
        logger.error(f"Error calculating geopolitical impact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating impact: {str(e)}"
        )



