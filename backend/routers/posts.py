"""
Posts router - View raw social media posts with AI classifications
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from sqlalchemy import select, and_, or_, func, String, cast
from models.ai_classification import AIClassification
from models.osint import OSINTResult, OSINTQuery
from models.case import Case
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/posts", tags=["Posts"])

class PostResponse(BaseModel):
    """Response model for a post with classification"""
    id: int
    osint_result_id: Optional[int]
    case_id: int
    content_type: str
    content_text: str
    content_metadata: Dict[str, Any]
    sentiment: str
    sentiment_score: float
    sentiment_confidence: float
    categories: List[str]
    concepts: List[str]
    topics: List[str]
    confidence_score: float
    created_at: str
    # Raw OSINT data
    raw_data: Optional[Dict[str, Any]] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    author: Optional[str] = None
    engagement: Optional[Dict[str, Any]] = None  # likes, comments, shares, views

@router.get("/case/{case_id}", response_model=List[PostResponse])
async def get_case_posts(
    case_id: int,
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: positive, negative, neutral"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    concept: Optional[str] = Query(None, description="Filter by concept name"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    search_text: Optional[str] = Query(None, description="Search in content text"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all posts for a case with optional filters"""
    try:
        # Build query
        query = select(AIClassification).where(AIClassification.case_id == case_id)
        
        # Apply filters
        if sentiment:
            query = query.where(AIClassification.sentiment == sentiment)
        
        if category:
            # Filter by category in JSON array
            query = query.where(
                func.json_contains(
                    AIClassification.categories,
                    func.json_quote(category)
                )
            )
        
        if concept:
            # Filter by concept in JSON array
            query = query.where(
                func.json_contains(
                    AIClassification.concepts,
                    func.json_quote(concept)
                )
            )
        
        if content_type:
            query = query.where(AIClassification.content_type == content_type)
        
        if search_text:
            query = query.where(AIClassification.content_text.contains(search_text))
        
        # Order by date (newest first)
        query = query.order_by(AIClassification.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        classifications = result.scalars().all()
        
        # Build response with raw OSINT data
        posts = []
        for classification in classifications:
            raw_data = None
            source_platform = None
            source_url = None
            author = None
            engagement = None
            
            # Get raw OSINT data if available
            if classification.osint_result_id:
                osint_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.id == classification.osint_result_id)
                )
                osint = osint_result.scalar_one_or_none()
                
                if osint and osint.data:
                    raw_data = osint.data
                    
                    # Extract metadata from raw data
                    if isinstance(raw_data, dict):
                        # Try to extract platform-specific data
                        if "data" in raw_data and isinstance(raw_data["data"], list):
                            # EnsembleData structure
                            for item in raw_data["data"]:
                                if isinstance(item, dict):
                                    source_platform = item.get("platform") or item.get("source")
                                    source_url = item.get("url") or item.get("post_url") or item.get("tweet_url")
                                    author = item.get("author") or item.get("username") or item.get("user", {}).get("username")
                                    
                                    # Extract engagement metrics
                                    engagement = {
                                        "likes": item.get("like_count") or item.get("likes") or 0,
                                        "comments": item.get("comment_count") or item.get("comments") or 0,
                                        "shares": item.get("share_count") or item.get("shares") or item.get("retweets") or 0,
                                        "views": item.get("view_count") or item.get("views") or 0
                                    }
                                    break
                        else:
                            # Direct structure
                            source_platform = raw_data.get("platform") or raw_data.get("source")
                            source_url = raw_data.get("url") or raw_data.get("post_url")
                            author = raw_data.get("author") or raw_data.get("username")
                            engagement = {
                                "likes": raw_data.get("like_count") or raw_data.get("likes") or 0,
                                "comments": raw_data.get("comment_count") or raw_data.get("comments") or 0,
                                "shares": raw_data.get("share_count") or raw_data.get("shares") or 0,
                                "views": raw_data.get("view_count") or raw_data.get("views") or 0
                            }
            
            posts.append(PostResponse(
                id=classification.id,
                osint_result_id=classification.osint_result_id,
                case_id=classification.case_id,
                content_type=classification.content_type,
                content_text=classification.content_text,
                content_metadata=classification.content_metadata or {},
                sentiment=classification.sentiment,
                sentiment_score=classification.sentiment_score or 0.0,
                sentiment_confidence=classification.sentiment_confidence or 0.0,
                categories=classification.categories or [],
                concepts=classification.concepts or [],
                topics=classification.topics or [],
                confidence_score=classification.confidence_score or 0.0,
                created_at=classification.created_at.isoformat() if classification.created_at else "",
                raw_data=raw_data,
                source_platform=source_platform,
                source_url=source_url,
                author=author,
                engagement=engagement
            ))
        
        return posts
        
    except Exception as e:
        logger.error(f"Error getting case posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting posts: {str(e)}"
        )

