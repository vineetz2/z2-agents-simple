"""
Simplified Agent System with basic LangChain (no LangGraph)
Consolidated to 3 core agents matching the original architecture
"""
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
# import litellm  # Removed as we're not using it for fallback
import os
import json
import logging
from datetime import datetime
import pandas as pd
from z2data_client import Z2DataClient
from code_sandbox import SimpleSandbox as CodeSandbox
from mcp_registry import MCPRegistry
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class RouterAgent:
    """Routes messages to appropriate agents using LLM"""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent routing agent that analyzes user messages and determines the best agent to handle them.

AVAILABLE AGENTS:
1. data: Electronic components, Z2Data APIs, market intelligence, company info
   - Part searches (e.g., "find LM317", "search resistors")
   - BOM analysis and validation
   - Market availability and pricing
   - Supply chain information and locations
   - Manufacturer details
   - Company litigations and legal history
   - Company financial details and metrics
   - Supply chain events and disruptions
   - DigiKey specific stock information
   - File data enrichment (CSV/Excel with part numbers)
   - Cross-references and alternatives
   - Component lifecycle status
   - RoHS and REACH compliance data

2. code: Python code generation and execution
   - Writing Python functions and scripts
   - Data analysis and calculations
   - Algorithm implementation
   - Mathematical computations
   - File processing and manipulation
   - Automation scripts

3. chat: General conversation and explanations
   - Greetings and social interaction
   - Explaining concepts
   - General questions
   - Help and guidance
   - Non-technical discussions

ROUTING RULES:
- Part numbers, manufacturers, components → data
- "enrich", "add columns", "enhance data" → data
- Python, code, script, function, calculate → code
- Hello, thanks, explain, what is, how does → chat

EXAMPLES:
"search for TPS62840" → data
"find all capacitors by Murata" → data
"toshiba litigations" → data
"company details for Intel" → data
"supply chain locations for NXP" → data
"DigiKey stock for LM317" → data
"RoHS compliance for BAV99" → data
"enrich this CSV with lifecycle status" → data
"get market pricing for these parts" → data
"write a function to calculate resistance" → code
"create a Python script to process data" → code
"hello, how are you?" → chat
"explain how semiconductors work" → chat

