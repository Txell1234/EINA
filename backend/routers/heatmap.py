"""
Heatmap router - Generate heatmap data for geographic visualizations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from services.heatmap_service import HeatmapService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float
    metadata: Dict[str, Any]

class LocationRelationship(BaseModel):
    source_location: Dict[str, Any]  # Changed from 'from_location' because 'from' is a reserved word
    target_location: Dict[str, Any]  # Changed from 'to' for clarity
    strength: float
    type: str
    count: int

class HeatmapDataResponse(BaseModel):
    status: str
    points: List[HeatmapPoint]
    relationships: Optional[List[LocationRelationship]] = []
    granularity: str
    metric_type: str
    total_points: int
    total_posts: int
    platform: Optional[str] = None
    date_range: Optional[Dict[str, str]] = None

# IMPORTANT: Dashboard summary must be BEFORE {case_id} routes to avoid route conflicts
@router.get("/dashboard/summary")
async def get_dashboard_heatmap_summary(
    granularity: str = Query("country", regex="^(country|region|city|municipality)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated heatmap data for all cases (dashboard summary)"""
    try:
        from sqlalchemy import select
        from models.case import Case
        
        # Get all cases
        cases_result = await db.execute(select(Case))
        cases = cases_result.scalars().all()
        
        service = HeatmapService(db)
        
        # Aggregate data from all cases
        all_points: Dict[str, Dict[str, Any]] = {}
        all_relationships: List[Dict[str, Any]] = []
        total_posts = 0
        
        for case in cases:
            try:
                result = await service.generate_heatmap_data(
                    case_id=case.id,
                    metric_type="posts",
                    granularity=granularity
                )
                
                if result.get("status") == "success":
                    total_posts += result.get("total_posts", 0)
                    
                    # Aggregate points
                    for point in result.get("points", []):
                        loc_key = f"{point['lat']}_{point['lng']}"
                        if loc_key not in all_points:
                            all_points[loc_key] = {
                                "lat": point["lat"],
                                "lng": point["lng"],
                                "intensity": 0,
                                "metadata": {
                                    "location_name": point["metadata"]["location_name"],
                                    "count": 0,
                                    "sentiment": 0,
                                    "engagement": 0,
                                    "cases": []
                                }
                            }
                        
                        all_points[loc_key]["intensity"] += point["intensity"]
                        all_points[loc_key]["metadata"]["count"] += point["metadata"].get("count", 0)
                        all_points[loc_key]["metadata"]["cases"].append(case.id)
                    
                    # Aggregate relationships
                    all_relationships.extend(result.get("relationships", []))
            except Exception as e:
                logger.warning(f"Error processing case {case.id} for dashboard heatmap: {e}")
                continue
        
        # Normalize intensities
        max_intensity = max((p["intensity"] for p in all_points.values()), default=1)
        if max_intensity > 0:
            for point in all_points.values():
                point["intensity"] = point["intensity"] / max_intensity
        
        points = list(all_points.values())
        
        return HeatmapDataResponse(
            status="success",
            points=[HeatmapPoint(**p) for p in points],
            relationships=[LocationRelationship(**r) for r in all_relationships[:50]],  # Limit to 50 relationships
            granularity=granularity,
            metric_type="posts",
            total_points=len(points),
            total_posts=total_posts,
            platform=None,
            date_range=None
        )
    except Exception as e:
        logger.error(f"Error generating dashboard heatmap summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating dashboard heatmap: {str(e)}"
        )

