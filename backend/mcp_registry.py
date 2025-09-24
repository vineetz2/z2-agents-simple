"""
Simplified MCP Registry for Z2Data API Tool Management
Provides intelligent routing to appropriate Z2Data APIs based on query analysis
"""
from typing import Dict, List, Any, Optional
import logging
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class MCPRegistry:
    """Manages MCP tool definitions and routing logic"""

    def __init__(self):
        self.tools = self._initialize_tools()
        # Use GPT-5 nano for fast extraction
        if os.getenv("OPENAI_API_KEY"):
            self.llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
        else:
            self.llm = None

        # Prompt for extraction
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract part numbers, manufacturers, and companies from the query.
Return a JSON object with these fields:
- part_number: the part number if present (e.g., "LM317", "TPS62840")
- manufacturer: the manufacturer if present, EXACTLY as written in the query (e.g., "Texas Instruments Incorporated", "TI", "Toshiba")
- company: the company name if present for litigation/details queries

Important:
- Extract manufacturer EXACTLY as it appears in the query, do NOT modify or expand abbreviations
- For "LM317-W Texas Instruments Incorporated", return manufacturer as "Texas Instruments Incorporated"
- For "BAV99 by TI", return manufacturer as "TI"
- Be case-sensitive for part numbers but preserve original case for manufacturers

