"""
Recon-ng wrapper - Framework modular de reconocimiento web
"""
import asyncio
from typing import Dict, Any
from app.config import settings

class ReconNGWrapper:
    def __init__(self):
        self.reconng_path = settings.RECONNG_PATH
    
    async def execute_module(
        self,
        module: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute recon-ng module"""
        try:
            # Build command
            cmd = [self.reconng_path, "-m", module]
            
            # Add parameters
            for key, value in params.items():
                cmd.extend(["-o", f"{key}={value}"])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "module": module,
                    "status": "success",
                    "output": stdout.decode(),
                    "params": params
                }
            else:
                return {
                    "module": module,
                    "status": "error",
                    "error": stderr.decode()
                }
        except Exception as e:
            return {
                "module": module,
                "status": "error",
                "error": str(e)
            }








