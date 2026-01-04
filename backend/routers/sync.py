"""
Data Synchronization router
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
# Autenticació eliminada
from typing import Dict, Any

router = APIRouter()

@router.get("/status/{case_id}", response_model=Dict[str, Any])
async def get_sync_status(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get synchronization status for a case"""
    from models.case import Case
    from models.osint import OSINTQuery
    from sqlalchemy import select
    
    result = await db.execute(
        select(Case).where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Count OSINT queries
    osint_result = await db.execute(
        select(OSINTQuery).where(OSINTQuery.case_id == case_id)
    )
    osint_queries = osint_result.scalars().all()
    
    return {
        "case_id": case_id,
        "status": case.status,
        "osint_queries_count": len(osint_queries),
        "last_sync": case.updated_at.isoformat() if case.updated_at else None,
        "synchronized": case.status == "completed"
    }

@router.post("/{case_id}", response_model=Dict[str, Any])
async def force_sync(
    case_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Force synchronization for a case"""
    from models.case import Case
    from services.case_service import CaseService
    from sqlalchemy import select
    
    result = await db.execute(
        select(Case).where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case_service = CaseService(db)
    background_tasks.add_task(case_service.execute_case_analysis, case_id)
    
    return {
        "case_id": case_id,
        "status": "syncing",
        "message": "Synchronization started"
    }

