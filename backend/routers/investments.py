"""
Investment Recommendations router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.investments import (
    InvestmentRecommendationRequest, InvestmentRecommendationResponse,
    RiskAnalysisResponse, OpportunityResponse
)
from models.investments import InvestmentRecommendation, RiskAnalysis, Opportunity
from services.investment_service import InvestmentService

router = APIRouter()

@router.post("/recommend", response_model=InvestmentRecommendationResponse)
async def generate_recommendation(
    request: InvestmentRecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate investment recommendation"""
    investment_service = InvestmentService(db)
    
    result = await investment_service.generate_recommendation(
        case_id=request.case_id
    )
    
    # Get the created recommendation
    from sqlalchemy import select
    
    result_db = await db.execute(
        select(InvestmentRecommendation)
        .where(InvestmentRecommendation.id == result["recommendation_id"])
    )
    recommendation = result_db.scalar_one_or_none()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return InvestmentRecommendationResponse.model_validate(recommendation)

@router.get("/risks", response_model=List[RiskAnalysisResponse])
async def get_risks(
    case_id: Optional[int] = None,
    recommendation_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get risk analyses"""
    from sqlalchemy import select
    
    if recommendation_id:
        result = await db.execute(
            select(RiskAnalysis).where(RiskAnalysis.recommendation_id == recommendation_id)
        )
    elif case_id:
        # Get recommendation for case first
        rec_result = await db.execute(
            select(InvestmentRecommendation)
            .where(InvestmentRecommendation.case_id == case_id)
            .limit(1)
        )
        rec = rec_result.scalar_one_or_none()
        if rec:
            result = await db.execute(
                select(RiskAnalysis).where(RiskAnalysis.recommendation_id == rec.id)
            )
        else:
            return []
    else:
        result = await db.execute(select(RiskAnalysis))
    
    risks = result.scalars().all()
    return [RiskAnalysisResponse.model_validate(r) for r in risks]

@router.get("/opportunities", response_model=List[OpportunityResponse])
async def get_opportunities(
    case_id: Optional[int] = None,
    recommendation_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get opportunities"""
    from sqlalchemy import select
    
    if recommendation_id:
        result = await db.execute(
            select(Opportunity).where(Opportunity.recommendation_id == recommendation_id)
        )
    elif case_id:
        # Get recommendation for case first
        rec_result = await db.execute(
            select(InvestmentRecommendation)
            .where(InvestmentRecommendation.case_id == case_id)
            .limit(1)
        )
        rec = rec_result.scalar_one_or_none()
        if rec:
            result = await db.execute(
                select(Opportunity).where(Opportunity.recommendation_id == rec.id)
            )
        else:
            return []
    else:
        result = await db.execute(select(Opportunity))
    
    opportunities = result.scalars().all()
    return [OpportunityResponse.model_validate(o) for o in opportunities]

@router.post("/analyze/{case_id}", response_model=InvestmentRecommendationResponse)
async def analyze_investment(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Analyze investment for a case - Autenticació eliminada"""
    return await generate_recommendation(
        InvestmentRecommendationRequest(case_id=case_id),
        db
    )

@router.get("/quote/{symbol}")
async def get_stock_quote(
    symbol: str,
    provider: str = "alphavantage",  # alphavantage or finnhub
    db: AsyncSession = Depends(get_db)
):
    """Get real-time stock quote from financial APIs"""
    from integrations.alphavantage_api import AlphaVantageAPIService
    from integrations.finnhub_api import FinnhubAPIService
    
    if provider == "finnhub":
        service = FinnhubAPIService()
        result = await service.get_quote(symbol)
    else:
        service = AlphaVantageAPIService()
        result = await service.get_quote(symbol)
    
    return result

@router.get("/search/{keywords}")
async def search_stock_symbols(
    keywords: str,
    db: AsyncSession = Depends(get_db)
):
    """Search for stock symbols"""
    from integrations.alphavantage_api import AlphaVantageAPIService
    
    service = AlphaVantageAPIService()
    result = await service.search_symbol(keywords)
    
    return result

@router.get("/profile/{symbol}")
async def get_company_profile(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get company profile from Finnhub"""
    from integrations.finnhub_api import FinnhubAPIService
    
    service = FinnhubAPIService()
    result = await service.get_company_profile(symbol)
    
    return result

@router.get("/institutional/{symbol}")
async def get_institutional_profile(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get institutional profile - ownership and holdings data"""
    from integrations.finnhub_api import FinnhubAPIService
    
    service = FinnhubAPIService()
    result = await service.get_institutional_profile(symbol)
    
    return result

@router.get("/geopolitical/sentiment")
async def get_geopolitical_sentiment(
    country: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get geopolitical sentiment data from Permutable AI"""
    from integrations.permutable_api import PermutableAPIService
    
    service = PermutableAPIService()
    result = await service.get_geopolitical_sentiment(country, start_date, end_date)
    
    return result

@router.get("/geopolitical/country/{country}")
async def get_country_geopolitical_profile(
    country: str,
    db: AsyncSession = Depends(get_db)
):
    """Get country geopolitical profile from Permutable AI"""
    from integrations.permutable_api import PermutableAPIService
    
    service = PermutableAPIService()
    result = await service.get_country_profile(country)
    
    return result

@router.get("/geopolitical/events")
async def get_geopolitical_events(
    location: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get geopolitical events (tariffs, sanctions, wars, etc.) from Permutable AI"""
    from integrations.permutable_api import PermutableAPIService
    
    service = PermutableAPIService()
    result = await service.get_geopolitical_events(location, topic, limit)
    
    return result

@router.get("/currency/rates")
async def get_currency_rates(
    base: str = "USD",
    provider: str = "exchangerate",
    db: AsyncSession = Depends(get_db)
):
    """Get currency exchange rates"""
    from integrations.currency_api import CurrencyAPIService
    
    service = CurrencyAPIService()
    result = await service.get_rates(base, provider)
    
    return result

@router.get("/currency/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    provider: str = "exchangerate",
    db: AsyncSession = Depends(get_db)
):
    """Convert currency amount"""
    from integrations.currency_api import CurrencyAPIService
    
    service = CurrencyAPIService()
    result = await service.convert(amount, from_currency, to_currency, provider)
    
    return result

@router.get("/crypto/{coin_id}")
async def get_crypto_price(
    coin_id: str,
    vs_currencies: str = "usd",
    db: AsyncSession = Depends(get_db)
):
    """Get cryptocurrency price from CoinGecko"""
    from integrations.crypto_api import CoinGeckoAPIService
    
    service = CoinGeckoAPIService()
    result = await service.get_price(coin_id, vs_currencies)
    
    return result

@router.get("/crypto/search/{query}")
async def search_cryptocurrencies(
    query: str,
    db: AsyncSession = Depends(get_db)
):
    """Search for cryptocurrencies"""
    from integrations.crypto_api import CoinGeckoAPIService
    
    service = CoinGeckoAPIService()
    result = await service.search(query)
    
    return result

@router.get("/crypto/trending")
async def get_trending_crypto(
    db: AsyncSession = Depends(get_db)
):
    """Get trending cryptocurrencies"""
    from integrations.crypto_api import CoinGeckoAPIService
    
    service = CoinGeckoAPIService()
    result = await service.get_trending()
    
    return result

