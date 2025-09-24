"""
Z2Data API Client - Comprehensive implementation for all Z2Data endpoints
"""
import os
import httpx
import json
from typing import Dict, Any, List, Optional
from urllib.parse import quote
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Z2DataClient:
    """Comprehensive client for all Z2Data API operations"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("Z2_API_KEY", "AyxfLYocWpE5HNG")
        self.base_url = "https://gateway.z2data.com"

    # ==================== PART OPERATIONS ====================

    async def validate_part(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Validate a part and get its part ID using GetValidationPart endpoint"""
        if not part_number:
            return {"success": False, "error": "Part number is required"}

        validation_payload = {
            "rows": [
                {
                    "rowNumber": 0,
                    "mpn": part_number,
                    "man": manufacturer or ""
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/GetValidationPart?ApiKey={self.api_key}",
                    json=validation_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                if data.get("results") and len(data["results"]) > 0:
                    part_info = data["results"][0]
                    part_id = part_info.get("z2PartData", {}).get("partID", 0)

                    # Check if we actually found a valid part
                    if part_id and part_id > 0:
                        return {
                            "success": True,
                            "part_id": part_id,
                            "validated_mpn": part_info.get("mpn"),
                            "validated_manufacturer": part_info.get("z2PartData", {}).get("companyName"),
                            "raw_data": part_info
                        }
                    else:
                        # Part validation returned but with no valid match
                        match_status = part_info.get("matchStatus", "No Match")
                        match_reason = part_info.get("matchReason", "")
                        return {
                            "success": False,
                            "error": f"Part '{part_number}' not found in Z2Data database",
                            "match_status": match_status,
                            "match_reason": match_reason,
                            "suggestion": f"Reason: {match_reason}" if match_reason else "Try adding manufacturer name"
                        }
                else:
                    return {"success": False, "error": f"Part {part_number} not found"}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error validating part: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error validating part: {e}")
            return {"success": False, "error": str(e)}

    async def get_part_details(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Get comprehensive part details using two-step process"""
        # Step 1: Validate and get part ID
        validation_result = await self.validate_part(part_number, manufacturer)
        if not validation_result.get("success"):
            return validation_result

        part_id = validation_result.get("part_id")
        if not part_id:
            return {"success": False, "error": "Could not obtain part ID"}

        # Step 2: Get full details
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetPartDetailsBypartID?ApiKey={self.api_key}&partId={part_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got part details for {part_number} with sections: {list(data.get('results', {}).keys())}")

                return {
                    "type": "part_details",
                    "success": True,
                    "data": data.get("results", {}),
                    "part_number": part_number,
                    "manufacturer": manufacturer
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting part details: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting part details: {e}")
            return {"success": False, "error": str(e)}

    async def search_parts(self, query: str, manufacturer: str = None) -> Dict[str, Any]:
        """Search for parts using appropriate method based on whether manufacturer is provided"""
        import re
        from urllib.parse import quote

        # Extract part number from query (handle various formats)
        # Examples: "search BAV99", "BAV99", "search for LM317"
        cleaned_query = re.sub(r'(search|for|find)\s+', '', query, flags=re.IGNORECASE)
        cleaned_query = cleaned_query.strip()

        # Try to extract a part number (alphanumeric with optional dashes/dots)
        part_match = re.search(r'([A-Z0-9][A-Z0-9\-\.]+)', cleaned_query, re.IGNORECASE)
        if part_match:
            part_number = part_match.group(1)
        else:
            part_number = cleaned_query

        logger.info(f"Searching for part: {part_number} from query: {query}, manufacturer: {manufacturer}")

        # If we have a manufacturer, use the two-step process
        if manufacturer:
            result = await self.get_part_details(part_number, manufacturer)
            if result.get("success"):
                return {
                    "type": "search_results",
                    "success": True,
                    "data": result.get("data"),
                    "query": query,
                    "part_found": part_number
                }
            else:
                return {
                    "type": "search_results",
                    "success": False,
                    "error": result.get("error", f"No parts found for '{part_number}'"),
                    "query": query
                }

        # No manufacturer - use GetPartDetailsBySearch for broader search
        logger.info(f"No manufacturer provided, using GetPartDetailsBySearch for {part_number}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetPartDetailsBySearch?ApiKey={self.api_key}&Z2MPN={quote(part_number)}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Parse the search results - Z2Data returns nested structure
                results = []
                if isinstance(data, dict) and data.get("results"):
                    # Handle nested results structure
                    if isinstance(data["results"], dict) and data["results"].get("results"):
                        results = data["results"]["results"]
                    else:
                        results = data["results"]
                elif isinstance(data, list):
                    results = data

                if results and len(results) > 0:
                    # Return all matching parts
                    return {
                        "type": "search_results",
                        "success": True,
                        "data": results,
                        "query": query,
                        "part_found": part_number,
                        "count": len(results),
                        "message": f"Found {len(results)} matching parts for '{part_number}'"
                    }
                else:
                    return {
                        "type": "search_results",
                        "success": False,
                        "error": f"No parts found for '{part_number}'",
                        "query": query
                    }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching parts: {e}")
            return {"type": "search_results", "success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error searching parts: {e}")
            return {"type": "search_results", "success": False, "error": str(e)}

    # ==================== MARKET AVAILABILITY ====================

    async def get_market_availability(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Get market availability and pricing data"""
        # First validate the part
        validation_result = await self.validate_part(part_number, manufacturer)
        if not validation_result.get("success"):
            return validation_result

        # Get the part ID from validation result
        part_id = validation_result.get("part_id")
        if not part_id:
            return {"success": False, "error": "Could not obtain part ID"}

        # MarketAvailability API expects just an array of part IDs
        part_ids = [part_id]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/MarketAvailability?ApiKey={self.api_key}",
                    json=part_ids,  # Send just the array of part IDs
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got market availability for {part_number}")

                # MarketAvailability API returns an array directly
                market_data = data if isinstance(data, list) else data.get("results", [])

                return {
                    "type": "market_availability",
                    "success": True,
                    "data": market_data,
                    "part_number": part_number,
                    "manufacturer": manufacturer
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting market availability: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting market availability: {e}")
            return {"success": False, "error": str(e)}

    # ==================== CROSS REFERENCES ====================

    async def get_cross_references(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Get cross reference parts"""
        # First validate and get part ID
        validation_result = await self.validate_part(part_number, manufacturer)
        if not validation_result.get("success"):
            return validation_result

        part_id = validation_result.get("part_id")
        if not part_id:
            return {"success": False, "error": "Could not obtain part ID"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetCrossDataByPartId?ApiKey={self.api_key}&PartID={part_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got cross references for {part_number}")

                return {
                    "type": "cross_references",
                    "success": True,
                    "data": data.get("results", []),
                    "part_number": part_number,
                    "manufacturer": manufacturer
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting cross references: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting cross references: {e}")
            return {"success": False, "error": str(e)}

    # ==================== COMPANY OPERATIONS ====================

    async def validate_company(self, company_name: str) -> Dict[str, Any]:
        """Validate a company and get its company ID"""
        if not company_name:
            return {"success": False, "error": "Company name is required"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/CompanyValidation?APIkey={self.api_key}&CompanySearch={quote(company_name)}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                if data.get("results") and len(data["results"]) > 0:
                    company_info = data["results"][0]
                    return {
                        "success": True,
                        "company_id": company_info.get("CompanyID"),
                        "company_name": company_info.get("CompanyName"),
                        "raw_data": company_info
                    }
                else:
                    return {"success": False, "error": f"Company {company_name} not found"}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error validating company: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error validating company: {e}")
            return {"success": False, "error": str(e)}

    async def get_company_details(self, company_name: str) -> Dict[str, Any]:
        """Get detailed company information"""
        # First validate and get company ID
        validation_result = await self.validate_company(company_name)
        if not validation_result.get("success"):
            return validation_result

        company_id = validation_result.get("company_id")
        if not company_id:
            return {"success": False, "error": "Could not obtain company ID"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetCompanyDataDetailsByCompanyID?ApiKey={self.api_key}&CompanyID={company_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got company details for {company_name}")

                return {
                    "type": "company_details",
                    "success": True,
                    "data": data.get("results", {}),
                    "company_name": company_name
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting company details: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting company details: {e}")
            return {"success": False, "error": str(e)}

    async def get_company_litigations(self, company_name: str) -> Dict[str, Any]:
        """Get company litigation information"""
        # First validate and get company ID
        validation_result = await self.validate_company(company_name)
        if not validation_result.get("success"):
            return validation_result

        company_id = validation_result.get("company_id")
        if not company_id:
            return {"success": False, "error": "Could not obtain company ID"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetCompanyLitigationsByCompanyID?ApiKey={self.api_key}&CompanyID={company_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got litigation data for {company_name}")

                return {
                    "type": "company_litigations",
                    "success": True,
                    "data": data.get("results", []),
                    "company_name": company_name
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting company litigations: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting company litigations: {e}")
            return {"success": False, "error": str(e)}

    async def get_company_supply_chain(self, company_name: str) -> Dict[str, Any]:
        """Get company supply chain information"""
        # First validate and get company ID
        validation_result = await self.validate_company(company_name)
        if not validation_result.get("success"):
            return validation_result

        company_id = validation_result.get("company_id")
        if not company_id:
            return {"success": False, "error": "Could not obtain company ID"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetCompanySupplyChainByCompanyID?ApiKey={self.api_key}&CompanyID={company_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got supply chain data for {company_name}")

                return {
                    "type": "supply_chain",
                    "success": True,
                    "data": data.get("results", {}),
                    "company_name": company_name
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting supply chain: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting supply chain: {e}")
            return {"success": False, "error": str(e)}

    # ==================== SUPPLY CHAIN EVENTS ====================

    async def get_supply_chain_events(self, days_back: int = 30) -> Dict[str, Any]:
        """Get recent supply chain events"""
        event_date_to = datetime.now().strftime("%Y-%m-%d")
        event_date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/GetAllEventsGrouped?ApiKey={self.api_key}&EventDateFrom={quote(event_date_from)}&EventDateTo={quote(event_date_to)}&From=0&Size=10",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Got supply chain events from {event_date_from} to {event_date_to}")

                return {
                    "type": "supply_chain_events",
                    "success": True,
                    "data": data.get("results", []),
                    "date_from": event_date_from,
                    "date_to": event_date_to
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting supply chain events: {e}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting supply chain events: {e}")
            return {"success": False, "error": str(e)}

    # ==================== COMPLIANCE OPERATIONS ====================

    async def get_compliance_data(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Get compliance data from part details"""
        result = await self.get_part_details(part_number, manufacturer)

        if result.get("success") and result.get("data"):
            compliance_data = result["data"].get("ComplianceDetails", {})

            return {
                "type": "compliance",
                "success": True,
                "data": compliance_data,
                "part_number": part_number,
                "manufacturer": manufacturer
            }

        return result

    async def check_rohs_compliance(self, part_number: str, manufacturer: str = "") -> Dict[str, Any]:
        """Check RoHS compliance status"""
        result = await self.get_compliance_data(part_number, manufacturer)

        if result.get("success"):
            rohs_status = result.get("data", {}).get("RoHSStatus", "Unknown")
            return {
                "success": True,
                "compliant": rohs_status.lower() in ["compliant", "yes", "true"],
                "status": rohs_status,
                "part_number": part_number
            }

        return result

    # ==================== FORMATTING METHODS ====================

    def format_results(self, result: Dict[str, Any], operation: str = None) -> str:
        """Format API results for display"""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        result_type = result.get("type", operation)

        if result_type == "part_details":
            return self._format_part_details(result)
        elif result_type == "market_availability":
            return self._format_market_availability(result)
        elif result_type == "cross_references":
            return self._format_cross_references(result)
        elif result_type == "company_details":
            return self._format_company_details(result)
        elif result_type == "supply_chain_events":
            return self._format_supply_chain_events(result)
        else:
            return json.dumps(result.get("data", {}), indent=2)

    def _format_part_details(self, result: Dict[str, Any]) -> str:
        """Format part details for display"""
        data = result.get("data", {})
        part_number = result.get("part_number", "Unknown")

        output = f"## Part Details: {part_number}\n\n"

        # Add summary if available
        if "MPNSummary" in data:
            summary = data["MPNSummary"]
            output += f"**Manufacturer:** {summary.get('Supplier', 'N/A')}\n"
            output += f"**Description:** {summary.get('Description', 'N/A')}\n"
            if summary.get('Datasheet'):
                output += f"**Datasheet:** [View]({summary['Datasheet']})\n"
            output += "\n"

        # Add lifecycle if available
        if "Lifecycle" in data:
            lifecycle = data["Lifecycle"]
            output += f"**Lifecycle Status:** {lifecycle.get('LifecycleStatus', 'N/A')}\n"
            output += f"**Estimated EOL:** {lifecycle.get('EstimatedEOL', 'N/A')}\n\n"

        return output

    def _format_market_availability(self, result: Dict[str, Any]) -> str:
        """Format market availability for display"""
        data = result.get("data", [])
        part_number = result.get("part_number", "Unknown")

        output = f"## Market Availability: {part_number}\n\n"

        if not data:
            return output + "No availability data found."

        # Table format for distributors
        output += "| Distributor | Stock | Price (USD) | MOQ | Lead Time |\n"
        output += "|-------------|-------|-------------|-----|----------|\n"

        for item in data[:10]:  # Limit to 10 results
            distributor = item.get("DistributorName", "N/A")
            stock = item.get("Stock", "N/A")
            price = item.get("UnitPrice", "N/A")
            moq = item.get("MOQ", "N/A")
            lead_time = item.get("LeadTime", "N/A")

            output += f"| {distributor} | {stock} | {price} | {moq} | {lead_time} |\n"

        return output

    def _format_cross_references(self, result: Dict[str, Any]) -> str:
        """Format cross references for display"""
        data = result.get("data", [])
        part_number = result.get("part_number", "Unknown")

        output = f"## Cross References: {part_number}\n\n"

        if not data:
            return output + "No cross references found."

        output += "| Part Number | Manufacturer | Type | Description |\n"
        output += "|-------------|--------------|------|------------|\n"

        for item in data[:10]:  # Limit to 10 results
            cross_part = item.get("CrossPartNumber", "N/A")
            cross_mfr = item.get("CrossManufacturer", "N/A")
            cross_type = item.get("CrossType", "N/A")
            description = item.get("Description", "N/A")
            if len(description) > 50:
                description = description[:50] + "..."

            output += f"| {cross_part} | {cross_mfr} | {cross_type} | {description} |\n"

        return output

    def _format_company_details(self, result: Dict[str, Any]) -> str:
        """Format company details for display"""
        data = result.get("data", {})
        company_name = result.get("company_name", "Unknown")

        output = f"## Company Details: {company_name}\n\n"

        if "CompanySummary" in data:
            summary = data["CompanySummary"]
            output += f"**Industry:** {summary.get('Industry', 'N/A')}\n"
            output += f"**Location:** {summary.get('Location', 'N/A')}\n"
            output += f"**Website:** {summary.get('Website', 'N/A')}\n"
            output += f"**Employees:** {summary.get('EmployeeCount', 'N/A')}\n\n"

        return output

    def _format_supply_chain_events(self, result: Dict[str, Any]) -> str:
        """Format supply chain events for display"""
        data = result.get("data", [])

        output = f"## Recent Supply Chain Events\n\n"
        output += f"**Period:** {result.get('date_from')} to {result.get('date_to')}\n\n"

        if not data:
            return output + "No recent events found."

        for event in data[:5]:  # Limit to 5 events
            output += f"### {event.get('EventType', 'Event')}\n"
            output += f"**Date:** {event.get('EventDate', 'N/A')}\n"
            output += f"**Description:** {event.get('Description', 'N/A')}\n"
            output += f"**Impact:** {event.get('Impact', 'N/A')}\n\n"

        return output

# Create singleton instance
z2_client = Z2DataClient()