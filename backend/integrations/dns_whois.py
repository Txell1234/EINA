"""
DNS and Whois lookup integration
"""
import asyncio
import socket
import httpx
from typing import Dict, Any, Optional, List

try:
    import dns.resolver
    import dns.reversename
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

class DNSWhoisService:
    def __init__(self):
        pass
    
    async def dns_lookup(
        self,
        domain: str,
        record_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform DNS lookups for various record types"""
        if not DNS_AVAILABLE:
            return {
                "domain": domain,
                "status": "error",
                "error": "dnspython not installed. Install with: pip install dnspython",
                "records": {}
            }
        
        if record_types is None:
            record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]
        
        results = {}
        
        try:
            for record_type in record_types:
                try:
                    answers = dns.resolver.resolve(domain, record_type)
                    results[record_type] = [str(rdata) for rdata in answers]
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                    results[record_type] = []
                except Exception as e:
                    results[record_type] = []
                    results[f"{record_type}_error"] = str(e)
            
            return {
                "domain": domain,
                "status": "success",
                "records": results
            }
        except Exception as e:
            return {
                "domain": domain,
                "status": "error",
                "error": str(e),
                "records": {}
            }
    
    async def reverse_dns(self, ip: str) -> Dict[str, Any]:
        """Perform reverse DNS lookup"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return {
                "ip": ip,
                "status": "success",
                "hostname": hostname
            }
        except Exception as e:
            return {
                "ip": ip,
                "status": "error",
                "error": str(e)
            }
    
    async def whois_lookup(self, domain: str) -> Dict[str, Any]:
        """Perform WHOIS lookup"""
        async with httpx.AsyncClient() as client:
            try:
                # Use a WHOIS API service
                response = await client.get(
                    f"https://whoisjson.com/api/v1/whois",
                    params={"domain": domain},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "domain": domain,
                        "status": "success",
                        "whois": data
                    }
                else:
                    # Fallback to python-whois if available
                    try:
                        import whois
                        w = whois.whois(domain)
                        return {
                            "domain": domain,
                            "status": "success",
                            "whois": {
                                "registrar": w.registrar,
                                "creation_date": str(w.creation_date) if w.creation_date else None,
                                "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                                "name_servers": w.name_servers
                            }
                        }
                    except ImportError:
                        return {
                            "domain": domain,
                            "status": "error",
                            "error": "WHOIS lookup not available - install python-whois or configure API"
                        }
            except Exception as e:
                return {
                    "domain": domain,
                    "status": "error",
                    "error": str(e)
                }

