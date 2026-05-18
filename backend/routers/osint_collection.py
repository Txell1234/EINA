"""
OSINT Collection router
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.osint import OSINTQueryRequest, OSINTQueryResponse, OSINTResultResponse
from models.osint import OSINTQuery, OSINTResult
from services.osint_service import OSINTService

router = APIRouter()

@router.post("/sherlock", response_model=OSINTResultResponse)
async def search_sherlock(
    username: str,
    case_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Search for username across social media platforms using Sherlock"""
    from fastapi import Query
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="sherlock",
        query_params={"username": username},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/recon-ng/domain", response_model=OSINTResultResponse)
async def reconng_domain(
    domain: str,
    case_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Analyze domain using Recon-ng"""
    from fastapi import Query
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="recon-ng",
        query_params={"module": "domain", "domain": domain},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/recon-ng/ip", response_model=OSINTResultResponse)
async def reconng_ip(
    ip_address: str,
    case_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Analyze IP address using Recon-ng"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="recon-ng",
        query_params={"module": "ip", "ip": ip_address},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/google-news", response_model=OSINTResultResponse)
async def search_google_news(
    query: str,
    language: str = "es",
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search Google News"""
    from fastapi import Query
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="google_news",
        query_params={"query": query, "language": language},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/reddit", response_model=OSINTResultResponse)
async def search_reddit(
    query: str,
    subreddit: Optional[str] = None,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search Reddit"""
    from fastapi import Query
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="reddit",
        query_params={"query": query, "subreddit": subreddit},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/github", response_model=OSINTResultResponse)
async def search_github(
    query: str,
    type: str = "repositories",
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search GitHub"""
    from fastapi import Query
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="github",
        query_params={"query": query, "type": type},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/theharvester", response_model=OSINTResultResponse)
async def search_theharvester(
    domain: str,
    sources: str = None,
    limit: int = 500,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search using theHarvester"""
    osint_service = OSINTService(db)
    
    sources_list = sources.split(",") if sources else None
    
    result = await osint_service.execute_query(
        query_type="theharvester",
        query_params={"domain": domain, "sources": sources_list, "limit": limit},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/shodan", response_model=OSINTResultResponse)
async def search_shodan(
    query: str,
    facets: str = None,
    page: int = 1,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search Shodan"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="shodan",
        query_params={"query": query, "facets": facets, "page": page},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/shodan/host", response_model=OSINTResultResponse)
async def shodan_host_info(
    ip: str,
    db: AsyncSession = Depends(get_db)
):
    """Get Shodan host information"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="shodan_host",
        query_params={"ip": ip},
        case_id=None
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/wayback", response_model=OSINTResultResponse)
async def search_wayback(
    url: str,
    limit: int = 10,
    from_date: str = None,
    to_date: str = None,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Search Wayback Machine"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="wayback",
        query_params={"url": url, "limit": limit, "from_date": from_date, "to_date": to_date},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/dns", response_model=OSINTResultResponse)
async def dns_lookup(
    domain: str,
    record_types: str = None,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """DNS lookup"""
    osint_service = OSINTService(db)
    
    record_types_list = record_types.split(",") if record_types else None
    
    result = await osint_service.execute_query(
        query_type="dns",
        query_params={"domain": domain, "record_types": record_types_list},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/whois", response_model=OSINTResultResponse)
async def whois_lookup(
    domain: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """WHOIS lookup"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="whois",
        query_params={"domain": domain},
        case_id=case_id
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/reverse-dns", response_model=OSINTResultResponse)
async def reverse_dns_lookup(
    ip: str,
    db: AsyncSession = Depends(get_db)
):
    """Reverse DNS lookup"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type="reverse_dns",
        query_params={"ip": ip},
        case_id=None
    )
    
    return OSINTResultResponse.model_validate(result)

@router.post("/gdelt", response_model=OSINTResultResponse)
async def search_gdelt(
    query: str,
    days: int = 7,
    max_results: int = 50,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Search GDELT global events and news (no API key required)"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="gdelt",
        query_params={"query": query, "days": days, "max_results": max_results},
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/rss", response_model=OSINTResultResponse)
async def fetch_rss_feed(
    source: str = "cfr",
    max_items: int = 20,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single RSS feed (iiss, cfr, csis, brookings, elcano, etc.)"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="rss_feed",
        query_params={"source": source, "max_items": max_items},
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/rss/all", response_model=OSINTResultResponse)
async def fetch_all_rss_feeds(
    max_items: int = 10,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch all configured think-tank and policy RSS feeds"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="rss_all",
        query_params={"max_items": max_items},
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/opensanctions", response_model=OSINTResultResponse)
async def search_opensanctions(
    query: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Check entity against OpenSanctions database"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="opensanctions",
        query_params={"query": query},
        case_id=case_id,
    )
    return OSINTResultResponse.model_validate(result)

@router.get("/queries", response_model=List[OSINTQueryResponse])
async def list_queries(
    skip: int = 0,
    limit: int = 100,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """List OSINT queries"""
    from sqlalchemy import select
    
    query = select(OSINTQuery)
    
    if case_id:
        query = query.where(OSINTQuery.case_id == case_id)
    
    query = query.offset(skip).limit(limit).order_by(OSINTQuery.created_at.desc())
    
    result = await db.execute(query)
    queries = result.scalars().all()
    
    return [OSINTQueryResponse.model_validate(q) for q in queries]

@router.get("/results/{result_id}", response_model=OSINTResultResponse)
async def get_result(
    result_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get OSINT result by ID"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OSINTResult).where(OSINTResult.id == result_id)
    )
    osint_result = result.scalar_one_or_none()
    
    if not osint_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    return OSINTResultResponse.model_validate(osint_result)

@router.post("/ip-geolocation", response_model=OSINTResultResponse)
async def ip_geolocation(
    ip_address: str,
    hostname: bool = True,
    security: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get geolocation information for an IP address using ipstack"""
    from integrations.ipstack_api import IPStackAPIService
    
    service = IPStackAPIService()
    result_data = await service.get_ip_info(ip_address, hostname=hostname, security=security)
    
    # Create OSINT query and result
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ip_geolocation",
        query_params={"ip": ip_address, "hostname": hostname, "security": security},
        case_id=case_id
    )
    
    # Update result with ipstack data
    if result.get("result_id"):
        from models.osint import OSINTResult
        from sqlalchemy import select
        
        result_obj = await db.execute(
            select(OSINTResult).where(OSINTResult.id == result["result_id"])
        )
        result_obj = result_obj.scalar_one_or_none()
        if result_obj:
            result_obj.data = result_data
            await db.commit()
            return OSINTResultResponse.model_validate(result_obj)
    
    return OSINTResultResponse(
        id=0,
        query_id=0,
        data=result_data,
        status="completed" if result_data.get("status") == "success" else "failed",
        created_at=None,
        updated_at=None
    )

@router.post("/ip-geolocation/bulk", response_model=List[OSINTResultResponse])
async def ip_geolocation_bulk(
    ip_addresses: List[str],
    hostname: bool = True,
    security: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get geolocation information for multiple IP addresses"""
    from integrations.ipstack_api import IPStackAPIService
    
    service = IPStackAPIService()
    result_data = await service.get_bulk_info(ip_addresses, hostname=hostname, security=security)
    
    if result_data.get("status") != "success":
        raise HTTPException(
            status_code=400,
            detail=result_data.get("error", "Error obteniendo información de IPs")
        )
    
    results = []
    for ip_data in result_data.get("results", []):
        results.append(OSINTResultResponse(
            id=0,
            query_id=0,
            data=ip_data,
            status="completed",
            created_at=None,
            updated_at=None
        ))
    
    return results

@router.get("/tools", response_model=List[dict])
async def get_osint_tools(
    db: AsyncSession = Depends(get_db)
):
    """Get available OSINT tools"""
    return [
        {"id": "sherlock", "name": "Sherlock", "description": "Search social media accounts"},
        {"id": "recon-ng", "name": "Recon-ng", "description": "Domain and DNS analysis"},
        {"id": "google_news", "name": "Google News", "description": "News and trends"},
        {"id": "reddit", "name": "Reddit", "description": "Discussions and communities"},
        {"id": "github", "name": "GitHub", "description": "Repositories and code"},
        {"id": "theharvester", "name": "theHarvester", "description": "Email, subdomain, and employee collection"},
        {"id": "shodan", "name": "Shodan", "description": "Search devices connected to internet (Requiere cuenta de pago - No disponible actualmente)"},
        {"id": "wayback", "name": "Wayback Machine", "description": "Historical website snapshots"},
        {"id": "dns", "name": "DNS Lookup", "description": "DNS record queries"},
        {"id": "whois", "name": "WHOIS Lookup", "description": "Domain registration information"},
        {"id": "ip_geolocation", "name": "IP Geolocation", "description": "Geolocate IP addresses (country, city, coordinates, ISP)"},
    ]

@router.post("/collect", response_model=OSINTResultResponse)
async def collect_osint(
    request: OSINTQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Collect OSINT data"""
    osint_service = OSINTService(db)
    
    result = await osint_service.execute_query(
        query_type=request.query_type,
        query_params=request.query_params,
        case_id=request.case_id
    )
    
    return OSINTResultResponse.model_validate(result)

# ========== EnsembleData API Endpoints ==========

# TikTok Endpoints
@router.post("/ensembledata/tiktok/user-info", response_model=OSINTResultResponse)
async def ensembledata_tiktok_user_info(
    username: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get TikTok user information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_tiktok_user_info",
        query_params={"username": username},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/tiktok/user-posts", response_model=OSINTResultResponse)
async def ensembledata_tiktok_user_posts(
    username: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get TikTok user posts via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_tiktok_user_posts",
        query_params={"username": username, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/tiktok/hashtag-posts", response_model=OSINTResultResponse)
async def ensembledata_tiktok_hashtag_posts(
    hashtag: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get TikTok posts by hashtag via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_tiktok_hashtag_posts",
        query_params={"hashtag": hashtag, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/tiktok/keyword-posts", response_model=OSINTResultResponse)
async def ensembledata_tiktok_keyword_posts(
    keyword: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get TikTok posts by keyword via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_tiktok_keyword_posts",
        query_params={"keyword": keyword, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Instagram Endpoints
@router.post("/ensembledata/instagram/user-info", response_model=OSINTResultResponse)
async def ensembledata_instagram_user_info(
    username: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Instagram user information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_instagram_user_info",
        query_params={"username": username},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/instagram/user-posts", response_model=OSINTResultResponse)
async def ensembledata_instagram_user_posts(
    username: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Instagram user posts via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_instagram_user_posts",
        query_params={"username": username, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/instagram/hashtag-posts", response_model=OSINTResultResponse)
async def ensembledata_instagram_hashtag_posts(
    hashtag: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Instagram posts by hashtag via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_instagram_hashtag_posts",
        query_params={"hashtag": hashtag, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# YouTube Endpoints
@router.post("/ensembledata/youtube/channel-info", response_model=OSINTResultResponse)
async def ensembledata_youtube_channel_info(
    channel_id: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get YouTube channel information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_youtube_channel_info",
        query_params={"channel_id": channel_id},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/youtube/channel-videos", response_model=OSINTResultResponse)
async def ensembledata_youtube_channel_videos(
    channel_id: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get YouTube channel videos via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_youtube_channel_videos",
        query_params={"channel_id": channel_id, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/youtube/keyword-posts", response_model=OSINTResultResponse)
async def ensembledata_youtube_keyword_posts(
    keyword: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get YouTube videos by keyword via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_youtube_keyword_posts",
        query_params={"keyword": keyword, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Threads Endpoints
@router.post("/ensembledata/threads/user-info", response_model=OSINTResultResponse)
async def ensembledata_threads_user_info(
    username: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Threads user information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_threads_user_info",
        query_params={"username": username},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/threads/user-posts", response_model=OSINTResultResponse)
async def ensembledata_threads_user_posts(
    username: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Threads user posts via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_threads_user_posts",
        query_params={"username": username, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/threads/keyword-posts", response_model=OSINTResultResponse)
async def ensembledata_threads_keyword_posts(
    keyword: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Threads posts by keyword via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_threads_keyword_posts",
        query_params={"keyword": keyword, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Reddit Endpoints (Adicional)
@router.post("/ensembledata/reddit/subreddit-posts", response_model=OSINTResultResponse)
async def ensembledata_reddit_subreddit_posts(
    subreddit: str,
    count: int = 25,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Reddit subreddit posts via EnsembleData (adicional a Reddit API existente)"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_reddit_subreddit_posts",
        query_params={"subreddit": subreddit, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Twitter/X Endpoints
@router.post("/ensembledata/twitter/user-info", response_model=OSINTResultResponse)
async def ensembledata_twitter_user_info(
    username: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Twitter/X user information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_twitter_user_info",
        query_params={"username": username},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.post("/ensembledata/twitter/user-tweets", response_model=OSINTResultResponse)
async def ensembledata_twitter_user_tweets(
    username: str,
    count: int = 20,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Twitter/X user tweets via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_twitter_user_tweets",
        query_params={"username": username, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Twitch Endpoints
@router.post("/ensembledata/twitch/keyword-posts", response_model=OSINTResultResponse)
async def ensembledata_twitch_keyword_posts(
    keyword: str,
    count: int = 30,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Twitch posts by keyword via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_twitch_keyword_posts",
        query_params={"keyword": keyword, "count": count},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

# Snapchat Endpoints
@router.post("/ensembledata/snapchat/user-info", response_model=OSINTResultResponse)
async def ensembledata_snapchat_user_info(
    username: str,
    case_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Snapchat user information via EnsembleData"""
    osint_service = OSINTService(db)
    result = await osint_service.execute_query(
        query_type="ensembledata_snapchat_user_info",
        query_params={"username": username},
        case_id=case_id
    )
    return OSINTResultResponse.model_validate(result)

@router.get("/recent-searches", response_model=List[OSINTQueryResponse])
async def get_recent_searches(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get recent OSINT searches"""
    from sqlalchemy import select
    
    query = select(OSINTQuery)
    query = query.order_by(OSINTQuery.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    queries = result.scalars().all()
    
    return [OSINTQueryResponse.model_validate(q) for q in queries]

