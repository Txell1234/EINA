"""
Research Planner Service - Expert-level research planning for different case types
Acts as: Geopolitical Analyst, Investment Advisor, Social Public Affairs Consultant, Data Analytics Expert
"""
from typing import Dict, Any, List, Optional
from services.ai_service import AIService
from services.osint_data_utils import extract_search_keywords, normalize_search_query
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def _news_api_configured() -> bool:
    key = getattr(settings, "NEWS_API_KEY", "").strip()
    return bool(key and key != "your-news-api-key")


def _tavily_configured() -> bool:
    key = getattr(settings, "TAVILY_API_KEY", "").strip()
    return bool(key and not key.startswith("your-"))


class ResearchPlannerService:
    """Service to generate comprehensive, expert-level research plans"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    async def generate_research_plan(
        self,
        case_id: int,
        case_type: str,
        case_description: str,
        case_name: str,
        existing_queries: List[Dict] = None,
        osint_only: bool = False,
    ) -> Dict[str, Any]:
        """Generate comprehensive research plan based on case type"""
        if osint_only:
            plan = self.generate_osint_only_plan(
                case_id=case_id,
                case_type=case_type,
                case_description=case_description,
                case_name=case_name,
            )
            return self._sanitize_plan(plan, case_name, case_description)

        if not self.ai_service.client:
            return self._sanitize_plan(
                self._get_fallback_plan(case_type, case_description, guided=True),
                case_name,
                case_description,
            )
        
        # Get expert prompt based on case type
        expert_prompt = self._get_expert_prompt(case_type, case_description, case_name)
        
        try:
            response = await self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": expert_prompt["system"]},
                    {"role": "user", "content": expert_prompt["user"]}
                ],
                temperature=0.7,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            import json
            plan = json.loads(content)
            
            # Add metadata
            plan["case_id"] = case_id
            plan["case_type"] = case_type
            plan["estimated_duration"] = self._estimate_duration(plan.get("research_phases", []))
            plan["data_sources"] = self._extract_data_sources(plan.get("research_phases", []))
            plan["research_depth"] = "comprehensive"
            plan.setdefault("run_extraction", True)
            plan.setdefault("suggested_variables", [])
            plan.setdefault("suggested_actors", [])
            plan["creation_mode"] = "guided"
            
            # Filter out duplicates if existing_queries provided
            if existing_queries:
                plan = self._filter_duplicates(plan, existing_queries)

            return self._sanitize_plan(plan, case_name, case_description)
            
        except Exception as e:
            logger.error(f"Error generating research plan: {e}", exc_info=True)
            return self._sanitize_plan(
                self._get_fallback_plan(case_type, case_description, guided=True),
                case_name,
                case_description,
            )

    def generate_osint_only_plan(
        self,
        case_id: int,
        case_type: str,
        case_description: str,
        case_name: str,
    ) -> Dict[str, Any]:
        """Pla mínim només OSINT per casos manuals (sense variables IA prèvies)."""
        keywords = case_name
        if case_description and case_description != case_name:
            keywords = f"{case_name} {case_description[:200]}"

        plan = {
            "case_id": case_id,
            "case_type": case_type,
            "creation_mode": "manual",
            "run_extraction": False,
            "research_strategy": "Recollida OSINT bàsica a partir del cas definit manualment",
            "key_entities": [],
            "suggested_variables": [],
            "suggested_actors": [],
            "temporal_scope": {
                "historical": "30 dies",
                "current": "actualitat",
                "monitoring": "opcional",
            },
            "research_phases": [
                {
                    "phase": "initial",
                    "phase_name": "Recollida OSINT inicial",
                    "queries": [
                        {
                            "type": "google_news",
                            "params": {
                                "query": keywords[:200],
                                "language": "en",
                                "max_results": 30,
                            },
                            "rationale": "Notícies recents relacionades amb el cas",
                        },
                        {
                            "type": "google_news",
                            "params": {
                                "query": keywords[:200],
                                "language": "es",
                                "max_results": 20,
                            },
                            "rationale": "Cobertura en castellà/català",
                        },
                    ],
                }
            ],
            "estimated_duration": "2-5 minuts",
            "data_sources": ["news"],
            "research_depth": "basic",
        }
        if _tavily_configured():
            keywords = extract_search_keywords(keywords, case_name)
            plan["research_phases"][0]["queries"].append(
                {
                    "type": "tavily",
                    "params": {
                        "query": keywords,
                        "max_results": 10,
                        "search_depth": "advanced",
                        "topic": "news",
                    },
                    "rationale": "Descoberta web en temps real (Tavily)",
                }
            )
            plan["data_sources"] = list(dict.fromkeys([*plan["data_sources"], "tavily"]))
        return plan

    def _sanitize_query_params(
        self, query_type: str, params: dict[str, Any], case_name: str
    ) -> dict[str, Any]:
        params = dict(params or {})
        q = str(params.get("query") or params.get("q") or "").strip()

        if query_type in ("google_news", "gdelt", "reddit", "github", "tavily"):
            if len(q) > 80 or not q:
                q = extract_search_keywords(q or case_name, case_name)
            else:
                q = normalize_search_query(q, max_len=100)
            params["query"] = q

        if query_type == "tavily":
            params["max_results"] = max(1, min(int(params.get("max_results", 10)), 15))
            params.setdefault("search_depth", "advanced")
            params.setdefault("topic", "news")

        if query_type == "tavily_research":
            if not str(params.get("input") or "").strip():
                params["input"] = extract_search_keywords(
                    str(params.get("query") or case_name), case_name
                )
            params.setdefault("model", "auto")
            params.setdefault("wait", True)
            params.setdefault("max_wait_seconds", 300)

        if query_type == "tavily_crawl":
            params["limit"] = max(1, min(int(params.get("limit", 30)), 100))
            params.setdefault("max_depth", 1)

        if query_type == "tavily_map":
            params["limit"] = max(1, min(int(params.get("limit", 50)), 200))
            params.setdefault("max_depth", 1)

        if query_type == "tavily_extract":
            urls = params.get("urls")
            if isinstance(urls, str):
                params["urls"] = [u.strip() for u in urls.split(",") if u.strip()]

        if query_type == "gdelt":
            params["days"] = max(1, min(int(params.get("days", 30)), 90))
            params["max_results"] = max(1, min(int(params.get("max_results", 50)), 75))

        if query_type == "google_news":
            params.setdefault("language", "en")
            if not _news_api_configured():
                params["_note"] = "Usarà Google News RSS (NEWS_API_KEY no configurada)"

        if query_type == "rss_feed":
            params.setdefault("source", "cfr")
            params["max_items"] = max(1, min(int(params.get("max_items", 20)), 30))

        if query_type == "rss_all":
            params["max_items"] = max(1, min(int(params.get("max_items", 10)), 15))

        if query_type == "rss_url":
            params["max_items"] = max(1, min(int(params.get("max_items", 20)), 40))
            params.setdefault("label", "curated")

        return params

    def _curated_rss_queries(self, case_name: str, case_description: str) -> list[dict[str, Any]]:
        from integrations.rss_feeds import match_curated_feeds

        queries = []
        for feed in match_curated_feeds(case_name, case_description, max_feeds=3):
            queries.append(
                {
                    "type": "rss_url",
                    "params": {
                        "url": feed["url"],
                        "label": feed.get("label", "curated"),
                        "category": feed.get("category", "curated"),
                        "max_items": 15,
                    },
                    "rationale": f"Font curada: {feed.get('label', feed['url'])} (RSS/Substack)",
                }
            )
        return queries

    def _sanitize_plan(
        self, plan: dict[str, Any], case_name: str, case_description: str = ""
    ) -> dict[str, Any]:
        """Post-process AI plan: short queries, valid GDELT params, diversify sources."""
        phases = plan.get("research_phases") or []
        has_gdelt = False
        has_rss = False
        has_tavily = False
        has_tavily_research = False

        for phase in phases:
            sanitized_queries = []
            for query in phase.get("queries") or []:
                qtype = query.get("type", "")
                params = self._sanitize_query_params(qtype, query.get("params") or {}, case_name)
                sanitized_queries.append({**query, "params": params})
                if qtype == "gdelt":
                    has_gdelt = True
                if qtype in ("rss_feed", "rss_all", "rss_url"):
                    has_rss = True
                if qtype == "tavily":
                    has_tavily = True
                if qtype == "tavily_research":
                    has_tavily_research = True
            phase["queries"] = sanitized_queries

        if phases and not has_gdelt:
            initial = phases[0]
            keywords = extract_search_keywords(
                str(plan.get("research_strategy") or case_name), case_name
            )
            initial.setdefault("queries", []).append(
                {
                    "type": "gdelt",
                    "params": {"query": keywords, "days": 30, "max_results": 40},
                    "rationale": "Monitorització d'esdeveniments globals (GDELT, gratuït)",
                }
            )

        if phases and _tavily_configured() and not has_tavily_research:
            keywords = extract_search_keywords(
                str(plan.get("research_strategy") or case_description or case_name), case_name
            )
            deep_phase = {
                "phase": "deep_dive",
                "phase_name": "Recerca profunda Tavily",
                "queries": [
                    {
                        "type": "tavily_research",
                        "params": {
                            "input": f"{case_name}: {keywords}"[:500],
                            "model": "auto",
                            "wait": True,
                            "max_wait_seconds": 300,
                        },
                        "rationale": "Informe multi-font amb cites (Tavily Research)",
                    }
                ],
            }
            phases.append(deep_phase)

        if phases and _tavily_configured() and not has_tavily:
            keywords = extract_search_keywords(
                str(plan.get("research_strategy") or case_name), case_name
            )
            phases[0].setdefault("queries", []).append(
                {
                    "type": "tavily",
                    "params": {
                        "query": keywords,
                        "max_results": 10,
                        "search_depth": "advanced",
                        "topic": "news",
                    },
                    "rationale": "Descoberta web en temps real (Tavily)",
                }
            )

        if phases and not has_rss:
            phases[0].setdefault("queries", []).append(
                {
                    "type": "rss_all",
                    "params": {"max_items": 7},
                    "rationale": "Think-tanks i analistes (RSS, sense clau API)",
                }
            )

        curated = self._curated_rss_queries(case_name, case_description)
        if curated and phases:
            existing_urls = {
                str(q.get("params", {}).get("url", ""))
                for phase in phases
                for q in phase.get("queries", [])
                if q.get("type") == "rss_url"
            }
            for cq in curated:
                url = cq["params"]["url"]
                if url not in existing_urls:
                    phases[0].setdefault("queries", []).append(cq)
                    existing_urls.add(url)

        plan["research_phases"] = phases
        plan["curated_feeds"] = [q["params"]["url"] for q in curated]
        plan["news_api_configured"] = _news_api_configured()
        plan["tavily_configured"] = _tavily_configured()
        return plan
    
    def _get_expert_prompt(self, case_type: str, case_description: str, case_name: str) -> Dict[str, str]:
        """Get expert-level prompt based on case type"""
        
        base_context = f"""
