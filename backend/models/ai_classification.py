"""
AI Classification models - Store AI classifications and feedback for training
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class AIClassification(Base):
    """Store AI classifications of content (posts, comments, etc.)"""
    __tablename__ = "ai_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    osint_result_id = Column(Integer, ForeignKey("osint_results.id"), nullable=True)  # Link to OSINT data
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # Content being classified
    content_type = Column(String, nullable=False)  # post, comment, article, etc.
    content_text = Column(Text, nullable=False)
    content_metadata = Column(JSON)  # Original metadata from OSINT
    
    # AI Classification results
    sentiment = Column(String, nullable=False)  # positive, negative, neutral
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_confidence = Column(Float, default=0.0)  # 0-1
    
    # Categories/Topics
    categories = Column(JSON)  # List of category names
    concepts = Column(JSON)  # List of extracted concepts
    topics = Column(JSON)  # List of topics
    
    # Classification metadata
    classification_model = Column(String)  # Which AI model was used
    classification_version = Column(String)  # Model version for tracking
    confidence_score = Column(Float, default=0.0)  # Overall confidence
    
    # Feedback (for training)
    has_feedback = Column(Boolean, default=False)
    feedback_correct = Column(Boolean, nullable=True)  # True if classification was correct
    feedback_notes = Column(Text, nullable=True)  # Admin notes on feedback
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    feedback_at = Column(DateTime(timezone=True), nullable=True)

class ClassificationCategory(Base):
    """Editable categories for classification (KPIs de categorització)"""
    __tablename__ = "classification_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category_type = Column(String, nullable=False)  # sentiment, topic, theme, industry, etc.
    
    # Classification rules (for AI)
    keywords = Column(JSON)  # List of keywords that indicate this category
    examples_positive = Column(JSON)  # Positive examples for training
    examples_negative = Column(JSON)  # Negative examples for training
    
    # Admin settings
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority = checked first
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String, nullable=True)  # Admin user who created it

class ClassificationFeedback(Base):
    """Human feedback on AI classifications for training"""
    __tablename__ = "classification_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    classification_id = Column(Integer, ForeignKey("ai_classifications.id"), nullable=False)
    
    # Feedback details
    feedback_type = Column(String, nullable=False)  # correct, incorrect, partial
    correct_sentiment = Column(String, nullable=True)  # What sentiment should be
    correct_categories = Column(JSON, nullable=True)  # What categories should be
    correct_concepts = Column(JSON, nullable=True)  # What concepts should be
    
    # Feedback metadata
    feedback_by = Column(String, nullable=True)  # Admin user who provided feedback
    feedback_notes = Column(Text, nullable=True)
    is_used_for_training = Column(Boolean, default=False)  # Whether used to train model
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    classification = relationship("AIClassification", backref="feedbacks")

class AIModelTraining(Base):
    """Track AI model training sessions and improvements"""
    __tablename__ = "ai_model_training"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    
    # Training data
    training_samples_count = Column(Integer, default=0)
    feedback_samples_count = Column(Integer, default=0)
    
    # Training results
    accuracy_before = Column(Float, nullable=True)
    accuracy_after = Column(Float, nullable=True)
    improvement = Column(Float, nullable=True)
    
    # Training metadata
    training_date = Column(DateTime(timezone=True), server_default=func.now())
    trained_by = Column(String, nullable=True)
    training_notes = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, training, completed, failed
    is_active = Column(Boolean, default=False)  # Whether this version is active



