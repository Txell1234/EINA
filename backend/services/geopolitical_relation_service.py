"""
Geopolitical Relation Service - Extracció i anàlisi de relacions bilaterals i multilaterals
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.geopolitical import BilateralRelation, Treaty, DiplomaticEvent, RelationType, RelationStatus, EventType, EventImportance
from models.osint import OSINTResult, OSINTQuery
from models.ai_classification import AIClassification
from services.ai_service import AIService
import logging
import re
import json

logger = logging.getLogger(__name__)

class GeopoliticalRelationService:
    """Servei per extreure i analitzar relacions geopolítiques des de dades OSINT"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        
        # Països coneguts per matching
        self.countries = {
            "andorra", "spain", "france", "germany", "italy", "uk", "united kingdom",
            "usa", "united states", "india", "uae", "united arab emirates", "china",
            "russia", "japan", "south korea", "brazil", "mexico", "canada", "australia",
            "singapore", "switzerland", "netherlands", "belgium", "portugal", "greece",
            "turkey", "saudi arabia", "israel", "egypt", "south africa", "nigeria"
        }
    
    async def extract_relations_from_osint(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extreu relacions bilaterals des de dades OSINT"""
        try:
            # Obtenir OSINT results per al cas (o tots si no s'especifica)
            query = select(OSINTResult).join(OSINTQuery)
            if case_id:
                query = query.where(OSINTQuery.case_id == case_id)
            
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            relations_found = []
            
            for osint_result in osint_results:
                if not osint_result.data:
                    continue
                
                # Extreure text de les dades
                text_content = self._extract_text_from_osint(osint_result.data)
                if not text_content:
                    continue
                
                # Detectar països mencionats
                countries_mentioned = self._detect_countries(text_content)
                if len(countries_mentioned) < 2:
                    continue
                
                # Detectar tipus de relació
                relation_type = self._detect_relation_type(text_content)
                
                # Detectar esdeveniments
                events = self._detect_events(text_content, countries_mentioned, osint_result.created_at)
                
                # Crear relacions per cada parella de països
                for i in range(len(countries_mentioned)):
                    for j in range(i + 1, len(countries_mentioned)):
                        country1 = countries_mentioned[i]
                        country2 = countries_mentioned[j]
                        
                        # Normalitzar noms de països
                        country1_norm = self._normalize_country_name(country1)
                        country2_norm = self._normalize_country_name(country2)
                        
                        # Crear o actualitzar relació
                        relation = await self._get_or_create_relation(
                            country1_norm, country2_norm, case_id, relation_type
                        )
                        
                        # Actualitzar scoring basat en el contingut
                        await self._update_relation_scoring(relation, text_content, events)
                        
                        # Afegir referències
                        if not relation.source_references:
                            relation.source_references = []
                        relation.source_references.append({
                            "osint_result_id": osint_result.id,
                            "created_at": osint_result.created_at.isoformat() if osint_result.created_at else None
                        })
                        
                        relations_found.append({
                            "country1": country1_norm,
                            "country2": country2_norm,
                            "relation_id": relation.id,
                            "type": relation_type,
                            "score": relation.relation_score
                        })
            
            await self.db.commit()
            return relations_found
            
        except Exception as e:
            logger.error(f"Error extracting relations from OSINT: {e}", exc_info=True)
            await self.db.rollback()
            return []
    
    async def extract_treaties_from_osint(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extreu tractats i acords des de dades OSINT"""
        try:
            query = select(OSINTResult).join(OSINTQuery)
            if case_id:
                query = query.where(OSINTQuery.case_id == case_id)
            
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            treaties_found = []
            
            for osint_result in osint_results:
                if not osint_result.data:
                    continue
                
                text_content = self._extract_text_from_osint(osint_result.data)
                if not text_content:
                    continue
                
                # Detectar menció de tractats
                treaty_patterns = [
                    r"(?:signed|signing|agreement|treaty|accord|pact|convention)\s+(?:between|among|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:and|&)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:signed|agreed|announced)",
                    r"treaty\s+(?:of|on|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
                ]
                
                for pattern in treaty_patterns:
                    matches = re.finditer(pattern, text_content, re.IGNORECASE)
                    for match in matches:
                        # Intentar extreure informació del tractat amb IA
                        treaty_info = await self._extract_treaty_info_with_ai(text_content, match.group(0))
                        
                        if treaty_info:
                            # Crear o actualitzar tractat
                            treaty = await self._create_or_update_treaty(
                                treaty_info, case_id, osint_result.id
                            )
                            
                            if treaty:
                                treaties_found.append({
                                    "id": treaty.id,
                                    "name": treaty.name,
                                    "countries": treaty.countries,
                                    "type": treaty.treaty_type
                                })
            
            await self.db.commit()
            return treaties_found
            
        except Exception as e:
            logger.error(f"Error extracting treaties from OSINT: {e}", exc_info=True)
            await self.db.rollback()
            return []
    
    async def get_relation_timeline(
        self, 
        country1: str, 
        country2: str, 
        days: int = 90
    ) -> Dict[str, Any]:
        """Obté timeline de relació entre dos països"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Obtenir relació
            relation = await self._get_relation(country1, country2)
            if not relation:
                return {"error": "Relation not found"}
            
            # Obtenir esdeveniments
            events_result = await self.db.execute(
                select(DiplomaticEvent)
                .where(
                    and_(
                        DiplomaticEvent.relation_id == relation.id,
                        DiplomaticEvent.event_date >= cutoff_date
                    )
                )
                .order_by(DiplomaticEvent.event_date.desc())
            )
            events = events_result.scalars().all()
            
            # Obtenir tractats
            treaties_result = await self.db.execute(
                select(Treaty)
                .where(Treaty.relation_id == relation.id)
                .order_by(Treaty.signing_date.desc())
            )
            treaties = treaties_result.scalars().all()
            
            # Calcular tendència
            trend = self._calculate_relation_trend(relation, events)
            
            return {
                "relation": {
                    "id": relation.id,
                    "country1": relation.country1,
                    "country2": relation.country2,
                    "status": relation.status.value,
                    "score": relation.relation_score,
                    "trend": trend
                },
                "events": [
                    {
                        "id": e.id,
                        "type": e.event_type.value,
                        "title": e.title,
                        "date": e.event_date.isoformat() if e.event_date else None,
                        "importance": e.importance.value,
                        "impact": e.impact_score
                    }
                    for e in events
                ],
                "treaties": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.treaty_type,
                        "signing_date": t.signing_date.isoformat() if t.signing_date else None,
                        "status": t.status
                    }
                    for t in treaties
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting relation timeline: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_bilateral_matrix(self, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Genera matriu de relacions bilaterals"""
        try:
            query = select(BilateralRelation)
            if case_id:
                query = query.where(BilateralRelation.case_id == case_id)
            
            result = await self.db.execute(query)
            relations = result.scalars().all()
            
            # Construir matriu
            countries_set = set()
            for rel in relations:
                countries_set.add(rel.country1)
                countries_set.add(rel.country2)
            
            countries_list = sorted(list(countries_set))
            matrix = {}
            
            for country1 in countries_list:
                matrix[country1] = {}
                for country2 in countries_list:
                    if country1 == country2:
                        matrix[country1][country2] = {"score": 100, "status": "self"}
                    else:
                        rel = await self._get_relation(country1, country2)
                        if rel:
                            matrix[country1][country2] = {
                                "score": rel.relation_score,
                                "status": rel.status.value,
                                "type": rel.relation_type.value
                            }
                        else:
                            matrix[country1][country2] = {"score": None, "status": "unknown"}
            
            return {
                "countries": countries_list,
                "matrix": matrix,
                "total_relations": len(relations)
            }
            
        except Exception as e:
            logger.error(f"Error generating bilateral matrix: {e}", exc_info=True)
            return {"error": str(e)}
    
    # Mètodes privats d'ajuda
    
    def _extract_text_from_osint(self, data: Any) -> str:
        """Extreu text de dades OSINT"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            text_parts = []
            # Buscar camps de text comuns
            for key in ["text", "content", "description", "title", "caption"]:
                if key in data and isinstance(data[key], str):
                    text_parts.append(data[key])
            
            # Si hi ha una llista de posts/items
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
    
    def _detect_countries(self, text: str) -> List[str]:
        """Detecta països mencionats al text"""
        countries_found = []
        text_lower = text.lower()
        
        for country in self.countries:
            # Buscar variacions del nom del país
            patterns = [
                country,
                country.replace(" ", ""),
                country.replace("united ", ""),
                country.replace("south ", ""),
            ]
            
            for pattern in patterns:
                if pattern in text_lower:
                    countries_found.append(country.title())
                    break
        
        # També buscar noms de països en majúscules (comun en notícies)
        country_caps_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        matches = re.finditer(country_caps_pattern, text)
        for match in matches:
            potential_country = match.group(1).lower()
            if potential_country in self.countries:
                if potential_country.title() not in countries_found:
                    countries_found.append(potential_country.title())
        
        return list(set(countries_found))  # Eliminar duplicats
    
    def _normalize_country_name(self, country: str) -> str:
        """Normalitza el nom d'un país"""
        country_lower = country.lower()
        
        # Mapeig de variacions
        mappings = {
            "united states": "USA",
            "usa": "USA",
            "united kingdom": "UK",
            "uk": "UK",
            "united arab emirates": "UAE",
            "uae": "UAE",
            "south korea": "South Korea",
        }
        
        if country_lower in mappings:
            return mappings[country_lower]
        
        return country.title()
    
    def _detect_relation_type(self, text: str) -> RelationType:
        """Detecta el tipus de relació basat en el text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["alliance", "ally", "allies", "defense pact"]):
            return RelationType.ALLIANCE
        elif any(word in text_lower for word in ["trade", "commerce", "economic", "business"]):
            return RelationType.TRADE
        elif any(word in text_lower for word in ["summit", "visit", "diplomatic", "meeting"]):
            return RelationType.DIPLOMATIC
        elif any(word in text_lower for word in ["multilateral", "multiple countries", "several nations"]):
            return RelationType.MULTILATERAL
        
        return RelationType.BILATERAL
    
    def _detect_events(
        self, 
        text: str, 
        countries: List[str], 
        event_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Detecta esdeveniments diplomàtics al text"""
        events = []
        text_lower = text.lower()
        
        # Detectar tipus d'esdeveniments
        if any(word in text_lower for word in ["summit", "meeting", "conference"]):
            events.append({
                "type": EventType.SUMMIT,
                "importance": EventImportance.HIGH if "summit" in text_lower else EventImportance.MEDIUM
            })
        
        if any(word in text_lower for word in ["treaty", "agreement", "accord", "signed"]):
            events.append({
                "type": EventType.TREATY_SIGNING,
                "importance": EventImportance.HIGH
            })
        
        if any(word in text_lower for word in ["sanction", "sanctions", "embargo"]):
            events.append({
                "type": EventType.SANCTION,
                "importance": EventImportance.HIGH
            })
        
        if any(word in text_lower for word in ["visit", "visiting", "diplomatic visit"]):
            events.append({
                "type": EventType.DIPLOMATIC_VISIT,
                "importance": EventImportance.MEDIUM
            })
        
        if any(word in text_lower for word in ["trade agreement", "commerce deal"]):
            events.append({
                "type": EventType.TRADE_AGREEMENT,
                "importance": EventImportance.MEDIUM
            })
        
        return events
    
    async def _get_or_create_relation(
        self,
        country1: str,
        country2: str,
        case_id: Optional[int],
        relation_type: RelationType
    ) -> BilateralRelation:
        """Obté o crea una relació bilateral"""
        # Normalitzar ordre (country1 < country2 per consistència)
        if country1 > country2:
            country1, country2 = country2, country1
        
        # Buscar relació existent
        result = await self.db.execute(
            select(BilateralRelation)
            .where(
                and_(
                    BilateralRelation.country1 == country1,
                    BilateralRelation.country2 == country2
                )
            )
            .limit(1)
        )
        relation = result.scalar_one_or_none()
        
        if not relation:
            relation = BilateralRelation(
                country1=country1,
                country2=country2,
                case_id=case_id,
                relation_type=relation_type,
                status=RelationStatus.STABLE,
                relation_score=50.0  # Score inicial neutral
            )
            self.db.add(relation)
            await self.db.flush()
        
        return relation
    
    async def _get_relation(self, country1: str, country2: str) -> Optional[BilateralRelation]:
        """Obté una relació existent"""
        if country1 > country2:
            country1, country2 = country2, country1
        
        result = await self.db.execute(
            select(BilateralRelation)
            .where(
                and_(
                    BilateralRelation.country1 == country1,
                    BilateralRelation.country2 == country2
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _update_relation_scoring(
        self,
        relation: BilateralRelation,
        text: str,
        events: List[Dict[str, Any]]
    ):
        """Actualitza el scoring de relació basat en contingut i esdeveniments"""
        # Anàlisi bàsica de sentiment del text
        sentiment = await self._analyze_sentiment(text)
        
        # Ajustar score basat en sentiment (-1 a 1 -> ajustar score 0-100)
        if sentiment > 0.3:
            relation.relation_score = min(100, relation.relation_score + 5)
        elif sentiment < -0.3:
            relation.relation_score = max(0, relation.relation_score - 5)
        
        # Ajustar basat en esdeveniments
        for event in events:
            if event["type"] == EventType.TREATY_SIGNING:
                relation.relation_score = min(100, relation.relation_score + 10)
            elif event["type"] == EventType.SANCTION:
                relation.relation_score = max(0, relation.relation_score - 15)
            elif event["type"] == EventType.SUMMIT:
                relation.relation_score = min(100, relation.relation_score + 5)
        
        # Actualitzar status basat en score
        if relation.relation_score >= 70:
            relation.status = RelationStatus.IMPROVING
        elif relation.relation_score <= 30:
            relation.status = RelationStatus.DETERIORATING
        elif relation.relation_score <= 20:
            relation.status = RelationStatus.CRITICAL
        else:
            relation.status = RelationStatus.STABLE
    
    async def _analyze_sentiment(self, text: str) -> float:
        """Analitza sentiment del text (retorna -1 a 1)"""
        try:
            if not self.ai_service.client:
                return 0.0
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analyzer. Return only a number between -1 and 1, where -1 is very negative, 0 is neutral, and 1 is very positive."},
                    {"role": "user", "content": f"Analyze sentiment: {text[:500]}"}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            try:
                return float(response.choices[0].message.content.strip())
            except ValueError:
                return 0.0
        except Exception:
            return 0.0
    
    def _calculate_relation_trend(
        self,
        relation: BilateralRelation,
        recent_events: List[DiplomaticEvent]
    ) -> str:
        """Calcula tendència de relació (improving/stable/deteriorating)"""
        if not recent_events:
            return "stable"
        
        # Analitzar esdeveniments recents
        positive_events = sum(1 for e in recent_events if e.impact_score > 50)
        negative_events = sum(1 for e in recent_events if e.impact_score < 30)
        
        if positive_events > negative_events * 2:
            return "improving"
        elif negative_events > positive_events * 2:
            return "deteriorating"
        
        return "stable"
    
    async def _extract_treaty_info_with_ai(self, text: str, match: str) -> Optional[Dict[str, Any]]:
        """Extreu informació de tractat utilitzant IA"""
        try:
            if not self.ai_service.client:
                return None
            
            prompt = f"""Extract treaty information from this text: {text[:1000]}

Return JSON with:
- name: treaty name
- type: treaty type (trade, defense, cultural, etc.)
- countries: list of countries involved
- date: signing date if mentioned
- key_provisions: main provisions

Return only valid JSON."""
            
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": "You are an expert in international relations. Extract treaty information and return only valid JSON."},
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
    
    async def _create_or_update_treaty(
        self,
        treaty_info: Dict[str, Any],
        case_id: Optional[int],
        osint_result_id: int
    ) -> Optional[Treaty]:
        """Crea o actualitza un tractat"""
        try:
            name = treaty_info.get("name", "Unknown Treaty")
            countries = treaty_info.get("countries", [])
            
            if not countries or len(countries) < 2:
                return None
            
            # Buscar tractat existent
            result = await self.db.execute(
                select(Treaty)
                .where(Treaty.name.ilike(f"%{name}%"))
                .limit(1)
            )
            treaty = result.scalar_one_or_none()
            
            if not treaty:
                treaty = Treaty(
                    case_id=case_id,
                    name=name,
                    treaty_type=treaty_info.get("type", "other"),
                    countries=countries,
                    description=treaty_info.get("description"),
                    key_provisions=treaty_info.get("key_provisions", []),
                    source_references=[{"osint_result_id": osint_result_id}]
                )
                self.db.add(treaty)
                await self.db.flush()
            
            return treaty
        except Exception as e:
            logger.error(f"Error creating/updating treaty: {e}", exc_info=True)
            return None
