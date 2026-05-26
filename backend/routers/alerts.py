"""
Alerts router — DEPRECATED / NOT MOUNTED.

This module references `services.alert_service.AlertService`, which does not exist.
It is intentionally NOT included in `app.main` to avoid import errors and route
collisions with the working alert system.

Use instead:
  - OSINT monitors:  GET/POST /api/prospective/monitors
  - Alert matches:   GET      /api/prospective/alerts
  - Dashboard feed:  GET      /api/dashboard/alerts (via dashboard router)

Do not mount this router until AlertService is implemented or routes are migrated.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.alert_service import AlertService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("/all")
async def get_all_alerts(
    case_id: Optional[int] = Query(None),
    entity_name: Optional[str] = Query(None),
    countries: Optional[str] = Query(None, description="Comma-separated list of countries"),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene todas las alertas"""
    try:
        service = AlertService(db)
        country_list = [c.strip() for c in countries.split(",")] if countries else None
        
        result = await service.get_all_alerts(
            case_id=case_id,
            entity_name=entity_name,
            countries=country_list
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
        logger.error(f"Error getting all alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting alerts: {str(e)}"
        )



