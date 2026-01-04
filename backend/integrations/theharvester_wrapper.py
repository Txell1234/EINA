"""
theHarvester wrapper - Email, subdomain, and employee name collection
"""
import asyncio
import subprocess
import json
from typing import Dict, Any, List
from pathlib import Path

class TheHarvesterWrapper:
    def __init__(self):
        self.harvester_path = "theHarvester"  # Assumes theHarvester is in PATH
    
    async def search(
        self,
        domain: str,
        sources: List[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """Search for emails, subdomains, and employee names"""
        try:
            if sources is None:
                sources = ["google", "bing", "yahoo"]
            
            # Build command
            cmd = [
                self.harvester_path,
                "-d", domain,
                "-b", ",".join(sources),
                "-l", str(limit),
                "-f", "json"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                try:
                    results = json.loads(stdout.decode())
                    return {
                        "domain": domain,
                        "status": "success",
                        "emails": results.get("emails", []),
                        "hosts": results.get("hosts", []),
                        "ips": results.get("ips", []),
                        "shodan": results.get("shodan", []),
                        "total_results": len(results.get("emails", [])) + len(results.get("hosts", []))
                    }
                except json.JSONDecodeError:
                    # Parse text output if JSON fails
                    output = stdout.decode()
                    return {
                        "domain": domain,
                        "status": "success",
                        "raw_output": output,
                        "emails": [],
                        "hosts": [],
                        "ips": []
                    }
            else:
                return {
                    "domain": domain,
                    "status": "error",
                    "error": stderr.decode()
                }
        except Exception as e:
            return {
                "domain": domain,
                "status": "error",
                "error": str(e)
            }









