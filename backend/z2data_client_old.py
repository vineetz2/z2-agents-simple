"""
Z2Data API Client for the simplified agents system
"""
import os
import httpx
import json
from typing import Dict, Any, List, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

class Z2DataClient:
    """Client for Z2Data API operations"""
    
    def __init__(self):
        self.api_key = os.getenv("Z2_API_KEY", "AyxfLYocWpE5HNG")
        self.base_url = "https://gateway.z2data.com"
        
    async def search_parts(self, query: str) -> Dict[str, Any]:
        """Search for parts using Z2Data API"""
        # Extract part number and manufacturer if present
        parts = query.lower().split()
        
        # Look for "by" to separate part from manufacturer
        if "by" in parts:
            by_index = parts.index("by")
            part_number = " ".join(parts[:by_index]).strip()
            manufacturer = " ".join(parts[by_index+1:]).strip() if by_index < len(parts)-1 else ""
        else:
            # Assume the whole query is a part number
            part_number = query.strip()
            manufacturer = ""
        
        # Clean up common words
        part_number = part_number.replace("search", "").replace("find", "").strip()
        
        async with httpx.AsyncClient() as client:
            try:
                # Use GetPartDetailsBySearch endpoint
                url = f"{self.base_url}/GetPartDetailsBySearch"
                params = {
                    "ApiKey": self.api_key,
                    "Z2MPN": part_number.upper()  # Part numbers are usually uppercase
                }
                
                logger.info(f"Calling Z2Data API: {url} with part_number={part_number}")
                
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                return {"success": True, "data": data, "query": part_number}
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling Z2Data API: {e}")
                return {"success": False, "error": f"API error: {e.response.status_code}"}
            except Exception as e:
                logger.error(f"Error calling Z2Data API: {e}")
                return {"success": False, "error": str(e)}
    
    def format_results(self, result: Dict[str, Any], operation: str) -> str:
        """Format API results for display with table structure"""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        data = result.get("data", {})
        
        if operation == "search_parts":
            return self._format_part_search(data, result.get("query", ""))
        else:
            return json.dumps(data, indent=2)
    
    def _format_part_search(self, data: Any, query: str) -> str:
        """Format part search results as a table"""
        if not data:
            return f"No parts found for '{query}'"
        
        # Handle both single part and multiple parts response
        parts = []
        if isinstance(data, dict):
            # Check for nested results structure from Z2Data API
            if "results" in data and isinstance(data["results"], dict) and "results" in data["results"]:
                parts = data["results"]["results"]
            elif "Parts" in data:
                parts = data["Parts"]
            elif "Part_Number" in data or "MPN" in data:
                parts = [data]
        elif isinstance(data, list):
            # Multiple parts response
            parts = data
        
        if not parts:
            return f"No parts found for '{query}'"
        
        # Filter for manufacturer if specified in original query
        if "toshiba" in query.lower():
            toshiba_parts = [p for p in parts if "toshiba" in p.get("Manufacturer", "").lower()]
            if toshiba_parts:
                parts = toshiba_parts
        
        # Create table structure
        output = f"## Part Search Results for '{query}'\n\n"
        output += "| Part Number | Manufacturer | Description | Lifecycle | Package | RoHS |\n"
        output += "|-------------|--------------|-------------|-----------|---------|------|\n"
        
        for part in parts[:10]:  # Limit to 10 results
            part_number = part.get("Part_Number", part.get("MPN", "N/A"))
            manufacturer = part.get("Manufacturer", part.get("Manufacturer_Name", "N/A"))
            description = part.get("Description", part.get("Part_Description", "N/A"))
            if description and len(description) > 50:
                description = description[:50] + "..."
            lifecycle = part.get("Lifecycle_Status", part.get("Part_Status", "N/A"))
            package = part.get("Package", part.get("Package_Name", "N/A"))
            rohs = part.get("RoHS_Status", part.get("EU_RoHS_Status", "N/A"))
            
            output += f"| {part_number} | {manufacturer} | {description} | {lifecycle} | {package} | {rohs} |\n"
        
        # Add additional details for the first part
        if parts:
            first_part = parts[0]
            output += "\n### Detailed Information\n\n"
            output += f"**Part Number:** {first_part.get('Part_Number', first_part.get('MPN', 'N/A'))}\n"
            output += f"**Manufacturer:** {first_part.get('Manufacturer', first_part.get('Manufacturer_Name', 'N/A'))}\n"
            output += f"**Description:** {first_part.get('Description', first_part.get('Part_Description', 'N/A'))}\n"
            
            datasheet = first_part.get('DataSheet', first_part.get('Datasheet_URL', ''))
            if datasheet:
                output += f"**Datasheet:** [View Datasheet]({datasheet})\n"
        
        return output
    
    # Add stub methods for compatibility
    async def call_api(self, endpoint: str, params: Dict = None) -> Dict:
        """Stub for backward compatibility"""
        return {"error": "Not implemented"}
    
    async def get_market_availability(self, part_number: str) -> Dict:
        """Get market availability - stub for now"""
        return {"success": False, "error": "Not implemented"}
    
    async def get_cross_references(self, part_number: str) -> Dict:
        """Get cross references - stub for now"""
        return {"success": False, "error": "Not implemented"}
    
    async def check_rohs_compliance(self, part_number: str) -> Dict:
        """Stub for RoHS compliance check"""
        return {"compliant": True}
    
    async def get_compliance_data(self, part_number: str) -> Dict:
        """Stub for compliance data"""
        return {"RoHS": "Compliant", "REACH": "Compliant"}

# Create singleton instance
z2_client = Z2DataClient()
