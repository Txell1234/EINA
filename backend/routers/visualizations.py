"""
Visualizations router - Generate data for Economic Intelligence Unit style visualizations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
# Autenticació eliminada
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import select, func
from models.osint import OSINTQuery, OSINTResult
from models.case import Case
from models.ai_analysis import AIAnalysis, Trend, Concept, AIPrediction
from models.ai_classification import AIClassification

router = APIRouter()

def _get_prediction_meaning(prediction_type: str) -> str:
    """Get human-readable meaning for prediction type"""
    meanings = {
        "trend": "Predicció de tendència: Indica la direcció esperada de l'evolució del tema analitzat",
        "risk": "Predicció de risc: Identifica possibles riscos geopolítics, polítics o socials",
        "opportunity": "Predicció d'oportunitat: Detecta oportunitats potencials basades en les dades",
        "sentiment": "Predicció de sentiment: Prediu l'evolució de l'opinió pública",
        "volume": "Predicció de volum: Estima canvis en el volum de mencions o activitat"
    }
    return meanings.get(prediction_type, f"Predicció de tipus {prediction_type}")

class NetworkNode(BaseModel):
    id: str
    label: str
    type: str
    size: Optional[int] = None

class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: Optional[int] = 1
    type: Optional[str] = None

class NetworkGraphResponse(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]

class TrendDataPoint(BaseModel):
    date: str
    value: float
    category: Optional[str] = None
    source: Optional[str] = None  # e.g., "news", "social_media", "osint"
    metric_type: Optional[str] = None  # e.g., "mentions", "sentiment", "volume"
    description: Optional[str] = None

class MetricValue(BaseModel):
    """A concrete metric value for a KPI"""
    kpi_name: str
    value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    trend: str  # increasing, decreasing, stable
    details: Optional[Dict[str, Any]] = None  # e.g., social_network, date_range
    measurement_unit: Optional[str] = None

class TrendAnalysisResponse(BaseModel):
    data: List[TrendDataPoint]
    prediction: Optional[List[TrendDataPoint]] = None
    metadata: Optional[Dict[str, Any]] = None  # Información sobre qué se está analizando
    data_sources_breakdown: Optional[List[Dict[str, Any]]] = None  # Desglose por herramienta
    queries_executed: Optional[List[Dict[str, Any]]] = None  # Detalles de consultas
    case_linked_queries: Optional[int] = None  # Cuántas consultas están vinculadas al caso
    total_results_by_source: Optional[Dict[str, int]] = None  # Total por herramienta
    # New fields for concrete metrics
    metrics: Optional[List[MetricValue]] = None  # Concrete metrics extracted
    insights: Optional[List[str]] = None  # AI-generated insights
    comments_by_social_network: Optional[Dict[str, Dict[str, int]]] = None
    concepts: Optional[List[Dict[str, Any]]] = None

class OpinionTrendPoint(BaseModel):
    date: str
    count: int
    average_sentiment: float

class OpinionTrendResponse(BaseModel):
    case_id: int
    concept: Optional[str] = None
    total_events: int
    sentiment_breakdown: Dict[str, int]
    trend: List[OpinionTrendPoint]
    top_concepts: Optional[List[Dict[str, Any]]] = None

class OpinionEventItem(BaseModel):
    classification_id: int
    osint_result_id: Optional[int]
    created_at: str
    sentiment: str
    sentiment_score: float
    concepts: List[str]
    topics: List[str]
    content_text: str
    source: Optional[str] = None

class OpinionEventResponse(BaseModel):
    case_id: int
    concept: Optional[str] = None
    total: int
    events: List[OpinionEventItem]

class Relationship(BaseModel):
    from_entity: str
    to_entity: str
    type: str
    strength: int

class RelationshipMapResponse(BaseModel):
    relationships: List[Relationship]

@router.get("/network/{case_id}", response_model=NetworkGraphResponse)
async def get_network_graph(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate network graph data for a case"""
    from sqlalchemy import select
    
    # Get case
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get OSINT results for this case
    queries_result = await db.execute(
        select(OSINTQuery).where(OSINTQuery.case_id == case_id)
    )
    queries = queries_result.scalars().all()
    
    nodes: List[NetworkNode] = []
    edges: List[NetworkEdge] = []
    node_ids = set()
    
    # Add case as central node
    nodes.append(NetworkNode(id=f"case_{case_id}", label=case.name, type="case", size=20))
    node_ids.add(f"case_{case_id}")
    
    # Process OSINT queries and results
    for query in queries:
        query_node_id = f"query_{query.id}"
        if query_node_id not in node_ids:
            nodes.append(NetworkNode(
                id=query_node_id,
                label=f"Query: {query.query_type}",
                type="query",
                size=10
            ))
            node_ids.add(query_node_id)
            edges.append(NetworkEdge(
                source=f"case_{case_id}",
                target=query_node_id,
                weight=1,
                type="has_query"
            ))
        
        # Get results for this query
        results_result = await db.execute(
            select(OSINTResult).where(OSINTResult.query_id == query.id)
        )
        results = results_result.scalars().all()
        
        for result in results:
            result_node_id = f"result_{result.id}"
            if result_node_id not in node_ids:
                nodes.append(NetworkNode(
                    id=result_node_id,
                    label=f"Result {result.id}",
                    type="result",
                    size=8
                ))
                node_ids.add(result_node_id)
                edges.append(NetworkEdge(
                    source=query_node_id,
                    target=result_node_id,
                    weight=1,
                    type="has_result"
                ))
            
            # Extract entities from result data
            if result.data and isinstance(result.data, dict):
                # Look for common entity types
                for key in ['emails', 'hosts', 'ips', 'domains']:
                    if key in result.data and isinstance(result.data[key], list):
                        for entity in result.data[key][:5]:  # Limit to 5 per type
                            entity_id = f"{key}_{entity}"
                            if entity_id not in node_ids:
                                nodes.append(NetworkNode(
                                    id=entity_id,
                                    label=str(entity),
                                    type=key[:-1],  # Remove 's'
                                    size=5
                                ))
                                node_ids.add(entity_id)
                                edges.append(NetworkEdge(
                                    source=result_node_id,
                                    target=entity_id,
                                    weight=1,
                                    type="contains"
                                ))
    
    return NetworkGraphResponse(nodes=nodes, edges=edges)

