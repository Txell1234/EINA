"""
Qualitative Analysis router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.qualitative import (
    PremiseCreate, PremiseResponse,
    KPICreate, KPIResponse,
    ReasoningFrameworkResponse,
    QualitativeAnalysisRequest, QualitativeAnalysisResponse
)
from models.qualitative import Premise, ReasoningFramework, KPI, QualitativeAnalysis
from services.qualitative_service import QualitativeService

from app.dependencies import get_current_user
from models.user import User

router = APIRouter()

@router.post("/premise", response_model=PremiseResponse, status_code=status.HTTP_201_CREATED)
async def create_premise(
    premise_data: PremiseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create premise for analysis"""
    new_premise = Premise(
        case_id=premise_data.case_id,
        premise_text=premise_data.premise_text,
        framework_id=premise_data.framework_id
    )
    db.add(new_premise)
    await db.commit()
    await db.refresh(new_premise)
    
    return PremiseResponse.model_validate(new_premise)

@router.post("/kpi", response_model=KPIResponse, status_code=status.HTTP_201_CREATED)
async def create_kpi(
    kpi_data: KPICreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create KPI"""
    new_kpi = KPI(
        name=kpi_data.name,
        kpi_type=kpi_data.kpi_type,
        description=kpi_data.description,
        target_value=kpi_data.target_value
    )
    db.add(new_kpi)
    await db.commit()
    await db.refresh(new_kpi)
    
    return KPIResponse.model_validate(new_kpi)

@router.get("/frameworks", response_model=List[ReasoningFrameworkResponse])
async def list_frameworks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all reasoning frameworks"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(ReasoningFramework)
        .where(ReasoningFramework.is_active == True)
    )
    frameworks = result.scalars().all()
    
    return [ReasoningFrameworkResponse.model_validate(f) for f in frameworks]

@router.post("/analyze", response_model=QualitativeAnalysisResponse)
async def run_qualitative_analysis(
    request: QualitativeAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run qualitative/quantitative analysis"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate request
        if not request.case_id:
            raise HTTPException(status_code=400, detail="case_id és obligatori")
        if not request.premise or not request.premise.strip():
            raise HTTPException(status_code=400, detail="premisa és obligatòria")
        if not request.framework:
            raise HTTPException(status_code=400, detail="framework és obligatori")
        
        qualitative_service = QualitativeService(db)
        
        result = await qualitative_service.run_analysis(
            case_id=request.case_id,
            premise=request.premise,
            framework=request.framework,
            kpi_ids=request.kpi_ids or []
        )
        
        # Get the created analysis
        from sqlalchemy import select
        
        if not result or "analysis_id" not in result:
            raise HTTPException(
                status_code=500, 
                detail="Error: L'anàlisi no s'ha pogut crear. El servei no ha retornat un ID vàlid."
            )
        
        result_db = await db.execute(
            select(QualitativeAnalysis)
            .where(QualitativeAnalysis.id == result["analysis_id"])
        )
        analysis = result_db.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=404, 
                detail=f"Anàlisi no trobada amb ID: {result['analysis_id']}"
            )
        
        return QualitativeAnalysisResponse.model_validate(analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en run_qualitative_analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error intern del servidor: {str(e)}"
        )

@router.get("/kpis", response_model=List[KPIResponse])
async def list_kpis(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all KPIs"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(KPI)
        .where(KPI.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    kpis = result.scalars().all()
    
    return [KPIResponse.model_validate(k) for k in kpis]