Case Name: {case_name}
Case Description: {case_description}
Case Type: {case_type}
"""
        
        expert_prompts = {
            "geopolitical": {
                "system": """You are a senior Geopolitical Intelligence Analyst with 20+ years of experience.
Your expertise includes:
- Bilateral and multilateral relations analysis
- Treaty and agreement tracking
- Diplomatic event monitoring
- Policy change impact assessment
- Trade flow and economic relations
- Regional sentiment analysis

Generate a comprehensive, multi-phase research plan for deep geopolitical intelligence gathering.
Focus on:
1. Official channels (government websites, diplomatic statements, treaties)
2. News analysis (major outlets, regional sources, policy journals)
3. Social media sentiment (official accounts, expert commentary, public opinion)
4. Historical context (past agreements, relations evolution)
5. Economic indicators (trade data, investment flows)

Return ONLY valid JSON with this structure:
{
  "research_phases": [
    {
      "phase": "initial|deep_dive|monitoring",
      "phase_name": "Descriptive name",
      "queries": [
        {
          "type": "query_type (google_news, ensembledata_twitter_keyword_posts, etc.)",
          "params": {
            "query": "search query",
            "language": "en|es|etc",
            "count": 50,
            "max_results": 100
          },
          "rationale": "Why this query is important"
        }
      ]
    }
  ],
  "research_strategy": "Brief description of overall strategy",
  "key_entities": ["List of key countries, organizations, people to track"],
  "temporal_scope": {
    "historical": "How far back to search",
    "current": "Current period focus",
    "monitoring": "Ongoing monitoring strategy"
  },
  "suggested_variables": [
    {
      "code": "V1",
      "name": "Variable name for MIC-MAC",
      "description": "Why this variable matters",
      "var_type": "independent|dependent|regulator"
    }
  ],
  "suggested_actors": [
    {
      "code": "A1",
      "name": "Actor or stakeholder",
      "strategic_goals": ["goal1", "goal2"]
    }
  ],
  "run_extraction": true
}""",
                "user": f"""{base_context}

