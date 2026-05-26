"""
Geographic data router - Extract and return geographic information from cases
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
# Autenticació eliminada
from pydantic import BaseModel
from sqlalchemy import select
from models.osint import OSINTQuery, OSINTResult
from models.case import Case
from models.ai_analysis import AIAnalysis, Concept
from models.extract import ExtractedStatement
from services.geo_keywords import find_geo_hits
from services.geo_ner import extract_geo_entities
from services.osint_data_utils import flatten_osint_items, text_from_osint_item
from services.osint_geo_utils import bump_osint_source_counts, osint_provider_from_query_type, article_provider

router = APIRouter()

class Location(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    type: str  # country, region, city, neighborhood, point
    data: Optional[Dict[str, Any]] = None
    count: Optional[int] = 1

class GeographicDataResponse(BaseModel):
    locations: List[Location]

# Base de datos de coordenadas (simplificada - en producción usar API de geocoding)
COUNTRY_COORDS: Dict[str, tuple] = {
    'spain': (40.4637, -3.7492),
    'france': (46.2276, 2.2137),
    'germany': (51.1657, 10.4515),
    'italy': (41.8719, 12.5674),
    'united kingdom': (55.3781, -3.4360),
    'united states': (37.0902, -95.7129),
    'china': (35.8617, 104.1954),
    'india': (20.5937, 78.9629),
    'japan': (36.2048, 138.2529),
    'brazil': (-14.2350, -51.9253),
    'russia': (61.5240, 105.3188),
    'mexico': (23.6345, -102.5528),
    'canada': (56.1304, -106.3468),
    'australia': (-25.2744, 133.7751),
    'argentina': (-38.4161, -63.6167),
    'south africa': (-30.5595, 22.9375),
    'egypt': (26.8206, 30.8025),
    'turkey': (38.9637, 35.2433),
    'uae': (23.4241, 53.8478),
    'andorra': (42.5462, 1.6016),
    'principality of andorra': (42.5462, 1.6016),
    'japan': (36.2048, 138.2529),
    'china': (35.8617, 104.1954),
    'taiwan': (25.0330, 121.5654),
    'south korea': (37.5665, 126.9780),
    'north korea': (39.0392, 125.7625),
    'ukraine': (48.3794, 31.1656),
    'israel': (31.0461, 34.8516),
    'iran': (32.4279, 53.6880),
    'saudi arabia': (23.8859, 45.0792),
    'european union': (50.8466, 4.3528),
}

CITY_COORDS: Dict[str, tuple] = {
    'madrid': (40.4168, -3.7038),
    'barcelona': (41.3851, 2.1734),
    'valencia': (39.4699, -0.3763),
    'seville': (37.3891, -5.9845),
    'paris': (48.8566, 2.3522),
    'london': (51.5074, -0.1278),
    'berlin': (52.5200, 13.4050),
    'rome': (41.9028, 12.4964),
    'new york': (40.7128, -74.0060),
    'los angeles': (34.0522, -118.2437),
    'tokyo': (35.6762, 139.6503),
    'beijing': (39.9042, 116.4074),
    'mumbai': (19.0760, 72.8777),
    'dubai': (25.2048, 55.2708),
    'sydney': (-33.8688, 151.2093),
    'moscow': (55.7558, 37.6173),
    'cairo': (30.0444, 31.2357),
    'istanbul': (41.0082, 28.9784),
    'mexico city': (19.4326, -99.1332),
    'sao paulo': (-23.5505, -46.6333),
    'buenos aires': (-34.6037, -58.3816),
    'andorra la vella': (42.5078, 1.5211),
    'andorra': (42.5462, 1.6016),
}

async def geocode_location(name: str) -> Optional[tuple]:
    """Geocode a location name to coordinates - Uses Nominatim API for real geocoding"""
    from integrations.nominatim_api import NominatimAPIService
    import re
    
    if not name or not name.strip():
        return None
    
    name_lower = name.lower().strip()
    
    # Extract location from patterns like "FEDA (Andorra)" or "Case Name - Spain"
    # Try to extract location in parentheses or after dash
    location_patterns = [
        r'\(([^)]+)\)',  # Text in parentheses: (Andorra)
        r'-\s*([^-]+)$',  # Text after dash: - Spain
        r',\s*([^,]+)$',  # Text after comma: , France
    ]
    
    extracted_location = None
    for pattern in location_patterns:
        match = re.search(pattern, name)
        if match:
            extracted_location = match.group(1).strip()
            break
    
    # Use extracted location if found, otherwise use full name
    search_name = extracted_location if extracted_location else name
    
    # First try static database (faster for common locations)
    search_lower = search_name.lower().strip()
    
    if search_lower in CITY_COORDS:
        return CITY_COORDS[search_lower]
    
    # Check if any country name is in the search string
    for country, coords in COUNTRY_COORDS.items():
        if country in search_lower or search_lower in country:
            return coords
    
    # Try common patterns
    if 'spain' in search_lower or 'españa' in search_lower or 'espanya' in search_lower:
        return COUNTRY_COORDS['spain']
    if 'france' in search_lower or 'francia' in search_lower:
        return COUNTRY_COORDS['france']
    if 'germany' in search_lower or 'alemania' in search_lower or 'alemanya' in search_lower:
        return COUNTRY_COORDS['germany']
    if 'italy' in search_lower or 'italia' in search_lower:
        return COUNTRY_COORDS['italy']
    if 'uk' in search_lower or 'united kingdom' in name_lower or 'reino unido' in search_lower:
        return COUNTRY_COORDS['united kingdom']
    if 'usa' in search_lower or 'united states' in search_lower or 'estados unidos' in search_lower or 'eeuu' in search_lower:
        return COUNTRY_COORDS['united states']
    if 'andorra' in search_lower:
        return COUNTRY_COORDS['andorra']
    
    # If not found in static DB, try Nominatim API
    try:
        nominatim = NominatimAPIService()
        result = await nominatim.geocode(search_name, limit=1)
        if result.get("status") == "success" and result.get("results"):
            first_result = result["results"][0]
            return (first_result["latitude"], first_result["longitude"])
    except Exception as e:
        # Fallback to None if API fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error geocoding {search_name}: {e}")
        pass
    
    return None

async def extract_locations_from_data(data: Dict[str, Any]) -> List[Location]:
    """Extract geographic locations from OSINT data"""
    locations: List[Location] = []
    location_ids = set()
    
    # Extract from various data fields
    if isinstance(data, dict):
        # Check for explicit location fields
        for field in ['location', 'country', 'city', 'region', 'address', 'place']:
            if field in data and data[field]:
                loc_name = str(data[field])
                coords = await geocode_location(loc_name)
                if coords:
                    loc_id = f"{field}_{loc_name}"
                    if loc_id not in location_ids:
                        location_ids.add(loc_id)
                        # Determine type based on field name
                        loc_type = 'point'
                        if field == 'country':
                            loc_type = 'country'
                        elif field == 'region':
                            loc_type = 'region'
                        elif field == 'city':
                            loc_type = 'city'
                        elif field == 'address' or field == 'place':
                            loc_type = 'neighborhood'
                        
                        locations.append(Location(
                            id=loc_id,
                            name=loc_name,
                            latitude=coords[0],
                            longitude=coords[1],
                            type=loc_type,
                            data={field: data[field]},
                            count=1
                        ))
        
        # Extract from text fields (simple keyword matching)
        text_fields = ['description', 'content', 'text', 'summary', 'title']
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                text = data[field].lower()
                for city, coords in CITY_COORDS.items():
                    if city in text:
                        loc_id = f"text_{city}"
                        if loc_id not in location_ids:
                            location_ids.add(loc_id)
                            locations.append(Location(
                                id=loc_id,
                                name=city.title(),
                                latitude=coords[0],
                                longitude=coords[1],
                                type='city',
                                data={'source': field, 'text': data[field][:100]},
                                count=1
                            ))
                            break  # Only add first match per field
    
    return locations

def _merge_geo_hits(
    location_map: Dict[str, Location],
    text: str,
    *,
    loc_id_prefix: str,
    loc_type: str = "country",
    data: Optional[Dict[str, Any]] = None,
    osint_provider: Optional[str] = None,
) -> None:
    for ent in extract_geo_entities(text):
        label = str(ent["label"])
        lat = float(ent["lat"])
        lng = float(ent["lng"])
        if label in location_map:
            location_map[label].count = (location_map[label].count or 1) + 1
            if osint_provider:
                location_map[label].data = bump_osint_source_counts(
                    location_map[label].data, osint_provider
                )
            continue
        loc_data = dict(data or {})
        if osint_provider:
            loc_data = bump_osint_source_counts(loc_data, osint_provider)
        loc_data["match_type"] = ent.get("match_type", "keyword")
        location_map[label] = Location(
            id=f"{loc_id_prefix}_{label.replace(' ', '_').lower()}",
            name=label,
            latitude=lat,
            longitude=lng,
            type=loc_type,
            data=loc_data,
            count=1,
        )

@router.get("/locations/{case_id}", response_model=GeographicDataResponse)
async def get_case_locations(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all geographic locations from a case - Millorat per extreure ubicacions del nom del cas"""
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get case
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    logger.info(f"Extreient ubicacions per al cas {case_id}: {case.name}")
    
    # Get OSINT results
    queries_result = await db.execute(
        select(OSINTQuery).where(OSINTQuery.case_id == case_id)
    )
    queries = queries_result.scalars().all()
    
    all_locations: List[Location] = []
    location_map: Dict[str, Location] = {}
    
    # Process OSINT results
    for query in queries:
        provider = osint_provider_from_query_type(query.query_type or "")
        results_result = await db.execute(
            select(OSINTResult).where(OSINTResult.query_id == query.id)
        )
        results = results_result.scalars().all()

        for result in results:
            if not result.data:
                continue
            locations = await extract_locations_from_data(result.data)
            for loc in locations:
                if provider:
                    loc.data = bump_osint_source_counts(loc.data, provider)
                if loc.name in location_map:
                    location_map[loc.name].count = (location_map[loc.name].count or 1) + 1
                    if loc.data:
                        existing = location_map[loc.name].data or {}
                        for src, n in (loc.data.get("osint_sources") or {}).items():
                            merged = bump_osint_source_counts(existing, src, increment=n)
                            existing = merged
                        location_map[loc.name].data = existing
                else:
                    location_map[loc.name] = loc

            for item in flatten_osint_items(result.data):
                blob = text_from_osint_item(item)
                if not blob:
                    continue
                art_provider = article_provider(item, provider)
                _merge_geo_hits(
                    location_map,
                    blob,
                    loc_id_prefix=f"osint_{result.id}",
                    loc_type="point",
                    data={
                        "osint_result_id": result.id,
                        "query_type": query.query_type,
                        "url": item.get("url"),
                    },
                    osint_provider=art_provider,
                )
    
    # Get locations from AI analysis concepts
    concepts_result = await db.execute(
        select(Concept).join(AIAnalysis).where(AIAnalysis.case_id == case_id)
    )
    concepts = concepts_result.scalars().all()
    
    for concept in concepts:
        if concept.name:
            concept_coords = await geocode_location(concept.name)
            if concept_coords:
                if concept.name in location_map:
                    location_map[concept.name].count = (location_map[concept.name].count or 1) + 1
                else:
                    location_map[concept.name] = Location(
                        id=f"concept_{concept.id}",
                        name=concept.name,
                        latitude=concept_coords[0],
                        longitude=concept_coords[1],
                        type='point',
                        data={'concept_id': concept.id, 'category': concept.category},
                        count=1
                    )
    
    # Extract from extracted statements (actors, topics — clau per casos geopolítics)
    stmts_result = await db.execute(
        select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
    )
    for stmt in stmts_result.scalars().all():
        blob = " ".join(
            filter(
                None,
                [stmt.actor, stmt.topic, stmt.statement, stmt.posture_toward, stmt.context],
            )
        )
        _merge_geo_hits(
            location_map,
            blob,
            loc_id_prefix=f"stmt_{stmt.id}",
            loc_type="point",
            data={"statement_id": stmt.id, "actor": stmt.actor},
        )

    # Keyword scan del nom i descripció del cas
    if case.name:
        _merge_geo_hits(
            location_map,
            case.name,
            loc_id_prefix=f"case_kw_{case_id}",
            loc_type="country",
            data={"case_id": case_id, "type": "case_keywords"},
        )
    if case.description:
        _merge_geo_hits(
            location_map,
            case.description,
            loc_id_prefix=f"case_desc_kw_{case_id}",
            loc_type="point",
            data={"case_id": case_id, "type": "description_keywords"},
        )

    # Extract from case name/description - Millorat per extreure ubicacions
    # Intentar extreure ubicació del nom del cas
    case_name_location = None
    if case.name:
        case_coords_result = await geocode_location(case.name)
        if case_coords_result:
            # Extreure nom de la ubicació del nom del cas
            import re
            location_match = re.search(r'\(([^)]+)\)', case.name)
            if location_match:
                case_name_location = location_match.group(1).strip()
            else:
                # Si no hi ha parèntesis, intentar extreure després de guió o coma
                for separator in [' - ', ', ', ' en ', ' in ']:
                    if separator in case.name:
                        parts = case.name.split(separator)
                        if len(parts) > 1:
                            case_name_location = parts[-1].strip()
                            break
            
            if not case_name_location:
                case_name_location = case.name
            
            if case_name_location in location_map:
                location_map[case_name_location].count = (location_map[case_name_location].count or 1) + 1
            else:
                location_map[case_name_location] = Location(
                    id=f"case_{case_id}",
                    name=case_name_location,
                    latitude=case_coords_result[0],
                    longitude=case_coords_result[1],
                    type='country' if any(case_coords_result == coords for coords in COUNTRY_COORDS.values()) else 'city' if any(case_coords_result == coords for coords in CITY_COORDS.values()) else 'point',
                    data={'case_id': case_id, 'type': 'case', 'original_name': case.name},
                    count=1
                )
    
    # També intentar extreure de la descripció si existeix
    if case.description:
        desc_coords_result = await geocode_location(case.description)
        if desc_coords_result:
            desc_location_name = case.description[:50]  # Primeres 50 lletres com a nom
            if desc_location_name not in location_map:
                location_map[desc_location_name] = Location(
                    id=f"case_desc_{case_id}",
                    name=desc_location_name,
                    latitude=desc_coords_result[0],
                    longitude=desc_coords_result[1],
                    type='point',
                    data={'case_id': case_id, 'type': 'case_description'},
                    count=1
                )
    
    locations_list = list(location_map.values())
    logger.info(f"Retornant {len(locations_list)} ubicacions per al cas {case_id}")
    
    # Si no hi ha ubicacions, intentar extreure del nom del cas com a mínim
    if len(locations_list) == 0 and case.name:
        logger.info(f"No s'han trobat ubicacions, intentant extreure del nom: {case.name}")
        case_coords = await geocode_location(case.name)
        if case_coords:
            # Extreure nom de la ubicació
            import re
            location_match = re.search(r'\(([^)]+)\)', case.name)
            location_name = location_match.group(1).strip() if location_match else case.name
            
            locations_list.append(Location(
                id=f"case_{case_id}_primary",
                name=location_name,
                latitude=case_coords[0],
                longitude=case_coords[1],
                type='country' if any(case_coords == coords for coords in COUNTRY_COORDS.values()) else 'city' if any(case_coords == coords for coords in CITY_COORDS.values()) else 'point',
                data={'case_id': case_id, 'type': 'case', 'original_name': case.name},
                count=1
            ))
            logger.info(f"Ubicació extreta del nom del cas: {location_name} at {case_coords}")
    
    return GeographicDataResponse(locations=locations_list)