@router.post("/trends/{case_id}/configure")
async def configure_trend_analysis(
    case_id: int,
    kpi_ids: List[int] = Body(default=[]),
    db: AsyncSession = Depends(get_db)
):
    """Configure which KPIs to track for trend analysis"""
    from sqlalchemy import select
    from models.case import CaseKPI
    from models.qualitative import KPI
    
    # Get case
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update is_tracked for all case KPIs
    all_case_kpis = await db.execute(
        select(CaseKPI).where(CaseKPI.case_id == case_id)
    )
    case_kpis = all_case_kpis.scalars().all()
    
    for case_kpi in case_kpis:
        case_kpi.is_tracked = case_kpi.kpi_id in kpi_ids
    
    await db.commit()
    
    return {
        "case_id": case_id,
        "tracked_kpi_ids": kpi_ids,
        "message": "KPIs configured successfully"
    }

@router.get("/opinion-trends", response_model=OpinionTrendResponse)
async def get_public_opinion_trends(
    case_id: int,
    concept: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get public opinion trends by case and optional concept."""
    from collections import defaultdict

    result = await db.execute(
        select(AIClassification).where(AIClassification.case_id == case_id)
    )
    classifications = result.scalars().all()

    if concept:
        concept_lower = concept.lower()
        classifications = [
            c for c in classifications
            if any(concept_lower == str(item).lower() for item in (c.concepts or []))
        ]

    sentiment_breakdown = defaultdict(int)
    daily_counts: Dict[str, List[float]] = defaultdict(list)

    for classification in classifications:
        sentiment = classification.sentiment or "neutral"
        sentiment_breakdown[sentiment] += 1
        created_at = classification.created_at.date().isoformat() if classification.created_at else None
        if created_at:
            daily_counts[created_at].append(classification.sentiment_score or 0.0)

    trend = [
        OpinionTrendPoint(
            date=day,
            count=len(scores),
            average_sentiment=sum(scores) / len(scores) if scores else 0.0
        )
        for day, scores in sorted(daily_counts.items())
    ]

    top_concepts = None
    if not concept:
        concept_counts = defaultdict(int)
        for classification in classifications:
            for item in classification.concepts or []:
                concept_counts[str(item)] += 1
        top_concepts = [
            {"concept": name, "count": count}
            for name, count in sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

    return OpinionTrendResponse(
        case_id=case_id,
        concept=concept,
        total_events=len(classifications),
        sentiment_breakdown=dict(sentiment_breakdown),
        trend=trend,
        top_concepts=top_concepts
    )

@router.get("/opinion-events", response_model=OpinionEventResponse)
async def list_public_opinion_events(
    case_id: int,
    concept: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List classified OSINT events for a case, optionally filtered by concept."""
    result = await db.execute(
        select(AIClassification)
        .where(AIClassification.case_id == case_id)
        .order_by(AIClassification.created_at.desc())
    )
    classifications = result.scalars().all()

    if concept:
        concept_lower = concept.lower()
        classifications = [
            c for c in classifications
            if any(concept_lower == str(item).lower() for item in (c.concepts or []))
        ]

    paged = classifications[offset:offset + limit]
    events: List[OpinionEventItem] = []
    osint_result_ids = [c.osint_result_id for c in paged if c.osint_result_id]
    osint_results = {}
    if osint_result_ids:
        result = await db.execute(
            select(OSINTResult).where(OSINTResult.id.in_(osint_result_ids))
        )
        osint_results = {r.id: r for r in result.scalars().all()}

    for classification in paged:
        osint_result = osint_results.get(classification.osint_result_id)
        source = None
        if osint_result and isinstance(osint_result.data, dict):
            source = osint_result.data.get("source") or osint_result.data.get("source_name")
        events.append(OpinionEventItem(
            classification_id=classification.id,
            osint_result_id=classification.osint_result_id,
            created_at=classification.created_at.isoformat() if classification.created_at else "",
            sentiment=classification.sentiment,
            sentiment_score=classification.sentiment_score or 0.0,
            concepts=classification.concepts or [],
            topics=classification.topics or [],
            content_text=classification.content_text,
            source=source
        ))

    return OpinionEventResponse(
        case_id=case_id,
        concept=concept,
        total=len(classifications),
        events=events
    )

@router.get("/trends/{case_id}", response_model=TrendAnalysisResponse)
async def get_trend_analysis(
    case_id: int,
    days: int = 30,
    kpi_ids: Optional[List[int]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate trend analysis data for a case with real metrics"""
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get case
        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get KPIs for this case (either specified or all tracked KPIs)
        from models.case import CaseKPI
        from models.qualitative import KPI
        
        if kpi_ids:
            # Use specified KPIs
            case_kpis_result = await db.execute(
                select(CaseKPI).where(
                    CaseKPI.case_id == case_id,
                    CaseKPI.kpi_id.in_(kpi_ids)
                )
            )
        else:
            # Get all tracked KPIs for this case
            case_kpis_result = await db.execute(
                select(CaseKPI).where(
                    CaseKPI.case_id == case_id,
                    CaseKPI.is_tracked == True
                )
            )
        
        case_kpis = case_kpis_result.scalars().all()
        kpis_to_track = []
        for case_kpi in case_kpis:
            kpi_result = await db.execute(select(KPI).where(KPI.id == case_kpi.kpi_id))
            kpi = kpi_result.scalar_one_or_none()
            if kpi:
                kpis_to_track.append({
                    "id": kpi.id,
                    "name": kpi.name,
                    "metric_type": kpi.metric_type,
                    "measurement_unit": case_kpi.measurement_unit or kpi.measurement_unit,
                    "target_value": case_kpi.target_value or kpi.target_value
                })
        
        # Get OSINT queries to understand data sources
        queries_result = await db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        )
        queries = queries_result.scalars().all()
        
        # Collect all OSINT data for AI analysis
        osint_data_for_ai = []
        for query in queries:
            results_result = await db.execute(
                select(OSINTResult).where(OSINTResult.query_id == query.id)
            )
            results = results_result.scalars().all()
            for result in results:
                if result.data:
                    osint_data_for_ai.append({
                        "query_id": query.id,
                        "query_type": query.query_type,
                        "data": result.data,
                        "created_at": result.created_at.isoformat() if result.created_at else None
                    })
        
        # Determine data sources and metric types
        sources = set()
        metric_types = []
        for query in queries:
            if query.query_type == "google_news":
                sources.add("notícies")
                metric_types.append("mencions en notícies")
            elif query.query_type == "reddit":
                sources.add("xarxes socials")
                metric_types.append("mencions a Reddit")
            elif query.query_type == "github":
                sources.add("repositoris")
                metric_types.append("activitat a GitHub")
            elif query.query_type in ["sherlock", "recon-ng", "theharvester"]:
                sources.add("eines OSINT")
                metric_types.append("dades OSINT")
            else:
                sources.add("dades OSINT")
                metric_types.append("dades recopilades")
        
        # Get trends from AI analysis
        trends_result = await db.execute(
            select(Trend).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
        )
        trends = trends_result.scalars().all()
        
        # Get concepts from AI analysis
        concepts_result = await db.execute(
            select(Concept).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
        )
        concepts = concepts_result.scalars().all()
        
        # Extract concepts data
        for concept in concepts:
            concepts_extracted.append({
                "name": concept.name,
                "category": concept.category or "general",
                "relevance": float(concept.relevance) if concept.relevance else 0.5,
                "confidence": float(concept.confidence) if concept.confidence else 0.5
            })
        
        # Get OSINT results to count actual data points
        results_count_by_date: Dict[str, int] = {}
        sentiment_by_date: Dict[str, List[float]] = {}
        
        # Desglose por herramienta OSINT
        results_by_tool: Dict[str, int] = {}  # Total de resultados por herramienta
        results_by_tool_and_date: Dict[str, Dict[str, int]] = {}  # Resultados por herramienta y fecha
        queries_executed_list: List[Dict[str, Any]] = []  # Lista de consultas ejecutadas
        
        # Análisis de comentarios por red social
        comments_by_social_network: Dict[str, Dict[str, int]] = {}  # {network: {positive: X, negative: Y, neutral: Z}}
        concepts_extracted: List[Dict[str, Any]] = []  # Conceptos extraídos del caso
        tool_names_map = {
            "google_news": "Google News",
            "reddit": "Reddit",
            "github": "GitHub",
            "sherlock": "Sherlock",
            "recon-ng": "Recon-ng",
            "theharvester": "theHarvester",
            "shodan": "Shodan",
            "wayback": "Wayback Machine",
            "dns": "DNS Lookup",
            "whois": "WHOIS Lookup",
            "ip_geolocation": "IP Geolocation",
            # EnsembleData tools
            "ensembledata_tiktok_user_info": "TikTok (EnsembleData)",
            "ensembledata_tiktok_user_posts": "TikTok (EnsembleData)",
            "ensembledata_tiktok_hashtag_posts": "TikTok (EnsembleData)",
            "ensembledata_tiktok_keyword_posts": "TikTok (EnsembleData)",
            "ensembledata_instagram_user_info": "Instagram (EnsembleData)",
            "ensembledata_instagram_user_posts": "Instagram (EnsembleData)",
            "ensembledata_instagram_hashtag_posts": "Instagram (EnsembleData)",
            "ensembledata_youtube_channel_info": "YouTube (EnsembleData)",
            "ensembledata_youtube_channel_videos": "YouTube (EnsembleData)",
            "ensembledata_youtube_keyword_posts": "YouTube (EnsembleData)",
            "ensembledata_threads_user_info": "Threads (EnsembleData)",
            "ensembledata_threads_user_posts": "Threads (EnsembleData)",
            "ensembledata_threads_keyword_posts": "Threads (EnsembleData)",
            "ensembledata_reddit_subreddit_posts": "Reddit (EnsembleData)",
            "ensembledata_twitter_user_info": "Twitter/X (EnsembleData)",
            "ensembledata_twitter_user_tweets": "Twitter/X (EnsembleData)",
            "ensembledata_twitch_keyword_posts": "Twitch (EnsembleData)",
            "ensembledata_snapchat_user_info": "Snapchat (EnsembleData)",
        }
        
        for query in queries:
            # Agregar consulta a la lista de consultas ejecutadas
            query_params = query.query_params if query.query_params else {}
            tool_name = tool_names_map.get(query.query_type, query.query_type.capitalize())
            
            queries_executed_list.append({
                "id": query.id,
                "tool": tool_name,
                "tool_type": query.query_type,
                "params": query_params,
                "status": query.status.value if hasattr(query.status, 'value') else str(query.status),
                "created_at": query.created_at.isoformat() if query.created_at else None,
                "case_linked": query.case_id == case_id
            })
            
            results_result = await db.execute(
                select(OSINTResult).where(OSINTResult.query_id == query.id)
            )
            results = results_result.scalars().all()
            
            # Inicializar contador por herramienta si no existe
            if query.query_type not in results_by_tool:
                results_by_tool[query.query_type] = 0
                results_by_tool_and_date[query.query_type] = {}
            
            for result in results:
                if result.created_at:
                    date_key = result.created_at.strftime("%Y-%m-%d")
                    results_count_by_date[date_key] = results_count_by_date.get(date_key, 0) + 1
                    results_by_tool[query.query_type] += 1
                    results_by_tool_and_date[query.query_type][date_key] = results_by_tool_and_date[query.query_type].get(date_key, 0) + 1
                    
                    # IMPORTANT: Use AI classifications if available, otherwise fallback to raw data
                    classification_result = await db.execute(
                        select(AIClassification).where(AIClassification.osint_result_id == result.id)
                    )
                    classification = classification_result.scalar_one_or_none()
                    
                    if classification:
                        # Use AI classification (preferred)
                        sentiment_val = classification.sentiment_score or 0.0
                        sentiment_label = classification.sentiment
                        
                        # Determine social network from classification content_type or query type
                        social_network = None
                        content_type = classification.content_type.lower()
                        if 'tiktok' in content_type or 'tiktok' in query.query_type.lower():
                            social_network = 'TikTok'
                        elif 'instagram' in content_type or 'instagram' in query.query_type.lower():
                            social_network = 'Instagram'
                        elif 'twitter' in content_type or 'x' in content_type or 'twitter' in query.query_type.lower() or 'x' in query.query_type.lower():
                            social_network = 'Twitter/X'
                        elif 'reddit' in content_type or 'reddit' in query.query_type.lower():
                            social_network = 'Reddit'
                        elif 'youtube' in content_type or 'youtube' in query.query_type.lower():
                            social_network = 'YouTube'
                        elif 'threads' in content_type or 'threads' in query.query_type.lower():
                            social_network = 'Threads'
                        elif 'snapchat' in content_type or 'snapchat' in query.query_type.lower():
                            social_network = 'Snapchat'
                        
                        if date_key not in sentiment_by_date:
                            sentiment_by_date[date_key] = []
                        sentiment_by_date[date_key].append(float(sentiment_val))
                        
                        # Contar comentarios por red social y sentimiento usando clasificación IA
                        if social_network:
                            if social_network not in comments_by_social_network:
                                comments_by_social_network[social_network] = {'positive': 0, 'negative': 0, 'neutral': 0}
                            comments_by_social_network[social_network][sentiment_label] = comments_by_social_network[social_network].get(sentiment_label, 0) + 1
                    else:
                        # Fallback: Try to extract sentiment from raw data if no classification available
                        if result.data and isinstance(result.data, dict):
                            try:
                                # Determinar red social basada en el tipo de query
                                social_network = None
                                if 'tiktok' in query.query_type.lower():
                                    social_network = 'TikTok'
                                elif 'instagram' in query.query_type.lower():
                                    social_network = 'Instagram'
                                elif 'twitter' in query.query_type.lower() or 'x' in query.query_type.lower():
                                    social_network = 'Twitter/X'
                                elif 'reddit' in query.query_type.lower():
                                    social_network = 'Reddit'
                                elif 'youtube' in query.query_type.lower():
                                    social_network = 'YouTube'
                                elif 'threads' in query.query_type.lower():
                                    social_network = 'Threads'
                                elif 'snapchat' in query.query_type.lower():
                                    social_network = 'Snapchat'
                                
                                if 'sentiment' in result.data:
                                    sentiment_data = result.data.get('sentiment', {})
                                    if isinstance(sentiment_data, dict):
                                        sentiment_val = sentiment_data.get('score', 0)
                                        sentiment_label = sentiment_data.get('label', 'neutral')
                                    elif isinstance(sentiment_data, (int, float)):
                                        sentiment_val = sentiment_data
                                        sentiment_label = 'positive' if sentiment_val > 0.1 else 'negative' if sentiment_val < -0.1 else 'neutral'
                                    else:
                                        sentiment_val = 0
                                        sentiment_label = 'neutral'
                                    
                                    if date_key not in sentiment_by_date:
                                        sentiment_by_date[date_key] = []
                                    sentiment_by_date[date_key].append(float(sentiment_val))
                                    
                                    # Contar comentarios por red social y sentimiento
                                    if social_network:
                                        if social_network not in comments_by_social_network:
                                            comments_by_social_network[social_network] = {'positive': 0, 'negative': 0, 'neutral': 0}
                                        comments_by_social_network[social_network][sentiment_label] = comments_by_social_network[social_network].get(sentiment_label, 0) + 1
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error extrayendo sentiment: {e}")
                                pass
        
        # Generate time series data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        data: List[TrendDataPoint] = []
        
        # Use actual OSINT results count if available, otherwise use trend confidence
        use_results_count = len(results_count_by_date) > 0
        
        # Fill in missing dates
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            
            if use_results_count:
                # Use count of OSINT results as value
                value = float(results_count_by_date.get(date_key, 0))
                metric_type = "volum de dades"
                description = f"Nombre de resultats OSINT recopilats el {date_key}"
            else:
                # Fallback to trend confidence
                trend_by_date: Dict[str, float] = {}
                for trend in trends:
                    if trend.created_at:
                        trend_date_key = trend.created_at.strftime("%Y-%m-%d")
                        trend_by_date[trend_date_key] = trend_by_date.get(trend_date_key, 0) + (trend.confidence or 0)
                value = trend_by_date.get(date_key, 0)
                metric_type = "intensitat de tendència"
                description = f"Intensitat de la tendència identificada (0-100%)"
            
            # Calculate average sentiment if available
            avg_sentiment = None
            if date_key in sentiment_by_date and len(sentiment_by_date[date_key]) > 0:
                avg_sentiment = sum(sentiment_by_date[date_key]) / len(sentiment_by_date[date_key])
            
            source_str = ", ".join(sources) if sources else "dades OSINT"
            
            data.append(TrendDataPoint(
                date=date_key,
                value=value,
                source=source_str,
                metric_type=metric_type,
                description=description
            ))
            current_date += timedelta(days=1)
        
        # Generate prediction (simple linear extrapolation)
        prediction: List[TrendDataPoint] = []
        if len(data) >= 2:
            last_value = data[-1].value
            second_last_value = data[-2].value
            trend_slope = last_value - second_last_value
            
            for i in range(1, 8):  # Predict next 7 days
                future_date = end_date + timedelta(days=i)
                predicted_value = max(0, last_value + (trend_slope * i))
                prediction.append(TrendDataPoint(
                    date=future_date.strftime("%Y-%m-%d"),
                    value=predicted_value,
                    category="prediction",
                    source=source_str,
                    metric_type=metric_type,
                    description=f"Predicció per al {future_date.strftime('%Y-%m-%d')}"
                ))
        
        # Construir desglose de fuentes de datos
        data_sources_breakdown = []
        for tool_type, count in results_by_tool.items():
            tool_name = tool_names_map.get(tool_type, tool_type.capitalize())
            data_sources_breakdown.append({
                "tool": tool_name,
                "tool_type": tool_type,
                "total_results": count,
                "has_data": count > 0,
                "results_by_date": results_by_tool_and_date.get(tool_type, {})
            })
        
        # Ordenar por total de resultados (mayor a menor)
        data_sources_breakdown.sort(key=lambda x: x["total_results"], reverse=True)
        
        # Calcular totales por fuente con nombres legibles
        total_results_by_source = {}
        for tool_type, count in results_by_tool.items():
            tool_name = tool_names_map.get(tool_type, tool_type.capitalize())
            total_results_by_source[tool_name] = count
        
        # Obtener herramientas utilizadas con nombres legibles
        tools_used = [tool_names_map.get(q.query_type, q.query_type.capitalize()) for q in queries]
        tools_used = list(set(tools_used))  # Eliminar duplicados
        
        # Determinar calidad de datos
        total_results = sum(results_by_tool.values())
        data_quality = "good" if total_results > 0 else "empty"
        if total_results > 0 and len(queries) > 0:
            avg_results_per_query = total_results / len(queries)
            if avg_results_per_query < 1:
                data_quality = "low"
            elif avg_results_per_query < 5:
                data_quality = "medium"
        
        # Obtener fechas de recopilación
        first_collection = None
        last_collection = None
        if queries:
            query_dates = [q.created_at for q in queries if q.created_at]
            if query_dates:
                first_collection = min(query_dates).isoformat()
                last_collection = max(query_dates).isoformat()
        
        # Get predictions with type information
        predictions_result = await db.execute(
            select(AIPrediction).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
        )
        predictions = predictions_result.scalars().all()
        
        # Extract real metrics using AI if we have KPIs and OSINT data
        concrete_metrics = []
        ai_insights = []
        
        if kpis_to_track and osint_data_for_ai:
            try:
                from services.ai_service import AIService
                ai_service = AIService()
                
                case_type_str = case.case_type.value if hasattr(case.case_type, 'value') else str(case.case_type) if case.case_type else "general"
                
                ai_result = await ai_service.extract_case_specific_metrics(
                    case_id=case_id,
                    osint_data=osint_data_for_ai,
                    kpis=kpis_to_track,
                    case_type=case_type_str,
                    case_description=case.description or case.name,
                    db=db
                )
                
                if "metrics" in ai_result:
                    for metric_data in ai_result["metrics"]:
                        if isinstance(metric_data, dict):
                            concrete_metrics.append(MetricValue(
                                kpi_name=metric_data.get("kpi_name", ""),
                                value=float(metric_data.get("value", 0)),
                                previous_value=float(metric_data.get("previous_value")) if metric_data.get("previous_value") is not None else None,
                                change_percent=float(metric_data.get("change_percent")) if metric_data.get("change_percent") is not None else None,
                                trend=metric_data.get("trend", "stable"),
                                details=metric_data.get("details"),
                                measurement_unit=metric_data.get("details", {}).get("measurement_unit") if isinstance(metric_data.get("details"), dict) else None
                            ))
                
                if "insights" in ai_result:
                    ai_insights = ai_result["insights"]
            except Exception as e:
                logger.error(f"Error extracting metrics with AI: {e}", exc_info=True)
                # Continue without AI metrics
        
        # Build metadata mejorada con información concreta
        metadata = {
            "case_name": case.name,
            "case_type": case.case_type or "general",
            "data_sources": list(sources) if sources else ["dades OSINT"],
            "tools_used": tools_used,  # Lista específica de herramientas
            "metric_type": metric_types[0] if metric_types else "volum de dades",
            "metric_description": f"Aquest gràfic mostra el volum de dades recopilades per dia mitjançant les eines OSINT: {', '.join(tools_used) if tools_used else 'cap eina'}. Cada punt representa la quantitat de resultats obtinguts en una data específica.",
            "value_meaning": "Volum de dades" if use_results_count else "Intensitat de tendència (0-100%)",
            "interpretation": {
                "high_value": "Valors alts indiquen més activitat o més dades recopilades en aquesta data",
                "low_value": "Valors baixos indiquen menys activitat o menys dades disponibles",
                "trend_up": "Una tendència creixent indica un augment en l'activitat o interès sobre el tema",
                "trend_down": "Una tendència decreixent indica una disminució en l'activitat"
            },
            "total_data_points": sum(results_count_by_date.values()) if use_results_count else len(trends),
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "data_quality": data_quality,  # good, medium, low, empty
            "collection_timeline": {
                "first_collection": first_collection,
                "last_collection": last_collection
            },
            "results_by_tool": total_results_by_source,
            # Información concreta añadida
            "comments_by_social_network": comments_by_social_network,  # Comentarios positivos/negativos por red
            "concepts": concepts_extracted,  # Conceptos extraídos
            "predictions": [
                {
                    "type": pred.prediction_type,
                    "text": pred.prediction_text,
                    "confidence": float(pred.confidence_percentage) if pred.confidence_percentage else 0.0,
                    "explanation": pred.extra_data.get("explanation", "") if pred.extra_data else "",
                    "meaning": _get_prediction_meaning(pred.prediction_type)
                }
                for pred in predictions
            ]
        }
        
        return TrendAnalysisResponse(
            data=data, 
            prediction=prediction if prediction else None,
            metadata=metadata,
            data_sources_breakdown=data_sources_breakdown,
            queries_executed=queries_executed_list,
            case_linked_queries=len([q for q in queries if q.case_id == case_id]),
            total_results_by_source=total_results_by_source,
            metrics=concrete_metrics if concrete_metrics else None,
            insights=ai_insights if ai_insights else None,
            comments_by_social_network=comments_by_social_network if comments_by_social_network else None,
            concepts=concepts_extracted if concepts_extracted else None
        )
    except Exception as e:
        logger.error(f"Error en get_trend_analysis para caso {case_id}: {str(e)}", exc_info=True)
        # Return empty data instead of crashing
        return TrendAnalysisResponse(
            data=[],
            prediction=None,
            metadata={
                "case_name": "Error",
                "case_type": "error",
                "data_sources": [],
                "tools_used": [],
                "metric_type": "error",
                "metric_description": f"Error al generar dades: {str(e)}",
                "value_meaning": "Error",
                "interpretation": {},
                "total_data_points": 0,
                "date_range": {
                    "start": datetime.now().strftime("%Y-%m-%d"),
                    "end": datetime.now().strftime("%Y-%m-%d")
                },
                "data_quality": "error"
            },
            data_sources_breakdown=[],
            queries_executed=[],
            case_linked_queries=0,
            total_results_by_source={}
        )

@router.get("/trends/{case_id}/details")
async def get_trend_details(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed breakdown of OSINT data sources for a case"""
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get case
        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get all OSINT queries linked to this case
        queries_result = await db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        )
        queries = queries_result.scalars().all()
        
        tool_names_map = {
            "google_news": "Google News",
            "reddit": "Reddit",
            "github": "GitHub",
            "sherlock": "Sherlock",
            "recon-ng": "Recon-ng",
            "theharvester": "theHarvester",
            "shodan": "Shodan",
            "wayback": "Wayback Machine",
            "dns": "DNS Lookup",
            "whois": "WHOIS Lookup",
            "ip_geolocation": "IP Geolocation",
            # EnsembleData tools
            "ensembledata_tiktok_user_info": "TikTok (EnsembleData)",
            "ensembledata_tiktok_user_posts": "TikTok (EnsembleData)",
            "ensembledata_tiktok_hashtag_posts": "TikTok (EnsembleData)",
            "ensembledata_tiktok_keyword_posts": "TikTok (EnsembleData)",
            "ensembledata_instagram_user_info": "Instagram (EnsembleData)",
            "ensembledata_instagram_user_posts": "Instagram (EnsembleData)",
            "ensembledata_instagram_hashtag_posts": "Instagram (EnsembleData)",
            "ensembledata_youtube_channel_info": "YouTube (EnsembleData)",
            "ensembledata_youtube_channel_videos": "YouTube (EnsembleData)",
            "ensembledata_youtube_keyword_posts": "YouTube (EnsembleData)",
            "ensembledata_threads_user_info": "Threads (EnsembleData)",
            "ensembledata_threads_user_posts": "Threads (EnsembleData)",
            "ensembledata_threads_keyword_posts": "Threads (EnsembleData)",
            "ensembledata_reddit_subreddit_posts": "Reddit (EnsembleData)",
            "ensembledata_twitter_user_info": "Twitter/X (EnsembleData)",
            "ensembledata_twitter_user_tweets": "Twitter/X (EnsembleData)",
            "ensembledata_twitch_keyword_posts": "Twitch (EnsembleData)",
            "ensembledata_snapchat_user_info": "Snapchat (EnsembleData)",
        }
        
        queries_details = []
        statistics_by_tool: Dict[str, Dict[str, Any]] = {}
        
        for query in queries:
            tool_name = tool_names_map.get(query.query_type, query.query_type.capitalize())
            
            # Get results for this query
            results_result = await db.execute(
                select(OSINTResult).where(OSINTResult.query_id == query.id)
            )
            results = results_result.scalars().all()
            
            # Calculate statistics
            if query.query_type not in statistics_by_tool:
                statistics_by_tool[query.query_type] = {
                    "tool_name": tool_name,
                    "total_queries": 0,
                    "total_results": 0,
                    "successful_queries": 0,
                    "failed_queries": 0
                }
            
            statistics_by_tool[query.query_type]["total_queries"] += 1
            statistics_by_tool[query.query_type]["total_results"] += len(results)
            
            query_status = query.status.value if hasattr(query.status, 'value') else str(query.status)
            if query_status == "completed":
                statistics_by_tool[query.query_type]["successful_queries"] += 1
            elif query_status == "failed":
                statistics_by_tool[query.query_type]["failed_queries"] += 1
            
            # Get sample results (first 3)
            sample_results = []
            for result in results[:3]:
                sample_data: Dict[str, Any] = {}
                if result.data and isinstance(result.data, dict):
                    # Extract key information
                    for key in ['title', 'url', 'description', 'text', 'content']:
                        if key in result.data:
                            sample_data[key] = str(result.data[key])[:200]  # Limit length
                            break
                    if not sample_data:
                        sample_data = {"preview": str(result.data)[:200]}
                else:
                    sample_data = {"preview": "Result data available"}
                
                sample_results.append({
                    "id": result.id,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "status": result.status,
                    "sample": sample_data
                })
            
            queries_details.append({
                "id": query.id,
                "tool": tool_name,
                "tool_type": query.query_type,
                "params": query.query_params if query.query_params else {},
                "status": query_status,
                "created_at": query.created_at.isoformat() if query.created_at else None,
                "completed_at": query.completed_at.isoformat() if query.completed_at else None,
                "total_results": len(results),
                "case_linked": query.case_id == case_id,
                "sample_results": sample_results
            })
        
        # Sort queries by creation date (newest first)
        queries_details.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        # Build timeline
        timeline = []
        for query in queries:
            if query.created_at:
                tool_name = tool_names_map.get(query.query_type, query.query_type)
                query_detail = next((q for q in queries_details if q["id"] == query.id), None)
                timeline.append({
                    "date": query.created_at.isoformat(),
                    "event": f"Query executed: {tool_name}",
                    "query_id": query.id,
                    "results_count": query_detail["total_results"] if query_detail else 0
                })
        
        timeline.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "case_id": case_id,
            "case_name": case.name,
            "total_queries": len(queries),
            "total_results": sum([q["total_results"] for q in queries_details]),
            "queries": queries_details,
            "statistics_by_tool": list(statistics_by_tool.values()),
            "timeline": timeline[:50]  # Limit to 50 most recent events
        }
    except Exception as e:
        logger.error(f"Error en get_trend_details para caso {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo detalles: {str(e)}"
        )

@router.get("/expert/{case_id}")
async def get_expert_analysis(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get expert-level analysis for a case based on its type"""
    from sqlalchemy import select
    from services.ai_service import AIService
    from services.data_extraction_service import DataExtractionService
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get case
        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get OSINT data for this case
        queries_result = await db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        )
        queries = queries_result.scalars().all()
        
        # Get results for these queries
        osint_data = []
        for query in queries:
            results_result = await db.execute(
                select(OSINTResult).where(OSINTResult.query_id == query.id)
            )
            results = results_result.scalars().all()
            for result in results:
                osint_data.append({
                    "query_type": query.query_type,
                    "data": result.result_data or {}
                })
        
        # Determine case type
        case_type_str = case.case_type.value if hasattr(case.case_type, 'value') else str(case.case_type) if case.case_type else "general"
        
        # Get expert analysis based on case type
        ai_service = AIService()
        expert_analysis = None
        
        if case_type_str == "geopolitical":
            expert_analysis = await ai_service.analyze_as_geopolitical_expert(
                case_id, osint_data, db
            )
        elif case_type_str in ["business", "investment"]:
            expert_analysis = await ai_service.analyze_as_investment_advisor(
                case_id, osint_data, db
            )
        elif case_type_str in ["social", "political"]:
            expert_analysis = await ai_service.analyze_as_social_consultant(
                case_id, osint_data, db
            )
        else:
            expert_analysis = await ai_service.analyze_as_data_analyst(
                case_id, osint_data, db
            )
        
        return {
            "case_id": case_id,
            "case_type": case_type_str,
            "expert_analysis": expert_analysis,
            "osint_data_count": len(osint_data)
        }
        
    except Exception as e:
        logger.error(f"Error in get_expert_analysis for case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating expert analysis: {str(e)}"
        )

@router.get("/relationships/{case_id}", response_model=RelationshipMapResponse)
async def get_relationship_map(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate relationship map data for a case"""
    from sqlalchemy import select
    
    # Get case
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get concepts from AI analysis
    concepts_result = await db.execute(
        select(Concept).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
    )
    concepts = concepts_result.scalars().all()
    
    relationships: List[Relationship] = []
    entities: Dict[str, int] = {}
    
    # Extract relationships from concepts
    for concept in concepts:
        if concept.name and concept.related_concepts:
            # Parse related concepts (assuming JSON or comma-separated)
            related = []
            if isinstance(concept.related_concepts, str):
                try:
                    import json
                    related = json.loads(concept.related_concepts)
                except:
                    related = [c.strip() for c in concept.related_concepts.split(",")]
            elif isinstance(concept.related_concepts, list):
                related = concept.related_concepts
            
            for related_concept in related[:5]:  # Limit relationships
                relationships.append(Relationship(
                    from_entity=concept.name,
                    to_entity=str(related_concept),
                    type=concept.category or "related",
                    strength=min(10, int((concept.relevance or 0.5) * 10))
                ))
                entities[concept.name] = entities.get(concept.name, 0) + 1
                entities[str(related_concept)] = entities.get(str(related_concept), 0) + 1
    
    # Add relationships from OSINT data
    queries_result = await db.execute(
        select(OSINTQuery).where(OSINTQuery.case_id == case_id)
    )
    queries = queries_result.scalars().all()
    
    for query in queries:
        results_result = await db.execute(
            select(OSINTResult).where(OSINTResult.query_id == query.id)
        )
        results = results_result.scalars().all()
        
        for result in results:
            if result.data and isinstance(result.data, dict):
                # Create relationships between entities found
                emails = result.data.get('emails', [])
                domains = result.data.get('hosts', []) or result.data.get('domains', [])
                
                for email in emails[:3]:
                    for domain in domains[:3]:
                        relationships.append(Relationship(
                            from_entity=str(email),
                            to_entity=str(domain),
                            type="email_domain",
                            strength=7
                        ))
    
    return RelationshipMapResponse(relationships=relationships)