Return ONLY the JSON object, no explanation."""),
            ("human", "{query}")
        ])

    def _initialize_tools(self) -> List[Dict[str, Any]]:
        """Initialize all Z2Data API tool definitions"""
        return [
            {
                'name': 'Part_Details',
                'description': 'Get detailed part information when both part number and manufacturer are provided',
                'keywords': ['part details', 'specifications', 'datasheet', 'parameters', 'features'],
                'requires': ['part_number', 'manufacturer'],
                'api_method': 'get_part_details'
            },
            {
                'name': 'Part_Search',
                'description': 'Search for parts when only part number is provided',
                'keywords': ['search', 'find', 'lookup', 'part number'],
                'requires': ['part_number'],
                'api_method': 'search_parts'
            },
            {
                'name': 'Market_Availability',
                'description': 'Get market availability, pricing, lead times, and distributor stock',
                'keywords': ['market', 'availability', 'price', 'pricing', 'stock', 'inventory', 'distributor', 'lead time'],
                'requires': ['part_number'],
                'optional': ['manufacturer'],
                'api_method': 'get_market_availability'
            },
            {
                'name': 'Cross_References',
                'description': 'Find alternative or replacement parts',
                'keywords': ['cross reference', 'alternative', 'replacement', 'substitute', 'equivalent', 'crosses'],
                'requires': ['part_number', 'manufacturer'],
                'api_method': 'get_cross_references'
            },
            {
                'name': 'Company_Litigations',
                'description': 'Get litigation history and legal cases for a company',
                'keywords': ['litigation', 'lawsuit', 'legal', 'court', 'case', 'litigations'],
                'requires': ['company'],
                'api_method': 'get_company_litigations'
            },
            {
                'name': 'Company_Details',
                'description': 'Get company information, revenue, employees, and business details',
                'keywords': ['company details', 'company info', 'business', 'revenue', 'employees'],
                'requires': ['company'],
                'api_method': 'get_company_details'
            },
            {
                'name': 'Supply_Chain_Locations',
                'description': 'Get supply chain and factory locations for a company',
                'keywords': ['supply chain', 'factory', 'location', 'manufacturing', 'facility'],
                'requires': ['company'],
                'api_method': 'get_supply_chain_locations'
            },
            {
                'name': 'Supply_Chain_Events',
                'description': 'Get supply chain events, disruptions, and news',
                'keywords': ['supply chain event', 'disruption', 'shortage', 'supply news'],
                'requires': [],
                'optional': ['date_from', 'date_to'],
                'api_method': 'get_supply_chain_events'
            },
            {
                'name': 'Digikey_Stock',
                'description': 'Get DigiKey specific stock and pricing information',
                'keywords': ['digikey', 'digi-key', 'digikey stock', 'digikey price'],
                'requires': ['part_number'],
                'optional': ['manufacturer'],
                'api_method': 'get_digikey_stock'
            },
            {
                'name': 'Compliance_Data',
                'description': 'Get compliance information (RoHS, REACH, environmental)',
                'keywords': ['rohs', 'reach', 'compliance', 'environmental', 'restriction', 'hazardous'],
                'requires': ['part_number'],
                'optional': ['manufacturer'],
                'api_method': 'get_compliance_data'
            }
        ]

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine the best tool and extract parameters using GPT-5 nano"""
        query_lower = query.lower()

        # Extract parameters using GPT-5 nano if available
        parameters = self._extract_parameters(query)

        # Find the best matching tool
        best_tool = None
        best_score = 0

        for tool in self.tools:
            score = self._score_tool(tool, query_lower, parameters)
            if score > best_score:
                best_score = score
                best_tool = tool

        logger.info(f"Query analysis: '{query}' -> Tool: {best_tool['name'] if best_tool else 'None'}, Score: {best_score}")

        return {
            'tool': best_tool,
            'parameters': parameters,
            'confidence': best_score
        }

    def _extract_parameters(self, query: str) -> Dict[str, Optional[str]]:
        """Extract parameters from query using GPT-5 nano"""
        parameters = {
            'part_number': None,
            'manufacturer': None,
            'company': None
        }

        if self.llm:
            try:
                # Use GPT-5 nano for extraction
                response = self.llm.invoke(self.extraction_prompt.format_messages(query=query))
                import json
                extracted = json.loads(response.content)

                # Update parameters with extracted values
                parameters['part_number'] = extracted.get('part_number')
                parameters['manufacturer'] = extracted.get('manufacturer')
                parameters['company'] = extracted.get('company')

                logger.info(f"GPT-5 nano extraction: {parameters}")
            except Exception as e:
                logger.warning(f"GPT-5 nano extraction failed, using fallback: {e}")
                # Fallback to simple extraction if LLM fails
                parameters = self._simple_extraction_fallback(query)
        else:
            # No LLM available, use simple fallback
            parameters = self._simple_extraction_fallback(query)

        return parameters

    def _simple_extraction_fallback(self, query: str) -> Dict[str, Optional[str]]:
        """Simple fallback extraction when LLM is not available"""
        import re
        parameters = {
            'part_number': None,
            'manufacturer': None,
            'company': None
        }

        # Enhanced part number pattern to include suffixes like -W, -T, etc.
        # Use non-greedy match to capture full part numbers with dashes
        part_match = re.search(r'\b([A-Z]{2,}[0-9]+(?:[-][A-Z0-9]+)*)\b', query, re.IGNORECASE)
        if part_match:
            parameters['part_number'] = part_match.group(1).upper()

        # Check for company keywords
        query_lower = query.lower()

        # For litigation/lawsuit/legal queries, set company field
        if 'litigation' in query_lower or 'lawsuit' in query_lower or 'legal' in query_lower:
            if 'toshiba' in query_lower:
                parameters['company'] = 'Toshiba'
            elif 'texas instruments' in query_lower:
                parameters['company'] = 'Texas Instruments'
            elif 'intel' in query_lower:
                parameters['company'] = 'Intel'
            elif 'nxp' in query_lower:
                parameters['company'] = 'NXP'
        # For part queries, set manufacturer field
        else:
            if 'toshiba' in query_lower:
                parameters['manufacturer'] = 'Toshiba'
            elif 'texas instruments' in query_lower or ' ti ' in query_lower or query_lower.endswith(' ti'):
                parameters['manufacturer'] = 'Texas Instruments'
            elif 'digikey' in query_lower:
                # Keep part number but don't set manufacturer for DigiKey queries
                pass
            elif 'onsemi' in query_lower:
                parameters['manufacturer'] = 'onsemi'

        return parameters

    def _score_tool(self, tool: Dict[str, Any], query_lower: str, params: Dict[str, Optional[str]]) -> float:
        """Score how well a tool matches the query"""
        score = 0.0

        # Check keyword matches
        for keyword in tool['keywords']:
            if keyword in query_lower:
                score += 2.0

        # Check if we have required parameters
        has_required = True
        for req in tool.get('requires', []):
            if req == 'company' and not params['company']:
                # Check if we have a company (could be from manufacturer field)
                if not params.get('manufacturer'):
                    has_required = False
            elif req == 'part_number' and not params['part_number']:
                has_required = False
            elif req == 'manufacturer' and not params['manufacturer']:
                # Some tools require manufacturer
                if tool['name'] in ['Part_Details', 'Cross_References']:
                    has_required = False

        if not has_required:
            return 0.0  # Can't use this tool without required params

        # Special scoring for specific patterns
        if 'cross reference' in query_lower and tool['name'] == 'Cross_References':
            score += 15.0  # Very strong match for cross references

        if 'alternative' in query_lower and tool['name'] == 'Cross_References':
            score += 10.0  # Alternative parts are cross references

        if 'replacement' in query_lower and tool['name'] == 'Cross_References':
            score += 10.0  # Replacement parts are cross references

        if 'litigation' in query_lower and tool['name'] == 'Company_Litigations':
            score += 10.0  # Very strong match

        if 'company' in query_lower and 'details' in query_lower and tool['name'] == 'Company_Details':
            score += 8.0

        if 'supply chain' in query_lower:
            if 'location' in query_lower and tool['name'] == 'Supply_Chain_Locations':
                score += 8.0
            elif 'event' in query_lower and tool['name'] == 'Supply_Chain_Events':
                score += 8.0

        if 'digikey' in query_lower and tool['name'] == 'Digikey_Stock':
            score += 10.0

        if any(word in query_lower for word in ['rohs', 'reach', 'compliance']) and tool['name'] == 'Compliance_Data':
            score += 8.0

        # If we have both part and manufacturer, prefer Part_Details
        if params['part_number'] and params['manufacturer'] and tool['name'] == 'Part_Details':
            score += 3.0

        # If only part number, prefer Part_Search
        if params['part_number'] and not params['manufacturer'] and tool['name'] == 'Part_Search':
            score += 2.0

        return score

    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name"""
        for tool in self.tools:
            if tool['name'] == name:
                return tool
        return None