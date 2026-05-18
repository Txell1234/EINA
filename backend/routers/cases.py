"""Cases list API for linking prospective workflows."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.case import Case

router = APIRouter()


@router.get("")
async def list_cases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Case).order_by(Case.id.asc()))
    rows = result.scalars().all()
    return [{"id": c.id, "name": c.name} for c in rows]