Generate a comprehensive research plan for this geopolitical case.
Include queries for:
- Bilateral/multilateral agreements and treaties
- Diplomatic events and statements
- Trade relations and economic data
- Policy changes and their impacts
- Regional sentiment and public opinion
- Historical context and evolution

Be specific with search queries - use exact country names, treaty names, key dates, etc."""
            },
            
            "business": {
                "system": """You are a senior Investment Advisor and Business Intelligence Analyst.
Your expertise includes:
- Market trend analysis
- Company performance evaluation
- Risk assessment (geopolitical, market, operational)
- Opportunity identification
- Competitive landscape analysis
- Financial data interpretation

Generate a comprehensive research plan for investment and business intelligence.
Focus on:
1. Market data (stock prices, commodity trends, market indices)
2. Company information (financials, partnerships, strategic initiatives)
3. News and analysis (financial news, industry reports, expert opinions)
4. Social sentiment (investor sentiment, customer feedback)
5. Risk factors (geopolitical, market volatility, operational risks)

Return ONLY valid JSON with the same structure as geopolitical case.""",
                "user": f"""{base_context}

Generate a comprehensive research plan for this investment/business case.
Include queries for:
- Market trends and stock/commodity data
- Company performance and financials
- Partnership and M&A activity
- Risk factors (geopolitical, market, operational)
- Investment opportunities
- Competitive landscape
- Customer and investor sentiment"""
            },
            
            "social": {
                "system": """You are a senior Social Public Affairs Consultant and Reputation Management Expert.
