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
    ReasoningFrameworkCreate,
    ReasoningFrameworkUpdate,
    FrameworkGenerateRequest,
    FrameworkPreviewRequest,
    QualitativeAnalysisRequest, QualitativeAnalysisResponse
)
from models.qualitative import Premise, ReasoningFramework, KPI, QualitativeAnalysis, ReasoningFrameworkType
from services.qualitative_service import QualitativeService
from services.reasoning_framework_service import ReasoningFrameworkService

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
    svc = ReasoningFrameworkService(db)
    return await svc.list_frameworks()


@router.get("/frameworks/{framework_id}", response_model=ReasoningFrameworkResponse)
async def get_framework(
    framework_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ReasoningFrameworkService(db)
    fw = await svc.get_framework(framework_id)
    if not fw:
        raise HTTPException(status_code=404, detail="Marc no trobat")
    return fw


@router.post("/frameworks", response_model=ReasoningFrameworkResponse, status_code=status.HTTP_201_CREATED)
async def create_framework(
    body: ReasoningFrameworkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ReasoningFrameworkService(db)
    definition = body.definition.model_dump() if body.definition else None
    return await svc.create_framework(
        name=body.name,
        framework_type=body.framework_type,
        description=body.description,
        definition=definition,
        user_id=current_user.id,
        is_custom=body.framework_type == ReasoningFrameworkType.CUSTOM,
    )


@router.put("/frameworks/{framework_id}", response_model=ReasoningFrameworkResponse)
async def update_framework(
    framework_id: int,
    body: ReasoningFrameworkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ReasoningFrameworkService(db)
    definition = body.definition.model_dump() if body.definition else None
    updated = await svc.update_framework(
        framework_id,
        name=body.name,
        framework_type=body.framework_type,
        description=body.description,
        definition=definition,
        is_active=body.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Marc no trobat")
    return updated


@router.delete("/frameworks/{framework_id}")
async def delete_framework(
    framework_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ReasoningFrameworkService(db)
    ok = await svc.delete_framework(framework_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Marc no trobat")
    return {"deleted": True}


@router.post("/frameworks/generate")
async def generate_framework(
    body: FrameworkGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a draft framework definition with LLM from a brief."""
    svc = ReasoningFrameworkService(db)
    try:
        return await svc.generate_from_brief(
            body.brief,
            framework_type=body.framework_type,
            language=body.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/frameworks/{framework_id}/preview")
async def preview_framework(
    framework_id: int,
    body: FrameworkPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview LLM analysis using this framework without persisting."""
    svc = ReasoningFrameworkService(db)
    try:
        return await svc.preview_analysis(
            framework_id,
            body.premise,
            case_context=body.case_context or "",
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Marc no trobat")

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
        if not request.framework_id and not request.framework:
            raise HTTPException(status_code=400, detail="framework o framework_id és obligatori")

        framework_name = request.framework or "deductive"
        if request.framework_id:
            from sqlalchemy import select
            fw_result = await db.execute(
                select(ReasoningFramework).where(ReasoningFramework.id == request.framework_id)
            )
            fw = fw_result.scalar_one_or_none()
            if fw:
                framework_name = fw.name

        premise = request.premise.strip()
        if request.focus_entity:
            premise += f"\n\nEntitat focus: {request.focus_entity}"
        if request.focus_topic:
            premise += f"\nTema focus: {request.focus_topic}"
        
        qualitative_service = QualitativeService(db)
        
        result = await qualitative_service.run_analysis(
            case_id=request.case_id,
            premise=premise,
            framework=framework_name,
            kpi_ids=request.kpi_ids or [],
            framework_id=request.framework_id,
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