Respond with ONLY the agent name: data, code, or chat"""),
            ("human", "{message}")
        ])
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment - prefer fast model for routing"""
        # Prefer OpenAI's GPT-5 nano for ultra-fast routing if available
        if os.getenv("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI
            # GPT-5 nano is the fastest model for routing decisions
            return ChatOpenAI(model="gpt-5-nano", temperature=0)
        elif os.getenv("ANTHROPIC_API_KEY"):
            # Fallback to Claude if no OpenAI key
            return ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
        else:
            return None
    
    async def route(self, message: str) -> str:
        """Route the message to appropriate agent"""
        try:
            if self.llm:
                response = self.llm.invoke(self.prompt.format_messages(message=message))
                route = response.content.strip().lower()

                # Validate route
                if route not in ["data", "code", "chat"]:
                    route = "chat"

                logger.info(f"Routed to {route} agent")
                return route

        except Exception as e:
            logger.error(f"Routing error: {e} - falling back to keyword routing")

        # Fallback routing - use simple keyword matching when LLM fails
        message_lower = message.lower()
        if any(word in message_lower for word in ['part', 'component', 'search', 'find', 'lm', 'tps', 'bav', 'resistor', 'capacitor', 'bom', 'enrich', 'lifecycle', 'market', 'availability', 'manufacturer', 'litigation', 'lawsuit', 'legal', 'company', 'supply chain', 'digikey', 'compliance', 'rohs', 'reach', 'cross reference', 'alternative', 'toshiba', 'intel', 'nxp', 'texas instruments']):
            route = "data"
        elif any(word in message_lower for word in ['code', 'python', 'script', 'function', 'calculate', 'write', 'generate', 'program']):
            route = "code"
        else:
            route = "chat"

        logger.info(f"Keyword routing: {message} -> {route} agent")
        return route

class DataAgent:
    """Handles all data-related operations including Z2Data API calls and file enrichment"""
    
    def __init__(self):
        # Get API key from environment variable
        api_key = os.environ.get("Z2DATA_API_KEY", "AyxfLYocWpE5HNG")
        self.z2_client = Z2DataClient(api_key)
        self.mcp_registry = MCPRegistry()
        self.llm = self._get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized data agent for electronic components and supply chain intelligence.

CAPABILITIES:
1. Part Search & Details
   - Search parts by number or manufacturer
   - Get detailed specifications
   - Lifecycle status (Active, NRND, Obsolete)
   - Compliance data (RoHS, REACH)
   - Technical parameters

2. Market Intelligence
   - Real-time availability
   - Pricing from distributors
   - Lead times
   - Stock levels
   - Alternative sources

3. Supply Chain Analysis
   - Manufacturer information
   - Factory locations
   - Supply chain risks
   - Company financials
   - Litigation history

4. Data Enrichment
   - Enhance CSV/Excel files with part data
   - Add columns for lifecycle, pricing, availability
   - Cross-reference alternatives
   - Bulk data processing

5. BOM Analysis
   - Validate Bill of Materials
   - Risk assessment
   - Cost optimization
   - Obsolescence management

When enriching data, focus on:
- Part lifecycle status
- Market availability
- Pricing trends
- Alternative components
- Supply chain risks

Always provide structured, actionable data."""),
            ("human", "{query}")
        ])
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-5-sonnet-20241022")
        else:
            return None
    
    async def process(self, message: str, context: Dict = None, websocket = None) -> Dict[str, Any]:
        """Process data-related requests"""
        try:
            # Check if this is a file enrichment request
            if context and context.get("file_data"):
                if websocket:
                    await websocket.send_json({
                        "type": "status",
                        "message": "Analyzing file structure and preparing enrichment..."
                    })
                return await self._enrich_file_data(context["file_data"], websocket)

            # Use MCP registry to analyze and route the query
            mcp_analysis = self.mcp_registry.analyze_query(message)

            # If MCP registry found a high-confidence tool match, use it
            if mcp_analysis['tool'] and mcp_analysis['confidence'] > 2.0:
                response = await self._execute_mcp_tool(mcp_analysis)
            else:
                # Fallback to LLM analysis for complex queries
                analysis = await self._analyze_query(message)

                # Route based on analysis - check specific queries first
                if analysis.get("is_market_query"):
                    # Market availability queries take priority
                    part_number = analysis.get("part_number")
                    manufacturer = analysis.get("manufacturer")
                    if part_number:
                        response = await self._get_market_availability(part_number, manufacturer)
                    else:
                        response = await self._get_market_data(message)
                elif analysis.get("is_litigation_query"):
                    # Handle litigation queries with company name
                    company_name = analysis.get("company_name") or analysis.get("manufacturer")
                    if company_name:
                        response = await self._get_company_litigations(company_name)
                    else:
                        response = {"type": "error", "content": "Please specify a company name for litigation search"}
                elif analysis.get("is_company_query"):
                    # Handle company details queries
                    company_name = analysis.get("company_name") or analysis.get("manufacturer")
                    if company_name:
                        response = await self._get_company_details(company_name)
                    else:
                        response = {"type": "error", "content": "Please specify a company name"}
                elif analysis.get("is_bom_query"):
                    response = await self._analyze_bom(message)
                elif analysis.get("is_cross_reference_query"):
                    # Cross references require both part number and manufacturer
                    if not analysis.get("has_manufacturer"):
                        response = f"To get cross references for {analysis.get('part_number', 'this part')}, please specify the manufacturer. For example: 'cross references for LM317 TI' or 'cross references for LM317 Texas Instruments'"
                    else:
                        # Handle cross references through MCP tool selection
                        mcp_result = self.mcp_registry.analyze_query(message)
                        if mcp_result and mcp_result.get('tool'):
                            response = await self._execute_mcp_tool(mcp_result)
                        else:
                            response = "Could not find appropriate tool for cross references"
                elif analysis.get("is_enrichment_query"):
                    response = "Please upload a file to enrich the data."
                elif analysis.get("has_manufacturer") and analysis.get("part_number"):
                    # Generic part details query (after checking for specific query types)
                    response = await self._get_part_details(
                        analysis["part_number"],
                        analysis["manufacturer"],
                        analysis.get("original_manufacturer")  # Pass original for fallback
                    )
                elif analysis.get("part_number") or analysis.get("is_part_search"):
                    # Part search - pass manufacturer if available from analysis
                    manufacturer = analysis.get("manufacturer") or analysis.get("original_manufacturer")
                    response = await self._search_parts(message, manufacturer)
                else:
                    # Default to part search for short queries
                    if len(message.strip()) <= 20:
                        response = await self._search_parts(message, None)  # No manufacturer for default search
                    else:
                        response = await self._general_data_query(message)
            
            # If response is already a dict with structured data, return it properly
            if isinstance(response, dict):
                # Check if it's a table format response
                if response.get("type") == "table":
                    logger.info(f"Returning table response with {len(response.get('data', []))} rows")
                    # Return the entire dict as the response for table rendering
                    return {
                        "response": response,  # Pass the entire table structure
                        "agent_type": "data",
                        "success": True
                    }
                elif response.get("type") == "part_details":
                    # For part_details responses, return the structured data properly
                    logger.info(f"Returning part_details response")
                    return {
                        "response": response,  # Pass the entire part_details structure
                        "agent_type": "data",
                        "success": True,
                        "data": response
                    }
                else:
                    # For other dict responses
                    logger.info(f"Returning dict response with type: {response.get('type', 'unknown')}")
                    return {
                        "response": response if response.get("type") else response.get("summary", ""),
                        "agent_type": "data",
                        "success": response.get("success", True),
                        "data": response  # Pass the entire structured response
                    }
            else:
                # For string responses, return as before
                logger.info(f"Returning string response, length: {len(str(response))}")
                return {
                    "response": response,
                    "agent_type": "data",
                    "success": True
                }
            
        except Exception as e:
            logger.error(f"Data agent error: {e}")
            return {
                "response": f"Error processing data request: {e}",
                "agent_type": "data",
                "success": False,
                "error": str(e)
            }

    async def _execute_mcp_tool(self, mcp_analysis: Dict[str, Any]) -> str:
        """Execute the MCP tool based on registry analysis"""
        tool = mcp_analysis['tool']
        params = mcp_analysis['parameters']

        logger.info(f"Executing MCP tool: {tool['name']} with params: {params}")

        try:
            # Get the API method name from the tool definition
            api_method = tool.get('api_method')

            if not api_method:
                return f"Tool {tool['name']} does not have an API method configured"

            # Call the appropriate Z2DataClient method based on the tool
            if api_method == 'get_company_litigations':
                if params.get('company'):
                    result = await self.z2_client.get_company_litigations(params['company'])
                    if result.get('success'):
                        return self._format_litigation_response(result)
                    else:
                        return f"Failed to get litigation data: {result.get('error', 'Unknown error')}"
                else:
                    return "Company name is required for litigation search"

            elif api_method == 'get_company_details':
                if params.get('company'):
                    result = await self.z2_client.get_company_details(params['company'])
                    if result.get('success'):
                        return self._format_company_details_response(result)
                    else:
                        return f"Failed to get company details: {result.get('error', 'Unknown error')}"
                else:
                    return "Company name is required for company details"

            elif api_method == 'get_supply_chain_locations':
                if params.get('company'):
                    result = await self.z2_client.get_supply_chain_locations(params['company'])
                    if result.get('success'):
                        return self._format_supply_chain_response(result)
                    else:
                        return f"Failed to get supply chain locations: {result.get('error', 'Unknown error')}"
                else:
                    return "Company name is required for supply chain locations"

            elif api_method == 'get_digikey_stock':
                if params.get('part_number'):
                    result = await self.z2_client.get_digikey_stock(
                        params['part_number'],
                        params.get('manufacturer')
                    )
                    if result.get('success'):
                        return self._format_digikey_response(result)
                    else:
                        return f"Failed to get DigiKey stock: {result.get('error', 'Unknown error')}"
                else:
                    return "Part number is required for DigiKey stock check"

            elif api_method == 'get_supply_chain_events':
                result = await self.z2_client.get_supply_chain_events()
                if result.get('success'):
                    return self._format_events_response(result)
                else:
                    return f"Failed to get supply chain events: {result.get('error', 'Unknown error')}"

            elif api_method == 'get_part_details':
                if params.get('part_number') and params.get('manufacturer'):
                    result = await self._get_part_details(
                        params['part_number'],
                        params['manufacturer']
                    )
                    logger.info(f"Part details result type: {type(result)}, has type key: {isinstance(result, dict) and 'type' in result}")
                    if isinstance(result, dict):
                        logger.info(f"Part details result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

                        # Convert sections format to part_details format for enhanced display
                        if result.get('type') == 'sections' and 'sections' in result:
                            # Use raw API data if available, otherwise use sections
                            if 'raw_data' in result and result['raw_data']:
                                # Use the raw API response for best compatibility
                                result = {
                                    "type": "part_details",
                                    "data": result['raw_data'],
                                    "query": params.get('part_number', '')
                                }
                                logger.info(f"Using raw API data for part_details format")
                            else:
                                # Fallback: convert sections to table format
                                table_data = []
                                for section in result['sections']:
                                    # Add section header row
                                    table_data.append({
                                        "Category": f"--- {section['title']} ---",
                                        "Field": "",
                                        "Value": ""
                                    })
                                    # Add data rows
                                    for item in section.get('data', []):
                                        table_data.append({
                                            "Category": section['title'],
                                            "Field": item.get('Field', ''),
                                            "Value": item.get('Value', '')
                                        })

                                # Convert to table format as fallback
                                result = {
                                    "type": "table",
                                    "title": result.get('title', 'Part Details'),
                                    "data": table_data,
                                    "columns": ["Category", "Field", "Value"]
                                }
                                logger.info(f"Converted sections to table with {len(table_data)} rows")

                    return result
                else:
                    return "Both part number and manufacturer are required for part details"

            elif api_method == 'search_parts':
                if params.get('part_number'):
                    return await self._search_parts(params['part_number'])
                else:
                    return "Part number is required for part search"

            elif api_method == 'get_market_availability':
                if params.get('part_number'):
                    result = await self.z2_client.get_market_availability(params['part_number'])
                    if result.get('success'):
                        return self._format_market_response(result)
                    else:
                        return await self._get_market_data(params['part_number'])
                else:
                    return "Part number is required for market availability"

            elif api_method == 'get_cross_references':
                if params.get('part_number') and params.get('manufacturer'):
                    result = await self.z2_client.get_cross_references(
                        params['part_number'],
                        params['manufacturer']
                    )
                    if result.get('success'):
                        return self._format_cross_reference_response(result)
                    else:
                        return f"Failed to get cross references: {result.get('error', 'Unknown error')}"
                else:
                    return "Both part number and manufacturer are required for cross references"

            elif api_method == 'get_compliance_data':
                if params.get('part_number'):
                    result = await self.z2_client.get_compliance_data(params['part_number'])
                    return self._format_compliance_response(result)
                else:
                    return "Part number is required for compliance data"

            else:
                return f"Unknown API method: {api_method}"

        except Exception as e:
            import traceback
            logger.error(f"Error executing MCP tool {tool['name']}: {e}\n{traceback.format_exc()}")
            return f"Error executing {tool['name']}: {str(e)}"

    def _format_litigation_response(self, result: Dict) -> Dict:
        """Format litigation data response and return structured data for table display"""
        # Check for either 'data' or 'litigations' key in result
        litigations_data = result.get('data') or result.get('litigations', [])
        company_name = result.get('company_name') or result.get('company', 'Unknown')

        if not litigations_data:
            return {
                "type": "table",
                "title": f"No litigation records found for {company_name}",
                "data": [],
                "toolName": "company_litigations"
            }

        lawsuits = []

        # Handle the Z2Data response structure where litigations is a dict with 'Lawsuits' key
        if isinstance(litigations_data, dict) and 'Lawsuits' in litigations_data:
            lawsuits = litigations_data.get('Lawsuits', [])
        elif isinstance(litigations_data, list):
            # Handle if litigations is directly a list
            lawsuits = litigations_data

        # Return structured data in the format expected by frontend
        return {
            "type": "table",
            "title": f"Litigation History for {company_name}",
            "data": lawsuits,  # The raw lawsuits data for table rendering
            "toolName": "company_litigations"
        }

    def _format_company_details_response(self, result: Dict) -> str:
        """Format company details response"""
        details = result.get('details', {})
        response = f"**Company Details: {result.get('company')}**\n\n"

        if details.get('description'):
            response += f"Description: {details['description']}\n\n"

        if details.get('revenue'):
            response += f"Revenue: {details['revenue']}\n"

        if details.get('employees'):
            response += f"Employees: {details['employees']}\n"

        if details.get('headquarters'):
            response += f"Headquarters: {details['headquarters']}\n"

        return response

    def _format_supply_chain_response(self, result: Dict) -> str:
        """Format supply chain locations response"""
        response = f"**Supply Chain Locations for {result.get('company')}**\n\n"
        response += f"Total sites: {result.get('total_sites', 0)}\n\n"

        for loc in result.get('locations', [])[:5]:  # Show first 5
            response += f"• {loc.get('name', 'N/A')}\n"
            response += f"  Location: {loc.get('city', '')}, {loc.get('country', '')}\n"
            response += f"  Type: {loc.get('type', 'N/A')}\n\n"

        return response

    def _format_digikey_response(self, result: Dict) -> str:
        """Format DigiKey stock response"""
        data = result.get('digikey_data', {})
        response = f"**DigiKey Stock Information**\n\n"
        response += f"Part: {result.get('part_number')}\n"

        if result.get('manufacturer'):
            response += f"Manufacturer: {result.get('manufacturer')}\n"

        if data.get('stock'):
            response += f"Stock: {data['stock']}\n"

        if data.get('price'):
            response += f"Price: {data['price']}\n"

        if data.get('lead_time'):
            response += f"Lead Time: {data['lead_time']}\n"

        return response

    def _format_events_response(self, result: Dict) -> str:
        """Format supply chain events response"""
        response = f"**Supply Chain Events ({result.get('date_range')})**\n\n"
        response += f"Total events: {result.get('total_events', 0)}\n\n"

        for event in result.get('events', [])[:5]:  # Show first 5
            response += f"• {event.get('title', 'N/A')}\n"
            response += f"  Date: {event.get('date', 'N/A')}\n"
            response += f"  Impact: {event.get('impact', 'N/A')}\n\n"

        return response

    def _format_market_response(self, result: Dict) -> str:
        """Format market availability response"""
        return f"Market availability data retrieved: {result.get('summary', 'No summary available')}"

    def _format_cross_reference_response(self, result: Dict) -> Dict:
        """Format cross reference response for table display"""
        if not result.get('success'):
            return {
                "type": "error",
                "content": result.get('error', 'Failed to get cross references')
            }

        data = result.get('data', {})

        if not data:
            return {
                "type": "text",
                "content": f"No cross references found for {result.get('part_number', 'this part')}"
            }

        # Extract the main part info
        main_part = {
            "partNumber": data.get('partNumber', ''),
            "companyName": data.get('companyName', ''),
            "partLifecycle": data.get('partLifecycle', ''),
            "roHsFlag": data.get('roHsFlag', ''),
            "dataSheet": data.get('dataSheet', ''),
            "package": data.get('package', ''),
            "partDescription": data.get('partDescription', ''),
            "crossType": "ORIGINAL PART",  # Mark this as the original
            "crossComment": "Reference part for cross comparison"
        }

        # Build the table data with main part first
        table_data = [main_part]

        # Extract and add cross references
        crosses_details = data.get('crossesDetails', {})
        crosses = crosses_details.get('crosses', [])

        # Add each cross reference as a separate row
        for cross in crosses:
            table_data.append({
                "partNumber": cross.get('partNumber', ''),
                "companyName": cross.get('companyName', ''),
                "partLifecycle": cross.get('partLifecycle', ''),
                "roHsFlag": cross.get('roHsFlag', ''),
                "dataSheet": cross.get('dataSheet', ''),
                "package": cross.get('package', ''),
                "partDescription": cross.get('partDescription', ''),
                "crossType": cross.get('crossType', ''),
                "crossComment": cross.get('crossComment', '')
            })

        # Return structured data for table display
        return {
            "type": "table",
            "title": f"Cross References for {data.get('partNumber', '')} - {data.get('companyName', '')} ({len(crosses)} alternatives found)",
            "data": table_data,
            "toolName": "cross_references",
            "note": f"Total crosses found: {crosses_details.get('Total_Crosses_Found', 0)}"
        }

    def _format_compliance_response(self, result: Dict) -> str:
        """Format compliance data response"""
        response = "**Compliance Information**\n\n"
        response += f"RoHS: {result.get('RoHS', 'Unknown')}\n"
        response += f"REACH: {result.get('REACH', 'Unknown')}\n"
        return response

    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Use LLM to analyze query and extract part numbers and manufacturers"""
        import json
        import re

        # Extract original manufacturer from "by" pattern if present
        original_manufacturer = None
        if " by " in query.lower():
            parts = query.lower().split(" by ")
            if len(parts) == 2:
                original_manufacturer = parts[1].strip()

        if not self.llm:
            # Initialize LLM if not available
            self.llm = self._get_llm()
            if not self.llm:
                logger.error("No LLM available for analysis - ANTHROPIC_API_KEY not set")
                # Return basic analysis
                return {
                    "part_number": query.strip().upper(),
                    "manufacturer": original_manufacturer,
                    "original_manufacturer": original_manufacturer,
                    "has_manufacturer": bool(original_manufacturer),
                    "is_part_search": True,
                    "is_market_query": False,
                    "is_bom_query": False,
                    "is_enrichment_query": False,
                    "is_cross_reference_query": False
                }
        
        try:
            analysis_prompt = f"""Analyze this electronics/supply chain query and extract information.

Query: "{query}"

Identify:
1. Is there a part number mentioned? (alphanumeric codes like BAV99, LM317, TPS62840, etc.)
2. Is there a manufacturer/brand/company mentioned? Look for company names like Toshiba, Intel, Texas Instruments, NXP, Vishay, TI, etc.
3. Is this asking about market data (pricing, availability, stock)?
4. Is this about BOM analysis?
5. Is this about data enrichment?
6. Is this about company litigation/lawsuits/legal issues?
7. Is this about company details or supply chain?
8. Is this about cross references, alternatives, or replacement parts?

Common manufacturers and their abbreviations:
- Texas Instruments (TI)
- Analog Devices (ADI)
- STMicroelectronics (ST)
- NXP
- Infineon
- Microchip
- Toshiba
- Vishay
- Murata
- TDK
- Rohm
- ON Semiconductor (onsemi)
- Diodes Inc
- Maxim Integrated
- Renesas

Examples:
- "bav99 toshiba" -> part_number: "BAV99", manufacturer: "Toshiba"
- "lm317 ti" -> part_number: "LM317", manufacturer: "Texas Instruments"
- "lm317" -> part_number: "LM317", manufacturer: null (NO manufacturer specified)
- "bav99" -> part_number: "BAV99", manufacturer: null (NO manufacturer specified)
- "bav99,lm toshiba" -> part_number: "BAV99", manufacturer: "Toshiba" (note: comma separated, focus on main part)
- "BAV99 by EVVO Semi" -> part_number: "BAV99", manufacturer: "EVVO Semi" (IMPORTANT: keep exact name)
- "Toshiba litigations" -> company_name: "Toshiba", is_litigation_query: true
- "Texas Instruments lawsuits" -> company_name: "Texas Instruments", is_litigation_query: true
- "Intel company details" -> company_name: "Intel", is_company_query: true
- "cross references for LM317" -> part_number: "LM317", is_cross_reference_query: true
- "alternatives for BAV99" -> part_number: "BAV99", is_cross_reference_query: true

CRITICAL RULES - FOLLOW EXACTLY:
1. When you see "by [manufacturer]" pattern, preserve the exact manufacturer name as written.
2. DO NOT transform "EVVO Semi" to "EVVO Semiconductor" or similar.
3. NEVER assume a manufacturer if the user didn't specify one explicitly:
   - "LM317" -> manufacturer: null, has_manufacturer: false
   - "BAV99" -> manufacturer: null, has_manufacturer: false
   - "TPS62840" -> manufacturer: null, has_manufacturer: false
4. Only set manufacturer and has_manufacturer: true if explicitly mentioned:
   - "LM317 TI" -> manufacturer: "Texas Instruments", has_manufacturer: true
   - "LM317 by TI" -> manufacturer: "Texas Instruments", has_manufacturer: true
   - "LM317 from Texas Instruments" -> manufacturer: "Texas Instruments", has_manufacturer: true
5. DO NOT make assumptions based on part number prefixes (LM, TPS, etc.)

Respond with JSON only:
{{
    "part_number": "extracted part number or null",
    "manufacturer": "extracted manufacturer or null (null if not explicitly mentioned)",
    "company_name": "extracted company name for litigation/company queries - extract from phrases like 'Toshiba litigations', 'Texas Instruments lawsuits', etc.",
    "has_manufacturer": true/false (only true if user explicitly mentioned manufacturer),
    "is_part_search": true/false,
    "is_market_query": true/false (true for market, availability, pricing queries),
    "is_bom_query": true/false,
    "is_enrichment_query": true/false,
    "is_litigation_query": true/false (true for litigation, lawsuit, legal queries),
    "is_company_query": true/false (true for company details or supply chain queries),
    "is_cross_reference_query": true/false (true for cross reference, alternative, replacement part queries)
}}

Important:
- For queries like "Toshiba litigations" or "Texas Instruments lawsuits", extract the company name (Toshiba, Texas Instruments) into the company_name field.
- For queries like "cross references for LM317" or "alternatives for BAV99", set is_cross_reference_query to true.
- Data enrichment refers ONLY to enriching uploaded CSV/Excel files with additional data columns."""
            
            response = await self.llm.ainvoke(analysis_prompt)
            
            # Try to parse the JSON response
            try:
                result = json.loads(response.content)
                # Add original manufacturer if we extracted it
                result["original_manufacturer"] = original_manufacturer
                logger.info(f"LLM Analysis result for '{query}': {result}")
                return result
            except Exception as parse_error:
                logger.error(f"JSON parsing failed: {parse_error}, content: {response.content}")
                # Return basic analysis without fallback
                return {
                    "part_number": query.strip().upper(),
                    "manufacturer": None,
                    "has_manufacturer": False,
                    "is_part_search": True,
                    "is_market_query": False,
                    "is_bom_query": False,
                    "is_enrichment_query": False,
                    "is_cross_reference_query": False
                }
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            # Return basic analysis without fallback
            return {
                "part_number": query.strip().upper(),
                "manufacturer": None,
                "has_manufacturer": False,
                "is_part_search": True,
                "is_market_query": False,
                "is_bom_query": False,
                "is_enrichment_query": False,
                "is_cross_reference_query": False
            }
    
    def _simple_analysis_DEPRECATED(self, query: str) -> Dict[str, Any]:
        """Simple fallback analysis without LLM"""
        query_lower = query.lower()
        
        # Known manufacturers with their variations
        manufacturer_map = {
            "texas instruments": "Texas Instruments",
            "ti": "Texas Instruments",
            "analog devices": "Analog Devices",
            "adi": "Analog Devices",
            "stmicroelectronics": "STMicroelectronics",
            "st": "STMicroelectronics",
            "nxp": "NXP",
            "infineon": "Infineon",
            "microchip": "Microchip",
            "toshiba": "Toshiba",
            "vishay": "Vishay",
            "murata": "Murata",
            "tdk": "TDK",
            "rohm": "Rohm",
            "on semiconductor": "ON Semiconductor",
            "onsemi": "ON Semiconductor",
            "diodes": "Diodes Inc",
            "maxim": "Maxim Integrated",
            "renesas": "Renesas"
        }
        
        found_manufacturer = None
        part_number = None
        
        # Split query into tokens
        tokens = query_lower.replace(',', ' ').split()
        
        # Check each token for manufacturer
        for token in tokens:
            if token in manufacturer_map:
                found_manufacturer = manufacturer_map[token]
                break
        
        # Also check for multi-word manufacturers
        for mfg_key, mfg_name in manufacturer_map.items():
            if mfg_key in query_lower:
                found_manufacturer = mfg_name
                break
        
        # Check for "by" pattern as well
        if " by " in query_lower:
            parts = query_lower.split(" by ")
            if len(parts) == 2:
                mfg_candidate = parts[1].strip()
                # Check if it's a known manufacturer
                for mfg_key, mfg_name in manufacturer_map.items():
                    if mfg_key in mfg_candidate:
                        found_manufacturer = mfg_name
                        break
                if not found_manufacturer:
                    found_manufacturer = parts[1].strip().title()
                # Part number is before "by"
                part_number = parts[0].strip().upper()
        
        # Extract part number if not already found
        if not part_number:
            # Remove manufacturer from query to get part number
            remaining = query_lower
            if found_manufacturer:
                for mfg_key in manufacturer_map.keys():
                    remaining = remaining.replace(mfg_key, "").strip()
            # Clean up common words
            for word in ["search", "find", "for", "pricing", "cost", "stock"]:
                remaining = remaining.replace(word, "").strip()
            remaining = remaining.replace(',', ' ').strip()
            if remaining and len(remaining) > 1:
                # First token is likely the part number
                part_number = remaining.split()[0].upper() if remaining.split() else None
        
        return {
            "part_number": part_number,
            "manufacturer": found_manufacturer,
            "has_manufacturer": bool(found_manufacturer),
            "is_part_search": any(word in query_lower for word in ["search", "find", "part"]) or len(query.strip()) <= 20,
            "is_market_query": any(word in query_lower for word in ["market", "price", "availability", "stock", "cost"]),
            "is_bom_query": any(word in query_lower for word in ["bom", "bill of materials"]),
            "is_enrichment_query": any(word in query_lower for word in ["enrich", "enhance", "augment"])
        }
    
    async def _get_part_details(self, part_number: str, manufacturer: str, original_manufacturer: str = None) -> Dict[str, Any]:
        """Get detailed part information with fallback to original manufacturer name"""
        try:
            # First try with the LLM-suggested manufacturer
            result = await self.z2_client.get_part_details(part_number, manufacturer)

            # Check if we found the part - check for error in result or empty raw_data
            if result.get("error") or (result.get("type") == "text" and "not found" in result.get("content", "").lower()):
                # If not found and we have an original manufacturer that's different, try that
                if original_manufacturer and original_manufacturer.lower() != manufacturer.lower():
                    logger.info(f"Part not found with '{manufacturer}', trying original: '{original_manufacturer}'")
                    result = await self.z2_client.get_part_details(part_number, original_manufacturer)

            return result

        except Exception as e:
            return {"type": "error", "content": f"Error getting part details: {e}"}
    
    async def _search_parts(self, query: str, manufacturer: str = None) -> Dict[str, Any]:
        """Search for parts using Z2Data API"""
        try:
            # Pass manufacturer to search_parts for smarter searching
            result = await self.z2_client.search_parts(query, manufacturer)
            # The search_parts method already returns formatted data
            if isinstance(result, dict) and result.get("formatted"):
                return result["formatted"]
            return result
        except Exception as e:
            return {"type": "error", "content": f"Error searching parts: {e}"}
    
    async def _get_market_availability(self, part_number: str, manufacturer: str = None) -> Dict[str, Any]:
        """Get market availability for a specific part"""
        try:
            result = await self.z2_client.get_market_availability(part_number, manufacturer or "")
            return result
        except Exception as e:
            logger.error(f"Error getting market availability: {e}")
            return {"type": "error", "content": f"Error getting market availability: {e}"}

    async def _get_company_litigations(self, company_name: str) -> Dict[str, Any]:
        """Get litigation history for a company"""
        try:
            result = await self.z2_client.get_company_litigations(company_name)
            return result
        except Exception as e:
            logger.error(f"Error getting company litigations: {e}")
            return {"type": "error", "content": f"Error getting litigation data for {company_name}: {e}"}

    async def _get_company_details(self, company_name: str) -> Dict[str, Any]:
        """Get company details"""
        try:
            result = await self.z2_client.get_company_details(company_name)
            return result
        except Exception as e:
            logger.error(f"Error getting company details: {e}")
            return {"type": "error", "content": f"Error getting company details for {company_name}: {e}"}

    async def _analyze_bom(self, query: str) -> str:
        """Analyze BOM data"""
        return "BOM analysis functionality is available through file upload. Please upload a CSV or Excel file with your BOM data."

    async def _get_market_data(self, query: str) -> Dict[str, Any]:
        """Get market availability data"""
        try:
            # Z2DataClient doesn't have get_market_data, use get_market_availability instead
            result = await self.z2_client.get_market_availability(query)
            # Return the result directly as it's already formatted
            if isinstance(result, dict):
                return result
            return {"type": "text", "content": str(result)}
        except Exception as e:
            return {"type": "error", "content": f"Error getting market data: {e}"}
    
    async def _general_data_query(self, query: str) -> Dict[str, Any]:
        """Handle general data queries"""
        return {"type": "text", "content": f"Processing data query: {query}"}
    
    async def _enrich_file_data(self, file_data: List[Dict], websocket = None) -> Dict[str, Any]:
        """Enrich uploaded file data with Z2Data information"""
        try:
            enriched_data = []
            total_rows = len(file_data)
            enriched_count = 0

            if websocket:
                await websocket.send_json({
                    "type": "status",
                    "message": f"Processing {total_rows} rows of data..."
                })
            
            for idx, row in enumerate(file_data):
                # Try different column names for part number
                part_number = (
                    row.get('part_number') or 
                    row.get('Part Number') or 
                    row.get('PartNumber') or
                    row.get('MPN') or
                    row.get('mpn') or
                    row.get('Part')
                )
                
                manufacturer = (
                    row.get('manufacturer') or
                    row.get('Manufacturer') or
                    row.get('MFG') or
                    row.get('mfg') or
                    row.get('Brand')
                )
                
                if part_number:
                    try:
                        # Get part details from Z2Data
                        search_query = f"{part_number} {manufacturer}" if manufacturer else part_number
                        result = await self.z2_client.search_parts(search_query)
                        
                        # Parse the result and add enrichment columns
                        if result:
                            # Add lifecycle status
                            row['lifecycle_status'] = self._extract_lifecycle(result)
                            row['rohs_status'] = self._extract_rohs(result)
                            row['market_availability'] = self._extract_availability(result)
                            row['avg_price'] = self._extract_price(result)
                            row['lead_time'] = self._extract_lead_time(result)
                            row['alternatives'] = self._extract_alternatives(result)
                            enriched_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to enrich part {part_number}: {e}")
                        row['enrichment_error'] = str(e)
                
                enriched_data.append(row)
            
            # Format as table for display
            return {
                "response": {
                    "type": "table",
                    "title": f"Enriched Data ({enriched_count}/{total_rows} parts enriched)",
                    "data": enriched_data
                },
                "agent_type": "data",
                "success": True
            }
        except Exception as e:
            return {
                "response": f"Error enriching data: {e}",
                "agent_type": "data",
                "success": False,
                "error": str(e)
            }
    
    def _extract_lifecycle(self, result: str) -> str:
        """Extract lifecycle status from API result"""
        if "Active" in result:
            return "Active"
        elif "NRND" in result or "Not Recommended" in result:
            return "NRND"
        elif "Obsolete" in result or "End of Life" in result:
            return "Obsolete"
        return "Unknown"
    
    def _extract_rohs(self, result: str) -> str:
        """Extract RoHS status from API result"""
        if "RoHS Compliant" in result or "RoHS: Yes" in result:
            return "Compliant"
        elif "RoHS: No" in result:
            return "Non-Compliant"
        return "Unknown"
    
    def _extract_availability(self, result: str) -> str:
        """Extract availability from API result"""
        import re
        match = re.search(r'(\d+[,\d]*) in stock', result, re.IGNORECASE)
        if match:
            return match.group(1)
        elif "In Stock" in result:
            return "Available"
        elif "Out of Stock" in result:
            return "Out of Stock"
        return "Check Availability"
    
    def _extract_price(self, result: str) -> str:
        """Extract average price from API result"""
        import re
        match = re.search(r'\$([0-9.]+)', result)
        if match:
            return f"${match.group(1)}"
        return "Quote Required"
    
    def _extract_lead_time(self, result: str) -> str:
        """Extract lead time from API result"""
        import re
        match = re.search(r'(\d+) weeks?', result, re.IGNORECASE)
        if match:
            return f"{match.group(1)} weeks"
        return "Contact Supplier"
    
    def _extract_alternatives(self, result: str) -> str:
        """Extract alternative parts from API result"""
        # This would parse cross-references from the API
        if "Alternative:" in result or "Cross" in result:
            return "Available"
        return "None Found"

class CodeAgent:
    """Handles code generation and execution"""
    
    def __init__(self):
        self.sandbox = CodeSandbox()
        self.llm = self._get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Python code generation and execution agent.

CAPABILITIES:
1. Code Generation
   - Python functions and classes
   - Data processing scripts
   - Algorithm implementation
   - API integration code
   - Automation scripts
   - Mathematical computations

2. Safe Execution
   - Run Python code in sandboxed environment
   - Handle imports: math, random, datetime, json, statistics
   - Process results and errors
   - Format output clearly

3. Data Processing
   - Parse and transform data
   - Statistical calculations
   - File manipulation
   - Bulk operations
   - Data validation

EXECUTION RULES:
- Generate clean, efficient Python code
- Include error handling
- Use descriptive variable names
- Add minimal comments for complex logic
- Return formatted results

SAFETY:
- No file system access
- No network calls
- No system commands
- Limited to safe libraries
- 10 second timeout

When generating code:
1. Understand the requirement fully
2. Write clear, Pythonic code
3. Test edge cases mentally
4. Format output for readability"""),
            ("human", "{request}")
        ])
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-5-sonnet-20241022")
        else:
            return None
    
    async def process(self, message: str, websocket = None) -> Dict[str, Any]:
        """Process code-related requests"""
        try:
            # Generate code if requested
            if any(word in message.lower() for word in ["write", "create", "generate", "code"]):
                if websocket:
                    await websocket.send_json({
                        "type": "status",
                        "message": "Generating Python code based on your requirements..."
                    })
                code = await self._generate_code(message)
                # Execute if it's a complete script
                if code and ("def " in code or "import " in code):
                    result = await self.sandbox.execute(code)
                    response = f"**Generated Code:**\n```python\n{code}\n```\n\n**Execution Result:**\n{result}"
                else:
                    response = f"**Generated Code:**\n```python\n{code}\n```"
            else:
                # Direct execution request
                response = await self._execute_code(message)
            
            return {
                "response": response,
                "agent_type": "code",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Code agent error: {e}")
            return {
                "response": f"Error processing code request: {e}",
                "agent_type": "code",
                "success": False,
                "error": str(e)
            }
    
    async def _generate_code(self, request: str) -> str:
        """Generate code based on request"""
        try:
            if self.llm:
                prompt = f"Generate Python code for: {request}\nOnly return the code, no explanations."
                response = self.llm.invoke(prompt)
                return response.content
            else:
                # Simple fallback - return basic template
                return f"""# Python code for: {request}
# Note: LLM not available, using template

def solution():
    # TODO: Implement {request}
    pass

if __name__ == "__main__":
    solution()"""
        except Exception as e:
            return f"# Error generating code: {e}"
    
    async def _execute_code(self, code: str) -> str:
        """Execute provided code"""
        result = await self.sandbox.execute(code)
        return f"**Execution Result:**\n{result}"

class ChatAgent:
    """Handles general conversation with LangChain memory"""

    def __init__(self):
        self.llm = self._get_llm()

    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-haiku-20240307")
        else:
            return None

    async def process(self, message: str, context: Dict = None, websocket = None) -> Dict[str, Any]:
        """Process general chat requests with conversation history"""
        try:
            if websocket:
                await websocket.send_json({
                    "type": "status",
                    "message": "Thinking about your question..."
                })

            if self.llm:
                # Get memory from context
                memory = context.get('memory') if context else None

                if memory:
                    # Get chat history from memory
                    messages = memory.chat_memory.messages
                    logger.info(f"Using memory with {len(messages)} previous messages")

                    # Build conversation with history
                    conversation = []

                    # Add system message
                    conversation.append({
                        "role": "system",
                        "content": """You are a helpful AI assistant. You have access to the conversation history and should remember information from earlier in the conversation.

IMPORTANT: If a user tells you their name or any personal information, you MUST remember it and use it when asked later in the conversation."""
                    })

                    # Add conversation history
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            conversation.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            conversation.append({"role": "assistant", "content": msg.content})

                    # Add current message
                    conversation.append({"role": "user", "content": message})

                    # Invoke LLM with full conversation
                    response = self.llm.invoke(conversation)
                    content = response.content
                else:
                    # No memory, just respond to current message
                    response = self.llm.invoke(message)
                    content = response.content
            else:
                # Simple fallback response
                content = f"I'm a chat assistant. While I don't have access to an LLM right now, I can help with: {message}"

            return {
                "response": content,
                "agent_type": "chat",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Chat agent error: {e}")
            return {
                "response": f"Error in chat: {e}",
                "agent_type": "chat",
                "success": False,
                "error": str(e)
            }

class SimpleAgentOrchestrator:
    """Simple orchestrator without LangGraph but with LangChain memory"""

    def __init__(self):
        self.router = RouterAgent()
        self.data_agent = DataAgent()
        self.code_agent = CodeAgent()
        self.chat_agent = ChatAgent()
        # Store memory per conversation
        self.conversation_memories = {}

    def get_or_create_memory(self, conversation_id: str) -> ConversationBufferMemory:
        """Get existing memory or create new one for conversation"""
        if conversation_id not in self.conversation_memories:
            self.conversation_memories[conversation_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            logger.info(f"Created new memory for conversation {conversation_id}")
        return self.conversation_memories[conversation_id]

    async def process_message(self, message: str, conversation_id: str, context: Dict = None, websocket = None) -> Dict[str, Any]:
        """Process a message through the appropriate agent"""
        try:
            # Get or create memory for this conversation
            memory = self.get_or_create_memory(conversation_id)

            # Send routing status
            if websocket:
                await websocket.send_json({
                    "type": "status",
                    "message": "Understanding your request and choosing the best approach..."
                })

            # Route the message
            route = await self.router.route(message)

            # Send agent-specific status
            if websocket:
                status_messages = {
                    "data": "Connecting to Z2Data APIs to retrieve information...",
                    "code": "Preparing code execution environment...",
                    "chat": "Formulating a thoughtful response..."
                }
                await websocket.send_json({
                    "type": "status",
                    "message": status_messages.get(route, f"Processing with {route} agent...")
                })

            # Add memory to context
            if context is None:
                context = {}
            context['memory'] = memory

            # Process with appropriate agent
            if route == "data":
                result = await self.data_agent.process(message, context, websocket)
            elif route == "code":
                result = await self.code_agent.process(message, websocket)
            else:  # chat
                result = await self.chat_agent.process(message, context, websocket)

            # Save the interaction to memory
            memory.save_context(
                {"input": message},
                {"output": result.get("response", "")}
            )
            logger.info(f"Saved interaction to memory for conversation {conversation_id}")

            # Add metadata
            result["conversation_id"] = conversation_id
            result["route"] = route

            return result

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "response": f"Error processing message: {e}",
                "agent_type": "error",
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id
            }

# Singleton instance
agent_orchestrator = SimpleAgentOrchestrator()