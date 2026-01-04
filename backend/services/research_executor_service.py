"""
Research Executor Service - Automatically execute approved research plans
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from services.osint_service import OSINTService
import logging
import asyncio

logger = logging.getLogger(__name__)

class ResearchExecutorService:
    """Service to execute research plans automatically"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.osint_service = OSINTService(db)
    
    async def execute_research_plan(
        self,
        case_id: int,
        research_plan: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute a complete research plan
        
        Args:
            case_id: Case ID
            research_plan: Research plan with phases and queries
            progress_callback: Optional callback for progress updates (phase, query, status)
            
        Returns:
            Execution results with statistics
        """
        phases = research_plan.get("research_phases", [])
        total_queries = sum(len(phase.get("queries", [])) for phase in phases)
        
        results = {
            "case_id": case_id,
            "total_phases": len(phases),
            "total_queries": total_queries,
            "executed_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "phase_results": [],
            "errors": []
        }
        
        logger.info(f"Starting research execution for case {case_id}: {total_queries} queries across {len(phases)} phases")
        
        for phase_idx, phase in enumerate(phases):
            phase_name = phase.get("phase_name", phase.get("phase", f"Phase {phase_idx + 1}"))
            queries = phase.get("queries", [])
            
            if progress_callback:
                await progress_callback(phase_idx, None, "starting", f"Starting {phase_name}")
            
            phase_result = {
                "phase": phase.get("phase", f"phase_{phase_idx}"),
                "phase_name": phase_name,
                "queries_executed": 0,
                "queries_successful": 0,
                "queries_failed": 0,
                "query_results": []
            }
            
            # Execute queries in sequence (to avoid rate limits)
            for query_idx, query in enumerate(queries):
                query_type = query.get("type")
                query_params = query.get("params", {})
                
                if progress_callback:
                    await progress_callback(
                        phase_idx, 
                        query_idx, 
                        "executing",
                        f"Executing {query_type}..."
                    )
                
                try:
                    # Execute query
                    result = await self.osint_service.execute_query(
                        query_type=query_type,
                        query_params=query_params,
                        case_id=case_id
                    )
                    
                    if result.get("status") == "completed" and not result.get("error"):
                        phase_result["queries_successful"] += 1
                        results["successful_queries"] += 1
                        query_status = "success"
                    else:
                        phase_result["queries_failed"] += 1
                        results["failed_queries"] += 1
                        query_status = "failed"
                        error_msg = result.get("error", "Unknown error")
                        results["errors"].append({
                            "phase": phase_name,
                            "query_type": query_type,
                            "error": error_msg
                        })
                    
                    phase_result["query_results"].append({
                        "query_type": query_type,
                        "status": query_status,
                        "result_id": result.get("result_id"),
                        "error": result.get("error")
                    })
                    
                    phase_result["queries_executed"] += 1
                    results["executed_queries"] += 1
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error executing query {query_type}: {e}", exc_info=True)
                    phase_result["queries_failed"] += 1
                    results["failed_queries"] += 1
                    results["errors"].append({
                        "phase": phase_name,
                        "query_type": query_type,
                        "error": str(e)
                    })
                    phase_result["query_results"].append({
                        "query_type": query_type,
                        "status": "error",
                        "error": str(e)
                    })
                    phase_result["queries_executed"] += 1
                    results["executed_queries"] += 1
            
            results["phase_results"].append(phase_result)
            
            if progress_callback:
                await progress_callback(phase_idx, None, "completed", f"Completed {phase_name}")
        
        logger.info(f"Research execution completed for case {case_id}: {results['successful_queries']}/{results['total_queries']} successful")
        
        return results
    
    async def execute_research_plan_parallel(
        self,
        case_id: int,
        research_plan: Dict[str, Any],
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Execute research plan with parallel queries (faster but may hit rate limits)
        
        Args:
            case_id: Case ID
            research_plan: Research plan
            max_concurrent: Maximum concurrent queries
            
        Returns:
            Execution results
        """
        phases = research_plan.get("research_phases", [])
        total_queries = sum(len(phase.get("queries", [])) for phase in phases)
        
        results = {
            "case_id": case_id,
            "total_phases": len(phases),
            "total_queries": total_queries,
            "executed_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "phase_results": [],
            "errors": []
        }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_query_with_semaphore(phase_idx: int, query_idx: int, query: Dict):
            async with semaphore:
                query_type = query.get("type")
                query_params = query.get("params", {})
                
                try:
                    result = await self.osint_service.execute_query(
                        query_type=query_type,
                        query_params=query_params,
                        case_id=case_id
                    )
                    
                    if result.get("status") == "completed" and not result.get("error"):
                        return {"status": "success", "result": result, "query_type": query_type}
                    else:
                        return {
                            "status": "failed",
                            "error": result.get("error", "Unknown error"),
                            "query_type": query_type
                        }
                except Exception as e:
                    logger.error(f"Error executing query {query_type}: {e}", exc_info=True)
                    return {"status": "error", "error": str(e), "query_type": query_type}
        
        for phase_idx, phase in enumerate(phases):
            phase_name = phase.get("phase_name", phase.get("phase", f"Phase {phase_idx + 1}"))
            queries = phase.get("queries", [])
            
            # Execute all queries in phase in parallel (with semaphore limit)
            query_tasks = [
                execute_query_with_semaphore(phase_idx, query_idx, query)
                for query_idx, query in enumerate(queries)
            ]
            
            query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
            
            phase_result = {
                "phase": phase.get("phase", f"phase_{phase_idx}"),
                "phase_name": phase_name,
                "queries_executed": len(queries),
                "queries_successful": sum(1 for r in query_results if isinstance(r, dict) and r.get("status") == "success"),
                "queries_failed": sum(1 for r in query_results if isinstance(r, dict) and r.get("status") != "success" or isinstance(r, Exception)),
                "query_results": query_results
            }
            
            results["phase_results"].append(phase_result)
            results["executed_queries"] += phase_result["queries_executed"]
            results["successful_queries"] += phase_result["queries_successful"]
            results["failed_queries"] += phase_result["queries_failed"]
            
            # Collect errors
            for result in query_results:
                if isinstance(result, Exception):
                    results["errors"].append({
                        "phase": phase_name,
                        "error": str(result)
                    })
                elif isinstance(result, dict) and result.get("status") != "success":
                    results["errors"].append({
                        "phase": phase_name,
                        "query_type": result.get("query_type"),
                        "error": result.get("error", "Unknown error")
                    })
        
        return results