Your expertise includes:
- Public sentiment analysis
- Viral content tracking
- Influencer network analysis
- Community engagement metrics
- Reputation risk assessment
- Crisis communication

Generate a comprehensive research plan for social and public affairs analysis.
Focus on:
1. Social media platforms (Instagram, TikTok, Twitter/X, Facebook, YouTube, Reddit, Threads)
2. Sentiment analysis across platforms
3. Viral content identification
4. Influencer and key opinion leader tracking
5. Community reactions and engagement
6. News coverage and media sentiment

Return ONLY valid JSON with the same structure as geopolitical case.""",
                "user": f"""{base_context}

Generate a comprehensive research plan for this social/public affairs case.
Include queries for:
- Sentiment analysis across all major social platforms
- Viral content and trending topics
- Influencer mentions and key opinion leaders
- Community reactions and engagement metrics
- News coverage and media sentiment
- Hashtag and keyword tracking
- User-generated content analysis"""
            },
            
            "political": {
                "system": """You are a senior Political Intelligence Analyst.
Your expertise includes:
- Policy analysis
- Election monitoring
- Political sentiment tracking
- Government action analysis
- Political risk assessment

Generate a comprehensive research plan for political intelligence.
Focus on:
1. Official government sources
2. Political news and analysis
3. Social media political sentiment
4. Policy documents and legislation
5. Electoral data and polling

Return ONLY valid JSON with the same structure as geopolitical case.""",
                "user": f"""{base_context}

Generate a comprehensive research plan for this political case.
Include queries for:
- Policy changes and legislation
- Political statements and positions
- Election-related data
- Political sentiment analysis
- Government actions and decisions
- Media coverage and analysis"""
            },
            
            "general": {
                "system": """You are a senior Data Analytics Expert and OSINT Specialist.
