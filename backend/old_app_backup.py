"""
Simplified Agents Backend - Everything in one file initially
"""
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import json
import asyncio
import logging
import litellm
import httpx
from datetime import datetime
import hashlib
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Agents Simple API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/agentsimple")
Z2_API_KEY = os.getenv("Z2_API_KEY")
Z2_API_URL = os.getenv("Z2_API_URL", "https://api.z2data.com")

# Configure litellm
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# In-memory storage (will be replaced with database)
conversations: Dict[str, List[dict]] = {}
routing_cache: Dict[str, str] = {}  # Simple routing cache

# Models
class Message(BaseModel):
    content: str
    conversation_id: str
    role: str = "user"

class ChatResponse(BaseModel):
    content: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = {}

# Simple Agent Classes
class RouterAgent:
    """LLM-based router with examples for better routing"""
    
    def route(self, message: str) -> str:
        """Determine which agent should handle the message using LLM"""
        message_lower = message.lower()
        
        # Check cache first
        cache_key = hashlib.md5(message_lower.encode()).hexdigest()[:8]
        if cache_key in routing_cache:
            return routing_cache[cache_key]
        
        # Use LLM for routing with examples
        try:
            routing_prompt = f"""Analyze this user input and determine which agent should handle it.

Available agents:
- data: Handles part searches, component details, pricing, market availability, cross-references, company info, supply chain data
- code: Handles code generation, Python scripts, calculations, automation
- chat: General conversation, greetings, questions

Examples:
"LM317 details" → data (part lookup)
"bav99 by toshiba" → data (part with manufacturer)
"lm317 pricing from digikey" → data (pricing query)
"LM317T by onsemi market availability" → data (market availability)
"search for resistors" → data (component search)
"lawsuits of intel" → data (company information)
"write python script" → code (code generation)
"create a function to calculate" → code (code creation)
"hello" → chat (greeting)
"what can you do" → chat (capability question)

User input: "{message}"

Respond with ONLY one word: data, code, or chat"""

            response = litellm.completion(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": routing_prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip().lower()
            
            # Validate response
            if result not in ['data', 'code', 'chat']:
                # Fallback to simple keyword matching if LLM gives unexpected response
                result = self._fallback_route(message_lower)
                
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}, using fallback")
            result = self._fallback_route(message_lower)
        
        # Cache the result
        routing_cache[cache_key] = result
        logger.info(f"Routing '{message[:50]}...' to {result} agent")
        return result
    
    def _fallback_route(self, message_lower: str) -> str:
        """Simple fallback routing if LLM fails"""
        # Data-related keywords
        data_keywords = ['search', 'find', 'part', 'component', 'pricing', 
                        'availability', 'market', 'digikey', 'cross-reference',
                        'resistor', 'capacitor', 'transistor', 'ic', 'chip',
                        'by', 'from']  # 'by' for manufacturer, 'from' for supplier
        
        # Common manufacturer names
        manufacturers = ['toshiba', 'onsemi', 'ti', 'texas', 'intel',
                        'amd', 'nvidia', 'qualcomm', 'broadcom', 'infineon',
                        'stmicroelectronics', 'nxp', 'analog', 'maxim']
        
        # Code-related keywords  
        code_keywords = ['code', 'python', 'script', 'function', 'write', 'create',
                        'program', 'calculate', 'fibonacci', 'algorithm']
        
        # Check for part numbers (contains letters and numbers)
        has_part_pattern = any(c.isdigit() for c in message_lower) and any(c.isalpha() for c in message_lower)
        
        # Check for manufacturer names
        has_manufacturer = any(mfr in message_lower for mfr in manufacturers)
        
        # Route to data if: has part pattern, has manufacturer, or has data keywords
        if has_part_pattern or has_manufacturer or any(keyword in message_lower for keyword in data_keywords):
            return 'data'
        elif any(keyword in message_lower for keyword in code_keywords):
            return 'code'
        else:
            return 'chat'

