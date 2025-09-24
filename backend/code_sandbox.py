"""
Simplified Code Execution Sandbox
Uses subprocess with timeout for basic safety (not production-ready)
In production, use WebAssembly or container-based sandboxing
"""
import subprocess
import tempfile
import os
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SimpleSandbox:
    """Simple code execution sandbox with basic safety measures"""
    
    def __init__(self):
        self.timeout = 10  # 10 second timeout
        self.max_output_size = 10000  # Max 10KB output
        
    async def execute(self, code: str) -> Dict[str, Any]:
        """Execute Python code in a subprocess with timeout"""
        
        # Basic safety checks
        dangerous_patterns = [
            'import os',
            'import subprocess', 
            'import sys',
            '__import__',
            'eval(',
            'exec(',
            'compile(',
            'open(',
            'file(',
            'input(',
            'raw_input',
            'globals(',
            'locals(',
            'vars(',
            'dir(',
            'getattr(',
            'setattr(',
            'delattr(',
            'type(',
            'help(',
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                return {
                    "success": False,
                    "error": f"Code contains potentially unsafe operation: {pattern}",
                    "output": ""
                }
        
        # Add safe imports
        safe_code = """
import math
import random
import datetime
import json
import statistics

# User code below
""" + code
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(safe_code)
            temp_file = f.name
        
        try:
            # Run in subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                output = stdout.decode('utf-8')
                error = stderr.decode('utf-8')
                
                # Limit output size
                if len(output) > self.max_output_size:
                    output = output[:self.max_output_size] + "\n... (output truncated)"
                
                if error:
                    return {
                        "success": False,
                        "error": error,
                        "output": output
                    }
                
                return {
                    "success": True,
                    "output": output,
                    "error": ""
                }
                
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Code execution timed out after {self.timeout} seconds",
                    "output": ""
                }
                
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

class ProductionSandbox:
    """
    Placeholder for production-ready sandbox using WebAssembly or containers
    This would use Pyodide, Docker, or other secure isolation
    """
    
    def __init__(self):
        self.available = False
        
        # Try to import pyodide or other sandbox
        try:
            # from pyodide import create_proxy, run_python
            # self.available = True
            pass
        except ImportError:
            logger.info("Production sandbox not available, using simple sandbox")
    
    async def execute(self, code: str) -> Dict[str, Any]:
        """Execute code in production sandbox"""
        if not self.available:
            # Fall back to simple sandbox
            simple = SimpleSandbox()
            return await simple.execute(code)
        
        # Production implementation would go here
        return {
            "success": False,
            "error": "Production sandbox not implemented",
            "output": ""
        }

# Global sandbox instance
sandbox = SimpleSandbox()  # Use ProductionSandbox() when available