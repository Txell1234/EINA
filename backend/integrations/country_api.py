"""
REST Countries API integration - Free country data
No API key required
"""
import httpx
from typing import Dict, Any, Optional, List

class CountryAPIService:
    def __init__(self):
        self.base_url = "https://restcountries.com/v3.1"
    
    async def get_country(self, country_name: str) -> Dict[str, Any]:
        """Get country information by name"""
        async with httpx.AsyncClient() as client:
            try:
                # Try by name first
                response = await client.get(
                    f"{self.base_url}/name/{country_name}",
                    params={"fullText": "false"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    country = data[0]
                    return {
                        "status": "success",
                        "country": self._format_country_data(country)
                    }
                
                return {
                    "status": "error",
                    "error": "Country not found",
                    "query": country_name
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {
                        "status": "error",
                        "error": "Country not found",
                        "query": country_name
                    }
                return {
                    "status": "error",
                    "error": f"HTTP error: {e.response.status_code}",
                    "query": country_name
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "query": country_name
                }
    
    async def get_country_by_code(self, code: str) -> Dict[str, Any]:
        """Get country information by ISO code (2 or 3 letters)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/alpha/{code}",
                    timeout=10.0
                )
                response.raise_for_status()
                country = response.json()
                
                return {
                    "status": "success",
                    "country": self._format_country_data(country)
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {
                        "status": "error",
                        "error": "Country code not found",
                        "code": code
                    }
                return {
                    "status": "error",
                    "error": f"HTTP error: {e.response.status_code}",
                    "code": code
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "code": code
                }
    
    async def search_countries(self, query: str) -> Dict[str, Any]:
        """Search countries by name"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/name/{query}",
                    timeout=10.0
                )
                response.raise_for_status()
                countries = response.json()
                
                if isinstance(countries, list):
                    return {
                        "status": "success",
                        "count": len(countries),
                        "countries": [self._format_country_data(c) for c in countries]
                    }
                
                return {
                    "status": "error",
                    "error": "No countries found",
                    "query": query
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "query": query
                }
    
    def _format_country_data(self, country: Dict[str, Any]) -> Dict[str, Any]:
        """Format country data to a standard structure"""
        name = country.get("name", {})
        capital = country.get("capital", [])
        currencies = country.get("currencies", {})
        languages = country.get("languages", {})
        region = country.get("region", "")
        subregion = country.get("subregion", "")
        population = country.get("population", 0)
        area = country.get("area", 0)
        latlng = country.get("latlng", [None, None])
        
        return {
            "name": name.get("common", ""),
            "official_name": name.get("official", ""),
            "capital": capital[0] if capital else None,
            "region": region,
            "subregion": subregion,
            "population": population,
            "area": area,
            "latitude": latlng[0] if latlng else None,
            "longitude": latlng[1] if latlng else None,
            "currencies": list(currencies.keys()) if currencies else [],
            "languages": list(languages.values()) if languages else [],
            "cca2": country.get("cca2", ""),  # ISO 3166-1 alpha-2
            "cca3": country.get("cca3", ""),  # ISO 3166-1 alpha-3
            "flag": country.get("flag", ""),
            "maps": country.get("maps", {}),
            "timezones": country.get("timezones", [])
        }









