"""
Tavily API router — Search, Extract, Crawl, Map, Research.
https://docs.tavily.com/documentation/api-reference/introduction
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.database import get_db
from integrations.tavily_api import TavilyAPIService
from models.user import User
from schemas.osint import OSINTResultResponse
from services.osint_service import OSINTService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _require_tavily() -> TavilyAPIService:
    svc = TavilyAPIService()
    if not svc.configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TAVILY_API_KEY no configurada al backend (.env)",
        )
    return svc


@router.post("/search", response_model=OSINTResultResponse)
async def tavily_search(
    query: str,
    max_results: int = 10,
    search_depth: str = "advanced",
    topic: str = "news",
    case_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_tavily()
    result = await OSINTService(db).execute_query(
        query_type="tavily",
        query_params={
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
        },
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)


@router.post("/extract", response_model=OSINTResultResponse)
async def tavily_extract(
    urls: str,
    extract_depth: str = "basic",
    format: str = "markdown",
    case_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract content from URLs (comma-separated)."""
    _require_tavily()
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    result = await OSINTService(db).execute_query(
        query_type="tavily_extract",
        query_params={
            "urls": url_list,
            "extract_depth": extract_depth,
            "format": format,
        },
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)


@router.post("/crawl", response_model=OSINTResultResponse)
async def tavily_crawl(
    url: str,
    instructions: Optional[str] = None,
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    extract_depth: str = "basic",
    case_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_tavily()
    result = await OSINTService(db).execute_query(
        query_type="tavily_crawl",
        query_params={
            "url": url,
            "instructions": instructions,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "limit": limit,
            "extract_depth": extract_depth,
        },
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)


@router.post("/map", response_model=OSINTResultResponse)
async def tavily_map(
    url: str,
    instructions: Optional[str] = None,
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    case_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_tavily()
    result = await OSINTService(db).execute_query(
        query_type="tavily_map",
        query_params={
            "url": url,
            "instructions": instructions,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "limit": limit,
        },
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)


@router.post("/research", response_model=OSINTResultResponse)
async def tavily_create_research(
    input: str,
    model: str = "auto",
    wait: bool = True,
    max_wait_seconds: int = 300,
    case_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create research task; optionally wait until completed and persist sources to case."""
    _require_tavily()
    result = await OSINTService(db).execute_query(
        query_type="tavily_research",
        query_params={
            "input": input,
            "model": model,
            "wait": wait,
            "max_wait_seconds": max_wait_seconds,
        },
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)


@router.get("/research/{request_id}")
async def tavily_get_research(
    request_id: str,
    case_id: Optional[int] = None,
    persist: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get research task status. Set persist=true + case_id to save completed results to case."""
    _require_tavily()
    if persist and case_id:
        result = await OSINTService(db).execute_query(
            query_type="tavily_research_get",
            query_params={"request_id": request_id},
            case_id=case_id,
        )
        return OSINTResultResponse.model_validate(result)

    svc = TavilyAPIService()
    return await svc.get_research(request_id)