class DataAgent:
    """Handles all data-related operations"""
    
    def __init__(self):
        # Import here to avoid circular dependency
        try:
            from z2data_client import z2_client
            self.z2_client = z2_client
        except ImportError:
            # z2data_client not available, mock it
            self.z2_client = None
    
    async def process(self, message: str, files: List[Any] = None) -> str:
        """Process data requests"""
        message_lower = message.lower()
        
        # Check if message contains part number pattern or manufacturer
        has_part_pattern = any(c.isdigit() for c in message_lower) and any(c.isalpha() for c in message_lower)
        manufacturers = ["toshiba", "onsemi", "ti", "texas", "intel", "amd", "nvidia",
                        "qualcomm", "broadcom", "infineon", "stmicroelectronics", "nxp",
                        "analog", "maxim", "digikey", "mouser", "arrow"]
        has_manufacturer = any(mfr in message_lower for mfr in manufacturers)
        
        # Default to search parts for part patterns or manufacturers
        if has_part_pattern or has_manufacturer or "by" in message_lower:
            return await self.search_parts(message)
        elif "pricing" in message_lower or "price" in message_lower:
            return await self.get_market_data(message)
        elif "market" in message_lower or "availability" in message_lower:
            return await self.get_market_data(message)
        elif "cross" in message_lower and "reference" in message_lower:
            return await self.get_cross_references(message)
        elif "compliance" in message_lower or "rohs" in message_lower:
            return await self.get_compliance_data(message)
        elif files:
            return await self.process_files(files)
        else:
            # Default to part search
            return await self.search_parts(message)
    
    async def search_parts(self, query: str) -> str:
        """Search for parts using Z2Data API"""
            
        # Pass the full query to z2_client which will handle extraction
        result = await self.z2_client.search_parts(query)
        return self.z2_client.format_results(result, "search_parts")
    
    async def search_companies(self, query: str) -> str:
        """Search for companies"""
        # Extract company name
        search_term = query.lower().replace('search', '').replace('find', '').replace('company', '').replace('supplier', '').strip()
        
        result = await self.z2_client.call_api("companies/search", params={"q": search_term})
        
        if "error" in result:
            return f"Error searching companies: {result['error']}"
        
        if not result.get("results"):
            return f"No companies found for '{search_term}'"
        
        output = "Found the following companies:\n\n"
        for company in result["results"][:5]:
            output += f"**{company.get('name', 'N/A')}**\n"
            output += f"  Location: {company.get('location', 'N/A')}\n"
            output += f"  Type: {company.get('type', 'N/A')}\n\n"
        return output
    
    async def get_cross_references(self, query: str) -> str:
        """Get cross-reference parts"""
        # Extract part number (simple extraction)
        parts = query.split()
        part_number = next((p for p in parts if any(c.isdigit() for c in p)), None)
        
        if not part_number:
            return "Please provide a part number for cross-reference lookup."
        
        result = await self.z2_client.get_cross_references(part_number)
        return self.z2_client.format_results(result, "cross_reference")
    
    async def get_market_data(self, query: str) -> str:
        """Get market availability data"""
        # Extract part number
        parts = query.split()
        part_number = next((p for p in parts if any(c.isdigit() for c in p)), None)
        
        if not part_number:
            return "Please provide a part number for market availability."
        
        result = await self.z2_client.get_market_availability(part_number)
        return self.z2_client.format_results(result, "market_availability")
    
    async def get_compliance_data(self, query: str) -> str:
        """Get compliance information"""
        # Extract part number
        parts = query.split()
        part_number = next((p for p in parts if any(c.isdigit() for c in p)), None)
        
        if not part_number:
            return "Please provide a part number for compliance check."
        
        if 'rohs' in query.lower():
            result = await self.z2_client.check_rohs_compliance(part_number)
            if "error" in result:
                return f"Error checking RoHS compliance: {result['error']}"
            return f"RoHS Compliance for {part_number}: {'✅ Compliant' if result.get('compliant') else '❌ Non-compliant'}"
        else:
            result = await self.z2_client.get_compliance_data(part_number)
            if "error" in result:
                return f"Error getting compliance data: {result['error']}"
            
            output = f"Compliance Information for {part_number}:\n\n"
            for standard, status in result.items():
                output += f"- {standard}: {status}\n"
            return output
    
    async def process_files(self, files: List[Any]) -> str:
        """Process uploaded files"""
        # Simplified file processing
        return "File processing will be implemented in the next phase."
    
    async def general_data_query(self, message: str) -> str:
        """Handle general data questions using LLM"""
        try:
            response = litellm.completion(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "system", "content": "You are a data analysis assistant."},
                    {"role": "user", "content": message}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in general_data_query: {e}")
            return f"Error processing data query: {str(e)}"

