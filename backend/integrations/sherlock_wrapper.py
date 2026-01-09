"""
Sherlock wrapper - Search for usernames across social media platforms
"""
import asyncio
import json
from typing import Dict, Any
from app.config import settings

class SherlockWrapper:
    def __init__(self):
        self.sherlock_path = settings.SHERLOCK_PATH
    
    async def search(self, username: str) -> Dict[str, Any]:
        """Search for username across platforms"""
        try:
            # Execute sherlock asynchronously
            process = await asyncio.create_subprocess_exec(
                self.sherlock_path,
                username,
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                try:
                    results = json.loads(stdout.decode())
                    return {
                        "username": username,
                        "platforms_found": len(results),
                        "results": results,
                        "status": "success"
                    }
                except json.JSONDecodeError:
                    return {
                        "username": username,
                        "platforms_found": 0,
                        "results": {},
                        "status": "success",
                        "raw_output": stdout.decode()
                    }
            else:
                return {
                    "username": username,
                    "status": "error",
                    "error": stderr.decode()
                }
        except Exception as e:
            return {
                "username": username,
                "status": "error",
                "error": str(e)
            }








