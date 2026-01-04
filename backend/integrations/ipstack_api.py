"""
ipstack API integration - IP geolocation service
"""
import httpx
from typing import Dict, Any, Optional, List
from app.config import settings

class IPStackAPIService:
    def __init__(self):
        self.base_url = "http://api.ipstack.com"
        self.api_key = getattr(settings, "IPSTACK_API_KEY", "").strip()
    
    async def get_ip_info(
        self,
        ip_address: str,
        fields: Optional[str] = None,
        hostname: bool = True,
        security: bool = True,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Get geolocation information for an IP address"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-ipstack-api-key":
            return {
                "status": "error",
                "error": "IPSTACK_API_KEY no está configurada. Obtén una API key gratuita en https://ipstack.com/",
                "message": "API key no configurada",
                "info": "Plan gratuito: 10,000 requests/mes"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "access_key": self.api_key,
                    "hostname": 1 if hostname else 0,
                    "security": 1 if security else 0,
                    "language": language
                }
                
                if fields:
                    params["fields"] = fields
                
                response = await client.get(
                    f"{self.base_url}/{ip_address}",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors
                if "error" in data:
                    return {
                        "status": "error",
                        "error": data.get("error", {}).get("info", "Unknown error"),
                        "code": data.get("error", {}).get("code"),
                        "message": "Error de API"
                    }
                
                # Format response
                location = data.get("location", {})
                return {
                    "status": "success",
                    "ip": data.get("ip", ip_address),
                    "type": data.get("type", "unknown"),
                    "continent_code": data.get("continent_code", ""),
                    "continent_name": data.get("continent_name", ""),
                    "country_code": data.get("country_code", ""),
                    "country_name": data.get("country_name", ""),
                    "region_code": data.get("region_code", ""),
                    "region_name": data.get("region_name", ""),
                    "city": data.get("city", ""),
                    "zip": data.get("zip", ""),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "location": {
                        "geoname_id": location.get("geoname_id"),
                        "capital": location.get("capital", ""),
                        "languages": location.get("languages", []),
                        "country_flag": location.get("country_flag", ""),
                        "country_flag_emoji": location.get("country_flag_emoji", ""),
                        "country_flag_emoji_unicode": location.get("country_flag_emoji_unicode", ""),
                        "calling_code": location.get("calling_code", ""),
                        "is_eu": location.get("is_eu", False)
                    },
                    "time_zone": data.get("time_zone", {}),
                    "currency": data.get("currency", {}),
                    "connection": data.get("connection", {}),
                    "security": data.get("security", {}) if security else None,
                    "hostname": data.get("hostname", "") if hostname else None
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    return {
                        "status": "error",
                        "error": "API key inválida o límite excedido. Verifica tu IPSTACK_API_KEY en el archivo .env",
                        "message": "Error de autenticación"
                    }
                elif e.response.status_code == 429:
                    return {
                        "status": "error",
                        "error": "Límite de peticiones excedido. Plan gratuito: 10,000 requests/mes",
                        "message": "Límite excedido"
                    }
                return {
                    "status": "error",
                    "error": f"HTTP error: {e.response.status_code}",
                    "message": "Error HTTP"
                }
            except httpx.RequestError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "message": "Error de conexión"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error inesperado: {str(e)}",
                    "message": "Error inesperado"
                }
    
    async def get_bulk_info(
        self,
        ip_addresses: List[str],
        fields: Optional[str] = None,
        hostname: bool = True,
        security: bool = True,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Get geolocation information for multiple IP addresses"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-ipstack-api-key":
            return {
                "status": "error",
                "error": "IPSTACK_API_KEY no está configurada",
                "message": "API key no configurada"
            }
        
        # Join IPs with comma
        ips_string = ",".join(ip_addresses[:50])  # Limit to 50 IPs per request
        
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "access_key": self.api_key,
                    "hostname": 1 if hostname else 0,
                    "security": 1 if security else 0,
                    "language": language
                }
                
                if fields:
                    params["fields"] = fields
                
                response = await client.get(
                    f"{self.base_url}/{ips_string}",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    return {
                        "status": "error",
                        "error": data.get("error", {}).get("info", "Unknown error"),
                        "message": "Error de API"
                    }
                
                # Format bulk response
                results = []
                if isinstance(data, list):
                    for item in data:
                        results.append(self._format_ip_data(item))
                else:
                    # Single result returned as dict
                    results.append(self._format_ip_data(data))
                
                return {
                    "status": "success",
                    "count": len(results),
                    "results": results
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error obteniendo información"
                }
    
    async def get_requester_info(
        self,
        fields: Optional[str] = None,
        hostname: bool = True,
        security: bool = True,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Get geolocation information for the requester's IP address"""
        return await self.get_ip_info("check", fields, hostname, security, language)
    
    def _format_ip_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format IP data to standard structure"""
        location = data.get("location", {})
        return {
            "ip": data.get("ip", ""),
            "type": data.get("type", "unknown"),
            "continent_code": data.get("continent_code", ""),
            "continent_name": data.get("continent_name", ""),
            "country_code": data.get("country_code", ""),
            "country_name": data.get("country_name", ""),
            "region_code": data.get("region_code", ""),
            "region_name": data.get("region_name", ""),
            "city": data.get("city", ""),
            "zip": data.get("zip", ""),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "location": {
                "geoname_id": location.get("geoname_id"),
                "capital": location.get("capital", ""),
                "languages": location.get("languages", []),
                "country_flag": location.get("country_flag", ""),
                "country_flag_emoji": location.get("country_flag_emoji", ""),
                "calling_code": location.get("calling_code", ""),
                "is_eu": location.get("is_eu", False)
            },
            "time_zone": data.get("time_zone", {}),
            "currency": data.get("currency", {}),
            "connection": data.get("connection", {}),
            "security": data.get("security", {}),
            "hostname": data.get("hostname", "")
        }









