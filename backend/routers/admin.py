"""
Admin router - Manage AI classification, feedback, and training
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from sqlalchemy import select, func, desc, String, cast
from services.db_json_filters import json_array_contains_column
from models.ai_classification import (
    AIClassification, 
    ClassificationCategory, 
    ClassificationFeedback,
    AIModelTraining
)
from models.case import Case
from services.ai_classification_service import AIClassificationService
from pydantic import BaseModel
from passlib.context import CryptContext
from app.dependencies import get_current_user
from models.user import User
import logging

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ========== Schemas ==========

class ClassificationResponse(BaseModel):
    id: int
    osint_result_id: Optional[int]
    case_id: int
    content_type: str
    content_text: str
    sentiment: str
    sentiment_score: float
    sentiment_confidence: float
    categories: List[str]
    concepts: List[str]
    topics: List[str]
    confidence_score: float
    has_feedback: bool
    feedback_correct: Optional[bool]
    created_at: str

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_type: str  # sentiment, topic, theme, industry
    keywords: Optional[List[str]] = []
    examples_positive: Optional[List[str]] = []
    examples_negative: Optional[List[str]] = []
    is_active: bool = True
    priority: int = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    examples_positive: Optional[List[str]] = None
    examples_negative: Optional[List[str]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category_type: str
    keywords: List[str]
    examples_positive: List[str]
    examples_negative: List[str]
    is_active: bool
    priority: int
    created_at: str
    updated_at: Optional[str]

class FeedbackCreate(BaseModel):
    classification_id: int
    feedback_type: str  # correct, incorrect, partial
    correct_sentiment: Optional[str] = None
    correct_categories: Optional[List[str]] = None
    correct_concepts: Optional[List[str]] = None
    feedback_notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    classification_id: int
    feedback_type: str
    correct_sentiment: Optional[str]
    correct_categories: Optional[List[str]]
    correct_concepts: Optional[List[str]]
    feedback_notes: Optional[str]
    is_used_for_training: bool
    created_at: str


class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    password: str
    is_superuser: bool = False


class ChangePasswordRequest(BaseModel):
    new_password: str

# ========== Classification Management ==========

@router.get("/classifications", response_model=List[ClassificationResponse])
async def list_classifications(
    case_id: Optional[int] = Query(None),
    sentiment: Optional[str] = Query(None),
    has_feedback: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List AI classifications with filters"""
    try:
        query = select(AIClassification)
        
        if case_id:
            query = query.where(AIClassification.case_id == case_id)
        if sentiment:
            query = query.where(AIClassification.sentiment == sentiment)
        if has_feedback is not None:
            query = query.where(AIClassification.has_feedback == has_feedback)
        
        query = query.order_by(desc(AIClassification.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        classifications = result.scalars().all()
        
        return [
            ClassificationResponse(
                id=c.id,
                osint_result_id=c.osint_result_id,
                case_id=c.case_id,
                content_type=c.content_type,
                content_text=c.content_text[:200] + "..." if len(c.content_text) > 200 else c.content_text,
                sentiment=c.sentiment,
                sentiment_score=c.sentiment_score,
                sentiment_confidence=c.sentiment_confidence,
                categories=c.categories or [],
                concepts=c.concepts or [],
                topics=c.topics or [],
                confidence_score=c.confidence_score,
                has_feedback=c.has_feedback,
                feedback_correct=c.feedback_correct,
                created_at=c.created_at.isoformat() if c.created_at else ""
            )
            for c in classifications
        ]
    except Exception as e:
        logger.error(f"Error listing classifications: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing classifications: {str(e)}"
        )

@router.get("/classifications/{classification_id}", response_model=ClassificationResponse)
async def get_classification(
    classification_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific classification with full details"""
    try:
        result = await db.execute(
            select(AIClassification).where(AIClassification.id == classification_id)
        )
        classification = result.scalar_one_or_none()
        
        if not classification:
            raise HTTPException(status_code=404, detail="Classification not found")
        
        return ClassificationResponse(
            id=classification.id,
            osint_result_id=classification.osint_result_id,
            case_id=classification.case_id,
            content_type=classification.content_type,
            content_text=classification.content_text,
            sentiment=classification.sentiment,
            sentiment_score=classification.sentiment_score,
            sentiment_confidence=classification.sentiment_confidence,
            categories=classification.categories or [],
            concepts=classification.concepts or [],
            topics=classification.topics or [],
            confidence_score=classification.confidence_score,
            has_feedback=classification.has_feedback,
            feedback_correct=classification.feedback_correct,
            created_at=classification.created_at.isoformat() if classification.created_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting classification: {str(e)}"
        )

@router.post("/classifications/{case_id}/reclassify")
async def reclassify_case(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Reclassify all OSINT results for a case (useful after updating categories)"""
    try:
        service = AIClassificationService(db)
        classifications = await service.classify_all_case_osint(case_id)
        
        return {
            "case_id": case_id,
            "classifications_created": len(classifications),
            "message": f"Reclassified {len(classifications)} OSINT results"
        }
    except Exception as e:
        logger.error(f"Error reclassifying case: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reclassifying case: {str(e)}"
        )

# ========== Category Management (KPIs de Categorització) ==========

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    category_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List classification categories"""
    try:
        query = select(ClassificationCategory)
        
        if category_type:
            query = query.where(ClassificationCategory.category_type == category_type)
        if is_active is not None:
            query = query.where(ClassificationCategory.is_active == is_active)
        
        query = query.order_by(desc(ClassificationCategory.priority), ClassificationCategory.name)
        
        result = await db.execute(query)
        categories = result.scalars().all()
        
        return [
            CategoryResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                category_type=c.category_type,
                keywords=c.keywords or [],
                examples_positive=c.examples_positive or [],
                examples_negative=c.examples_negative or [],
                is_active=c.is_active,
                priority=c.priority,
                created_at=c.created_at.isoformat() if c.created_at else "",
                updated_at=c.updated_at.isoformat() if c.updated_at else None
            )
            for c in categories
        ]
    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing categories: {str(e)}"
        )

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new classification category"""
    try:
        # Check if category with same name exists
        existing = await db.execute(
            select(ClassificationCategory).where(ClassificationCategory.name == category_data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_data.name}' already exists"
            )
        
        category = ClassificationCategory(
            name=category_data.name,
            description=category_data.description,
            category_type=category_data.category_type,
            keywords=category_data.keywords or [],
            examples_positive=category_data.examples_positive or [],
            examples_negative=category_data.examples_negative or [],
            is_active=category_data.is_active,
            priority=category_data.priority,
            created_by=current_user.username or str(current_user.id),
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        return CategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            category_type=category.category_type,
            keywords=category.keywords or [],
            examples_positive=category.examples_positive or [],
            examples_negative=category.examples_negative or [],
            is_active=category.is_active,
            priority=category.priority,
            created_at=category.created_at.isoformat() if category.created_at else "",
            updated_at=category.updated_at.isoformat() if category.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating category: {str(e)}"
        )

@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a classification category"""
    try:
        result = await db.execute(
            select(ClassificationCategory).where(ClassificationCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Update fields
        if category_data.name is not None:
            category.name = category_data.name
        if category_data.description is not None:
            category.description = category_data.description
        if category_data.category_type is not None:
            category.category_type = category_data.category_type
        if category_data.keywords is not None:
            category.keywords = category_data.keywords
        if category_data.examples_positive is not None:
            category.examples_positive = category_data.examples_positive
        if category_data.examples_negative is not None:
            category.examples_negative = category_data.examples_negative
        if category_data.is_active is not None:
            category.is_active = category_data.is_active
        if category_data.priority is not None:
            category.priority = category_data.priority
        
        await db.commit()
        await db.refresh(category)
        
        return CategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            category_type=category.category_type,
            keywords=category.keywords or [],
            examples_positive=category.examples_positive or [],
            examples_negative=category.examples_negative or [],
            is_active=category.is_active,
            priority=category.priority,
            created_at=category.created_at.isoformat() if category.created_at else "",
            updated_at=category.updated_at.isoformat() if category.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating category: {str(e)}"
        )

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a classification category"""
    try:
        result = await db.execute(
            select(ClassificationCategory).where(ClassificationCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        await db.delete(category)
        await db.commit()
        
        return {"message": f"Category {category_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting category: {str(e)}"
        )

# ========== Feedback Management ==========

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def add_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add feedback to a classification for training"""
    try:
        service = AIClassificationService(db)
        feedback = await service.add_feedback(
            classification_id=feedback_data.classification_id,
            feedback_type=feedback_data.feedback_type,
            correct_sentiment=feedback_data.correct_sentiment,
            correct_categories=feedback_data.correct_categories,
            correct_concepts=feedback_data.correct_concepts,
            feedback_notes=feedback_data.feedback_notes,
            feedback_by=current_user.username or str(current_user.id),
        )
        
        return FeedbackResponse(
            id=feedback.id,
            classification_id=feedback.classification_id,
            feedback_type=feedback.feedback_type,
            correct_sentiment=feedback.correct_sentiment,
            correct_categories=feedback.correct_categories or [],
            correct_concepts=feedback.correct_concepts or [],
            feedback_notes=feedback.feedback_notes,
            is_used_for_training=feedback.is_used_for_training,
            created_at=feedback.created_at.isoformat() if feedback.created_at else ""
        )
    except Exception as e:
        logger.error(f"Error adding feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding feedback: {str(e)}"
        )

@router.get("/feedback", response_model=List[FeedbackResponse])
async def list_feedback(
    classification_id: Optional[int] = Query(None),
    feedback_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List feedback entries"""
    try:
        query = select(ClassificationFeedback)
        
        if classification_id:
            query = query.where(ClassificationFeedback.classification_id == classification_id)
        if feedback_type:
            query = query.where(ClassificationFeedback.feedback_type == feedback_type)
        
        query = query.order_by(desc(ClassificationFeedback.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        feedbacks = result.scalars().all()
        
        return [
            FeedbackResponse(
                id=f.id,
                classification_id=f.classification_id,
                feedback_type=f.feedback_type,
                correct_sentiment=f.correct_sentiment,
                correct_categories=f.correct_categories or [],
                correct_concepts=f.correct_concepts or [],
                feedback_notes=f.feedback_notes,
                is_used_for_training=f.is_used_for_training,
                created_at=f.created_at.isoformat() if f.created_at else ""
            )
            for f in feedbacks
        ]
    except Exception as e:
        logger.error(f"Error listing feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing feedback: {str(e)}"
        )

# ========== Statistics ==========

@router.get("/stats/classifications")
async def get_classification_stats(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics on classifications and feedback"""
    try:
        service = AIClassificationService(db)
        stats = await service.get_classification_stats(case_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting classification stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}"
        )

@router.get("/stats/categories")
async def get_category_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get statistics on category usage"""
    try:
        # Count classifications per category
        result = await db.execute(
            select(
                ClassificationCategory.name,
                func.count(AIClassification.id).label("usage_count"),
            )
            .join(
                AIClassification,
                json_array_contains_column(AIClassification.categories, ClassificationCategory.name),
            )
            .group_by(ClassificationCategory.name)
        )
        
        category_usage = {}
        for row in result.all():
            category_usage[row.name] = row.usage_count
        
        # Total categories
        total_result = await db.execute(
            select(func.count(ClassificationCategory.id))
        )
        total_categories = total_result.scalar() or 0
        
        active_result = await db.execute(
            select(func.count(ClassificationCategory.id))
            .where(ClassificationCategory.is_active == True)
        )
        active_categories = active_result.scalar() or 0
        
        return {
            "total_categories": total_categories,
            "active_categories": active_categories,
            "category_usage": category_usage
        }
    except Exception as e:
        logger.error(f"Error getting category stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting category stats: {str(e)}"
        )


# ── User management ───────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users. Requires superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requereix permisos d'administrador")
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new user. Requires superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requereix permisos d'administrador")

    existing = (
        await db.execute(select(User).where(User.email == data.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="L'email ja existeix")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=_pwd_context.hash(data.password),
        is_active=True,
        is_superuser=data.is_superuser,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate or deactivate a user. Requires superuser. Cannot deactivate yourself."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requereix permisos d'administrador")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No pots desactivar el teu propi compte")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    user.is_active = not user.is_active
    await db.commit()
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


@router.patch("/users/{user_id}/make-superuser")
async def make_superuser(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grant superuser privileges to a user. Requires superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requereix permisos d'administrador")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    user.is_superuser = True
    await db.commit()
    return {"id": user.id, "email": user.email, "is_superuser": user.is_superuser}


@router.patch("/users/{user_id}/password")
async def change_user_password(
    user_id: int,
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a user's password. Requires superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requereix permisos d'administrador")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contrasenya ha de tenir mínim 8 caràcters")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    user.hashed_password = _pwd_context.hash(data.new_password)
    await db.commit()
    return {"id": user.id, "email": user.email, "message": "Contrasenya actualitzada"}