Your expertise includes:
- Comprehensive data collection strategies
- Multi-source intelligence gathering
- Cross-platform analysis
- Temporal data analysis

Generate a comprehensive research plan for general intelligence gathering.
Focus on:
1. News sources (multiple languages and regions)
2. Social media platforms (all major platforms)
3. Official channels and public records
4. Specialized databases and repositories

Return ONLY valid JSON with the same structure as geopolitical case.""",
                "user": f"""{base_context}

Generate a comprehensive research plan for this general case.
Include queries across multiple sources and platforms to gather comprehensive intelligence."""
            }
        }
        
        return expert_prompts.get(case_type.lower(), expert_prompts["general"])
    
    def _estimate_duration(self, phases: List[Dict]) -> str:
        """Estimate research duration based on phases and queries"""
        total_queries = sum(len(phase.get("queries", [])) for phase in phases)
        
        # Estimate: ~30 seconds per query on average (some faster, some slower)
        estimated_seconds = total_queries * 30
        minutes = estimated_seconds // 60
        
        if minutes < 5:
            return "2-5 minutes"
        elif minutes < 15:
            return f"{minutes-2}-{minutes+2} minutes"
        elif minutes < 30:
            return f"{minutes-5}-{minutes+5} minutes"
        else:
            return f"{minutes-10}-{minutes+10} minutes"
    
    def _extract_data_sources(self, phases: List[Dict]) -> List[str]:
        """Extract unique data sources from research phases"""
        sources = set()
        
        source_mapping = {
            "google_news": "news",
            "reddit": "social_media",
            "github": "repositories",
            "ensembledata_tiktok": "social_media",
            "ensembledata_instagram": "social_media",
            "ensembledata_twitter": "social_media",
            "ensembledata_youtube": "social_media",
            "ensembledata_threads": "social_media",
            "ensembledata_reddit": "social_media",
            "sherlock": "social_media",
            "recon-ng": "technical",
            "theharvester": "technical",
            "shodan": "technical"
        }
        
        for phase in phases:
            for query in phase.get("queries", []):
                query_type = query.get("type", "")
                for key, source in source_mapping.items():
                    if key in query_type.lower():
                        sources.add(source)
                        break
        
        return list(sources) if sources else ["osint"]
    
    def _filter_duplicates(self, plan: Dict, existing_queries: List[Dict]) -> Dict:
        """Filter out queries that are similar to existing ones"""
        existing_signatures = set()
        for eq in existing_queries:
            sig = f"{eq.get('type', '')}_{str(eq.get('params', {}))}"
            existing_signatures.add(sig)
        
        filtered_phases = []
        for phase in plan.get("research_phases", []):
            filtered_queries = []
            for query in phase.get("queries", []):
                sig = f"{query.get('type', '')}_{str(query.get('params', {}))}"
                if sig not in existing_signatures:
                    filtered_queries.append(query)
                else:
                    logger.info(f"Filtered duplicate query: {query.get('type')}")
            
            if filtered_queries:
                filtered_phase = phase.copy()
                filtered_phase["queries"] = filtered_queries
                filtered_phases.append(filtered_phase)
        
        plan["research_phases"] = filtered_phases
        return plan
    
    def _get_fallback_plan(
        self, case_type: str, case_description: str, guided: bool = True
    ) -> Dict[str, Any]:
        """Fallback plan when AI is not available"""
        return {
            "research_phases": [
                {
                    "phase": "initial",
                    "phase_name": "Initial Research",
                    "queries": [
                        {
                            "type": "google_news",
                            "params": {"query": case_description[:100], "language": "en", "max_results": 20},
                            "rationale": "Basic news search"
                        }
                    ]
                }
            ],
            "research_strategy": "Basic research plan (AI unavailable)",
            "key_entities": [],
            "suggested_variables": [],
            "suggested_actors": [],
            "run_extraction": guided,
            "creation_mode": "guided" if guided else "manual",
            "temporal_scope": {
                "historical": "30 days",
                "current": "current",
                "monitoring": "none"
            },
            "estimated_duration": "2-5 minutes",
            "data_sources": ["news"],
            "research_depth": "basic"
        }



