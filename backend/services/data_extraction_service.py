"""
Data Extraction Service - Parse structured data from OSINT APIs
Extracts concrete metrics from EnsembleData, news APIs, and other sources
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataExtractionService:
    """Service to extract structured metrics from OSINT data"""
    
    def extract_social_media_metrics(self, data: Dict[str, Any], query_type: str = None) -> Dict[str, Any]:
        """Extract social media metrics from EnsembleData responses
        
        Returns metrics like:
        - Total posts/comments
        - Likes, shares, views
        - Engagement rates
        - Posts by date
        """
        metrics = {
            "total_posts": 0,
            "total_comments": 0,
            "total_likes": 0,
            "total_shares": 0,
            "total_views": 0,
            "posts_by_date": {},
            "engagement_by_date": {},
            "platform": None
        }
        
        if not isinstance(data, dict):
            return metrics
        
        # Determine platform from query_type or data structure
        if query_type:
            if 'tiktok' in query_type.lower():
                metrics["platform"] = "TikTok"
            elif 'instagram' in query_type.lower():
                metrics["platform"] = "Instagram"
            elif 'twitter' in query_type.lower() or 'x' in query_type.lower():
                metrics["platform"] = "Twitter/X"
            elif 'reddit' in query_type.lower():
                metrics["platform"] = "Reddit"
            elif 'youtube' in query_type.lower():
                metrics["platform"] = "YouTube"
            elif 'threads' in query_type.lower():
                metrics["platform"] = "Threads"
            elif 'snapchat' in query_type.lower():
                metrics["platform"] = "Snapchat"
        
        # Extract from EnsembleData structure
        if data.get("status") == "success" and "data" in data:
            posts = data.get("data", [])
            if isinstance(posts, list):
                metrics["total_posts"] = len(posts)
                
                for post in posts:
                    if isinstance(post, dict):
                        # Extract engagement metrics
                        metrics["total_likes"] += post.get("like_count", 0) or 0
                        metrics["total_comments"] += post.get("comment_count", 0) or 0
                        metrics["total_shares"] += post.get("share_count", 0) or 0
                        metrics["total_views"] += post.get("view_count", 0) or 0
                        
                        # Extract date for time series
                        date_key = None
                        if "created_time" in post:
                            try:
                                # Parse various date formats
                                date_str = post["created_time"]
                                if isinstance(date_str, str):
                                    # Try to parse ISO format or timestamp
                                    if "T" in date_str:
                                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                    elif date_str.isdigit():
                                        dt = datetime.fromtimestamp(int(date_str))
                                    else:
                                        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                                    date_key = dt.strftime("%Y-%m-%d")
                            except Exception as e:
                                logger.debug(f"Error parsing date: {e}")
                        
                        if date_key:
                            metrics["posts_by_date"][date_key] = metrics["posts_by_date"].get(date_key, 0) + 1
                            # Calculate engagement for this date
                            engagement = (
                                (post.get("like_count", 0) or 0) +
                                (post.get("comment_count", 0) or 0) +
                                (post.get("share_count", 0) or 0)
                            )
                            metrics["engagement_by_date"][date_key] = (
                                metrics["engagement_by_date"].get(date_key, 0) + engagement
                            )
        
        return metrics
    
    def extract_sentiment_metrics(self, data: Dict[str, Any], use_classifications: bool = True, db: Any = None, osint_result_id: int = None) -> Dict[str, Any]:
        """Extract sentiment metrics from OSINT data
        
        Args:
            data: OSINT data dictionary
            use_classifications: If True, use AI classifications instead of raw data
            db: Database session (required if use_classifications=True)
            osint_result_id: OSINT result ID to lookup classifications
        
        Returns:
        - Sentiment scores (positive, negative, neutral counts)
        - Average sentiment score
        - Sentiment by date
        """
        metrics = {
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "total_sentiment_score": 0.0,
            "sentiment_count": 0,
            "sentiment_by_date": {},
            "average_sentiment": 0.0
        }
        
        # IMPORTANT: If use_classifications=True, use AI classifications instead of raw data
        if use_classifications and db and osint_result_id:
            try:
                from models.ai_classification import AIClassification
                from sqlalchemy import select
                
                result = db.execute(
                    select(AIClassification).where(
                        AIClassification.osint_result_id == osint_result_id
                    )
                )
                classification = result.scalar_one_or_none()
                
                if classification:
                    # Use AI classification
                    sentiment = classification.sentiment
                    sentiment_score = classification.sentiment_score or 0.0
                    
                    if sentiment == "positive":
                        metrics["positive_count"] = 1
                    elif sentiment == "negative":
                        metrics["negative_count"] = 1
                    else:
                        metrics["neutral_count"] = 1
                    
                    metrics["total_sentiment_score"] = sentiment_score
                    metrics["sentiment_count"] = 1
                    metrics["average_sentiment"] = sentiment_score
                    
                    return metrics
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error using AI classifications for sentiment: {e}, falling back to raw data")
        
        if not isinstance(data, dict):
            return metrics
        
        # Check for explicit sentiment field
        if "sentiment" in data:
            sentiment_data = data["sentiment"]
            if isinstance(sentiment_data, dict):
                score = sentiment_data.get("score", 0)
                label = sentiment_data.get("label", "neutral")
                
                if label == "positive" or (isinstance(score, (int, float)) and score > 0.1):
                    metrics["positive_count"] += 1
                elif label == "negative" or (isinstance(score, (int, float)) and score < -0.1):
                    metrics["negative_count"] += 1
                else:
                    metrics["neutral_count"] += 1
                
                if isinstance(score, (int, float)):
                    metrics["total_sentiment_score"] += float(score)
                    metrics["sentiment_count"] += 1
        
        # Extract from posts/comments in EnsembleData structure
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if isinstance(item, dict):
                    # Check for sentiment in post
                    if "sentiment" in item:
                        sentiment_data = item["sentiment"]
                        if isinstance(sentiment_data, dict):
                            score = sentiment_data.get("score", 0)
                            label = sentiment_data.get("label", "neutral")
                        elif isinstance(sentiment_data, (int, float)):
                            score = sentiment_data
                            label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
                        else:
                            continue
                        
                        if label == "positive":
                            metrics["positive_count"] += 1
                        elif label == "negative":
                            metrics["negative_count"] += 1
                        else:
                            metrics["neutral_count"] += 1
                        
                        if isinstance(score, (int, float)):
                            metrics["total_sentiment_score"] += float(score)
                            metrics["sentiment_count"] += 1
                            
                            # Extract date for sentiment by date
                            date_key = None
                            if "created_time" in item:
                                try:
                                    date_str = item["created_time"]
                                    if isinstance(date_str, str):
                                        if "T" in date_str:
                                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                        elif date_str.isdigit():
                                            dt = datetime.fromtimestamp(int(date_str))
                                        else:
                                            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                                        date_key = dt.strftime("%Y-%m-%d")
                                except Exception:
                                    pass
                            
                            if date_key:
                                if date_key not in metrics["sentiment_by_date"]:
                                    metrics["sentiment_by_date"][date_key] = {"scores": [], "count": 0}
                                metrics["sentiment_by_date"][date_key]["scores"].append(float(score))
                                metrics["sentiment_by_date"][date_key]["count"] += 1
        
        # Calculate average
        if metrics["sentiment_count"] > 0:
            metrics["average_sentiment"] = metrics["total_sentiment_score"] / metrics["sentiment_count"]
        
        return metrics
    
    def extract_news_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract news article metrics
        
        Returns:
        - Article count
        - Articles by date
        - Sources
        - Keywords/mentions
        """
        metrics = {
            "total_articles": 0,
            "articles_by_date": {},
            "sources": set(),
            "keywords": {},
            "mentions": 0
        }
        
        if not isinstance(data, dict):
            return metrics
        
        # Google News structure
        if "articles" in data:
            articles = data["articles"]
            if isinstance(articles, list):
                metrics["total_articles"] = len(articles)
                for article in articles:
                    if isinstance(article, dict):
                        # Extract date
                        if "publishedAt" in article:
                            try:
                                date_str = article["publishedAt"]
                                if isinstance(date_str, str):
                                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                    date_key = dt.strftime("%Y-%m-%d")
                                    metrics["articles_by_date"][date_key] = metrics["articles_by_date"].get(date_key, 0) + 1
                            except Exception:
                                pass
                        
                        # Extract source
                        if "source" in article:
                            source = article["source"]
                            if isinstance(source, dict) and "name" in source:
                                metrics["sources"].add(source["name"])
        
        # Convert set to list for JSON serialization
        metrics["sources"] = list(metrics["sources"])
        
        return metrics
    
    def extract_commercial_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract commercial/business metrics
        
        Returns:
        - Agreement mentions
        - Trade volume mentions
        - Partnership mentions
        - Bilateral accord counts
        """
        metrics = {
            "agreement_mentions": 0,
            "trade_mentions": 0,
            "partnership_mentions": 0,
            "bilateral_accord_mentions": 0,
            "investment_mentions": 0,
            "mentions_by_date": {},
            "keywords_found": []
        }
        
        if not isinstance(data, dict):
            return metrics
        
        # Keywords to search for
        commercial_keywords = {
            "agreement": ["agreement", "acuerdo", "pact", "pacto", "deal", "trato"],
            "trade": ["trade", "comercio", "commercial", "comercial", "exchange", "intercambio"],
            "partnership": ["partnership", "asociación", "collaboration", "colaboración", "alliance", "alianza"],
            "bilateral": ["bilateral", "bilaterales", "accord", "acuerdo bilateral", "treaty", "tratado"],
            "investment": ["investment", "inversión", "invest", "invertir", "funding", "financiación"]
        }
        
        # Search in text fields
        text_to_search = ""
        if "data" in data:
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        text_to_search += " " + str(item.get("text", ""))
                        text_to_search += " " + str(item.get("description", ""))
                        text_to_search += " " + str(item.get("title", ""))
            elif isinstance(data["data"], dict):
                text_to_search += " " + str(data["data"].get("text", ""))
                text_to_search += " " + str(data["data"].get("description", ""))
        
        text_to_search = text_to_search.lower()
        
        # Count keyword matches
        for category, keywords in commercial_keywords.items():
            for keyword in keywords:
                count = text_to_search.count(keyword)
                if count > 0:
                    if category == "agreement":
                        metrics["agreement_mentions"] += count
                    elif category == "trade":
                        metrics["trade_mentions"] += count
                    elif category == "partnership":
                        metrics["partnership_mentions"] += count
                    elif category == "bilateral":
                        metrics["bilateral_accord_mentions"] += count
                    elif category == "investment":
                        metrics["investment_mentions"] += count
                    
                    if keyword not in metrics["keywords_found"]:
                        metrics["keywords_found"].append(keyword)
        
        return metrics
    
    def extract_all_metrics(self, data: Dict[str, Any], query_type: str = None) -> Dict[str, Any]:
        """Extract all available metrics from OSINT data"""
        all_metrics = {
            "social_media": self.extract_social_media_metrics(data, query_type),
            "sentiment": self.extract_sentiment_metrics(data),
            "news": self.extract_news_metrics(data),
            "commercial": self.extract_commercial_metrics(data)
        }
        
        return all_metrics
    
    def extract_geopolitical_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract geopolitical-specific metrics
        
        Returns:
        - Treaty/agreement mentions
        - Diplomatic event counts
        - Policy change mentions
        - Bilateral relation indicators
        - Trade volume mentions
        """
        metrics = {
            "treaty_mentions": 0,
            "diplomatic_events": 0,
            "policy_changes": 0,
            "bilateral_mentions": 0,
            "trade_volume_mentions": 0,
            "countries_mentioned": set(),
            "treaties_by_date": {},
            "events_by_date": {}
        }
        
        if not isinstance(data, dict):
            return metrics
        
        # Keywords for geopolitical analysis
        geopolitical_keywords = {
            "treaty": ["treaty", "tratado", "accord", "acuerdo", "pact", "pacto", "convention", "convención"],
            "diplomatic": ["diplomatic", "diplomático", "embassy", "embajada", "summit", "cumbre", "meeting", "reunión"],
            "policy": ["policy", "política", "legislation", "legislación", "regulation", "regulación", "law", "ley"],
            "bilateral": ["bilateral", "bilaterales", "between", "entre", "relations", "relaciones"],
            "trade": ["trade", "comercio", "export", "exportación", "import", "importación", "volume", "volumen"]
        }
        
        # Search in text fields
        text_to_search = ""
        if "data" in data:
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        text_to_search += " " + str(item.get("text", ""))
                        text_to_search += " " + str(item.get("description", ""))
                        text_to_search += " " + str(item.get("title", ""))
                        text_to_search += " " + str(item.get("content", ""))
            elif isinstance(data["data"], dict):
                text_to_search += " " + str(data["data"].get("text", ""))
                text_to_search += " " + str(data["data"].get("description", ""))
        
        text_lower = text_to_search.lower()
        
        # Count keyword matches
        for category, keywords in geopolitical_keywords.items():
            for keyword in keywords:
                count = text_lower.count(keyword)
                if count > 0:
                    if category == "treaty":
                        metrics["treaty_mentions"] += count
                    elif category == "diplomatic":
                        metrics["diplomatic_events"] += count
                    elif category == "policy":
                        metrics["policy_changes"] += count
                    elif category == "bilateral":
                        metrics["bilateral_mentions"] += count
                    elif category == "trade":
                        metrics["trade_volume_mentions"] += count
        
        # Extract country names (basic - can be enhanced with NLP)
        import re
        country_patterns = [
            r'\b(India|UAE|United Arab Emirates|Spain|France|Germany|China|USA|United States)\b',
            r'\b(India|UAE|España|Francia|Alemania|China|EEUU|Estados Unidos)\b'
        ]
        for pattern in country_patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            metrics["countries_mentioned"].update(matches)
        
        metrics["countries_mentioned"] = list(metrics["countries_mentioned"])
        
        return metrics
    
    def extract_investment_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract investment-specific metrics
        
        Returns:
        - Market data mentions
        - Company performance indicators
        - Risk factor mentions
        - Opportunity mentions
        - Financial metrics
        """
        metrics = {
            "market_mentions": 0,
            "company_mentions": 0,
            "risk_mentions": 0,
            "opportunity_mentions": 0,
            "financial_metrics": {
                "revenue_mentions": 0,
                "profit_mentions": 0,
                "roi_mentions": 0,
                "valuation_mentions": 0
            },
            "risk_categories": {
                "geopolitical_risk": 0,
                "market_risk": 0,
                "operational_risk": 0
            }
        }
        
        if not isinstance(data, dict):
            return metrics
        
        text_to_search = ""
        if "data" in data:
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        text_to_search += " " + str(item.get("text", ""))
                        text_to_search += " " + str(item.get("description", ""))
                        text_to_search += " " + str(item.get("title", ""))
        
        text_lower = text_to_search.lower()
        
        # Investment keywords
        investment_keywords = {
            "market": ["market", "mercado", "stock", "acción", "share", "participación"],
            "company": ["company", "empresa", "corporation", "corporación", "firm", "firma"],
            "risk": ["risk", "riesgo", "threat", "amenaza", "danger", "peligro"],
            "opportunity": ["opportunity", "oportunidad", "potential", "potencial", "prospect", "perspectiva"],
            "revenue": ["revenue", "ingresos", "income", "renta"],
            "profit": ["profit", "beneficio", "earnings", "ganancias"],
            "roi": ["roi", "return on investment", "retorno", "return"],
            "valuation": ["valuation", "valoración", "value", "valor", "worth", "valor"]
        }
        
        for category, keywords in investment_keywords.items():
            count = sum(text_lower.count(kw) for kw in keywords)
            if category == "market":
                metrics["market_mentions"] += count
            elif category == "company":
                metrics["company_mentions"] += count
            elif category == "risk":
                metrics["risk_mentions"] += count
            elif category == "opportunity":
                metrics["opportunity_mentions"] += count
            elif category in ["revenue", "profit", "roi", "valuation"]:
                metrics["financial_metrics"][f"{category}_mentions"] += count
        
        # Risk category detection
        if "geopolitical" in text_lower or "geopolítico" in text_lower:
            metrics["risk_categories"]["geopolitical_risk"] += text_lower.count("geopolitical") + text_lower.count("geopolítico")
        if "market" in text_lower or "volatility" in text_lower or "volatilidad" in text_lower:
            metrics["risk_categories"]["market_risk"] += 1
        if "operational" in text_lower or "operacional" in text_lower:
            metrics["risk_categories"]["operational_risk"] += 1
        
        return metrics
    
    def extract_social_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract social/public affairs-specific metrics
        
        Returns:
        - Viral content indicators
        - Influencer mentions
        - Community engagement metrics
        - Reputation indicators
        """
        metrics = {
            "viral_indicators": {
                "high_engagement_posts": 0,
                "trending_hashtags": 0,
                "viral_potential": 0
            },
            "influencer_mentions": 0,
            "community_metrics": {
                "mentions": 0,
                "shares": 0,
                "comments": 0,
                "reactions": 0
            },
            "reputation_indicators": {
                "positive_mentions": 0,
                "negative_mentions": 0,
                "crisis_mentions": 0
            }
        }
        
        if not isinstance(data, dict):
            return metrics
        
        # Get social media metrics first
        social_metrics = self.extract_social_media_metrics(data)
        
        # High engagement posts (threshold: >1000 likes or >100 comments)
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if isinstance(item, dict):
                    likes = item.get("like_count", 0) or 0
                    comments = item.get("comment_count", 0) or 0
                    shares = item.get("share_count", 0) or 0
                    views = item.get("view_count", 0) or 0
                    
                    if likes > 1000 or comments > 100 or shares > 50:
                        metrics["viral_indicators"]["high_engagement_posts"] += 1
                    
                    if views > 10000:
                        metrics["viral_indicators"]["viral_potential"] += 1
                    
                    metrics["community_metrics"]["mentions"] += 1
                    metrics["community_metrics"]["shares"] += shares
                    metrics["community_metrics"]["comments"] += comments
                    metrics["community_metrics"]["reactions"] += likes
        
        # Hashtag detection
        text_to_search = ""
        if "data" in data:
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        text_to_search += " " + str(item.get("text", ""))
                        text_to_search += " " + str(item.get("hashtags", ""))
        
        import re
        hashtag_pattern = r'#\w+'
        hashtags = re.findall(hashtag_pattern, text_to_search)
        metrics["viral_indicators"]["trending_hashtags"] = len(set(hashtags))
        
        # Influencer keywords
        influencer_keywords = ["influencer", "influencer", "kols", "key opinion leader", "celebrity", "celebridad"]
        text_lower = text_to_search.lower()
        metrics["influencer_mentions"] = sum(text_lower.count(kw) for kw in influencer_keywords)
        
        # Reputation indicators
        sentiment_metrics = self.extract_sentiment_metrics(data)
        metrics["reputation_indicators"]["positive_mentions"] = sentiment_metrics.get("positive_count", 0)
        metrics["reputation_indicators"]["negative_mentions"] = sentiment_metrics.get("negative_count", 0)
        
        crisis_keywords = ["crisis", "crisis", "scandal", "escándalo", "controversy", "controversia"]
        metrics["reputation_indicators"]["crisis_mentions"] = sum(text_lower.count(kw) for kw in crisis_keywords)
        
        return metrics
    
    def extract_business_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract business intelligence-specific metrics
        
        Returns:
        - Partnership mentions
        - Market share indicators
        - Revenue/profit mentions
        - Competitive positioning
        - Strategic initiatives
        """
        metrics = {
            "partnership_mentions": 0,
            "market_share_mentions": 0,
            "revenue_mentions": 0,
            "competitive_mentions": 0,
            "strategic_initiatives": 0,
            "partnership_types": {
                "joint_venture": 0,
                "merger_acquisition": 0,
                "strategic_alliance": 0,
                "partnership": 0
            }
        }
        
        if not isinstance(data, dict):
            return metrics
        
        text_to_search = ""
        if "data" in data:
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        text_to_search += " " + str(item.get("text", ""))
                        text_to_search += " " + str(item.get("description", ""))
                        text_to_search += " " + str(item.get("title", ""))
        
        text_lower = text_to_search.lower()
        
        # Business keywords
        business_keywords = {
            "partnership": ["partnership", "asociación", "collaboration", "colaboración", "alliance", "alianza"],
            "market_share": ["market share", "cuota de mercado", "market position", "posición de mercado"],
            "revenue": ["revenue", "ingresos", "sales", "ventas", "turnover", "facturación"],
            "competitive": ["competitor", "competidor", "competition", "competencia", "rival", "rival"],
            "strategic": ["strategic", "estratégico", "initiative", "iniciativa", "plan", "plan"]
        }
        
        for category, keywords in business_keywords.items():
            count = sum(text_lower.count(kw) for kw in keywords)
            if category == "partnership":
                metrics["partnership_mentions"] += count
            elif category == "market_share":
                metrics["market_share_mentions"] += count
            elif category == "revenue":
                metrics["revenue_mentions"] += count
            elif category == "competitive":
                metrics["competitive_mentions"] += count
            elif category == "strategic":
                metrics["strategic_initiatives"] += count
        
        # Partnership type detection
        if "joint venture" in text_lower or "empresa conjunta" in text_lower:
            metrics["partnership_types"]["joint_venture"] += 1
        if "merger" in text_lower or "acquisition" in text_lower or "fusión" in text_lower or "adquisición" in text_lower:
            metrics["partnership_types"]["merger_acquisition"] += 1
        if "strategic alliance" in text_lower or "alianza estratégica" in text_lower:
            metrics["partnership_types"]["strategic_alliance"] += 1
        if "partnership" in text_lower or "asociación" in text_lower:
            metrics["partnership_types"]["partnership"] += 1
        
        return metrics

