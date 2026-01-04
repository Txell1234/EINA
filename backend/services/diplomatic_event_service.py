"""
Diplomatic Event Service - Extracció automàtica d'esdeveniments diplomàtics
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.geopolitical import DiplomaticEvent, BilateralRelation, EventType, EventImportance
from models.osint import OSINTResult, OSINTQuery
from services.ai_service import AIService
import logging
import re
import json

logger = logging.getLogger(__name__)

class DiplomaticEventService:
    """Servei per extreure esdeveniments diplomàtics des de dades OSINT"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
    
    async def extract_events_from_osint(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extreu esdeveniments diplomàtics des de dades OSINT"""
        try:
            query = select(OSINTResult).join(OSINTQuery)
            if case_id:
                query = query.where(OSINTQuery.case_id == case_id)
            
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            events_found = []
            
            for osint_result in osint_results:
                if not osint_result.data:
                    continue
                
                text_content = self._extract_text_from_osint(osint_result.data)
                if not text_content:
                    continue
                
                # Detectar esdeveniments
                events = await self._detect_events_in_text(
                    text_content,
                    osint_result.created_at,
                    case_id,
                    osint_result.id
                )
                
                events_found.extend(events)
            
            await self.db.commit()
            
            return [
                {
                    "id": e.id,
                    "type": e.event_type.value,
                    "title": e.title,
                    "importance": e.importance.value,
                    "countries": e.countries
                }
                for e in events_found
            ]
            
        except Exception as e:
            logger.error(f"Error extracting events from OSINT: {e}", exc_info=True)
            await self.db.rollback()
            return []
    
    async def _detect_events_in_text(
        self,
        text: str,
        event_date: Optional[datetime],
        case_id: Optional[int],
        osint_result_id: int
    ) -> List[DiplomaticEvent]:
        """Detecta esdeveniments en un text"""
        events = []
        text_lower = text.lower()
        
        # Patrons per detectar diferents tipus d'esdeveniments
        event_patterns = {
            EventType.SUMMIT: [
                r"summit\s+(?:between|of|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"(?:leaders|presidents|ministers)\s+(?:of|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:meet|gather|convene)",
                r"g\d+\s+summit",
                r"bilateral\s+meeting"
            ],
            EventType.TREATY_SIGNING: [
                r"(?:signed|signing|agreement|treaty|accord)\s+(?:between|among)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:and|&)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:sign|agree|announce)"
            ],
            EventType.SANCTION: [
                r"sanction(?:s)?\s+(?:against|on|imposed\s+on)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"embargo\s+(?:on|against)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:impose|announce)\s+sanction"
            ],
            EventType.DIPLOMATIC_VISIT: [
                r"(?:visit|visiting)\s+(?:to|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"(?:president|prime minister|minister|leader)\s+(?:of|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:visit|travel)"
            ],
            EventType.TRADE_AGREEMENT: [
                r"trade\s+(?:agreement|deal|pact)\s+(?:between|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"commerce\s+(?:agreement|deal)"
            ],
            EventType.ALLIANCE_CHANGE: [
                r"(?:join|leave|exit)\s+(?:alliance|pact|treaty)",
                r"alliance\s+(?:with|between)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
            ]
        }
        
        # Detectar cada tipus d'esdeveniment
        for event_type, patterns in event_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extreure informació amb IA
                    event_info = await self._extract_event_info_with_ai(text, event_type, match.group(0))
                    
                    if event_info:
                        event = await self._create_event(
                            event_info,
                            event_type,
                            event_date or datetime.now(),
                            case_id,
                            osint_result_id
                        )
                        
                        if event:
                            events.append(event)
        
        return events
    
    async def _extract_event_info_with_ai(
        self,
        text: str,
        event_type: EventType,
        match: str
    ) -> Optional[Dict[str, Any]]:
        """Extreu informació d'esdeveniment utilitzant IA"""
        try:
            if not self.ai_service.client:
                return None
            
            prompt = f"""Extract diplomatic event information from this text: {text[:1000]}

Event type: {event_type.value}
Context: {match}

Return JSON with:
- title: event title
- description: brief description
- countries: list of countries involved
- location: location if mentioned
- importance: high, medium, or low
- impact_score: estimated impact (0-100)

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are an expert in international relations. Extract event information and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return None
        except Exception:
            return None
    
    async def _create_event(
        self,
        event_info: Dict[str, Any],
        event_type: EventType,
        event_date: datetime,
        case_id: Optional[int],
        osint_result_id: int
    ) -> Optional[DiplomaticEvent]:
        """Crea un esdeveniment diplomàtic"""
        try:
            title = event_info.get("title", f"{event_type.value.replace('_', ' ').title()}")
            countries = event_info.get("countries", [])
            importance_str = event_info.get("importance", "medium").lower()
            
            # Determinar importància
            if importance_str == "high":
                importance = EventImportance.HIGH
            elif importance_str == "low":
                importance = EventImportance.LOW
            else:
                importance = EventImportance.MEDIUM
            
            # Calcular impacte
            impact_score = event_info.get("impact_score", 50.0)
            if event_type == EventType.SANCTION:
                impact_score = max(impact_score, 70.0)  # Sancions són sempre d'alt impacte
            elif event_type == EventType.TREATY_SIGNING:
                impact_score = max(impact_score, 60.0)
            
            # Analitzar sentiment
            sentiment = await self._analyze_event_sentiment(event_info.get("description", ""))
            
            # Crear esdeveniment
            event = DiplomaticEvent(
                case_id=case_id,
                event_type=event_type,
                importance=importance,
                title=title,
                description=event_info.get("description"),
                event_date=event_date,
                countries=countries,
                entities=event_info.get("entities", []),
                impact_score=impact_score,
                sentiment_score=sentiment,
                location=event_info.get("location"),
                source_references=[{"osint_result_id": osint_result_id}],
                verified=False
            )
            
            self.db.add(event)
            await self.db.flush()
            
            return event
        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            return None
    
    async def _analyze_event_sentiment(self, description: str) -> Optional[float]:
        """Analitza sentiment d'un esdeveniment"""
        try:
            if not self.ai_service.client or not description:
                return None
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analyzer. Return only a number between -1 and 1."},
                    {"role": "user", "content": f"Analyze sentiment: {description[:500]}"}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            try:
                return float(response.choices[0].message.content.strip())
            except ValueError:
                return None
        except Exception:
            return None
    
    def _extract_text_from_osint(self, data: Any) -> str:
        """Extreu text de dades OSINT"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            text_parts = []
            for key in ["text", "content", "description", "title", "caption"]:
                if key in data and isinstance(data[key], str):
                    text_parts.append(data[key])
            
            if "data" in data and isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        for key in ["text", "content", "description", "caption"]:
                            if key in item and isinstance(item[key], str):
                                text_parts.append(item[key])
            
            return " ".join(text_parts)
        elif isinstance(data, list):
            return " ".join([self._extract_text_from_osint(item) for item in data])
        
        return ""