@router.get("/case/{case_id}/stats")
async def get_posts_stats(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about posts for a case"""
    try:
        # Count by sentiment
        sentiment_counts = {}
        for sentiment in ["positive", "negative", "neutral"]:
            result = await db.execute(
                select(func.count(AIClassification.id)).where(
                    and_(
                        AIClassification.case_id == case_id,
                        AIClassification.sentiment == sentiment
                    )
                )
            )
            sentiment_counts[sentiment] = result.scalar() or 0
        
        # Count by content type
        content_type_counts = {}
        result = await db.execute(
            select(
                AIClassification.content_type,
                func.count(AIClassification.id).label("count")
            )
            .where(AIClassification.case_id == case_id)
            .group_by(AIClassification.content_type)
        )
        for row in result.all():
            content_type_counts[row.content_type] = row.count
        
        # Get all categories used
        all_categories = set()
        result = await db.execute(
            select(AIClassification.categories).where(AIClassification.case_id == case_id)
        )
        for row in result.all():
            if row.categories:
                all_categories.update(row.categories)
        
        # Get all concepts used
        all_concepts = set()
        result = await db.execute(
            select(AIClassification.concepts).where(AIClassification.case_id == case_id)
        )
        for row in result.all():
            if row.concepts:
                all_concepts.update(row.concepts)
        
        return {
            "total_posts": sum(sentiment_counts.values()),
            "sentiment_distribution": sentiment_counts,
            "content_type_distribution": content_type_counts,
            "available_categories": list(all_categories),
            "available_concepts": list(all_concepts)
        }
        
    except Exception as e:
        logger.error(f"Error getting posts stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting posts stats: {str(e)}"
        )

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific post by classification ID"""
    try:
        result = await db.execute(
            select(AIClassification).where(AIClassification.id == post_id)
        )
        classification = result.scalar_one_or_none()
        
        if not classification:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get raw OSINT data
        raw_data = None
        source_platform = None
        source_url = None
        author = None
        engagement = None
        
        if classification.osint_result_id:
            osint_result = await db.execute(
                select(OSINTResult).where(OSINTResult.id == classification.osint_result_id)
            )
            osint = osint_result.scalar_one_or_none()
            
            if osint and osint.data:
                raw_data = osint.data
                
                if isinstance(raw_data, dict):
                    if "data" in raw_data and isinstance(raw_data["data"], list):
                        for item in raw_data["data"]:
                            if isinstance(item, dict):
                                source_platform = item.get("platform") or item.get("source")
                                source_url = item.get("url") or item.get("post_url")
                                author = item.get("author") or item.get("username")
                                engagement = {
                                    "likes": item.get("like_count") or 0,
                                    "comments": item.get("comment_count") or 0,
                                    "shares": item.get("share_count") or 0,
                                    "views": item.get("view_count") or 0
                                }
                                break
                    else:
                        source_platform = raw_data.get("platform")
                        source_url = raw_data.get("url")
                        author = raw_data.get("author")
                        engagement = {
                            "likes": raw_data.get("like_count") or 0,
                            "comments": raw_data.get("comment_count") or 0,
                            "shares": raw_data.get("share_count") or 0,
                            "views": raw_data.get("view_count") or 0
                        }
        
        return PostResponse(
            id=classification.id,
            osint_result_id=classification.osint_result_id,
            case_id=classification.case_id,
            content_type=classification.content_type,
            content_text=classification.content_text,
            content_metadata=classification.content_metadata or {},
            sentiment=classification.sentiment,
            sentiment_score=classification.sentiment_score or 0.0,
            sentiment_confidence=classification.sentiment_confidence or 0.0,
            categories=classification.categories or [],
            concepts=classification.concepts or [],
            topics=classification.topics or [],
            confidence_score=classification.confidence_score or 0.0,
            created_at=classification.created_at.isoformat() if classification.created_at else "",
            raw_data=raw_data,
            source_platform=source_platform,
            source_url=source_url,
            author=author,
            engagement=engagement
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting post: {str(e)}"
        )

