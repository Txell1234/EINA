"""
Research router - Deep research automation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app.database import get_db
from sqlalchemy import select
from models.case import Case
from models.osint import OSINTQuery
from services.research_planner_service import ResearchPlannerService
from services.research_executor_service import ResearchExecutorService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Store research plans and execution status in memory (in production, use Redis or DB)
research_plans_store: Dict[int, Dict[str, Any]] = {}
research_status_store: Dict[int, Dict[str, Any]] = {}

@router.post("/plan/{case_id}")
async def generate_research_plan(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive research plan for a case"""
    try:
        # Get case
        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get existing queries to avoid duplicates
        existing_queries_result = await db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        )
        existing_queries = existing_queries_result.scalars().all()
        existing_queries_list = [
            {
                "type": q.query_type,
                "params": q.query_params or {}
            }
            for q in existing_queries
        ]
        
        # Generate research plan
        planner = ResearchPlannerService()
        case_type_str = case.case_type.value if hasattr(case.case_type, 'value') else str(case.case_type) if case.case_type else "general"
        
        research_plan = await planner.generate_research_plan(
            case_id=case_id,
            case_type=case_type_str,
            case_description=case.description or case.name,
            case_name=case.name,
            existing_queries=existing_queries_list
        )
        
        # Store plan
        research_plans_store[case_id] = research_plan
        
        return research_plan
        
    except Exception as e:
        logger.error(f"Error generating research plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating research plan: {str(e)}"
        )

@router.get("/plan/{case_id}")
async def get_research_plan(
    case_id: int
):
    """Get current research plan for a case"""
    if case_id not in research_plans_store:
        raise HTTPException(status_code=404, detail="Research plan not found. Generate one first.")
    
    return research_plans_store[case_id]

@router.post("/plan/{case_id}/approve")
async def approve_and_execute_research_plan(
    case_id: int,
    approved_plan: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """Approve and execute research plan"""
    try:
        # Get case
        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Update stored plan with approved version
        research_plans_store[case_id] = approved_plan
        
        # Initialize execution status
        research_status_store[case_id] = {
            "status": "executing",
            "current_phase": 0,
            "current_query": 0,
            "total_phases": len(approved_plan.get("research_phases", [])),
            "total_queries": sum(len(p.get("queries", [])) for p in approved_plan.get("research_phases", [])),
            "executed_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "message": "Starting research execution..."
        }
        
        # Execute in background
        async def execute_research(case_id: int, plan: Dict[str, Any]):
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as bg_db:
                try:
                    executor = ResearchExecutorService(bg_db)
                    
                    # Progress callback
                    async def progress_callback(phase_idx, query_idx, status, message):
                        if case_id in research_status_store:
                            research_status_store[case_id].update({
                                "current_phase": phase_idx,
                                "current_query": query_idx or 0,
                                "message": message,
                                "status": status
                            })
                    
                    # Execute plan
                    results = await executor.execute_research_plan(
                        case_id=case_id,
                        research_plan=plan,
                        progress_callback=progress_callback
                    )
                    
                    # Update final status
                    research_status_store[case_id] = {
                        "status": "completed",
                        "total_phases": results["total_phases"],
                        "total_queries": results["total_queries"],
                        "executed_queries": results["executed_queries"],
                        "successful_queries": results["successful_queries"],
                        "failed_queries": results["failed_queries"],
                        "message": f"Research completed: {results['successful_queries']}/{results['total_queries']} queries successful",
                        "results": results
                    }
                    
                    logger.info(f"Research execution completed for case {case_id}")
                    
                except Exception as e:
                    logger.error(f"Error executing research plan: {e}", exc_info=True)
                    if case_id in research_status_store:
                        research_status_store[case_id].update({
                            "status": "failed",
                            "message": f"Error: {str(e)}"
                        })
        
        background_tasks.add_task(execute_research, case_id, approved_plan)
        
        return {
            "case_id": case_id,
            "status": "executing",
            "message": "Research plan approved and execution started",
            "estimated_duration": approved_plan.get("estimated_duration", "Unknown")
        }
        
    except Exception as e:
        logger.error(f"Error approving research plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving research plan: {str(e)}"
        )

@router.get("/status/{case_id}")
async def get_research_status(
    case_id: int
):
    """Get research execution status"""
    if case_id not in research_status_store:
        return {
            "case_id": case_id,
            "status": "not_started",
            "message": "No research execution in progress"
        }
    
    return research_status_store[case_id]

@router.delete("/plan/{case_id}")
async def clear_research_plan(
    case_id: int
):
    """Clear research plan for a case"""
    if case_id in research_plans_store:
        del research_plans_store[case_id]
    if case_id in research_status_store:
        del research_status_store[case_id]
    
    return {
        "case_id": case_id,
        "message": "Research plan cleared"
    }



