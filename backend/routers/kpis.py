"""
KPIs router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
# Autenticació eliminada
from schemas.qualitative import KPICreate, KPIResponse
from models.qualitative import KPI

router = APIRouter()

@router.post("/", response_model=KPIResponse, status_code=status.HTTP_201_CREATED)
async def create_kpi(
    kpi_data: KPICreate,
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

@router.get("/{case_id}", response_model=List[KPIResponse])
async def get_kpis(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get KPIs for a case"""
    from models.case import CaseKPI
    
    result = await db.execute(
        KPI.__table__.select()
        .join(CaseKPI)
        .where(CaseKPI.case_id == case_id)
    )
    kpis = result.all()
    
    return [KPIResponse.model_validate(k) for k in kpis]

