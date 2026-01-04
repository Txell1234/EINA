"""
Predictions router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.predictions import PredictionRequest, PredictionResponse, TrendPredictionResponse
from models.predictions import Prediction, PredictionModel
from services.ai_service import AIService

router = APIRouter()

@router.post("/generate", response_model=PredictionResponse)
async def generate_prediction(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate prediction with confidence percentage"""
    ai_service = AIService()
    
    # Generate prediction using AI with REAL case data (OSINT, KPIs, objectives)
    prediction_text = await ai_service.generate_prediction(
        prediction_type=request.prediction_type,
        context_data=request.context_data or {},
        case_id=request.case_id,
        db=db  # Pass db to fetch all case data
    )
    
    # Create prediction record with explanation
    new_prediction = Prediction(
        case_id=request.case_id,
        model_id=request.model_id,
        prediction_type=request.prediction_type,
        prediction_text=prediction_text.get("text", ""),
        confidence_percentage=prediction_text.get("confidence", 0.0),
        predicted_date=request.predicted_date,
        metadata={
            "explanation": prediction_text.get("explanation", ""),
            "supporting_data": prediction_text.get("supporting_data", []),
            **prediction_text.get("metadata", {})
        }
    )
    db.add(new_prediction)
    await db.commit()
    await db.refresh(new_prediction)
    
    return PredictionResponse.model_validate(new_prediction)

@router.get("/case/{case_id}", response_model=List[PredictionResponse])
async def get_case_predictions(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all predictions for a case with detailed explanations"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Prediction).where(Prediction.case_id == case_id)
        .order_by(Prediction.created_at.desc())
    )
    predictions = result.scalars().all()
    
    return [PredictionResponse.model_validate(p) for p in predictions]

@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get prediction by ID"""
    result = await db.execute(
        Prediction.__table__.select().where(Prediction.id == prediction_id)
    )
    prediction = result.first()
    
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    
    return PredictionResponse.from_orm(prediction)

@router.get("/trends", response_model=List[TrendPredictionResponse])
async def get_trend_predictions(
    case_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get trend predictions"""
    query = Prediction.__table__.select().where(
        Prediction.prediction_type == "trend"
    )
    
    if case_id:
        query = query.where(Prediction.case_id == case_id)
    
    query = query.offset(skip).limit(limit).order_by(Prediction.created_at.desc())
    
    result = await db.execute(query)
    predictions = result.all()
    
    return [TrendPredictionResponse.model_validate(p) for p in predictions]

