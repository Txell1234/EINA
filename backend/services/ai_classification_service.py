"""
AI Classification Service - Classify all OSINT content through AI before visualization
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List, Optional
from models.ai_classification import AIClassification, ClassificationCategory, ClassificationFeedback, AIModelTraining
from models.osint import OSINTResult
from models.case import Case
from services.ai_service import AIService
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class AIClassificationService:
    """Service to classify OSINT content through AI and manage feedback for training"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
    
    async def classify_osint_result(
        self,
        osint_result: OSINTResult,
        case_id: int
    ) -> AIClassification:
        """Classify a single OSINT result through AI"""
        try:
            # Extract content from OSINT result
            content_data = osint_result.data
            if not content_data:
                logger.warning(f"OSINT result {osint_result.id} has no data")
                return None
            
            # Extract text content based on data structure
            content_text = self._extract_text_from_data(content_data)
            if not content_text:
                logger.warning(f"No text content found in OSINT result {osint_result.id}")
                return None
            
            # Get active categories for classification
            categories_result = await self.db.execute(
                select(ClassificationCategory).where(
                    ClassificationCategory.is_active == True
                ).order_by(ClassificationCategory.priority.desc())
            )
            active_categories = categories_result.scalars().all()
            
            # Classify with AI
            classification_result = await self._classify_with_ai(
                content_text=content_text,
                categories=active_categories,
                metadata=content_data
            )
            
            # Create classification record
            classification = AIClassification(
                osint_result_id=osint_result.id,
                case_id=case_id,
                content_type=self._determine_content_type(content_data),
                content_text=content_text[:5000],  # Limit text length
                content_metadata=content_data,
                sentiment=classification_result.get("sentiment", "neutral"),
                sentiment_score=classification_result.get("sentiment_score", 0.0),
                sentiment_confidence=classification_result.get("sentiment_confidence", 0.0),
                categories=classification_result.get("categories", []),
                concepts=classification_result.get("concepts", []),
                topics=classification_result.get("topics", []),
                classification_model=settings.OPENAI_MODEL if hasattr(settings, 'OPENAI_MODEL') else "gpt-4",
                classification_version="1.0",
                confidence_score=classification_result.get("confidence", 0.0)
            )
            
            self.db.add(classification)
            await self.db.flush()
            
            logger.info(f"Classified OSINT result {osint_result.id} with sentiment: {classification.sentiment}")
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying OSINT result {osint_result.id}: {e}", exc_info=True)
            return None
    
    async def classify_all_case_osint(self, case_id: int) -> List[AIClassification]:
        """Classify all OSINT results for a case"""
        try:
            # Get all OSINT results for this case
            from models.osint import OSINTQuery
            
            queries_result = await self.db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            all_classifications = []
            
            for query in queries:
                results_result = await self.db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                
                for result in results:
                    # Check if already classified
                    existing = await self.db.execute(
                        select(AIClassification).where(
                            AIClassification.osint_result_id == result.id
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Skip if already classified
                    
                    classification = await self.classify_osint_result(result, case_id)
                    if classification:
                        all_classifications.append(classification)
            
            await self.db.commit()
            logger.info(f"Classified {len(all_classifications)} OSINT results for case {case_id}")
            return all_classifications
            
        except Exception as e:
            logger.error(f"Error classifying all OSINT for case {case_id}: {e}", exc_info=True)
            await self.db.rollback()
            return []
    
    async def _classify_with_ai(
        self,
        content_text: str,
        categories: List[ClassificationCategory],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify content using AI with active categories"""
        if not self.ai_service.client:
            # Fallback classification without AI
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 0.5,
                "categories": [],
                "concepts": [],
                "topics": [],
                "confidence": 0.5
            }
        
        try:
            # Build category context for AI
            category_context = ""
            if categories:
                category_list = [f"- {cat.name}: {cat.description or ''}" for cat in categories[:20]]
                category_context = f"\n\nCategories to consider:\n" + "\n".join(category_list)
            
            system_prompt = f"""Eres un experto en análisis de contenido y clasificación de sentimiento.
            
Analiza el siguiente contenido y proporciona:
1. Sentimiento: positive, negative, o neutral (con score de -1 a 1)
2. Categorías relevantes de la lista proporcionada
3. Conceptos clave mencionados
4. Temas principales

Responde en formato JSON con esta estructura:
{{
    "sentiment": "positive|negative|neutral",
    "sentiment_score": -1.0 a 1.0,
    "sentiment_confidence": 0.0 a 1.0,
    "categories": ["categoria1", "categoria2"],
    "concepts": ["concepto1", "concepto2"],
    "topics": ["tema1", "tema2"],
    "confidence": 0.0 a 1.0
}}
{category_context}"""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_text[:4000]}  # Limit text length
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                timeout=30.0,
            )
            
            content = response.choices[0].message.content
            try:
                # Try to parse JSON response
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If not JSON, try to extract sentiment from text
                content_lower = content.lower()
                sentiment = "neutral"
                sentiment_score = 0.0
                
                if "positive" in content_lower or "positivo" in content_lower:
                    sentiment = "positive"
                    sentiment_score = 0.5
                elif "negative" in content_lower or "negativo" in content_lower:
                    sentiment = "negative"
                    sentiment_score = -0.5
                
                return {
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "sentiment_confidence": 0.7,
                    "categories": [],
                    "concepts": [],
                    "topics": [],
                    "confidence": 0.7
                }
                
        except Exception as e:
            logger.error(f"Error in AI classification: {e}", exc_info=True)
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 0.5,
                "categories": [],
                "concepts": [],
                "topics": [],
                "confidence": 0.5
            }
    
    def _extract_text_from_data(self, data: Dict[str, Any]) -> str:
        """Extract text content from OSINT data structure"""
        if isinstance(data, dict):
            # Try common text fields
            text_fields = ["text", "description", "caption", "content", "title", "message", "body"]
            for field in text_fields:
                if field in data and data[field]:
                    text = str(data[field])
                    if text.strip():
                        return text
            
            # Try nested structures
            if "data" in data and isinstance(data["data"], list):
                texts = []
                for item in data["data"]:
                    if isinstance(item, dict):
                        for field in text_fields:
                            if field in item and item[field]:
                                texts.append(str(item[field]))
                if texts:
                    return " ".join(texts)
            
            # Try articles (News API structure)
            if "articles" in data and isinstance(data["articles"], list):
                texts = []
                for article in data["articles"]:
                    if isinstance(article, dict):
                        title = article.get("title", "")
                        description = article.get("description", "")
                        if title:
                            texts.append(title)
                        if description:
                            texts.append(description)
                if texts:
                    return " ".join(texts)
        
        elif isinstance(data, list):
            # If data is a list, try to extract text from each item
            texts = []
            for item in data:
                if isinstance(item, dict):
                    text = self._extract_text_from_data(item)
                    if text:
                        texts.append(text)
            if texts:
                return " ".join(texts)
        
        return ""
    
    def _determine_content_type(self, data: Dict[str, Any]) -> str:
        """Determine content type from OSINT data"""
        if isinstance(data, dict):
            # Check for platform indicators
            if "platform" in data:
                return data["platform"].lower()
            if "source" in data:
                source = str(data["source"]).lower()
                if "instagram" in source or "ig" in source:
                    return "instagram_post"
                if "tiktok" in source or "tt" in source:
                    return "tiktok_video"
                if "twitter" in source or "x" in source or "tw" in source:
                    return "tweet"
                if "youtube" in source or "yt" in source:
                    return "youtube_video"
                if "reddit" in source or "rd" in source:
                    return "reddit_post"
                if "news" in source:
                    return "news_article"
        
        return "unknown"
    
    async def add_feedback(
        self,
        classification_id: int,
        feedback_type: str,
        correct_sentiment: Optional[str] = None,
        correct_categories: Optional[List[str]] = None,
        correct_concepts: Optional[List[str]] = None,
        feedback_notes: Optional[str] = None,
        feedback_by: Optional[str] = None
    ) -> ClassificationFeedback:
        """Add human feedback to a classification for training"""
        try:
            # Get classification
            classification_result = await self.db.execute(
                select(AIClassification).where(AIClassification.id == classification_id)
            )
            classification = classification_result.scalar_one_or_none()
            
            if not classification:
                raise ValueError(f"Classification {classification_id} not found")
            
            # Create feedback
            feedback = ClassificationFeedback(
                classification_id=classification_id,
                feedback_type=feedback_type,
                correct_sentiment=correct_sentiment,
                correct_categories=correct_categories,
                correct_concepts=correct_concepts,
                feedback_notes=feedback_notes,
                feedback_by=feedback_by or "admin"
            )
            
            self.db.add(feedback)
            
            # Update classification with feedback
            classification.has_feedback = True
            classification.feedback_correct = (feedback_type == "correct")
            classification.feedback_notes = feedback_notes
            classification.feedback_at = func.now()
            
            await self.db.commit()
            await self.db.refresh(feedback)
            
            logger.info(f"Added feedback for classification {classification_id}")
            return feedback
            
        except Exception as e:
            logger.error(f"Error adding feedback: {e}", exc_info=True)
            await self.db.rollback()
            raise
    
    async def get_classification_stats(self, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics on classifications and feedback"""
        try:
            query = select(AIClassification)
            if case_id:
                query = query.where(AIClassification.case_id == case_id)
            
            result = await self.db.execute(query)
            all_classifications = result.scalars().all()
            
            total = len(all_classifications)
            with_feedback = sum(1 for c in all_classifications if c.has_feedback)
            correct = sum(1 for c in all_classifications if c.feedback_correct == True)
            incorrect = sum(1 for c in all_classifications if c.feedback_correct == False)
            
            # Sentiment distribution
            sentiment_counts = {}
            for c in all_classifications:
                sentiment_counts[c.sentiment] = sentiment_counts.get(c.sentiment, 0) + 1
            
            return {
                "total_classifications": total,
                "with_feedback": with_feedback,
                "feedback_percentage": (with_feedback / total * 100) if total > 0 else 0,
                "correct_classifications": correct,
                "incorrect_classifications": incorrect,
                "accuracy": (correct / with_feedback * 100) if with_feedback > 0 else 0,
                "sentiment_distribution": sentiment_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting classification stats: {e}", exc_info=True)
            return {}

