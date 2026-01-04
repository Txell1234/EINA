"""
Heatmap Service - Extract locations from posts and generate heatmap data
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.osint import OSINTQuery, OSINTResult
from models.case import Case
from integrations.nominatim_api import NominatimAPIService
from integrations.ipstack_api import IPStackAPIService
import re
import logging

logger = logging.getLogger(__name__)

# Andorra comuns (municipis) amb coordenades aproximades
ANDORRA_COMUNS = {
    "andorra la vella": (42.5078, 1.5211),
    "canillo": (42.5670, 1.5976),
    "encamp": (42.5369, 1.5801),
    "escaldes-engordany": (42.5083, 1.5389),
    "la massana": (42.5450, 1.5147),
    "ordino": (42.5562, 1.5332),
    "sant julià de lòria": (42.4637, 1.4914),
    "sant julia de loria": (42.4637, 1.4914),  # Variant sense accent
}

class HeatmapService:
    """Service to generate heatmap data from OSINT posts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nominatim = NominatimAPIService()
        self.ipstack = IPStackAPIService()
    
    def _extract_ip_addresses(self, data: Dict[str, Any]) -> List[str]:
        """Extract IP addresses from post data"""
        ips = []
        
        # Check common IP fields
        ip_fields = ["ip", "ip_address", "ipAddress", "client_ip", "source_ip", "origin_ip"]
        for field in ip_fields:
            if field in data and data[field]:
                ip = str(data[field]).strip()
                # Validate IP format (simple check)
                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                    ips.append(ip)
        
        # Check in nested user object
        if "user" in data and isinstance(data["user"], dict):
            for field in ip_fields:
                if field in data["user"] and data["user"][field]:
                    ip = str(data["user"][field]).strip()
                    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                        ips.append(ip)
        
        # Extract IPs from text fields (less reliable)
        text_fields = ["text", "description", "caption", "content", "title", "message"]
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                # Find IP addresses in text
                ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
                found_ips = re.findall(ip_pattern, data[field])
                ips.extend(found_ips)
        
        return list(set(ips))  # Remove duplicates
    
    async def extract_locations_from_posts(
        self,
        posts: List[Dict[str, Any]],
        granularity: str = "city"
    ) -> List[Dict[str, Any]]:
        """Extract locations from social media posts
        
        Args:
            posts: List of post dictionaries from OSINT results
            granularity: 'country', 'region', 'city', 'municipality'
            
        Returns:
            List of location dictionaries with extracted location names
        """
        locations = []
        ip_addresses_to_geocode = []  # Collect IPs for batch geocoding
        
        for post in posts:
            if not isinstance(post, dict):
                continue
            
            # FIRST: Try to extract IP addresses and geolocate them
            ips = self._extract_ip_addresses(post)
            for ip in ips:
                ip_addresses_to_geocode.append({
                    "ip": ip,
                    "post_id": post.get("id") or post.get("post_id")
                })
            
            # Extract from various fields
            text_fields = [
                post.get("text", ""),
                post.get("description", ""),
                post.get("caption", ""),
                post.get("content", ""),
                post.get("title", ""),
            ]
            
            # Extract from hashtags
            hashtags = []
            for field in text_fields:
                if isinstance(field, str):
                    # Find hashtags
                    hashtag_pattern = r'#(\w+)'
                    found_hashtags = re.findall(hashtag_pattern, field, re.IGNORECASE)
                    hashtags.extend(found_hashtags)
            
            # Extract from user location/bio
            user_location = None
            if "user" in post and isinstance(post["user"], dict):
                user_location = post["user"].get("location") or post["user"].get("bio")
            
            # Extract from structured location fields (prioritize these as they're more accurate)
            structured_location = None
            location_coords = None
            
            # Check for location object with coordinates (common in social media APIs)
            if "location" in post and isinstance(post["location"], dict):
                loc_obj = post["location"]
                if "latitude" in loc_obj and "longitude" in loc_obj:
                    location_coords = (float(loc_obj["latitude"]), float(loc_obj["longitude"]))
                    structured_location = loc_obj.get("name") or loc_obj.get("city") or loc_obj.get("country")
                else:
                    structured_location = loc_obj.get("name") or loc_obj.get("city") or loc_obj.get("country")
            
            # Check for place object
            if not structured_location and "place" in post and isinstance(post["place"], dict):
                place_obj = post["place"]
                if "location" in place_obj and isinstance(place_obj["location"], dict):
                    loc = place_obj["location"]
                    if "latitude" in loc and "longitude" in loc:
                        location_coords = (float(loc["latitude"]), float(loc["longitude"]))
                structured_location = place_obj.get("name") or place_obj.get("city") or place_obj.get("country")
            
            # Check for direct coordinate fields
            if not location_coords:
                if "latitude" in post and "longitude" in post:
                    try:
                        location_coords = (float(post["latitude"]), float(post["longitude"]))
                    except (ValueError, TypeError):
                        pass
            
            # Fallback to simple location fields
            if not structured_location:
                structured_location = post.get("city") or post.get("country") or post.get("region")
            
            # If we have coordinates, add location immediately
            if location_coords:
                location_name = structured_location or "Unknown Location"
                locations.append({
                    "location_name": location_name,
                    "source": "coordinates",
                    "post_id": post.get("id") or post.get("post_id"),
                    "coordinates": location_coords,
                    "granularity": "city" if post.get("city") else "region" if post.get("region") else "country"
                })
            
            # Combine all location sources
            location_texts = []
            if structured_location:
                location_texts.append(str(structured_location))
            if user_location:
                location_texts.append(str(user_location))
            
            # Extract location names from text
            for text in text_fields:
                if not text:
                    continue
                text_lower = text.lower()
                
                # Check for Andorra comuns specifically
                for comu_name, coords in ANDORRA_COMUNS.items():
                    if comu_name in text_lower:
                        locations.append({
                            "location_name": comu_name.title(),
                            "source": "text",
                            "post_id": post.get("id") or post.get("post_id"),
                            "coordinates": coords,
                            "granularity": "municipality"
                        })
                        break
                
                # Check for common city/country patterns
                # This is a simplified extraction - can be enhanced with NLP
                location_patterns = [
                    r'\b(Andorra|Spain|France|Germany|Italy|UK|United Kingdom|USA|United States|India|UAE|United Arab Emirates)\b',
                    r'\b(Madrid|Barcelona|Paris|London|Berlin|Rome|New York|Dubai|Mumbai)\b',
                ]
                
                for pattern in location_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if match not in [loc.get("location_name", "").lower() for loc in locations]:
                            locations.append({
                                "location_name": match,
                                "source": "text",
                                "post_id": post.get("id") or post.get("post_id"),
                                "coordinates": None,  # Will be geocoded later
                                "granularity": "country" if match in ["Andorra", "Spain", "France", "Germany", "Italy", "UK", "United Kingdom", "USA", "United States", "India", "UAE", "United Arab Emirates"] else "city"
                            })
            
            # Extract from hashtags
            for hashtag in hashtags:
                hashtag_lower = hashtag.lower()
                # Check if hashtag is a location
                if any(loc in hashtag_lower for loc in ["andorra", "spain", "france", "madrid", "barcelona", "paris"]):
                    if hashtag not in [loc.get("location_name", "").lower() for loc in locations]:
                        locations.append({
                            "location_name": hashtag.title(),
                            "source": "hashtag",
                            "post_id": post.get("id") or post.get("post_id"),
                            "coordinates": None,
                            "granularity": "city"
                        })
        
        # Geocode IP addresses in batch (more efficient)
        if ip_addresses_to_geocode:
            unique_ips = list(set([item["ip"] for item in ip_addresses_to_geocode]))
            logger.info(f"Geocoding {len(unique_ips)} unique IP addresses for heatmap")
            
            # Use bulk geocoding if available
            if len(unique_ips) > 1:
                try:
                    bulk_result = await self.ipstack.get_bulk_info(unique_ips, hostname=False, security=False)
                    if bulk_result.get("status") == "success":
                        ip_location_map = {}
                        for ip_data in bulk_result.get("results", []):
                            if ip_data.get("latitude") and ip_data.get("longitude"):
                                ip_location_map[ip_data.get("ip", "")] = {
                                    "city": ip_data.get("city", ""),
                                    "country": ip_data.get("country_name", ""),
                                    "region": ip_data.get("region_name", ""),
                                    "coordinates": (ip_data.get("latitude"), ip_data.get("longitude"))
                                }
                        
                        # Add locations from IP geocoding
                        for ip_item in ip_addresses_to_geocode:
                            ip = ip_item["ip"]
                            if ip in ip_location_map:
                                ip_loc = ip_location_map[ip]
                                location_name = ip_loc["city"] or ip_loc["region"] or ip_loc["country"] or ip
                                locations.append({
                                    "location_name": location_name,
                                    "source": "ip_geolocation",
                                    "post_id": ip_item["post_id"],
                                    "coordinates": ip_loc["coordinates"],
                                    "granularity": "city" if ip_loc["city"] else "region" if ip_loc["region"] else "country"
                                })
                except Exception as e:
                    logger.warning(f"Error in bulk IP geocoding: {e}, falling back to individual requests")
                    # Fallback to individual requests
                    for ip_item in ip_addresses_to_geocode[:10]:  # Limit to 10 to avoid rate limits
                        try:
                            ip_result = await self.ipstack.get_ip_info(ip_item["ip"], hostname=False, security=False)
                            if ip_result.get("status") == "success" and ip_result.get("latitude") and ip_result.get("longitude"):
                                location_name = ip_result.get("city") or ip_result.get("region_name") or ip_result.get("country_name") or ip_item["ip"]
                                locations.append({
                                    "location_name": location_name,
                                    "source": "ip_geolocation",
                                    "post_id": ip_item["post_id"],
                                    "coordinates": (ip_result.get("latitude"), ip_result.get("longitude")),
                                    "granularity": "city" if ip_result.get("city") else "region" if ip_result.get("region_name") else "country"
                                })
                        except Exception as e:
                            logger.warning(f"Error geocoding IP {ip_item['ip']}: {e}")
            else:
                # Single IP
                try:
                    ip_result = await self.ipstack.get_ip_info(unique_ips[0], hostname=False, security=False)
                    if ip_result.get("status") == "success" and ip_result.get("latitude") and ip_result.get("longitude"):
                        location_name = ip_result.get("city") or ip_result.get("region_name") or ip_result.get("country_name") or unique_ips[0]
                        for ip_item in ip_addresses_to_geocode:
                            locations.append({
                                "location_name": location_name,
                                "source": "ip_geolocation",
                                "post_id": ip_item["post_id"],
                                "coordinates": (ip_result.get("latitude"), ip_result.get("longitude")),
                                "granularity": "city" if ip_result.get("city") else "region" if ip_result.get("region_name") else "country"
                            })
                except Exception as e:
                    logger.warning(f"Error geocoding IP {unique_ips[0]}: {e}")
        
        return locations
    
    async def geocode_locations(
        self,
        locations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Geocode location names to coordinates"""
        geocoded = []
        
        for loc in locations:
            if loc.get("coordinates"):
                # Already has coordinates
                geocoded.append(loc)
                continue
            
            location_name = loc.get("location_name")
            if not location_name:
                continue
            
            try:
                # Try Nominatim geocoding
                result = await self.nominatim.geocode(location_name, limit=1)
                if result.get("status") == "success" and result.get("results"):
                    first_result = result["results"][0]
                    loc["coordinates"] = (first_result["latitude"], first_result["longitude"])
                    geocoded.append(loc)
                else:
                    logger.warning(f"Could not geocode location: {location_name}")
            except Exception as e:
                logger.error(f"Error geocoding {location_name}: {e}")
        
        return geocoded
    
    async def extract_themes_from_posts(
        self,
        posts: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract themes/topics from posts and group by location
        
        Returns:
            Dictionary mapping location names to list of themes mentioned
        """
        from services.data_extraction_service import DataExtractionService
        from models.ai_analysis import Concept
        
        extraction_service = DataExtractionService()
        themes_by_location: Dict[str, List[str]] = {}
        
        # Common themes/keywords for public advocacy
        theme_keywords = {
            "reputation": ["reputació", "reputation", "imatge", "image", "marca", "brand"],
            "crisis": ["crisi", "crisis", "escàndol", "scandal", "controversia", "controversy"],
            "support": ["suport", "support", "apoyo", "endorsement", "endorsement"],
            "opposition": ["oposició", "opposition", "crítica", "criticism", "rebut", "rejection"],
            "policy": ["política", "policy", "legislació", "legislation", "regulació", "regulation"],
            "economic": ["econòmic", "economic", "financer", "financial", "comerç", "trade"],
            "social": ["social", "comunitat", "community", "societat", "society"],
            "environmental": ["medi ambient", "environment", "sostenibilitat", "sustainability", "clima", "climate"]
        }
        
        for post in posts:
            if not isinstance(post, dict):
                continue
            
            # Extract text from post
            text_fields = [
                post.get("text", ""),
                post.get("description", ""),
                post.get("caption", ""),
                post.get("content", ""),
            ]
            
            text_content = " ".join(str(f) for f in text_fields if f).lower()
            
            # Find location in post (simplified - can be enhanced)
            post_location = None
            for comu_name in ANDORRA_COMUNS.keys():
                if comu_name in text_content:
                    post_location = comu_name.title()
                    break
            
            if not post_location:
                # Try to extract from other location patterns
                import re
                location_patterns = [
                    r'\b(Andorra la Vella|Canillo|Encamp|Escaldes-Engordany|La Massana|Ordino|Sant Julià de Lòria)\b',
                    r'\b(Madrid|Barcelona|Paris|London)\b'
                ]
                for pattern in location_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        post_location = match.group(1)
                        break
            
            if post_location:
                if post_location not in themes_by_location:
                    themes_by_location[post_location] = []
                
                # Detect themes
                for theme, keywords in theme_keywords.items():
                    if any(kw in text_content for kw in keywords):
                        if theme not in themes_by_location[post_location]:
                            themes_by_location[post_location].append(theme)
        
        return themes_by_location
    
    async def extract_location_relationships(
        self,
        posts: List[Dict[str, Any]],
        locations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between locations from posts
        
        Returns:
            List of relationships with source_location, target_location, strength, type
        """
        relationships = []
        
        # Create mapping of post_id to locations
        post_locations = {}
        for loc in locations:
            post_id = loc.get("post_id")
            if post_id:
                if post_id not in post_locations:
                    post_locations[post_id] = []
                post_locations[post_id].append(loc.get("location_name", "").lower())
        
        # Find posts that mention multiple locations (indicating relationship)
        for post in posts:
            post_id = post.get("id") or post.get("post_id")
            if post_id not in post_locations:
                continue
            
            locs = post_locations[post_id]
            if len(locs) >= 2:
                # Create relationships between all pairs
                for i in range(len(locs)):
                    for j in range(i + 1, len(locs)):
                        relationships.append({
                            "source_location": locs[i],  # Changed from 'from_location'
                            "target_location": locs[j],  # Changed from 'to_location'
                            "strength": 1,  # Can be enhanced based on post engagement
                            "type": "mentioned_together",
                            "post_id": post_id
                        })
        
        # Aggregate relationships
        relationship_map: Dict[str, Dict[str, Any]] = {}
        for rel in relationships:
            key = f"{rel['source_location']}_{rel['target_location']}"
            if key not in relationship_map:
                relationship_map[key] = {
                    "source_location": rel["source_location"],  # Changed from 'from_location'
                    "target_location": rel["target_location"],  # Changed from 'to_location'
                    "strength": 0,
                    "type": rel["type"],
                    "count": 0
                }
            relationship_map[key]["strength"] += rel["strength"]
            relationship_map[key]["count"] += 1
        
        return list(relationship_map.values())
    
    async def aggregate_by_location(
        self,
        posts: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        metric: str = "count"
    ) -> Dict[str, Any]:
        """Aggregate posts by location with specified metric
        
        Args:
            posts: List of posts
            locations: List of extracted locations
            metric: 'count', 'sentiment', 'engagement'
            
        Returns:
            Dictionary mapping location names to aggregated metrics
        """
        from services.data_extraction_service import DataExtractionService
        
        extraction_service = DataExtractionService()
        
        # Create mapping of post_id to location
        post_locations = {}
        for loc in locations:
            post_id = loc.get("post_id")
            if post_id:
                if post_id not in post_locations:
                    post_locations[post_id] = []
                post_locations[post_id].append(loc)
        
        # Aggregate by location
        location_metrics = {}
        
        for post in posts:
            post_id = post.get("id") or post.get("post_id")
            if post_id not in post_locations:
                continue
            
            for loc in post_locations[post_id]:
                loc_name = loc.get("location_name", "").lower()
                if not loc_name:
                    continue
                
                if loc_name not in location_metrics:
                    location_metrics[loc_name] = {
                        "location_name": loc.get("location_name"),
                        "coordinates": loc.get("coordinates"),
                        "count": 0,
                        "sentiment_scores": [],
                        "total_engagement": 0,
                        "posts": []
                    }
                
                location_metrics[loc_name]["count"] += 1
                location_metrics[loc_name]["posts"].append(post_id)
                
                # Extract sentiment if metric includes sentiment
                if metric in ["sentiment", "all"]:
                    sentiment_metrics = extraction_service.extract_sentiment_metrics({"data": [post]})
                    sentiment_score = sentiment_metrics.get("average_sentiment", 0)
                    if sentiment_score:
                        location_metrics[loc_name]["sentiment_scores"].append(sentiment_score)
                
                # Extract engagement if metric includes engagement
                if metric in ["engagement", "all"]:
                    social_metrics = extraction_service.extract_social_media_metrics({"data": [post]})
                    engagement = (
                        (social_metrics.get("total_likes", 0) or 0) +
                        (social_metrics.get("total_comments", 0) or 0) +
                        (social_metrics.get("total_shares", 0) or 0)
                    )
                    location_metrics[loc_name]["total_engagement"] += engagement
        
        # Extract themes for each location
        themes_by_location = await self.extract_themes_from_posts(posts)
        
        # Calculate final metrics
        aggregated = {}
        for loc_name, metrics in location_metrics.items():
            loc_name_lower = loc_name.lower()
            themes = themes_by_location.get(loc_name_lower, [])
            
            # Determine dominant theme
            dominant_theme = themes[0] if themes else "general"
            
            aggregated[loc_name] = {
                "location_name": metrics["location_name"],
                "coordinates": metrics["coordinates"],
                "count": metrics["count"],
                "sentiment": (
                    sum(metrics["sentiment_scores"]) / len(metrics["sentiment_scores"])
                    if metrics["sentiment_scores"] else 0
                ),
                "engagement": metrics["total_engagement"],
                "posts_count": len(set(metrics["posts"])),
                "themes": themes,
                "dominant_theme": dominant_theme
            }
        
        return aggregated
    
    async def generate_heatmap_data(
        self,
        case_id: int,
        metric_type: str = "posts",
        granularity: str = "city",
        platform: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Generate heatmap data for a case
        
        Args:
            case_id: Case ID
            metric_type: 'posts', 'sentiment', 'engagement', 'custom'
            granularity: 'country', 'region', 'city', 'municipality'
            platform: Filter by platform (Instagram, TikTok, etc.)
            time_range: Optional time range filter
            
        Returns:
            Dictionary with heatmap points and metadata
        """
        # Get case
        case_result = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        
        if not case:
            return {
                "status": "error",
                "error": "Case not found",
                "points": []
            }
        
        # Get OSINT queries for this case
        query_filter = select(OSINTQuery).where(OSINTQuery.case_id == case_id)
        if platform:
            # Filter by platform (query_type contains platform name)
            platform_keywords = {
                "instagram": "instagram",
                "tiktok": "tiktok",
                "twitter": "twitter",
                "youtube": "youtube",
                "threads": "threads",
                "reddit": "reddit"
            }
            if platform.lower() in platform_keywords:
                keyword = platform_keywords[platform.lower()]
                query_filter = query_filter.where(OSINTQuery.query_type.contains(keyword))
        
        queries_result = await self.db.execute(query_filter)
        queries = queries_result.scalars().all()
        
        # Collect all posts
        all_posts = []
        for query in queries:
            results_result = await self.db.execute(
                select(OSINTResult).where(OSINTResult.query_id == query.id)
            )
            results = results_result.scalars().all()
            
            for result in results:
                if not result.data:
                    continue
                
                # Extract posts from result data
                data = result.data
                if isinstance(data, dict):
                    if data.get("status") == "success" and "data" in data:
                        posts = data["data"]
                        if isinstance(posts, list):
                            all_posts.extend(posts)
                        elif isinstance(posts, dict):
                            all_posts.append(posts)
                    else:
                        # Single post
                        all_posts.append(data)
                elif isinstance(data, list):
                    all_posts.extend(data)
        
        # Filter by time range if provided
        if time_range:
            filtered_posts = []
            for post in all_posts:
                post_date = post.get("created_time") or post.get("created_at") or post.get("date")
                if post_date:
                    # Simple date comparison (can be enhanced)
                    if isinstance(post_date, str):
                        try:
                            from datetime import datetime
                            post_dt = datetime.fromisoformat(post_date.replace("Z", "+00:00"))
                            start_dt = datetime.fromisoformat(time_range.get("start", ""))
                            end_dt = datetime.fromisoformat(time_range.get("end", ""))
                            if start_dt <= post_dt <= end_dt:
                                filtered_posts.append(post)
                        except:
                            pass
            all_posts = filtered_posts
        
        # Extract locations from posts
        locations = await self.extract_locations_from_posts(all_posts, granularity)
        
        # Geocode locations
        geocoded_locations = await self.geocode_locations(locations)
        
        # Aggregate by location
        aggregated = await self.aggregate_by_location(all_posts, geocoded_locations, metric_type)
        
        # Generate heatmap points
        points = []
        max_value = 0
        
        for loc_name, metrics in aggregated.items():
            if not metrics.get("coordinates"):
                continue
            
            lat, lng = metrics["coordinates"]
            
            # Calculate intensity based on metric type
            if metric_type == "posts":
                intensity = metrics["count"]
            elif metric_type == "sentiment":
                # Normalize sentiment to 0-1 (assuming sentiment is -1 to 1)
                intensity = (metrics["sentiment"] + 1) / 2
            elif metric_type == "engagement":
                intensity = metrics["engagement"]
            else:
                intensity = metrics["count"]
            
            max_value = max(max_value, intensity)
            
            points.append({
                "lat": lat,
                "lng": lng,
                "intensity": intensity,
                "metadata": {
                    "location_name": metrics["location_name"],
                    "count": metrics["count"],
                    "sentiment": metrics.get("sentiment", 0),
                    "engagement": metrics.get("engagement", 0)
                }
            })
        
        # Normalize intensities to 0-1 range
        if max_value > 0:
            for point in points:
                point["intensity"] = point["intensity"] / max_value
        
        # Extract relationships between locations
        relationships = await self.extract_location_relationships(all_posts, geocoded_locations)
        
        # Format relationships with coordinates
        formatted_relationships = []
        location_coords_map = {loc.get("location_name", "").lower(): loc.get("coordinates") for loc in geocoded_locations if loc.get("coordinates")}
        
        for rel in relationships:
            source_coords = location_coords_map.get(rel["source_location"])  # Changed from 'from_location'
            target_coords = location_coords_map.get(rel["target_location"])  # Changed from 'to_location'
            
            if source_coords and target_coords:
                formatted_relationships.append({
                    "source_location": {  # Changed from 'from_location'
                        "location": rel["source_location"],
                        "lat": source_coords[0],
                        "lng": source_coords[1]
                    },
                    "target_location": {  # Changed from 'to'
                        "location": rel["target_location"],
                        "lat": target_coords[0],
                        "lng": target_coords[1]
                    },
                    "strength": rel["strength"],
                    "type": rel["type"],
                    "count": rel.get("count", 1)
                })
        
        return {
            "status": "success",
            "points": points,
            "relationships": formatted_relationships,
            "granularity": granularity,
            "metric_type": metric_type,
            "total_points": len(points),
            "total_posts": len(all_posts),
            "platform": platform,
            "date_range": time_range
        }

