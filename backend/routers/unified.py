"""
Unified Analysis router - Análisis completo unificado
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
# Autenticació eliminada
from typing import Dict, Any
from services.case_service import CaseService

router = APIRouter()

@router.post("/analyze/{case_id}", response_model=Dict[str, Any])
async def analyze_unified(
    case_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Unified analysis - Ejecuta todos los análisis (OSINT + AI + Qualitative + Predictions)"""
    from models.case import Case
    
    result = await db.execute(
        Case.__table__.select().where(Case.id == case_id)
    )
    case = result.first()
    
    if not case:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Case not found")
    
    case_service = CaseService(db)
    
    # Ejecutar análisis completo en background
    background_tasks.add_task(case_service.execute_case_analysis, case_id)
    
    return {
        "case_id": case_id,
        "status": "analyzing",
        "message": "Unified analysis started. This includes OSINT collection, AI analysis, qualitative analysis, and predictions."
    }









