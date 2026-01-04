"""
Geopolitical Risk Service - Càlcul de riscos geopolítics quantificats
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.geopolitical import GeopoliticalRisk
from models.osint import OSINTResult, OSINTQuery
from models.ai_classification import AIClassification
from services.ai_service import AIService
import logging
import re

logger = logging.getLogger(__name__)

class GeopoliticalRiskService:
    """Servei per calcular riscos geopolítics quantificats"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
    
    async def calculate_risks_from_osint(self, case_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcula riscos geopolítics des de dades OSINT"""
        try:
            # Obtenir OSINT results
            query = select(OSINTResult).join(OSINTQuery)
            if case_id:
                query = query.where(OSINTQuery.case_id == case_id)
            
            result = await self.db.execute(query)
            osint_results = result.scalars().all()
            
            # Agrupar per país
            country_data = {}
            
            for osint_result in osint_results:
                if not osint_result.data:
                    continue
                
                text_content = self._extract_text_from_osint(osint_result.data)
                if not text_content:
                    continue
                
                # Detectar països mencionats
                countries = self._detect_countries(text_content)
                
                for country in countries:
                    if country not in country_data:
                        country_data[country] = {
                            "texts": [],
                            "classifications": [],
                            "dates": []
                        }
                    
                    country_data[country]["texts"].append(text_content)
                    if osint_result.created_at:
                        country_data[country]["dates"].append(osint_result.created_at)
            
            # Calcular riscos per cada país
            risks_calculated = []
            
            for country, data in country_data.items():
                risk = await self._calculate_country_risk(country, data, case_id)
                if risk:
                    risks_calculated.append({
                        "country": country,
                        "risk_score": risk.overall_risk_score,
                        "alert_triggered": risk.alert_triggered
                    })
            
            await self.db.commit()
            
            return {
                "status": "success",
                "risks_calculated": len(risks_calculated),
                "risks": risks_calculated
            }
            
        except Exception as e:
            logger.error(f"Error calculating risks from OSINT: {e}", exc_info=True)
            await self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    async def get_risks(
        self,
        case_id: Optional[int] = None,
        country: Optional[str] = None,
        region: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obté riscos geopolítics"""
        try:
            query = select(GeopoliticalRisk)
            conditions = []
            
            if case_id:
                conditions.append(GeopoliticalRisk.case_id == case_id)
            if country:
                conditions.append(GeopoliticalRisk.country.ilike(f"%{country}%"))
            if region:
                conditions.append(GeopoliticalRisk.region.ilike(f"%{region}%"))
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await self.db.execute(query.order_by(GeopoliticalRisk.overall_risk_score.desc()))
            risks = result.scalars().all()
            
            return [
                {
                    "id": r.id,
                    "country": r.country,
                    "region": r.region,
                    "overall_risk_score": r.overall_risk_score,
                    "political_stability_risk": r.political_stability_risk,
                    "conflict_risk": r.conflict_risk,
                    "economic_risk": r.economic_risk,
                    "security_risk": r.security_risk,
                    "risk_change_7d": r.risk_change_7d,
                    "risk_change_30d": r.risk_change_30d,
                    "alert_triggered": r.alert_triggered,
                    "alert_reason": r.alert_reason,
                    "risk_3_months": r.risk_3_months,
                    "risk_6_months": r.risk_6_months,
                    "risk_12_months": r.risk_12_months
                }
                for r in risks
            ]
        except Exception as e:
            logger.error(f"Error getting risks: {e}", exc_info=True)
            return []
    
    async def compare_country_risks(self, countries: List[str]) -> Dict[str, Any]:
        """Compara riscos entre múltiples països"""
        try:
            risks = []
            
            for country in countries:
                result = await self.db.execute(
                    select(GeopoliticalRisk)
                    .where(GeopoliticalRisk.country.ilike(f"%{country}%"))
                    .order_by(GeopoliticalRisk.calculated_at.desc())
                    .limit(1)
                )
                risk = result.scalar_one_or_none()
                
                if risk:
                    risks.append({
                        "country": risk.country,
                        "overall_risk": risk.overall_risk_score,
                        "political": risk.political_stability_risk,
                        "conflict": risk.conflict_risk,
                        "economic": risk.economic_risk,
                        "security": risk.security_risk,
                        "trend_7d": risk.risk_change_7d,
                        "trend_30d": risk.risk_change_30d
                    })
            
            # Ordenar per risc general
            risks.sort(key=lambda x: x["overall_risk"], reverse=True)
            
            return {
                "comparison_date": datetime.now().isoformat(),
                "countries_compared": len(risks),
                "risks": risks,
                "highest_risk": risks[0] if risks else None,
                "lowest_risk": risks[-1] if risks else None
            }
        except Exception as e:
            logger.error(f"Error comparing risks: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _calculate_country_risk(
        self,
        country: str,
        data: Dict[str, Any],
        case_id: Optional[int]
    ) -> Optional[GeopoliticalRisk]:
        """Calcula risc per un país específic"""
        try:
            # Obtenir risc existent o crear nou
            result = await self.db.execute(
                select(GeopoliticalRisk)
                .where(GeopoliticalRisk.country == country)
                .order_by(GeopoliticalRisk.calculated_at.desc())
                .limit(1)
            )
            existing_risk = result.scalar_one_or_none()
            
            # Calcular factors de risc
            political_risk = await self._calculate_political_stability_risk(data["texts"])
            conflict_risk = await self._calculate_conflict_risk(data["texts"])
            economic_risk = await self._calculate_economic_risk(data["texts"])
            security_risk = await self._calculate_security_risk(data["texts"])
            
            # Calcular risc general (mitjana ponderada)
            overall_risk = (
                political_risk * 0.25 +
                conflict_risk * 0.30 +
                economic_risk * 0.25 +
                security_risk * 0.20
            )
            
            # Calcular canvis
            risk_change_7d = 0.0
            risk_change_30d = 0.0
            
            if existing_risk:
                risk_change_7d = overall_risk - existing_risk.overall_risk_score
                # Buscar risc de fa 30 dies
                thirty_days_ago = datetime.now() - timedelta(days=30)
                old_result = await self.db.execute(
                    select(GeopoliticalRisk)
                    .where(
                        and_(
                            GeopoliticalRisk.country == country,
                            GeopoliticalRisk.calculated_at <= thirty_days_ago
                        )
                    )
                    .order_by(GeopoliticalRisk.calculated_at.desc())
                    .limit(1)
                )
                old_risk = old_result.scalar_one_or_none()
                if old_risk:
                    risk_change_30d = overall_risk - old_risk.overall_risk_score
            
            # Verificar alertes (>15% canvi en 7 dies)
            alert_triggered = False
            alert_reason = None
            if existing_risk and abs(risk_change_7d) > 15:
                alert_triggered = True
                alert_reason = f"Risk changed by {risk_change_7d:.1f} points in 7 days"
            
            # Crear o actualitzar risc
            if existing_risk:
                existing_risk.overall_risk_score = overall_risk
                existing_risk.political_stability_risk = political_risk
                existing_risk.conflict_risk = conflict_risk
                existing_risk.economic_risk = economic_risk
                existing_risk.security_risk = security_risk
                existing_risk.risk_change_7d = risk_change_7d
                existing_risk.risk_change_30d = risk_change_30d
                existing_risk.alert_triggered = alert_triggered
                existing_risk.alert_reason = alert_reason
                
                # Calcular prediccions
                existing_risk.risk_3_months = await self._predict_risk(overall_risk, risk_change_7d, 3)
                existing_risk.risk_6_months = await self._predict_risk(overall_risk, risk_change_7d, 6)
                existing_risk.risk_12_months = await self._predict_risk(overall_risk, risk_change_7d, 12)
                
                await self.db.flush()
                return existing_risk
            else:
                new_risk = GeopoliticalRisk(
                    case_id=case_id,
                    country=country,
                    overall_risk_score=overall_risk,
                    political_stability_risk=political_risk,
                    conflict_risk=conflict_risk,
                    economic_risk=economic_risk,
                    security_risk=security_risk,
                    risk_change_7d=risk_change_7d,
                    risk_change_30d=risk_change_30d,
                    alert_triggered=alert_triggered,
                    alert_reason=alert_reason,
                    risk_3_months=await self._predict_risk(overall_risk, risk_change_7d, 3),
                    risk_6_months=await self._predict_risk(overall_risk, risk_change_7d, 6),
                    risk_12_months=await self._predict_risk(overall_risk, risk_change_7d, 12)
                )
                self.db.add(new_risk)
                await self.db.flush()
                return new_risk
                
        except Exception as e:
            logger.error(f"Error calculating country risk: {e}", exc_info=True)
            return None
    
    async def _calculate_political_stability_risk(self, texts: List[str]) -> float:
        """Calcula risc d'inestabilitat política (0-100)"""
        risk_indicators = [
            "protest", "riot", "unrest", "coup", "government collapse",
            "election fraud", "political crisis", "resignation", "impeachment"
        ]
        
        text_combined = " ".join(texts).lower()
        indicator_count = sum(1 for indicator in risk_indicators if indicator in text_combined)
        
        # Base risk + indicator impact
        base_risk = 20.0
        risk = base_risk + (indicator_count * 10)
        
        return min(100.0, risk)
    
    async def _calculate_conflict_risk(self, texts: List[str]) -> float:
        """Calcula risc de conflicte (0-100)"""
        conflict_indicators = [
            "war", "conflict", "attack", "bombing", "invasion", "military",
            "tension", "escalation", "border", "dispute", "hostility"
        ]
        
        text_combined = " ".join(texts).lower()
        indicator_count = sum(1 for indicator in conflict_indicators if indicator in text_combined)
        
        base_risk = 15.0
        risk = base_risk + (indicator_count * 12)
        
        return min(100.0, risk)
    
    async def _calculate_economic_risk(self, texts: List[str]) -> float:
        """Calcula risc econòmic (0-100)"""
        economic_indicators = [
            "sanction", "embargo", "trade war", "economic crisis",
            "recession", "inflation", "currency collapse", "default"
        ]
        
        text_combined = " ".join(texts).lower()
        indicator_count = sum(1 for indicator in economic_indicators if indicator in text_combined)
        
        base_risk = 25.0
        risk = base_risk + (indicator_count * 15)
        
        return min(100.0, risk)
    
    async def _calculate_security_risk(self, texts: List[str]) -> float:
        """Calcula risc de seguretat (0-100)"""
        security_indicators = [
            "terrorist", "attack", "bomb", "threat", "security alert",
            "violence", "assassination", "kidnapping"
        ]
        
        text_combined = " ".join(texts).lower()
        indicator_count = sum(1 for indicator in security_indicators if indicator in text_combined)
        
        base_risk = 10.0
        risk = base_risk + (indicator_count * 20)
        
        return min(100.0, risk)
    
    async def _predict_risk(self, current_risk: float, trend_7d: float, months: int) -> float:
        """Prediu risc futur basat en tendència"""
        # Extrapolar tendència
        trend_per_month = trend_7d / 7 * 30  # Aproximació
        predicted_risk = current_risk + (trend_per_month * months)
        
        # Limitar entre 0 i 100
        return max(0.0, min(100.0, predicted_risk))
    
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
    
    def _detect_countries(self, text: str) -> List[str]:
        """Detecta països mencionats"""
        countries = {
            "andorra", "spain", "france", "germany", "italy", "uk", "united kingdom",
            "usa", "united states", "india", "uae", "united arab emirates", "china",
            "russia", "japan", "south korea", "brazil", "mexico", "canada"
        }
        
        countries_found = []
        text_lower = text.lower()
        
        for country in countries:
            if country in text_lower:
                countries_found.append(country.title())
        
        return list(set(countries_found))
