"""
Integration router - Análisis cross-módulo
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.config import settings
from services.integration_service import IntegrationService
from datetime import datetime, timedelta
from pathlib import Path
import os
import shutil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integration", tags=["Integration"])

# Cache for API status (TTL: 60 seconds)
_status_cache: Optional[Dict[str, Any]] = None
_status_cache_timestamp: Optional[datetime] = None
_STATUS_CACHE_TTL = 60  # seconds

def _get_api_status() -> Dict[str, Any]:
    """
    Get API status information.
    This function is cached for 60 seconds to reduce overhead.
    """
    global _status_cache, _status_cache_timestamp
    
    # Check if cache is valid
    if _status_cache and _status_cache_timestamp:
        cache_age = (datetime.now() - _status_cache_timestamp).total_seconds()
        if cache_age < _STATUS_CACHE_TTL:
            return _status_cache
    
    # Cache expired or doesn't exist, rebuild
    from app.config import settings

    def _is_tool_available(executable_path: str) -> bool:
        if not executable_path:
            return False
        if Path(executable_path).is_file():
            return os.access(executable_path, os.X_OK)
        return shutil.which(executable_path) is not None
    
    status_info = {
        "ai": {
            "openai": {
                "configured": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and settings.OPENAI_API_KEY != "sk-proj-TU_CLAVE_API_AQUI"),
                "model": settings.OPENAI_MODEL,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                "status": "configured" if (settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and settings.OPENAI_API_KEY != "sk-proj-TU_CLAVE_API_AQUI") else "not_configured"
            }
        },
        "osint_apis": {
            "news_api": {
                "configured": bool(settings.NEWS_API_KEY and settings.NEWS_API_KEY.strip() and settings.NEWS_API_KEY != "your-news-api-key"),
                "status": "configured" if (settings.NEWS_API_KEY and settings.NEWS_API_KEY.strip() and settings.NEWS_API_KEY != "your-news-api-key") else "not_configured"
            },
            "github": {
                "configured": bool(settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip() and settings.GITHUB_TOKEN != "your-github-token"),
                "status": "configured" if (settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip() and settings.GITHUB_TOKEN != "your-github-token") else "not_configured"
            },
            "shodan": {
                "configured": bool(settings.SHODAN_API_KEY and settings.SHODAN_API_KEY.strip() and settings.SHODAN_API_KEY != "your-shodan-api-key"),
                "status": "configured" if (settings.SHODAN_API_KEY and settings.SHODAN_API_KEY.strip() and settings.SHODAN_API_KEY != "your-shodan-api-key") else "not_configured",
                "note": "Requires paid account"
            },
            "ensembledata": {
                "configured": bool(settings.ENSEMBLEDATA_API_KEY and settings.ENSEMBLEDATA_API_KEY.strip() and settings.ENSEMBLEDATA_API_KEY != "your-ensembledata-api-key"),
                "status": "configured" if (settings.ENSEMBLEDATA_API_KEY and settings.ENSEMBLEDATA_API_KEY.strip() and settings.ENSEMBLEDATA_API_KEY != "your-ensembledata-api-key") else "not_configured",
                "note": "Endpoint implementation pending - requires official API documentation"
            },
            "ipstack": {
                "configured": bool(settings.IPSTACK_API_KEY and settings.IPSTACK_API_KEY.strip() and settings.IPSTACK_API_KEY != "your-ipstack-api-key"),
                "status": "configured" if (settings.IPSTACK_API_KEY and settings.IPSTACK_API_KEY.strip() and settings.IPSTACK_API_KEY != "your-ipstack-api-key") else "not_configured"
            }
        },
        "financial_apis": {
            "alphavantage": {
                "configured": bool(settings.ALPHAVANTAGE_API_KEY and settings.ALPHAVANTAGE_API_KEY.strip() and settings.ALPHAVANTAGE_API_KEY != "your-alphavantage-api-key"),
                "status": "configured" if (settings.ALPHAVANTAGE_API_KEY and settings.ALPHAVANTAGE_API_KEY.strip() and settings.ALPHAVANTAGE_API_KEY != "your-alphavantage-api-key") else "not_configured"
            },
            "finnhub": {
                "configured": bool(settings.FINNHUB_API_KEY and settings.FINNHUB_API_KEY.strip() and settings.FINNHUB_API_KEY != "your-finnhub-api-key"),
                "status": "configured" if (settings.FINNHUB_API_KEY and settings.FINNHUB_API_KEY.strip() and settings.FINNHUB_API_KEY != "your-finnhub-api-key") else "not_configured"
            },
            "financial_modeling_prep": {
                "configured": bool(getattr(settings, "FINANCIAL_MODELING_PREP_API_KEY", "") and settings.FINANCIAL_MODELING_PREP_API_KEY.strip() and settings.FINANCIAL_MODELING_PREP_API_KEY != "your-fmp-api-key"),
                "status": "configured" if (getattr(settings, "FINANCIAL_MODELING_PREP_API_KEY", "") and settings.FINANCIAL_MODELING_PREP_API_KEY.strip() and settings.FINANCIAL_MODELING_PREP_API_KEY != "your-fmp-api-key") else "not_configured"
            }
        },
        "geopolitical_apis": {
            "permutable": {
                "configured": bool(settings.PERMUTABLE_API_KEY and settings.PERMUTABLE_API_KEY.strip() and settings.PERMUTABLE_API_KEY != "your-permutable-api-key"),
                "status": "configured" if (settings.PERMUTABLE_API_KEY and settings.PERMUTABLE_API_KEY.strip() and settings.PERMUTABLE_API_KEY != "your-permutable-api-key") else "not_configured",
                "note": "Endpoint to be confirmed"
            }
        },
        "external_tools": {
            "sherlock": {
                "configured": _is_tool_available(settings.SHERLOCK_PATH),
                "status": "configured" if _is_tool_available(settings.SHERLOCK_PATH) else "not_configured",
                "path": settings.SHERLOCK_PATH,
                "note": "Requires installation in PATH. Configure SHERLOCK_PATH in .env if needed."
            },
            "recon-ng": {
                "configured": _is_tool_available(settings.RECONNG_PATH),
                "status": "configured" if _is_tool_available(settings.RECONNG_PATH) else "not_configured",
                "path": settings.RECONNG_PATH,
                "note": "Requires installation in PATH. Configure RECONNG_PATH in .env if needed."
            },
            "theharvester": {
                "configured": _is_tool_available(settings.THEHARVESTER_PATH),
                "status": "configured" if _is_tool_available(settings.THEHARVESTER_PATH) else "not_configured",
                "path": settings.THEHARVESTER_PATH,
                "note": "Requires installation in PATH"
            }
        },
        "summary": {
            "total_apis": 0,
            "configured_apis": 0,
            "not_configured_apis": 0,
            "critical_apis": {
                "openai": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and settings.OPENAI_API_KEY != "sk-proj-TU_CLAVE_API_AQUI")
            },
            "alerts": []
        }
    }
    
    # Calculate summary
    all_apis = []
    for category in ["osint_apis", "financial_apis", "geopolitical_apis"]:
        for api_name, api_info in status_info[category].items():
            all_apis.append(api_info)
    
    status_info["summary"]["total_apis"] = len(all_apis)
    status_info["summary"]["configured_apis"] = sum(1 for api in all_apis if api.get("configured", False))
    status_info["summary"]["not_configured_apis"] = status_info["summary"]["total_apis"] - status_info["summary"]["configured_apis"]
    
    # Generate alerts for critical APIs
    alerts = []
    if not status_info["summary"]["critical_apis"]["openai"]:
        alerts.append({
            "level": "critical",
            "api": "openai",
            "message": "OpenAI API key is not configured. AI analysis features will use fallback mode.",
            "impact": "All AI-powered features (analysis, classification, predictions) will be limited."
        })
    
    status_info["summary"]["alerts"] = alerts
    
    # Update cache
    _status_cache = status_info
    _status_cache_timestamp = datetime.now()
    
    return status_info

@router.get("/status")
async def get_integration_status():
    """
    Diagnóstico de estado de integraciones y API keys.
    Retorna el estado de configuración de todas las APIs externas.
    
    El resultado se cachea durante 60 segundos para mejorar el rendimiento.
    """
    status_info = _get_api_status()
    status_info["cache_info"] = {
        "cached": _status_cache_timestamp is not None,
        "cache_age_seconds": (datetime.now() - _status_cache_timestamp).total_seconds() if _status_cache_timestamp else None,
        "cache_ttl_seconds": _STATUS_CACHE_TTL
    }
    return status_info

@router.post("/status/refresh")
async def refresh_integration_status():
    """
    Fuerza la actualización del cache del estado de integraciones.
    Útil para testing o cuando se actualizan las configuraciones.
    """
    global _status_cache, _status_cache_timestamp
    _status_cache = None
    _status_cache_timestamp = None
    status_info = _get_api_status()
    return {
        "message": "Cache refreshed",
        "status": status_info
    }

@router.post("/comprehensive-analysis")
async def comprehensive_analysis(
    case_id: int = Query(...),
    entity_name: Optional[str] = Query(None),
    countries: Optional[str] = Query(None, description="Comma-separated list of countries"),
    db: AsyncSession = Depends(get_db)
):
    """Genera análisis integral combinando todos los módulos"""
    try:
        service = IntegrationService(db)
        country_list = [c.strip() for c in countries.split(",")] if countries else None
        
        result = await service.generate_comprehensive_risk_assessment(
            case_id=case_id,
            entity_name=entity_name,
            countries=country_list
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating comprehensive analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analysis: {str(e)}"
        )

@router.get("/geopolitical-investment-impact")
async def get_geopolitical_investment_impact(
    case_id: int = Query(...),
    countries: str = Query(..., description="Comma-separated list of countries"),
    investment_type: str = Query("general", description="general, long_term, regulatory_sensitive"),
    db: AsyncSession = Depends(get_db)
):
    """Analiza impacto geopolítico en inversiones"""
    try:
        service = IntegrationService(db)
        country_list = [c.strip() for c in countries.split(",")]
        
        result = await service.analyze_geopolitical_impact_on_investments(
            case_id=case_id,
            countries=country_list,
            investment_type=investment_type
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing geopolitical investment impact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing impact: {str(e)}"
        )

@router.get("/reputation-geopolitical")
async def get_reputation_geopolitical_correlation(
    entity_name: str = Query(...),
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Correlaciona reputación con eventos geopolíticos"""
    try:
        service = IntegrationService(db)
        result = await service.assess_reputation_impact_of_geopolitical_events(
            entity_name=entity_name,
            case_id=case_id
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error correlating reputation with geopolitics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error correlating: {str(e)}"
        )

@router.get("/public-affairs-reputation")
async def get_public_affairs_reputation_correlation(
    entity_name: str = Query(...),
    case_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Correlaciona asuntos públicos con reputación"""
    try:
        service = IntegrationService(db)
        result = await service.correlate_public_affairs_with_reputation(
            entity_name=entity_name,
            case_id=case_id
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error correlating public affairs with reputation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error correlating: {str(e)}"
        )
