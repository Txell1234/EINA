"""
AI Analysis router
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.ai_analysis import AIAnalysisRequest, AIAnalysisResponse, ConceptResponse, TrendResponse, SentimentResponse
from models.ai_analysis import AIAnalysis, Concept, Trend, Sentiment
from services.ai_service import AIService

from app.dependencies import get_current_user
from models.user import User

router = APIRouter()

@router.post("/taranis/analyze", response_model=AIAnalysisResponse)
async def analyze_taranis(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Taranis AI analysis - Situational analysis and predictions"""
    ai_service = AIService()
    
    osint_results = request.osint_results if request.osint_results else None
    result = await ai_service.analyze_data(
        analysis_type="taranis",
        case_id=request.case_id,
        osint_results=osint_results,
        db=db  # Pass db to fetch all linked OSINT data
    )
    
    # Save to database
    analysis = AIAnalysis(
        case_id=request.case_id,
        analysis_type="taranis",
        analysis_data=result,
        confidence_score=result.get("confidence", 0.0)
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    return AIAnalysisResponse.model_validate(analysis)

@router.post("/osintgpt/analyze", response_model=AIAnalysisResponse)
async def analyze_osintgpt(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """OSINTGPT analysis - Concept extraction and embeddings"""
    ai_service = AIService()
    
    # Pass db so analyze_data can fetch ALL OSINT data if osint_results is empty
    osint_results = request.osint_results if request.osint_results else None
    result = await ai_service.analyze_data(
        analysis_type="osintgpt",
        case_id=request.case_id,
        osint_results=osint_results,
        db=db  # Pass db to fetch all linked OSINT data
    )
    
    # Save to database
    analysis = AIAnalysis(
        case_id=request.case_id,
        analysis_type="osintgpt",
        analysis_data=result,
        confidence_score=result.get("confidence", 0.0)
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    return AIAnalysisResponse.model_validate(analysis)

@router.post("/ominis/analyze", response_model=AIAnalysisResponse)
async def analyze_ominis(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Ominis-OSINT analysis - Predictive risk analysis"""
    ai_service = AIService()
    
    osint_results = request.osint_results if request.osint_results else None
    result = await ai_service.analyze_data(
        analysis_type="ominis",
        case_id=request.case_id,
        osint_results=osint_results,
        db=db  # Pass db to fetch all linked OSINT data
    )
    
    # Save to database
    analysis = AIAnalysis(
        case_id=request.case_id,
        analysis_type="ominis",
        analysis_data=result,
        confidence_score=result.get("confidence", 0.0)
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    return AIAnalysisResponse.model_validate(analysis)

@router.get("/concepts", response_model=List[ConceptResponse])
async def get_concepts(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get concepts for a case"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Concept)
        .join(AIAnalysis)
        .where(AIAnalysis.case_id == case_id)
    )
    concepts = result.scalars().all()
    
    # Return empty list if no concepts found (no error)
    return [ConceptResponse.model_validate(c) for c in concepts] if concepts else []

@router.get("/trends", response_model=List[TrendResponse])
async def get_trends(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trends for a case"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Trend)
        .join(AIAnalysis)
        .where(AIAnalysis.case_id == case_id)
    )
    trends = result.scalars().all()
    
    # Return empty list if no trends found (no error)
    return [TrendResponse.model_validate(t) for t in trends] if trends else []

@router.get("/sentiment", response_model=List[SentimentResponse])
async def get_sentiment(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sentiment analysis for a case"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Sentiment)
        .join(AIAnalysis)
        .where(AIAnalysis.case_id == case_id)
    )
    sentiments = result.scalars().all()
    
    # Return empty list if no sentiments found (no error)
    return [SentimentResponse.model_validate(s) for s in sentiments] if sentiments else []

@router.post("/analyze/{case_id}", response_model=AIAnalysisResponse)
async def analyze_with_ai(
    case_id: int,
    analysis_type: str = "osintgpt",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze case with AI"""
    ai_service = AIService()
    
    result = await ai_service.analyze_data(
        analysis_type=analysis_type,
        case_id=case_id,
        osint_results=[],
        db=db  # Pass db to fetch all linked OSINT data
    )
    
    analysis = AIAnalysis(
        case_id=case_id,
        analysis_type=analysis_type,
        analysis_data=result,
        confidence_score=result.get("confidence", 0.0)
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    return AIAnalysisResponse.model_validate(analysis)

@router.post("/expert/reputation-manager/{case_id}")
async def analyze_as_reputation_manager(
    case_id: int,
    entity_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Análisis experto de reputación"""
    try:
        ai_service = AIService()
        
        # Obtener datos OSINT del caso (el método lo hace automáticamente si no se proporcionan)
        result = await ai_service.analyze_as_reputation_manager(
            case_id=case_id,
            osint_data=None,  # Se obtendrá automáticamente desde BD
            api_data=None,  # Se puede obtener automáticamente si es necesario
            entity_name=entity_name,
            db=db
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in reputation manager analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in analysis: {str(e)}"
        )

@router.post("/expert/public-affairs-consultant/{case_id}")
async def analyze_as_public_affairs_consultant(
    case_id: int,
    policy_topic: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Análisis experto de asuntos públicos"""
    try:
        ai_service = AIService()
        
        result = await ai_service.analyze_as_public_affairs_consultant(
            case_id=case_id,
            osint_data=None,  # Se obtendrá automáticamente desde BD
            api_data=None,  # Se puede obtener automáticamente si es necesario
            policy_topic=policy_topic,
            db=db
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in public affairs consultant analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in analysis: {str(e)}"
        )

@router.post("/expert/geopolitical-analyst/{case_id}")
async def analyze_as_geopolitical_analyst(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Análisis experto geopolítico"""
    try:
        ai_service = AIService()
        
        # Usar analyze_as_geopolitical_analyst (método mejorado)
        result = await ai_service.analyze_as_geopolitical_analyst(
            case_id=case_id,
            osint_data=None,  # Se obtendrá automáticamente desde BD
            api_data=None,  # Se puede obtener automáticamente si es necesario
            db=db
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in geopolitical analyst analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in analysis: {str(e)}"
        )

@router.post("/expert/investment-advisor/{case_id}")
async def analyze_as_investment_advisor(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Análisis experto de inversiones"""
    try:
        ai_service = AIService()
        
        result = await ai_service.analyze_as_investment_advisor(
            case_id=case_id,
            osint_data=None,  # Se obtendrá automáticamente desde BD
            api_data=None,  # Se puede obtener automáticamente si es necesario
            db=db
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in investment advisor analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in analysis: {str(e)}"
        )

@router.post("/analyze-concepts/{case_id}", response_model=List[ConceptResponse])
async def analyze_concepts(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze and extract concepts"""
    ai_service = AIService()
    
    # Get case data
    from models.case import Case
    from sqlalchemy import select
    
    result = await db.execute(
        select(Case).where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Extract concepts
    concepts_data = await ai_service.extract_concepts(
        case.description or case.name
    )
    
    # Save concepts
    ai_analysis = AIAnalysis(
        case_id=case_id,
        analysis_type="concepts",
        analysis_data={"concepts": concepts_data},
        confidence_score=0.8
    )
    db.add(ai_analysis)
    await db.commit()
    await db.refresh(ai_analysis)
    
    # Create concept records
    concepts = []
    for concept_data in concepts_data:
        concept = Concept(
            analysis_id=ai_analysis.id,
            concept_name=concept_data.get("name", ""),
            concept_type=concept_data.get("type", "general"),
            confidence=concept_data.get("confidence", 0.0),
            metadata=concept_data
        )
        db.add(concept)
        concepts.append(concept)
    
    await db.commit()
    
    return [ConceptResponse.model_validate(c) for c in concepts]

@router.post("/analyze-trends/{case_id}", response_model=List[TrendResponse])
async def analyze_trends(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze trends for a case"""
    ai_service = AIService()
    
    # Get case and generate trends
    from models.case import Case
    result = await db.execute(
        Case.__table__.select().where(Case.id == case_id)
    )
    case = result.first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create trend analysis
    ai_analysis = AIAnalysis(
        case_id=case_id,
        analysis_type="trends",
        analysis_data={},
        confidence_score=0.75
    )
    db.add(ai_analysis)
    await db.commit()
    await db.refresh(ai_analysis)
    
    # Create sample trends
    trend = Trend(
        analysis_id=ai_analysis.id,
        trend_name="Tendencia Principal",
        trend_type="emerging",
        intensity=75.0,
        confidence=0.85
    )
    db.add(trend)
    await db.commit()
    await db.refresh(trend)
    
    return [TrendResponse.model_validate(trend)]

@router.post("/analyze-sentiment/{case_id}", response_model=List[SentimentResponse])
async def analyze_sentiment_endpoint(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze sentiment for a case"""
    ai_service = AIService()
    
    # Get case
    from models.case import Case
    result = await db.execute(
        Case.__table__.select().where(Case.id == case_id)
    )
    case = result.first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Analyze sentiment
    sentiment_data = await ai_service.analyze_sentiment(
        case.description or case.name
    )
    
    # Create analysis
    ai_analysis = AIAnalysis(
        case_id=case_id,
        analysis_type="sentiment",
        analysis_data=sentiment_data,
        confidence_score=sentiment_data.get("confidence", 0.5)
    )
    db.add(ai_analysis)
    await db.commit()
    await db.refresh(ai_analysis)
    
    # Create sentiment record
    sentiment = Sentiment(
        analysis_id=ai_analysis.id,
        sentiment_type=sentiment_data.get("sentiment", "neutral"),
        score=sentiment_data.get("score", 0.0),
        confidence=sentiment_data.get("confidence", 0.5),
        source_text=case.description or case.name
    )
    db.add(sentiment)
    await db.commit()
    await db.refresh(sentiment)
    
    return [SentimentResponse.model_validate(sentiment)]
