"""
AI Service - Integration with OpenAI and other AI tools
"""
from openai import AsyncOpenAI
from openai import APIError, APITimeoutError, APIConnectionError
from app.config import settings
from typing import List, Dict, Any, Optional
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Validar API key antes de crear el cliente
        openai_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""
        if not openai_key or openai_key == "sk-proj-TU_CLAVE_API_AQUI":
            logger.warning(
                f"OPENAI_API_KEY no está configurada correctamente "
                f"(vacía o placeholder). Las funciones de IA usarán planes de fallback."
            )
            self.client = None
        else:
            # Create AsyncOpenAI client without proxies to avoid httpx compatibility issues
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=30.0,  # 30 segundos timeout por defecto
                http_client=None  # Use default httpx client without proxy configuration
            )
            logger.debug(f"AIService inicializado con modelo {settings.OPENAI_MODEL}")
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
    
    async def analyze_case_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze user prompt and generate analysis plan"""
        # Validar que tenemos cliente de OpenAI
        if not self.client:
            logger.warning(
                "OpenAI no configurado. Motivo: OPENAI_API_KEY no está configurada o es inválida. "
                "Usando plan de fallback básico (sin análisis de IA real)."
            )
            return self._get_fallback_plan(prompt)
        
        system_prompt = """Eres un experto en análisis OSINT e inteligencia. 
        Analiza el prompt del usuario y genera un plan de acción estructurado en JSON con:
        - name: nombre del caso
        - type: tipo (business, political, geopolitical, social, investigation)
        - osint_queries: lista de búsquedas OSINT a ejecutar (cada una con type y params)
        - ai_analyses: lista de tipos de análisis IA a realizar (taranis, osintgpt, ominis)
        - kpis: lista de KPIs relevantes (cada uno con id, name, type)
        - premise: premisa base para análisis cualitativo
        - framework: framework de razonamiento (deductive, inductive, abductive, causal)
        
        Responde SOLO con JSON válido, sin texto adicional."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Prompt: {prompt}"}
                ],
                temperature=0.7,
                timeout=30.0,  # 30 segundos timeout
            )
            
            content = response.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON de OpenAI: {e}. Usando plan de fallback.")
                return self._get_fallback_plan(prompt)
        
        except APITimeoutError as e:
            logger.error(f"Timeout en llamada a OpenAI: {e}")
            return self._get_fallback_plan(prompt)
        except APIConnectionError as e:
            logger.error(f"Error de conexión con OpenAI: {e}")
            return self._get_fallback_plan(prompt)
        except APIError as e:
            logger.error(f"Error de API de OpenAI: {e}")
            return self._get_fallback_plan(prompt)
        except Exception as e:
            logger.error(f"Error inesperado en analyze_case_prompt: {e}", exc_info=True)
            return self._get_fallback_plan(prompt)
    
    def _get_fallback_plan(self, prompt: str) -> Dict[str, Any]:
        """Genera un plan de fallback cuando OpenAI no está disponible"""
        # Extraer nombre básico del prompt
        name = prompt[:50] + "..." if len(prompt) > 50 else prompt
        if not name.strip():
            name = "Caso generado"
        
        return {
            "name": name,
            "type": "general",
            "osint_queries": [
                {"type": "sherlock", "params": {}},
                {"type": "recon-ng", "params": {"module": "domain"}}
            ],
            "ai_analyses": ["osintgpt"],
            "kpis": [],
            "premise": prompt,
            "framework": "deductive"
        }
    
    async def analyze_data(
        self,
        analysis_type: str,
        case_id: int,
        osint_results: List[Dict] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze data using specified AI analysis type
        
        If osint_results is None, fetches ALL OSINT data linked to the case from database.
        This ensures all manually collected OSINT data is included in the analysis.
        """
        # If no OSINT results provided, fetch ALL from database
        if osint_results is None and db is not None:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            # Get all queries linked to this case
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            # Get all results for these queries
            osint_results = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_results.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })

        osint_results = osint_results or []
        total_entries = len(osint_results)
        useful_results = [
            result for result in osint_results
            if result.get("data")
            and result.get("status") != "error"
            and not (
                isinstance(result.get("data"), dict)
                and result["data"].get("status") == "error"
            )
        ]
        useful_entries = len(useful_results)
        
        if analysis_type == "taranis":
            analysis = await self._taranis_analysis(useful_results)
        elif analysis_type == "osintgpt":
            analysis = await self._osintgpt_analysis(useful_results)
        elif analysis_type == "ominis":
            analysis = await self._ominis_analysis(useful_results)
        else:
            analysis = {}

        analysis["quality_metrics"] = {
            "total_entries": total_entries,
            "useful_entries": useful_entries
        }
        return analysis
    
    async def _taranis_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Taranis AI analysis - Situational analysis and predictions"""
        # Combine data for analysis
        combined_text = "\n".join([
            str(result.get("data", "")) for result in data
        ])
        
        system_prompt = """Eres Taranis AI, un sistema de análisis situacional OSINT.
        Analiza los datos proporcionados y genera:
        - Situational assessment
        - Risk predictions
        - Key findings
        - Confidence scores"""
        
        if not self.client:
            logger.warning("Taranis analysis: OpenAI no configurado, retornando análisis de fallback")
            return {
                "type": "taranis",
                "analysis": "Análisis no disponible: OpenAI no configurado. Configure OPENAI_API_KEY en .env para habilitar análisis completo.",
                "confidence": 0.0,
                "fallback": True
            }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text[:4000]}  # Limit length
                ],
                temperature=0.5,
                timeout=30.0,
            )
        except Exception as e:
            logger.error(f"Error en _taranis_analysis: {e}")
            return {
                "type": "taranis",
                "analysis": f"Error en análisis: {str(e)}",
                "confidence": 0.0
            }
        
        return {
            "type": "taranis",
            "analysis": response.choices[0].message.content,
            "confidence": 0.85
        }
    
    async def _osintgpt_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """OSINTGPT analysis - Concept extraction and embeddings"""
        combined_text = "\n".join([
            str(result.get("data", "")) for result in data
        ])
        
        if not self.client:
            logger.warning("OSINTGPT analysis: OpenAI no configurado, retornando análisis de fallback")
            return {
                "type": "osintgpt",
                "concepts": "Análisis no disponible: OpenAI no configurado. Configure OPENAI_API_KEY en .env para habilitar análisis completo.",
                "embeddings": [],
                "confidence": 0.0,
                "fallback": True
            }
        
        try:
            # Get embeddings
            embedding_response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=combined_text[:8000],  # Limit for embeddings
                timeout=30.0,
            )
            embeddings = embedding_response.data[0].embedding
            
            # Extract concepts
            system_prompt = """Extrae los conceptos principales, entidades y relaciones 
            de los datos OSINT proporcionados. Identifica:
            - Conceptos clave
            - Entidades (personas, empresas, lugares)
            - Relaciones entre entidades
            - Tendencias emergentes"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text[:4000]}
                ],
                temperature=0.7,
                timeout=30.0,
            )
        except Exception as e:
            logger.error(f"Error en _osintgpt_analysis: {e}")
            return {
                "type": "osintgpt",
                "concepts": f"Error en análisis: {str(e)}",
                "embeddings": [],
                "confidence": 0.0
            }
        
        return {
            "type": "osintgpt",
            "concepts": response.choices[0].message.content,
            "embeddings": embeddings,
            "confidence": 0.80
        }
    
    async def _ominis_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Ominis-OSINT analysis - Predictive risk analysis"""
        combined_text = "\n".join([
            str(result.get("data", "")) for result in data
        ])
        
        system_prompt = """Eres Ominis-OSINT, un sistema de análisis predictivo de riesgos.
        Analiza los datos y predice:
        - Riesgos identificados (geopolítico, político, social)
        - Probabilidades de eventos
        - Patrones detectados
        - Recomendaciones"""
        
        if not self.client:
            logger.warning("Ominis analysis: OpenAI no configurado, retornando análisis de fallback")
            return {
                "type": "ominis",
                "predictions": "Análisis no disponible: OpenAI no configurado. Configure OPENAI_API_KEY en .env para habilitar análisis completo.",
                "confidence": 0.0,
                "fallback": True
            }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text[:4000]}
                ],
                temperature=0.6,
                timeout=30.0,
            )
        except Exception as e:
            logger.error(f"Error en _ominis_analysis: {e}")
            return {
                "type": "ominis",
                "predictions": f"Error en análisis: {str(e)}",
                "confidence": 0.0
            }
        
        return {
            "type": "ominis",
            "predictions": response.choices[0].message.content,
            "confidence": 0.75
        }
    
    async def extract_concepts(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts from text"""
        system_prompt = """Extrae conceptos clave del texto. Responde SOLO con un JSON array válido.
        Cada concepto debe tener: {"name": "nombre del concepto", "type": "tipo (entity/topic/relationship)", "confidence": 0.0-1.0}
        Ejemplo: [{"name": "Empresa X", "type": "entity", "confidence": 0.9}, {"name": "Comercio internacional", "type": "topic", "confidence": 0.8}]"""
        
        if not self.client:
            return [
                {"name": "Concepto principal", "type": "topic", "confidence": 0.5}
            ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Texto a analizar:\n{text[:4000]}"}
                ],
                temperature=0.7,
                response_format={"type": "json_object"} if "gpt-4" in self.model.lower() else None,
                timeout=30.0,
            )
        except Exception as e:
            logger.error(f"Error en extract_concepts: {e}")
            return [
                {"name": "Error extrayendo conceptos", "type": "topic", "confidence": 0.0}
            ]
        
        try:
            content = response.choices[0].message.content
            # Try to parse as JSON
            parsed = json.loads(content)
            # If it's a dict with a list key, extract it
            if isinstance(parsed, dict):
                for key in ['concepts', 'items', 'data', 'result']:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                # If no list found, return empty
                return []
            # If it's already a list, return it
            if isinstance(parsed, list):
                return parsed
            return []
        except json.JSONDecodeError:
            # Fallback: try to extract concepts manually
            return [
                {"name": "Concepto principal", "type": "topic", "confidence": 0.7}
            ]
    
    async def suggest_kpis_for_case(
        self,
        case_type: str,
        case_description: str,
        existing_kpis: List[Dict] = None
    ) -> Dict[str, Any]:
        """Suggest relevant KPIs for a case based on case type and description
        
        Args:
            case_type: Type of case (business, political, geopolitical, social, investigation, general)
            case_description: Description of the case
            existing_kpis: List of existing KPIs to avoid duplicates
            
        Returns:
            Dict with suggested KPIs and their metadata
        """
        if not self.client:
            return {
                "suggested_kpis": [],
                "error": "OpenAI not configured"
            }
        
        existing_kpi_names = [k.get("name", "").lower() for k in (existing_kpis or [])]
        
        # Build context based on case type
        case_type_context = {
            "business": "Focus on commercial metrics: trade volumes, partnerships, market sentiment, revenue mentions, business agreements",
            "political": "Focus on political metrics: policy mentions, election data, political sentiment, government actions",
            "geopolitical": "Focus on geopolitical metrics: bilateral agreements, diplomatic events, trade relations, policy changes, international sentiment",
            "social": "Focus on social metrics: public sentiment, engagement rates, mentions by platform, viral content, community reactions",
            "investigation": "Focus on investigation metrics: evidence count, source credibility, timeline events, connection patterns",
            "general": "Focus on general metrics: mentions, sentiment, engagement, key events"
        }
        
        context = case_type_context.get(case_type.lower(), case_type_context["general"])
        
        system_prompt = f"""You are a business intelligence and geopolitical analysis expert. 
Suggest relevant KPIs (Key Performance Indicators) for analyzing a case.

Case Type: {case_type}
Context: {context}

For this case type, suggest 5-8 specific, measurable KPIs that would be useful for tracking.
Each KPI should have:
- A clear, specific name (e.g., "Negative Comments - Instagram", not just "Sentiment")
- A metric type: sentiment, volume, count, trend, engagement, ratio, or custom
- A measurement unit (e.g., "count", "percentage", "posts/day", "USD")
- A brief description of what it measures
- Whether it's quantitative or qualitative

Focus on metrics that can be extracted from OSINT data (social media, news, public records).

Return ONLY a valid JSON array, no other text. Format:
[
  {{
    "name": "KPI Name",
    "metric_type": "sentiment|volume|count|trend|engagement|ratio|custom",
    "kpi_type": "quantitative|qualitative",
    "description": "What this KPI measures",
    "measurement_unit": "unit (e.g., count, percentage, posts/day)",
    "target_value": "optional target or baseline"
  }}
]"""

        user_prompt = f"""Case Description: {case_description}

Existing KPIs (avoid duplicates): {', '.join(existing_kpi_names) if existing_kpi_names else 'None'}

Suggest relevant KPIs for this case."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                timeout=30.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Try to parse as JSON
            import json
            try:
                result = json.loads(content)
                # Handle both {"suggested_kpis": [...]} and [...] formats
                if isinstance(result, list):
                    kpis = result
                elif isinstance(result, dict) and "suggested_kpis" in result:
                    kpis = result["suggested_kpis"]
                elif isinstance(result, dict) and "kpis" in result:
                    kpis = result["kpis"]
                else:
                    kpis = []
                
                return {
                    "suggested_kpis": kpis,
                    "case_type": case_type,
                    "confidence": 0.85
                }
            except json.JSONDecodeError:
                # Fallback: try to extract JSON from text
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    kpis = json.loads(json_match.group())
                    return {
                        "suggested_kpis": kpis,
                        "case_type": case_type,
                        "confidence": 0.75
                    }
                return {
                    "suggested_kpis": [],
                    "error": "Failed to parse AI response",
                    "raw_response": content
                }
        except Exception as e:
            logger.error(f"Error suggesting KPIs: {e}", exc_info=True)
            return {
                "suggested_kpis": [],
                "error": str(e)
            }
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        if not self.client:
            return {"sentiment": "neutral", "score": 0.5, "confidence": 0.0}
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Analiza el sentimiento del texto. Responde en JSON con: sentiment (positive/negative/neutral), score (0-1), confidence."},
                    {"role": "user", "content": text[:4000]}
                ],
                temperature=0.3,
                timeout=30.0,
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {"sentiment": "neutral", "score": 0.5, "confidence": 0.5}
        except Exception as e:
            logger.error(f"Error en analyze_sentiment: {e}")
            return {"sentiment": "neutral", "score": 0.5, "confidence": 0.0}
    
    async def analyze_with_framework(
        self,
        premise: str,
        framework: str,
        kpis: List[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze data using specific reasoning framework"""
        framework_descriptions = {
            "deductive": "Aplica principios generales a casos específicos. Progresión lógica de lo general a lo particular.",
            "inductive": "Infiere reglas generales a partir de observaciones específicas. Detección de patrones.",
            "abductive": "Formula hipótesis más probables a partir de datos incompletos. Mejor explicación posible.",
            "causal": "Identifica relaciones de causa y efecto. Determina impacto y consecuencias."
        }
        
        framework_desc = framework_descriptions.get(framework, framework_descriptions["deductive"])
        
        kpi_text = ""
        if kpis:
            kpi_text = "\nKPIs a considerar:\n" + "\n".join([
                f"- {kpi.get('name', '')}: {kpi.get('type', '')}"
                for kpi in kpis
            ])
        
        system_prompt = f"""Eres un analista experto usando el framework de razonamiento {framework.upper()}.
        {framework_desc}
        
        Analiza la premisa proporcionada y genera:
        - conclusions: Conclusiones basadas en el framework
        - evidence: Lista de evidencia que soporta las conclusiones
        - confidence: Nivel de confianza (0-1)
        
        Responde en JSON válido."""
        
        user_prompt = f"Premisa: {premise}{kpi_text}"
        
        if not self.client:
            return {
                "conclusions": "Análisis no disponible: OpenAI no configurado",
                "evidence": [],
                "confidence": 0.0
            }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt[:4000]}
                ],
                temperature=0.7,
                timeout=30.0,
            )
            
            try:
                result = json.loads(response.choices[0].message.content)
                return {
                    "conclusions": result.get("conclusions", ""),
                    "evidence": result.get("evidence", []),
                    "confidence": float(result.get("confidence", 0.5))
                }
            except json.JSONDecodeError:
                return {
                    "conclusions": response.choices[0].message.content,
                    "evidence": [],
                    "confidence": 0.5
                }
        except Exception as e:
            logger.error(f"Error en analyze_with_framework: {e}")
            return {
                "conclusions": f"Error en análisis: {str(e)}",
                "evidence": [],
                "confidence": 0.0
            }
    
    async def generate_prediction(
        self,
        prediction_type: str,
        context_data: Dict[str, Any] = None,
        case_id: int = None,
        db = None
    ) -> Dict[str, Any]:
        """Generate prediction based on type, context, and REAL case data (OSINT, KPIs, objectives)
        
        If case_id and db are provided, fetches:
        - All OSINT data linked to the case
        - Case KPIs and their values
        - Case objectives and description
        - Previous AI analyses for the case
        """
        type_descriptions = {
            "trend": "Predice tendencias futuras basadas en datos históricos y actuales",
            "risk": "Predice riesgos (geopolítico, político, social) con probabilidades",
            "market": "Predice movimientos de mercado y oportunidades",
            "event": "Predice probabilidad de eventos específicos"
        }
        
        description = type_descriptions.get(prediction_type, "Genera una predicción")
        
        # Build comprehensive context from case data
        context_parts = []
        
        if case_id and db:
            from sqlalchemy import select
            from models.case import Case, CaseKPI
            from models.osint import OSINTQuery, OSINTResult
            from models.ai_analysis import AIAnalysis, Trend, Concept
            from models.qualitative import KPI
            
            # Get case info
            case_result = await db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if case:
                context_parts.append(f"CASO: {case.name}")
                context_parts.append(f"Tipo: {case.case_type}")
                context_parts.append(f"Descripción/Objetivo: {case.description or 'No especificado'}")
                
                # Get OSINT data summary
                queries_result = await db.execute(
                    select(OSINTQuery).where(OSINTQuery.case_id == case_id)
                )
                queries = queries_result.scalars().all()
                
                if queries:
                    context_parts.append(f"\nDATOS OSINT RECOPILADOS ({len(queries)} consultas):")
                    osint_summary = []
                    for query in queries[:10]:  # Limit to 10 most recent
                        results_result = await db.execute(
                            select(OSINTResult).where(OSINTResult.query_id == query.id)
                        )
                        results = results_result.scalars().all()
                        if results:
                            osint_summary.append(f"- {query.query_type}: {len(results)} resultados")
                    context_parts.append("\n".join(osint_summary))
                    
                    # Extract key data points from OSINT results
                    key_findings = []
                    for query in queries[:5]:
                        results_result = await db.execute(
                            select(OSINTResult).where(OSINTResult.query_id == query.id)
                        )
                        results = results_result.scalars().all()
                        for result in results[:2]:  # First 2 results per query
                            if result.data and isinstance(result.data, dict):
                                # Extract meaningful data
                                for key in ['title', 'description', 'text', 'content', 'summary']:
                                    if key in result.data:
                                        key_findings.append(f"  • {str(result.data[key])[:200]}")
                                        break
                    
                    if key_findings:
                        context_parts.append("\nHALLAZGOS CLAVE DE OSINT:")
                        context_parts.append("\n".join(key_findings[:10]))  # Limit to 10
                
                # Get KPIs
                kpi_result = await db.execute(
                    select(CaseKPI).where(CaseKPI.case_id == case_id)
                )
                case_kpis = kpi_result.scalars().all()
                
                if case_kpis:
                    context_parts.append(f"\nKPIs DEL CASO ({len(case_kpis)}):")
                    for case_kpi in case_kpis:
                        kpi_info = await db.execute(
                            select(KPI).where(KPI.id == case_kpi.kpi_id)
                        )
                        kpi = kpi_info.scalar_one_or_none()
                        if kpi:
                            context_parts.append(f"- {kpi.name}: {case_kpi.value or 'Sin valor'}")
                
                # Get trends and concepts from AI analysis
                trends_result = await db.execute(
                    select(Trend).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
                )
                trends = trends_result.scalars().all()
                
                if trends:
                    context_parts.append(f"\nTENDENCIAS IDENTIFICADAS ({len(trends)}):")
                    for trend in trends[:5]:
                        context_parts.append(f"- {trend.trend_name}: {trend.trend_type} (intensidad: {trend.intensity or 0})")
        
        # Add provided context data
        if context_data:
            context_parts.append(f"\nCONTEXTO ADICIONAL:\n{str(context_data)}")
        
        context_text = "\n".join(context_parts)
        
        system_prompt = f"""Eres un experto en predicciones basadas en análisis OSINT y datos reales.
        {description}
        
        IMPORTANTE: Tu predicción DEBE basarse en los datos OSINT reales proporcionados, los KPIs del caso, y los objetivos del caso.
        La explicación debe ser específica y referenciar datos concretos.
        
        Genera una predicción con:
        - text: Texto de la predicción con explicación detallada basada en los datos reales
        - confidence: Nivel de confianza (0-100) basado en la calidad y cantidad de datos
        - explanation: Explicación detallada de por qué se hace esta predicción, citando datos específicos
        - supporting_data: Lista de datos clave que sustentan la predicción
        - metadata: Información adicional relevante
        
        Responde en JSON válido."""
        
        if not self.client:
            return {
                "text": "Predicción no disponible: OpenAI no configurado",
                "confidence": 0.0,
                "explanation": "OpenAI no está configurado",
                "supporting_data": [],
                "metadata": {}
            }
        
        try:
            # Limit context to avoid token limits, but prioritize case data
            context_for_ai = context_text[:6000]  # Increased limit for comprehensive context
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_for_ai}
                ],
                temperature=0.7,
                timeout=45.0,  # Increased timeout for complex analysis
            )
            
            try:
                prediction_result = json.loads(response.choices[0].message.content)
                # Ensure all required fields exist
                if "explanation" not in prediction_result:
                    prediction_result["explanation"] = prediction_result.get("text", "")
                if "supporting_data" not in prediction_result:
                    prediction_result["supporting_data"] = []
                return prediction_result
            except json.JSONDecodeError:
                # Fallback: parse text response
                text_content = response.choices[0].message.content
                return {
                    "text": text_content,
                    "confidence": 50.0,
                    "explanation": text_content,
                    "supporting_data": [],
                    "metadata": {}
                }
        except Exception as e:
            logger.error(f"Error en generate_prediction: {e}")
            return {
                "text": f"Error generando predicción: {str(e)}",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}",
                "supporting_data": [],
                "metadata": {}
            }
    
    async def extract_case_specific_metrics(
        self,
        case_id: int,
        osint_data: List[Dict],
        kpis: List[Dict],
        case_type: str,
        case_description: str,
        db = None
    ) -> Dict[str, Any]:
        """Extract case-specific metrics from OSINT data using AI
        
        Args:
            case_id: Case ID
            osint_data: List of OSINT results with data
            kpis: List of KPIs to track (with name, metric_type, etc.)
            case_type: Type of case (business, political, etc.)
            case_description: Case description
            
        Returns:
            Dict with extracted metrics, insights, and trends
        """
        from services.data_extraction_service import DataExtractionService
        
        if not self.client:
            return {
                "metrics": [],
                "insights": ["AI analysis not available: OpenAI not configured"],
                "error": "OpenAI not configured"
            }
        
        # First, extract structured metrics using DataExtractionService
        extraction_service = DataExtractionService()
        structured_metrics = {}
        
        for osint_item in osint_data:
            query_type = osint_item.get("query_type", "")
            data = osint_item.get("data", {})
            
            # Extract all metrics
            all_metrics = extraction_service.extract_all_metrics(data, query_type)
            
            # Aggregate by query type
            if query_type not in structured_metrics:
                structured_metrics[query_type] = {
                    "social_media": {"total_posts": 0, "total_likes": 0, "total_comments": 0},
                    "sentiment": {"positive_count": 0, "negative_count": 0, "neutral_count": 0},
                    "news": {"total_articles": 0},
                    "commercial": {"agreement_mentions": 0, "bilateral_accord_mentions": 0}
                }
            
            # Aggregate metrics
            for metric_type, metrics in all_metrics.items():
                if metric_type in structured_metrics[query_type]:
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            structured_metrics[query_type][metric_type][key] = (
                                structured_metrics[query_type][metric_type].get(key, 0) + value
                            )
        
        # Prepare context for AI analysis
        context_parts = [
            f"Case Type: {case_type}",
            f"Case Description: {case_description}",
            f"KPIs to Track: {', '.join([k.get('name', '') for k in kpis])}",
            f"Structured Metrics Extracted: {len(structured_metrics)} query types"
        ]
        
        # Add structured metrics summary
        metrics_summary = []
        for query_type, metrics in structured_metrics.items():
            metrics_summary.append(f"{query_type}: {metrics}")
        context_parts.append(f"Metrics: {str(metrics_summary[:500])}")  # Limit length
        
        # Build AI prompt based on case type
        case_type_prompts = {
            "business": """Analyze commercial/business metrics. Focus on:
- Trade volumes, agreements, partnerships
- Investment mentions
- Bilateral accord counts
- Market sentiment
Generate concrete insights like "3 new bilateral accords mentioned in Q4 2024" or "Trade mentions increased 25% this month".""",
            "social": """Analyze reputation and social metrics. Focus on:
- Sentiment by social network (positive/negative/neutral counts)
- Engagement metrics (likes, comments, shares)
- Mentions by platform
- Trend changes (e.g., "Negative comments in Instagram increased by 15%")
Generate concrete insights like "Negative comments in Instagram: 45 (↑50% from 30)" or "TikTok shows 85% positive sentiment".""",
            "geopolitical": """Analyze geopolitical metrics. Focus on:
- Bilateral agreements and treaties
- Diplomatic events
- Policy changes
- International sentiment
Generate concrete insights with specific numbers and dates.""",
            "political": """Analyze political metrics. Focus on:
- Policy mentions
- Political sentiment
- Election-related data
- Government actions
Generate concrete insights with specific numbers.""",
            "general": """Analyze general OSINT metrics. Extract:
- Key trends and patterns
- Significant changes
- Important numbers and statistics
Generate concrete, actionable insights."""
        }
        
        system_prompt = f"""You are a business intelligence and geopolitical analysis expert.
{case_type_prompts.get(case_type.lower(), case_type_prompts["general"])}

Analyze the structured metrics and OSINT data to extract concrete, case-specific metrics that match the requested KPIs.

For each KPI, provide:
1. Current value
2. Previous value (if available) or baseline
3. Change percentage
4. Trend (increasing/decreasing/stable)
5. Specific details (e.g., which social network, date range)

Return ONLY valid JSON with this structure:
{{
  "metrics": [
    {{
      "kpi_name": "KPI Name",
      "value": 45,
      "previous_value": 30,
      "change_percent": 50.0,
      "trend": "increasing",
      "details": {{
        "social_network": "Instagram",
        "date_range": "2024-12-01 to 2024-12-25",
        "measurement_unit": "count"
      }}
    }}
  ],
  "insights": [
    "Concrete insight 1 with specific numbers",
    "Concrete insight 2 with specific numbers"
  ]
}}"""
        
        user_prompt = "\n".join(context_parts)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt[:4000]}  # Limit length
                ],
                temperature=0.7,
                timeout=30.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Add structured metrics to result
            result["structured_metrics"] = structured_metrics
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting case-specific metrics: {e}", exc_info=True)
            return {
                "metrics": [],
                "insights": [f"Error in AI analysis: {str(e)}"],
                "structured_metrics": structured_metrics,
                "error": str(e)
            }
    
    async def analyze_as_geopolitical_expert(
        self,
        case_id: int,
        osint_data: List[Dict] = None,
        api_data: Dict[str, Any] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Geopolitical Intelligence Analyst
        
        Provides expert-level geopolitical analysis including:
        - Bilateral relations assessment
        - Treaty and agreement analysis
        - Diplomatic event impact
        - Policy change implications
        - Trade flow analysis
        - Regional sentiment
        
        If osint_data is None, fetches ALL OSINT data linked to the case from database.
        If api_data is None, can fetch fresh data from geopolitical APIs when needed.
        Always uses case context from database.
        """
        if not self.client:
            return {
                "analysis_type": "geopolitical",
                "error": "OpenAI not configured"
            }
        
        # Get case context from database
        case_context = ""
        if db:
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if case:
                case_context = f"CASE: {case.name}\n"
                case_context += f"Type: {case.case_type.value if hasattr(case.case_type, 'value') else case.case_type}\n"
                case_context += f"Description: {case.description or 'No description'}\n"
        
        # If osint_data is None, fetch ALL OSINT data from database
        if osint_data is None and db:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            osint_data = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_data.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })
        
        # If api_data is None and we need fresh geopolitical data, fetch it
        if api_data is None:
            try:
                from integrations.ensembledata_api import EnsembleDataAPIService
                from integrations.news_api import NewsAPIService
                from integrations.permutable_api import PermutableAPIService
                
                ensembledata = EnsembleDataAPIService()
                news_api = NewsAPIService()
                permutable = PermutableAPIService()
                
                api_data = {
                    "geopolitical_events": [],
                    "news": []
                }
                
                # Extract countries from case context or OSINT data
                countries = []
                if db:
                    # Try to get countries from case description or OSINT data
                    from models.case import Case
                    case_result = await db.execute(select(Case).where(Case.id == case_id))
                    case = case_result.scalar_one_or_none()
                    if case and case.description:
                        # Simple extraction - in production, use NLP
                        import re
                        # Common country names pattern
                        country_pattern = r'\b(?:China|USA|United States|Russia|Germany|France|UK|United Kingdom|Spain|Italy|Japan|India|Brazil|Mexico|Canada|Australia)\b'
                        countries = list(set(re.findall(country_pattern, case.description, re.IGNORECASE)))
                
                # Fetch fresh geopolitical events from Permutable AI
                try:
                    if countries:
                        for country in countries[:3]:  # Limit to 3 countries to avoid too many requests
                            events_result = await permutable.get_geopolitical_events(
                                location=country,
                                limit=10
                            )
                            if events_result.get("status") == "success":
                                api_data["geopolitical_events"].extend(events_result.get("events", []))
                except Exception as e:
                    logger.warning(f"Error fetching fresh geopolitical events: {e}")
                
                # Fetch fresh news about countries
                try:
                    if countries:
                        for country in countries[:2]:  # Limit to 2 countries
                            news_result = await news_api.search(
                                query=country,
                                language="en",
                                sort_by="publishedAt"
                            )
                            if news_result.get("status") == "ok" and "articles" in news_result:
                                api_data["news"].extend(news_result["articles"][:5])  # 5 articles per country
                except Exception as e:
                    logger.warning(f"Error fetching fresh news for geopolitical analysis: {e}")
            except Exception as e:
                logger.warning(f"Error initializing APIs for fresh geopolitical data: {e}")
                api_data = {}
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract geopolitical metrics
        geopolitical_metrics = {}
        for osint_item in (osint_data or []):
            data = osint_item.get("data", {})
            metrics = extraction_service.extract_geopolitical_metrics(data)
            # Aggregate metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    geopolitical_metrics[key] = geopolitical_metrics.get(key, 0) + value
                elif isinstance(value, (list, set)):
                    if key not in geopolitical_metrics:
                        geopolitical_metrics[key] = set()
                    geopolitical_metrics[key].update(value)
        
        # Convert sets to lists
        for key, value in geopolitical_metrics.items():
            if isinstance(value, set):
                geopolitical_metrics[key] = list(value)
        
        system_prompt = """You are a senior Geopolitical Intelligence Analyst with 20+ years of experience.
Analyze the provided OSINT data and provide expert geopolitical intelligence assessment.

Focus on:
1. Bilateral and multilateral relations (strength, evolution, recent changes)
2. Treaties and agreements (new, expired, under negotiation)
3. Diplomatic events (summits, meetings, statements, their significance)
4. Policy changes (impact on relations, regional stability)
5. Trade flows (volumes, trends, key commodities, dependencies)
6. Regional sentiment (public opinion, media coverage, expert commentary)
7. Multiple scenario analysis (best case, worst case, base case scenarios)
8. Inflection point identification (key moments that could change dynamics)
9. Complex interdependence analysis (multi-layered economic and political dependencies)
10. Tension prediction (forecast potential escalations)
11. Supply chain impact analysis (how geopolitical events affect supply chains)

Provide concrete, actionable intelligence with specific numbers, dates, and entities.
Return JSON with:
{
  "bilateral_assessment": {
    "relations_strength": "strong|moderate|weak",
    "recent_trend": "improving|stable|deteriorating",
    "key_agreements": [{"name": "...", "date": "...", "status": "..."}],
    "diplomatic_events": [{"event": "...", "date": "...", "significance": "..."}]
  },
  "policy_analysis": {
    "recent_changes": [...],
    "impact_assessment": "...",
    "implications": [...]
  },
  "trade_analysis": {
    "volume_trends": "...",
    "key_commodities": [...],
    "dependencies": [...]
  },
  "scenario_analysis": {
    "best_case": {"description": "...", "probability": 0-100, "key_events": [...]},
    "worst_case": {"description": "...", "probability": 0-100, "key_events": [...]},
    "base_case": {"description": "...", "probability": 0-100, "key_events": [...]}
  },
  "inflection_points": [{"description": "...", "timeline": "...", "potential_impact": "..."}],
  "interdependence_analysis": {
    "economic_dependencies": [...],
    "political_dependencies": [...],
    "supply_chain_dependencies": [...]
  },
  "tension_forecast": {
    "potential_escalations": [...],
    "monitoring_priorities": [...]
  },
  "supply_chain_impact": {
    "affected_sectors": [...],
    "vulnerability_assessment": "..."
  },
  "regional_sentiment": {
    "overall": "positive|neutral|negative",
    "by_region": {...},
    "key_concerns": [...]
  },
  "key_insights": ["...", "..."],
  "recommendations": ["...", "..."]
}"""
        
        # Prepare context
        context = case_context
        context += f"\nGeopolitical Metrics Extracted:\n{str(geopolitical_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data or [])} sources analyzed\n"
        if api_data:
            context += f"API Data: {len(api_data)} fresh data points\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "geopolitical"
            result["metrics_extracted"] = geopolitical_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in geopolitical expert analysis: {e}", exc_info=True)
            return {
                "analysis_type": "geopolitical",
                "error": str(e),
                "metrics_extracted": geopolitical_metrics
            }
    
    async def analyze_as_investment_advisor(
        self,
        case_id: int,
        osint_data: List[Dict] = None,
        api_data: Dict[str, Any] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze as an Investment Advisor
        
        Provides expert-level investment analysis including:
        - Market trend analysis
        - Company performance evaluation
        - Risk assessment (geopolitical, market, operational)
        - Opportunity identification
        - ROI projections
        
        If osint_data is None, fetches ALL OSINT data linked to the case from database.
        If api_data is None, can fetch fresh data from financial APIs when needed.
        Always uses case context from database.
        """
        if not self.client:
            return {
                "analysis_type": "investment",
                "error": "OpenAI not configured"
            }
        
        # Get case context from database
        case_context = ""
        if db:
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if case:
                case_context = f"CASE: {case.name}\n"
                case_context += f"Type: {case.case_type.value if hasattr(case.case_type, 'value') else case.case_type}\n"
                case_context += f"Description: {case.description or 'No description'}\n"
        
        # If osint_data is None, fetch ALL OSINT data from database
        if osint_data is None and db:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            osint_data = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_data.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })
        
        # If api_data is None and we need fresh financial data, fetch it
        if api_data is None:
            try:
                from integrations.alphavantage_api import AlphaVantageAPIService
                from integrations.finnhub_api import FinnhubAPIService
                
                alphavantage = AlphaVantageAPIService()
                finnhub = FinnhubAPIService()
                
                api_data = {
                    "financial_data": {},
                    "market_data": {}
                }
                
                # Note: Financial APIs typically require specific symbols/companies
                # This is a placeholder - actual implementation would need company symbols
                # For now, we'll use OSINT data, but the structure is ready for API integration
            except Exception as e:
                logger.warning(f"Error initializing financial APIs: {e}")
                api_data = {}
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract investment metrics
        investment_metrics = {}
        for osint_item in (osint_data or []):
            data = osint_item.get("data", {})
            metrics = extraction_service.extract_investment_metrics(data)
            # Aggregate metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    investment_metrics[key] = investment_metrics.get(key, 0) + value
                elif isinstance(value, dict):
                    if key not in investment_metrics:
                        investment_metrics[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            investment_metrics[key][sub_key] = investment_metrics[key].get(sub_key, 0) + sub_value
        
        system_prompt = """You are a senior Investment Advisor and Financial Analyst with 20+ years of experience.
Analyze the provided OSINT data and provide expert investment analysis and recommendations.

Focus on:
1. Market trends (stock prices, commodity trends, market indices, volatility)
2. Company performance (financials, growth, profitability, market position)
3. Risk assessment (geopolitical risk, market risk, operational risk, with scores 0-100)
4. Investment opportunities (ROI projections, confidence levels, time horizons)
5. Competitive landscape (market share, positioning, competitive advantages)
6. Financial metrics (revenue trends, profit margins, valuation)
7. ESG factors (Environmental, Social, Governance detailed analysis)
8. Regulatory risk evaluation (current and potential regulatory changes)
9. Comparative market analysis (compare opportunities across markets)
10. Geopolitical factor integration (how geopolitical events affect investments)
11. Timing recommendations (optimal entry/exit points)

Provide concrete recommendations with specific numbers, risk scores, and ROI projections.
Return JSON with:
{
  "market_analysis": {
    "trend": "bullish|bearish|neutral",
    "volatility": "high|medium|low",
    "key_indicators": [...]
  },
  "company_performance": {
    "overall": "strong|moderate|weak",
    "financial_health": "...",
    "growth_prospects": "..."
  },
  "risk_assessment": {
    "geopolitical_risk": {"score": 0-100, "factors": [...]},
    "market_risk": {"score": 0-100, "factors": [...]},
    "operational_risk": {"score": 0-100, "factors": [...]},
    "regulatory_risk": {"score": 0-100, "factors": [...]},
    "overall_risk": "low|medium|high"
  },
  "esg_analysis": {
    "environmental_score": 0-100,
    "social_score": 0-100,
    "governance_score": 0-100,
    "esg_factors": {...}
  },
  "opportunities": [
    {
      "title": "...",
      "roi_projection": "...",
      "confidence": 0-100,
      "time_horizon": "...",
      "risk_level": "low|medium|high"
    }
  ],
  "market_comparison": {
    "markets_analyzed": [...],
    "best_opportunity": "...",
    "comparative_scores": {...}
  },
  "geopolitical_integration": {
    "impact_assessment": "...",
    "affected_factors": [...]
  },
  "timing_recommendation": {
    "entry_timing": "immediate|wait|monitor",
    "exit_timing": "...",
    "rationale": "..."
  },
  "recommendation": "BUY|HOLD|SELL",
  "confidence": 0-100,
  "rationale": "...",
  "key_insights": [...]
}"""
        
        context = case_context
        context += f"\nInvestment Metrics Extracted:\n{str(investment_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data or [])} sources analyzed\n"
        if api_data:
            context += f"API Data: {len(api_data)} fresh data points\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "investment"
            result["metrics_extracted"] = investment_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in investment advisor analysis: {e}", exc_info=True)
            return {
                "analysis_type": "investment",
                "error": str(e),
                "metrics_extracted": investment_metrics
            }
    
    async def analyze_as_social_consultant(
        self,
        case_id: int,
        osint_data: List[Dict],
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Social Public Affairs Consultant
        
        Provides expert-level social and reputation analysis including:
        - Public sentiment analysis by platform
        - Viral content identification
        - Influencer network analysis
        - Community engagement metrics
        - Reputation risk assessment
        """
        if not self.client:
            return {
                "analysis_type": "social",
                "error": "OpenAI not configured"
            }
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract social metrics
        social_metrics = {}
        for osint_item in osint_data:
            data = osint_item.get("data", {})
            metrics = extraction_service.extract_social_metrics(data)
            # Aggregate metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    social_metrics[key] = social_metrics.get(key, 0) + value
                elif isinstance(value, dict):
                    if key not in social_metrics:
                        social_metrics[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            social_metrics[key][sub_key] = social_metrics[key].get(sub_key, 0) + sub_value
        
        system_prompt = """You are a senior Social Public Affairs Consultant and Reputation Management Expert.
Analyze the provided OSINT data and provide expert social and reputation analysis.

Focus on:
1. Public sentiment (by platform: Instagram, TikTok, Twitter/X, YouTube, etc.)
2. Viral content (top posts, engagement metrics, reach, impact)
3. Influencer network (key opinion leaders, their reach, influence, sentiment)
4. Community engagement (engagement rates, growth, reactions, shares)
5. Reputation status (positive/negative trends, crisis indicators, recovery potential)
6. Platform-specific insights (which platforms are most active, sentiment differences)
7. Crisis detection in real-time (identify potential reputation crises early)
8. Narrative analysis (dominant narratives, counter-narratives, narrative shifts)
9. Reputation trend prediction (forecast future reputation trajectory)
10. Communication recommendations (specific messaging strategies)

Provide concrete insights with specific numbers, engagement metrics, and actionable recommendations.
Return JSON with:
{
  "sentiment_analysis": {
    "overall": "positive|neutral|negative",
    "by_platform": {
      "Instagram": {"positive": X, "negative": Y, "neutral": Z},
      "TikTok": {...},
      "Twitter/X": {...}
    },
    "trend": "improving|stable|deteriorating"
  },
  "viral_content": [
    {
      "platform": "...",
      "engagement": X,
      "reach": Y,
      "impact": "..."
    }
  ],
  "influencer_analysis": {
    "key_influencers": [...],
    "total_reach": X,
    "average_sentiment": "...",
    "critical_influencers": [...]
  },
  "community_metrics": {
    "engagement_rate": "...",
    "growth_rate": "...",
    "viral_coefficient": X
  },
  "reputation_assessment": {
    "status": "strong|moderate|at_risk|crisis",
    "risk_factors": [...],
    "recovery_potential": "...",
    "crisis_indicators": [...],
    "crisis_probability": 0-100
  },
  "narrative_analysis": {
    "dominant_narratives": [...],
    "counter_narratives": [...],
    "narrative_shifts": [...]
  },
  "reputation_forecast": {
    "30_days": "improving|stable|deteriorating",
    "90_days": "improving|stable|deteriorating",
    "confidence": 0-100
  },
  "communication_recommendations": [...],
  "recommendations": [...],
  "key_insights": [...]
}"""
        
        context = f"Social Metrics Extracted:\n{str(social_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data)} sources analyzed\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "social"
            result["metrics_extracted"] = social_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in social consultant analysis: {e}", exc_info=True)
            return {
                "analysis_type": "social",
                "error": str(e),
                "metrics_extracted": social_metrics
            }
    
    async def analyze_as_data_analyst(
        self,
        case_id: int,
        osint_data: List[Dict],
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Data Analytics Expert
        
        Provides comprehensive data analytics including:
        - Cross-platform analysis
        - Temporal trends
        - Data quality assessment
        - Statistical insights
        - Pattern recognition
        """
        if not self.client:
            return {
                "analysis_type": "data_analytics",
                "error": "OpenAI not configured"
            }
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract all metrics
        all_metrics = {}
        for osint_item in osint_data:
            data = osint_item.get("data", {})
            query_type = osint_item.get("query_type", "")
            metrics = extraction_service.extract_all_metrics(data, query_type)
            # Aggregate
            for category, category_metrics in metrics.items():
                if category not in all_metrics:
                    all_metrics[category] = {}
                for key, value in category_metrics.items():
                    if isinstance(value, (int, float)):
                        all_metrics[category][key] = all_metrics[category].get(key, 0) + value
        
        system_prompt = """You are a senior Data Analytics Expert and OSINT Specialist.
Analyze the provided OSINT data comprehensively across all dimensions.

Focus on:
1. Data quality and completeness
2. Cross-platform patterns and correlations
3. Temporal trends and anomalies
4. Statistical significance of findings
5. Data gaps and recommendations for additional collection
6. Key insights and actionable intelligence

Provide comprehensive analytics with statistical rigor.
Return JSON with:
{
  "data_quality": {
    "completeness": "high|medium|low",
    "sources_diversity": X,
    "temporal_coverage": "...",
    "gaps_identified": [...]
  },
  "cross_platform_analysis": {
    "patterns": [...],
    "correlations": [...],
    "platform_comparison": {...}
  },
  "temporal_trends": {
    "overall_trend": "...",
    "key_events": [...],
    "anomalies": [...]
  },
  "statistical_insights": {
    "significant_findings": [...],
    "confidence_levels": {...}
  },
  "recommendations": {
    "additional_data_needed": [...],
    "analysis_priorities": [...]
  },
  "key_insights": [...]
}"""
        
        context = f"All Metrics Extracted:\n{str(all_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data)} sources analyzed\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "data_analytics"
            result["metrics_extracted"] = all_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in data analyst analysis: {e}", exc_info=True)
            return {
                "analysis_type": "data_analytics",
                "error": str(e),
                "metrics_extracted": all_metrics
            }
    
    async def analyze_as_reputation_manager(
        self,
        case_id: int,
        osint_data: List[Dict] = None,
        api_data: Dict[str, Any] = None,
        entity_name: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Reputation Management Expert
        
        Provides expert-level reputation analysis including:
        - Real-time crisis detection
        - Key influencer identification
        - Narrative analysis
        - Reputation trend prediction
        - Communication recommendations
        
        If osint_data is None, fetches ALL OSINT data linked to the case from database.
        If api_data is None, can fetch fresh data from social APIs when needed.
        Always uses case context from database.
        """
        if not self.client:
            return {
                "analysis_type": "reputation",
                "error": "OpenAI not configured"
            }
        
        # Get case context from database
        case_context = ""
        if db:
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if case:
                case_context = f"CASE: {case.name}\n"
                case_context += f"Type: {case.case_type.value if hasattr(case.case_type, 'value') else case.case_type}\n"
                case_context += f"Description: {case.description or 'No description'}\n"
        
        # If osint_data is None, fetch ALL OSINT data from database
        if osint_data is None and db:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            osint_data = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_data.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })
        
        # If api_data is None and we need fresh social data, fetch it
        if api_data is None and entity_name:
            try:
                from integrations.news_api import NewsAPIService
                from integrations.reddit_api import RedditAPIService
                
                news_api = NewsAPIService()
                reddit_api = RedditAPIService()
                
                api_data = {
                    "news": [],
                    "reddit": []
                }
                
                # Fetch fresh news data
                try:
                    news_result = await news_api.search(
                        query=entity_name,
                        language="es",
                        sort_by="publishedAt"
                    )
                    if news_result.get("status") == "ok" and "articles" in news_result:
                        api_data["news"] = news_result["articles"][:10]  # Limit to 10 articles
                except Exception as e:
                    logger.warning(f"Error fetching fresh news data for reputation: {e}")
                
                # Fetch fresh Reddit data
                try:
                    reddit_result = await reddit_api.search(
                        query=entity_name,
                        limit=10
                    )
                    if "data" in reddit_result and "children" in reddit_result["data"]:
                        api_data["reddit"] = reddit_result["data"]["children"][:10]
                except Exception as e:
                    logger.warning(f"Error fetching fresh Reddit data for reputation: {e}")
            except Exception as e:
                logger.warning(f"Error initializing APIs for fresh data: {e}")
                api_data = {}
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract reputation metrics
        reputation_metrics = {}
        for osint_item in (osint_data or []):
            data = osint_item.get("data", {})
            metrics = extraction_service.extract_social_metrics(data)
            # Aggregate metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    reputation_metrics[key] = reputation_metrics.get(key, 0) + value
                elif isinstance(value, dict):
                    if key not in reputation_metrics:
                        reputation_metrics[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            reputation_metrics[key][sub_key] = reputation_metrics[key].get(sub_key, 0) + sub_value
        
        system_prompt = """You are a senior Reputation Management Expert with 20+ years of experience.
Analyze the provided OSINT data and provide expert reputation management analysis.

Focus on:
1. Crisis detection (identify potential or active reputation crises, severity, urgency)
2. Key influencers (identify opinion leaders, their reach, sentiment, influence score)
3. Narrative analysis (dominant narratives, emerging stories, narrative shifts)
4. Reputation trends (current trajectory, predicted changes, key drivers)
5. Communication strategy (recommendations for messaging, channels, timing, tone)

Provide actionable insights with specific recommendations.
Return JSON with:
{
  "crisis_analysis": {
    "crisis_level": "none|low|moderate|high|critical",
    "crisis_indicators": [...],
    "urgency": "low|medium|high|critical",
    "key_issues": [...]
  },
  "influencer_analysis": {
    "key_influencers": [
      {
        "name": "...",
        "platform": "...",
        "reach": X,
        "influence_score": 0-100,
        "sentiment": "positive|neutral|negative",
        "engagement": X
      }
    ],
    "total_reach": X,
    "average_sentiment": "..."
  },
  "narrative_analysis": {
    "dominant_narratives": [...],
    "emerging_stories": [...],
    "narrative_shifts": [...],
    "narrative_risk": "low|medium|high"
  },
  "reputation_trends": {
    "current_trajectory": "improving|stable|deteriorating",
    "predicted_change": "+/-X points",
    "key_drivers": [...],
    "confidence": 0-100
  },
  "communication_recommendations": [
    {
      "action": "...",
      "channel": "...",
      "timing": "...",
      "tone": "...",
      "priority": "low|medium|high"
    }
  ],
  "key_insights": [...]
}"""
        
        context = case_context
        context += f"\nEntity: {entity_name or 'Not specified'}\n"
        context += f"Reputation Metrics Extracted:\n{str(reputation_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data or [])} sources analyzed\n"
        if api_data:
            context += f"API Data: {len(api_data)} fresh data points\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "reputation"
            result["metrics_extracted"] = reputation_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in reputation manager analysis: {e}", exc_info=True)
            return {
                "analysis_type": "reputation",
                "error": str(e),
                "metrics_extracted": reputation_metrics
            }
    
    async def analyze_as_public_affairs_consultant(
        self,
        case_id: int,
        osint_data: List[Dict] = None,
        api_data: Dict[str, Any] = None,
        policy_topic: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Public Affairs Consultant
        
        Provides expert-level public affairs analysis including:
        - Stakeholder mapping
        - Political positioning analysis
        - Advocacy opportunity identification
        - Regulatory impact analysis
        - Engagement strategies
        
        If osint_data is None, fetches ALL OSINT data linked to the case from database.
        If api_data is None, can fetch fresh data from news/policy APIs when needed.
        Always uses case context from database.
        """
        if not self.client:
            return {
                "analysis_type": "public_affairs",
                "error": "OpenAI not configured"
            }
        
        # Get case context from database
        case_context = ""
        if db:
            from sqlalchemy import select
            from models.case import Case
            
            case_result = await db.execute(select(Case).where(Case.id == case_id))
            case = case_result.scalar_one_or_none()
            
            if case:
                case_context = f"CASE: {case.name}\n"
                case_context += f"Type: {case.case_type.value if hasattr(case.case_type, 'value') else case.case_type}\n"
                case_context += f"Description: {case.description or 'No description'}\n"
        
        # If osint_data is None, fetch ALL OSINT data from database
        if osint_data is None and db:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            osint_data = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_data.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })
        
        # If api_data is None and we need fresh news/policy data, fetch it
        if api_data is None and policy_topic:
            try:
                from integrations.news_api import NewsAPIService
                
                news_api = NewsAPIService()
                api_data = {
                    "news": []
                }
                
                # Fetch fresh news data about the policy topic
                try:
                    news_result = await news_api.search(
                        query=policy_topic,
                        language="es",
                        sort_by="publishedAt"
                    )
                    if news_result.get("status") == "ok" and "articles" in news_result:
                        api_data["news"] = news_result["articles"][:10]  # Limit to 10 articles
                except Exception as e:
                    logger.warning(f"Error fetching fresh news data for public affairs: {e}")
            except Exception as e:
                logger.warning(f"Error initializing News API for fresh data: {e}")
                api_data = {}
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract public affairs metrics
        public_affairs_metrics = {}
        for osint_item in (osint_data or []):
            data = osint_item.get("data", {})
            # Extract policy mentions, stakeholder mentions, etc.
            if isinstance(data, dict):
                for key in ['policy', 'regulation', 'stakeholder', 'government', 'legislative']:
                    if key in str(data).lower():
                        public_affairs_metrics[key] = public_affairs_metrics.get(key, 0) + 1
        
        system_prompt = """You are a senior Public Affairs Consultant with 20+ years of experience.
Analyze the provided OSINT data and provide expert public affairs analysis.

Focus on:
1. Stakeholder mapping (identify key stakeholders, their positions, influence, engagement level)
2. Political positioning (analyze political landscape, positions of key actors, alignment)
3. Advocacy opportunities (identify windows for advocacy, key decision points, leverage points)
4. Regulatory impact (assess impact of policies/regulations, compliance requirements, risks)
5. Engagement strategies (recommend approaches for stakeholder engagement, messaging, timing)

Provide actionable insights with specific recommendations.
Return JSON with:
{
  "stakeholder_mapping": {
    "key_stakeholders": [
      {
        "name": "...",
        "type": "government|media|influencer|community|industry",
        "position": "supportive|neutral|opposed|unknown",
        "influence_score": 0-100,
        "engagement_level": "high|medium|low"
      }
    ],
    "stakeholder_network": {...}
  },
  "political_positioning": {
    "political_landscape": "...",
    "key_actors": [...],
    "alignment_analysis": {...},
    "political_risks": [...]
  },
  "advocacy_opportunities": [
    {
      "opportunity": "...",
      "window": "...",
      "key_decision_points": [...],
      "leverage_points": [...],
      "priority": "low|medium|high"
    }
  ],
  "regulatory_impact": {
    "policies_identified": [...],
    "impact_assessment": "...",
    "compliance_requirements": [...],
    "regulatory_risks": [...]
  },
  "engagement_strategies": [
    {
      "stakeholder": "...",
      "approach": "...",
      "messaging": "...",
      "timing": "...",
      "channels": [...]
    }
  ],
  "key_insights": [...]
}"""
        
        context = case_context
        context += f"\nPolicy Topic: {policy_topic or 'Not specified'}\n"
        context += f"Public Affairs Metrics Extracted:\n{str(public_affairs_metrics)}\n\n"
        context += f"OSINT Data Summary: {len(osint_data or [])} sources analyzed\n"
        if api_data:
            context += f"API Data: {len(api_data)} fresh data points\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "public_affairs"
            result["metrics_extracted"] = public_affairs_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in public affairs consultant analysis: {e}", exc_info=True)
            return {
                "analysis_type": "public_affairs",
                "error": str(e),
                "metrics_extracted": public_affairs_metrics
            }
    
    async def analyze_as_geopolitical_analyst(
        self,
        case_id: int,
        osint_data: List[Dict] = None,
        api_data: Dict[str, Any] = None,
        countries: Optional[List[str]] = None,
        db = None
    ) -> Dict[str, Any]:
        """Analyze as a Geopolitical Analyst (Enhanced)
        
        Enhanced expert-level geopolitical analysis including:
        - Multiple scenario analysis
        - Inflection point identification
        - Complex interdependence analysis
        - Tension prediction
        - Supply chain impact analysis
        
        If osint_data is None, fetches ALL OSINT data linked to the case from database.
        If api_data is None, can fetch fresh data from geopolitical APIs when needed.
        Always uses case context from database.
        """
        if not self.client:
            return {
                "analysis_type": "geopolitical_advanced",
                "error": "OpenAI not configured"
            }
        
        # If osint_data is None, fetch ALL OSINT data from database
        if osint_data is None and db:
            from sqlalchemy import select
            from models.osint import OSINTQuery, OSINTResult
            
            queries_result = await db.execute(
                select(OSINTQuery).where(OSINTQuery.case_id == case_id)
            )
            queries = queries_result.scalars().all()
            
            osint_data = []
            for query in queries:
                results_result = await db.execute(
                    select(OSINTResult).where(OSINTResult.query_id == query.id)
                )
                results = results_result.scalars().all()
                for result in results:
                    osint_data.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "status": result.status
                    })
        
        # Use existing geopolitical expert analysis as base
        base_analysis = await self.analyze_as_geopolitical_expert(case_id, osint_data, api_data, db)
        
        if "error" in base_analysis:
            return base_analysis
        
        from services.data_extraction_service import DataExtractionService
        extraction_service = DataExtractionService()
        
        # Extract advanced metrics
        advanced_metrics = {}
        for osint_item in osint_data:
            data = osint_item.get("data", {})
            metrics = extraction_service.extract_geopolitical_metrics(data)
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    advanced_metrics[key] = advanced_metrics.get(key, 0) + value
        
        system_prompt = """You are a senior Geopolitical Analyst with 20+ years of experience.
Provide ADVANCED geopolitical analysis building on the base analysis.

Focus on:
1. Scenario analysis (develop best case, worst case, and base case scenarios with probabilities)
2. Inflection points (identify potential turning points, triggers, critical events)
3. Complex interdependencies (analyze economic, political, security interdependencies)
4. Tension prediction (predict potential conflicts, escalation risks, de-escalation opportunities)
5. Supply chain impact (assess impact on global supply chains, dependencies, vulnerabilities)

Return JSON with:
{
  "scenario_analysis": {
    "best_case": {
      "scenario": "...",
      "probability": 0-100,
      "key_factors": [...]
    },
    "worst_case": {
      "scenario": "...",
      "probability": 0-100,
      "key_factors": [...]
    },
    "base_case": {
      "scenario": "...",
      "probability": 0-100,
      "key_factors": [...]
    }
  },
  "inflection_points": [
    {
      "point": "...",
      "type": "political|economic|military|diplomatic",
      "timeline": "...",
      "impact": "low|medium|high|critical"
    }
  ],
  "interdependencies": {
    "economic": {...},
    "political": {...},
    "security": {...},
    "complexity_score": 0-100
  },
  "tension_prediction": {
    "current_tension_level": "low|medium|high|critical",
    "escalation_risks": [...],
    "de_escalation_opportunities": [...],
    "conflict_probability": 0-100
  },
  "supply_chain_impact": {
    "affected_sectors": [...],
    "dependency_risks": [...],
    "vulnerability_assessment": "...",
    "mitigation_recommendations": [...]
  },
  "key_insights": [...]
}"""
        
        context = f"Countries: {', '.join(countries or [])}\n"
        context += f"Base Analysis: {str(base_analysis)[:1000]}\n"
        context += f"Advanced Metrics: {str(advanced_metrics)}\n"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "geopolitical_advanced"
            result["base_analysis"] = base_analysis
            result["metrics_extracted"] = advanced_metrics
            return result
            
        except Exception as e:
            logger.error(f"Error in advanced geopolitical analyst analysis: {e}", exc_info=True)
            return {
                "analysis_type": "geopolitical_advanced",
                "error": str(e),
                "base_analysis": base_analysis,
                "metrics_extracted": advanced_metrics
            }
    
    async def generate_investment_recommendation(self, case_id: int) -> Dict[str, Any]:
        """Generate investment recommendation based on OSINT data"""
        system_prompt = """Eres un experto en análisis de inversiones basado en OSINT.
        Analiza los datos y genera una recomendación con:
        - type: BUY, HOLD, o SELL
        - confidence: Nivel de confianza (0-100)
        - rationale: Justificación de la recomendación
        - risks: Lista de riesgos (geopolítico, político, social) con level y percentage
        - opportunities: Lista de oportunidades con title, description, confidence, impact
        
        Responde en JSON válido."""
        
        # TODO: Get actual case data
        context = f"Caso ID: {case_id}"
        
        if not self.client:
            return {
                "type": "hold",
                "confidence": 0.0,
                "rationale": "Análisis no disponible: OpenAI no configurado",
                "risks": [],
                "opportunities": []
            }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context[:4000]}
                ],
                temperature=0.7,
                timeout=30.0,
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {
                    "type": "hold",
                    "confidence": 50.0,
                    "rationale": response.choices[0].message.content,
                    "risks": [],
                    "opportunities": []
                }
        except Exception as e:
            logger.error(f"Error en generate_investment_recommendation: {e}")
            return {
                "type": "hold",
                "confidence": 0.0,
                "rationale": f"Error en análisis: {str(e)}",
                "risks": [],
                "opportunities": []
            }