class CodeAgent:
    """Handles code execution in a safe environment"""
    
    def __init__(self):
        from code_sandbox import sandbox
        self.sandbox = sandbox
    
    async def execute(self, message: str) -> str:
        """Execute Python code safely"""
        # Extract code from message
        code = self.extract_code(message)
        
        if not code:
            # Generate code based on request
            code = await self.generate_code(message)
        
        # Format the code for display
        formatted = f"```python\n{code}\n```\n\n"
        
        # Execute in sandbox
        result = await self.sandbox.execute(code)
        
        if result["success"]:
            output = result["output"] if result["output"] else "Code executed successfully (no output)"
            return formatted + f"**Output:**\n```\n{output}\n```"
        else:
            return formatted + f"**Error:**\n```\n{result['error']}\n```"
    
    def extract_code(self, message: str) -> str:
        """Extract Python code from message"""
        # Look for code blocks
        import re
        
        # Match ```python ... ``` or ``` ... ```
        pattern = r'```(?:python)?\n?(.*?)\n?```'
        match = re.search(pattern, message, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Check if entire message looks like code
        if any(keyword in message for keyword in ['def ', 'import ', 'print(', 'for ', 'if ', 'class ']):
            return message
        
        return ""
    
    async def generate_code(self, request: str) -> str:
        """Generate Python code based on request"""
        try:
            response = litellm.completion(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "system", "content": "You are a Python code generator. Generate clean, simple Python code. Only return the code, no explanations."},
                    {"role": "user", "content": request}
                ],
                max_tokens=500
            )
            
            code = response.choices[0].message.content
            
            # Clean up the response
            code = code.replace('```python', '').replace('```', '').strip()
            
            return code
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            # Return a simple example
            return "# Error generating code\nprint('Hello, World!')"

# Initialize agents
router = RouterAgent()
data_agent = DataAgent()
code_agent = CodeAgent()

# WebSocket endpoint
@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """Main WebSocket endpoint for chat"""
    await websocket.accept()
    logger.info(f"WebSocket connected: {conversation_id}")
    
    # Initialize conversation if new
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data) if isinstance(data, str) else data
            
            user_message = message_data.get('content', message_data) if isinstance(message_data, dict) else message_data
            
            # Store user message
            conversations[conversation_id].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Route and process
            agent_type = router.route(user_message)
            logger.info(f"Routing to {agent_type} agent")
            
            # Process based on agent type
            if agent_type == 'data':
                response = await data_agent.process(user_message)
            elif agent_type == 'code':
                response = await code_agent.execute(user_message)
            else:
                # Direct chat using LLM
                response = await handle_chat(user_message, conversation_id)
            
            # Store assistant response
            conversations[conversation_id].append({
                "role": "assistant",
                "content": response,
                "agent_type": agent_type,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send response
            await websocket.send_json({
                "type": "response",
                "content": response,
                "agent_type": agent_type,
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket disconnected: {conversation_id}")

async def handle_chat(message: str, conversation_id: str) -> str:
    """Handle general chat using LLM"""
    try:
        # Get conversation history
        history = conversations.get(conversation_id, [])
        
        # Build messages for LLM
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        
        # Add recent history (last 10 messages)
        for msg in history[-10:]:
            if msg.get('role') in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Get LLM response
        response = litellm.completion(
            model="claude-3-haiku-20240307",
            messages=messages,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error in handle_chat: {e}")
        return f"I encountered an error: {str(e)}"

# REST API endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Agents Simple API",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id]
    }

@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history"""
    if conversation_id in conversations:
        conversations[conversation_id] = []
    return {"status": "cleared", "conversation_id": conversation_id}

@app.post("/chat")
async def chat_endpoint(message: Message):
    """REST endpoint for chat (alternative to WebSocket)"""
    # Initialize conversation if needed
    if message.conversation_id not in conversations:
        conversations[message.conversation_id] = []
    
    # Store user message
    conversations[message.conversation_id].append({
        "role": "user",
        "content": message.content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Route and process
    agent_type = router.route(message.content)
    
    # Process based on agent type
    if agent_type == 'data':
        response = await data_agent.process(message.content)
    elif agent_type == 'code':
        response = await code_agent.execute(message.content)
    else:
        response = await handle_chat(message.content, message.conversation_id)
    
    # Store assistant response
    conversations[message.conversation_id].append({
        "role": "assistant",
        "content": response,
        "agent_type": agent_type,
        "timestamp": datetime.now().isoformat()
    })
    
    return ChatResponse(
        content=response,
        agent_type=agent_type,
        metadata={"conversation_id": message.conversation_id}
    )

# File upload endpoint
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file uploads"""
    try:
        contents = await file.read()
        # Process file based on type
        if file.filename.endswith('.csv'):
            return {"status": "success", "message": "CSV file received", "filename": file.filename}
        elif file.filename.endswith('.xlsx'):
            return {"status": "success", "message": "Excel file received", "filename": file.filename}
        else:
            return {"status": "success", "message": "File received", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Agents Simple API on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)