@router.get("/{case_id}/posts", response_model=HeatmapDataResponse)
async def get_posts_heatmap(
    case_id: int,
    granularity: str = Query("city", regex="^(country|region|city|municipality)$"),
    platform: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get heatmap data for posts by location"""
    try:
        service = HeatmapService(db)
        
        time_range = None
        if start_date and end_date:
            time_range = {"start": start_date, "end": end_date}
        
        result = await service.generate_heatmap_data(
            case_id=case_id,
            metric_type="posts",
            granularity=granularity,
            platform=platform,
            time_range=time_range
        )
        
        # Convert to response model
        points = [
            HeatmapPoint(**point) for point in result.get("points", [])
        ]
        
        relationships = [
            LocationRelationship(**rel) for rel in result.get("relationships", [])
        ]
        
        return HeatmapDataResponse(
            status=result.get("status", "success"),
            points=points,
            relationships=relationships,
            granularity=result.get("granularity", granularity),
            metric_type=result.get("metric_type", "posts"),
            total_points=result.get("total_points", 0),
            total_posts=result.get("total_posts", 0),
            platform=result.get("platform"),
            date_range=result.get("date_range")
        )
    except Exception as e:
        logger.error(f"Error generating posts heatmap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating heatmap: {str(e)}"
        )

@router.get("/{case_id}/sentiment", response_model=HeatmapDataResponse)
async def get_sentiment_heatmap(
    case_id: int,
    granularity: str = Query("city", regex="^(country|region|city|municipality)$"),
    platform: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get heatmap data for sentiment by location"""
    try:
        service = HeatmapService(db)
        
        time_range = None
        if start_date and end_date:
            time_range = {"start": start_date, "end": end_date}
        
        result = await service.generate_heatmap_data(
            case_id=case_id,
            metric_type="sentiment",
            granularity=granularity,
            platform=platform,
            time_range=time_range
        )
        
        points = [
            HeatmapPoint(**point) for point in result.get("points", [])
        ]
        
        relationships = [
            LocationRelationship(**rel) for rel in result.get("relationships", [])
        ]
        
        return HeatmapDataResponse(
            status=result.get("status", "success"),
            points=points,
            relationships=relationships,
            granularity=result.get("granularity", granularity),
            metric_type=result.get("metric_type", "sentiment"),
            total_points=result.get("total_points", 0),
            total_posts=result.get("total_posts", 0),
            platform=result.get("platform"),
            date_range=result.get("date_range")
        )
    except Exception as e:
        logger.error(f"Error generating sentiment heatmap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating heatmap: {str(e)}"
        )

@router.get("/{case_id}/engagement", response_model=HeatmapDataResponse)
async def get_engagement_heatmap(
    case_id: int,
    granularity: str = Query("city", regex="^(country|region|city|municipality)$"),
    platform: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get heatmap data for engagement by location"""
    try:
        service = HeatmapService(db)
        
        time_range = None
        if start_date and end_date:
            time_range = {"start": start_date, "end": end_date}
        
        result = await service.generate_heatmap_data(
            case_id=case_id,
            metric_type="engagement",
            granularity=granularity,
            platform=platform,
            time_range=time_range
        )
        
        points = [
            HeatmapPoint(**point) for point in result.get("points", [])
        ]
        
        relationships = [
            LocationRelationship(**rel) for rel in result.get("relationships", [])
        ]
        
        return HeatmapDataResponse(
            status=result.get("status", "success"),
            points=points,
            relationships=relationships,
            granularity=result.get("granularity", granularity),
            metric_type=result.get("metric_type", "engagement"),
            total_points=result.get("total_points", 0),
            total_posts=result.get("total_posts", 0),
            platform=result.get("platform"),
            date_range=result.get("date_range")
        )
    except Exception as e:
        logger.error(f"Error generating engagement heatmap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating heatmap: {str(e)}"
        )

@router.get("/{case_id}/custom", response_model=HeatmapDataResponse)
async def get_custom_heatmap(
    case_id: int,
    metric: str = Query("posts", description="Metric type: posts, sentiment, engagement"),
    granularity: str = Query("city", regex="^(country|region|city|municipality)$"),
    platform: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get custom heatmap data"""
    try:
        service = HeatmapService(db)
        
        time_range = None
        if start_date and end_date:
            time_range = {"start": start_date, "end": end_date}
        
        result = await service.generate_heatmap_data(
            case_id=case_id,
            metric_type=metric,
            granularity=granularity,
            platform=platform,
            time_range=time_range
        )
        
        points = [
            HeatmapPoint(**point) for point in result.get("points", [])
        ]
        
        relationships = [
            LocationRelationship(**rel) for rel in result.get("relationships", [])
        ]
        
        return HeatmapDataResponse(
            status=result.get("status", "success"),
            points=points,
            relationships=relationships,
            granularity=result.get("granularity", granularity),
            metric_type=result.get("metric_type", metric),
            total_points=result.get("total_points", 0),
            total_posts=result.get("total_posts", 0),
            platform=result.get("platform"),
            date_range=result.get("date_range")
        )
    except Exception as e:
        logger.error(f"Error generating custom heatmap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating heatmap: {str(e)}"
        )