@router.get("/geocode")
async def geocode_location_endpoint(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    """Geocode a location using Nominatim (OpenStreetMap)"""
    from integrations.nominatim_api import NominatimAPIService
    
    service = NominatimAPIService()
    result = await service.geocode(q)
    
    return result

@router.get("/reverse-geocode")
async def reverse_geocode_endpoint(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    """Reverse geocode coordinates to location name"""
    from integrations.nominatim_api import NominatimAPIService
    
    service = NominatimAPIService()
    result = await service.reverse_geocode(lat, lon)
    
    return result

@router.get("/country/{country_name}")
async def get_country_info(
    country_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get country information from REST Countries API"""
    from integrations.country_api import CountryAPIService
    
    service = CountryAPIService()
    result = await service.get_country(country_name)
    
    return result

@router.get("/country/code/{code}")
async def get_country_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get country information by ISO code"""
    from integrations.country_api import CountryAPIService
    
    service = CountryAPIService()
    result = await service.get_country_by_code(code)
    
    return result

@router.get("/country/search/{query}")
async def search_countries(
    query: str,
    db: AsyncSession = Depends(get_db)
):
    """Search countries by name"""
    from integrations.country_api import CountryAPIService
    
    service = CountryAPIService()
    result = await service.search_countries(query)
    
    return result

@router.get("/ip/{ip_address}")
async def get_ip_location(
    ip_address: str,
    hostname: bool = True,
    security: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get geolocation information for an IP address"""
    from integrations.ipstack_api import IPStackAPIService
    
    service = IPStackAPIService()
    result = await service.get_ip_info(ip_address, hostname=hostname, security=security)
    
    # If successful, also return as Location for map visualization
    if result.get("status") == "success" and result.get("latitude") and result.get("longitude"):
        location = Location(
            id=f"ip_{ip_address}",
            name=f"{result.get('city', '')}, {result.get('country_name', '')} ({ip_address})",
            latitude=result["latitude"],
            longitude=result["longitude"],
            type="point",
            data={
                "ip": ip_address,
                "country_code": result.get("country_code", ""),
                "region_name": result.get("region_name", ""),
                "city": result.get("city", ""),
                "hostname": result.get("hostname", ""),
                "connection": result.get("connection", {}),
                "security": result.get("security", {})
            },
            count=1
        )
        return {
            "ip_info": result,
            "location": location
        }
    
    return result

