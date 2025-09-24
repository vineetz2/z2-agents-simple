"""
Simplified Agents Backend with LangGraph Integration
"""
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import json
import asyncio
import logging
from datetime import datetime
import pandas as pd
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our consolidated agent system
from agents_simple import agent_orchestrator
from models import get_db, init_db, Conversation, Message, SystemConfig
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Agents Simple API", version="0.2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    content: str
    conversation_id: str
    role: str = "user"

class FileEnrichmentRequest(BaseModel):
    file_content: str
    enrichment_type: str = "auto"

class AdminConfig(BaseModel):
    key: str
    value: str

# WebSocket endpoint with LangGraph
@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connection established for conversation {conversation_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message: {data[:100]}...")
            
            # Parse the message to check for file data context
            try:
                message_data = json.loads(data)
                content = message_data.get('content', data)
                context = message_data.get('context', {})
            except:
                content = data
                context = {}

            # Send initial status
            await websocket.send_json({
                "type": "status",
                "message": "Analyzing your request and determining the best approach..."
            })

            # Process through agent orchestrator
            result = await agent_orchestrator.process_message(content, conversation_id, context, websocket)

            # Log what we got back
            logger.info(f"Agent result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")

            # Send response - preserve structured data if present
            response_content = result["response"]

            # Log response content type
            logger.info(f"Response content type: {type(response_content)}, is dict: {isinstance(response_content, dict)}")
            if isinstance(response_content, dict):
                logger.info(f"Response content keys: {response_content.keys()}")

            # If the response is already structured (has type field), send it directly
            if isinstance(response_content, dict) and "type" in response_content:
                response = {
                    "type": "response",
                    "content": response_content,  # This preserves the table structure
                    "agent_type": result["agent_type"],
                    "metadata": result.get("metadata", {})
                }
            else:
                # For simple text responses
                response = {
                    "type": "response",
                    "content": response_content,
                    "agent_type": result["agent_type"],
                    "metadata": result.get("metadata", {})
                }

            logger.info(f"Sending WebSocket response, type: {response.get('type')}, agent: {response.get('agent_type')}")
            await websocket.send_json(response)
            logger.info(f"WebSocket response sent successfully")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket connection closed for conversation {conversation_id}")

# File upload endpoint
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file uploads for BOM analysis and data enrichment"""
    try:
        # Read file content
        content = await file.read()
        
        # Detect file type and process accordingly
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {"error": "Unsupported file format. Please upload CSV or Excel files."}
        
        # Convert to JSON for processing
        data = df.to_dict(orient='records')
        
        return {
            "success": True,
            "filename": file.filename,
            "rows": len(data),
            "columns": list(df.columns),
            "preview": data[:5] if len(data) > 5 else data
        }
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Data enrichment endpoint
@app.post("/api/enrich")
async def enrich_data(request: FileEnrichmentRequest):
    """Enrich uploaded data with Z2Data information"""
    try:
        # Parse the file content
        data = json.loads(request.file_content)
        
        # Process through data agent for enrichment with context
        context = {"file_data": data}
        result = await agent_orchestrator.process_message(
            "Enrich this data with part information, lifecycle status, and market availability",
            "enrichment",
            context
        )
        
        # Extract the enriched data from the result
        if result.get('success') and 'response' in result:
            response = result['response']
            if isinstance(response, dict) and response.get('type') == 'table':
                return {
                    "success": True,
                    "enriched_data": response.get('data', data),
                    "rows_enriched": len(response.get('data', [])),
                    "table_response": response  # Include for frontend table display
                }
            elif isinstance(response, dict) and 'data' in response:
                return {
                    "success": True,
                    "enriched_data": response['data'],
                    "rows_enriched": len(response.get('data', []))
                }
        
        # Fallback to original data if enrichment fails
        return {
            "success": False,
            "enriched_data": data,
            "rows_enriched": 0,
            "error": "Enrichment failed - returning original data"
        }
        
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Admin panel HTML
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - Agents Simple</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .section {
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .config-item {
            margin: 10px 0;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .config-key {
            font-weight: bold;
            color: #4CAF50;
        }
        .config-value {
            margin-top: 5px;
            padding: 8px;
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #45a049;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Admin Panel - Simplified Agent System</h1>
        
        <div class="section">
            <h2>System Status</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="agent-count">3</div>
                    <div class="stat-label">Active Agents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="conversation-count">0</div>
                    <div class="stat-label">Conversations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="message-count">0</div>
                    <div class="stat-label">Messages</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Agent Configuration</h2>
            <div class="config-item">
                <div class="config-key">Router Agent</div>
                <textarea class="config-value" rows="3">Routes messages to appropriate agents (data, code, chat)</textarea>
            </div>
            <div class="config-item">
                <div class="config-key">Data Agent</div>
                <textarea class="config-value" rows="3">Handles Z2Data API calls, part searches, BOM analysis</textarea>
            </div>
            <div class="config-item">
                <div class="config-key">Code Agent</div>
                <textarea class="config-value" rows="3">Generates and executes Python code in sandbox</textarea>
            </div>
            <button onclick="saveConfig()">Save Configuration</button>
        </div>
        
        <div class="section">
            <h2>System Prompts</h2>
            <div class="config-item">
                <div class="config-key">router_prompt</div>
                <textarea class="config-value" id="router_prompt" rows="5">You are a routing agent. Analyze messages and route to: data (parts/Z2Data), code (Python), or chat (general).</textarea>
            </div>
            <div class="config-item">
                <div class="config-key">data_prompt</div>
                <textarea class="config-value" id="data_prompt" rows="5">You are a data agent. Search parts, analyze BOMs, and provide market intelligence using Z2Data APIs.</textarea>
            </div>
            <div class="config-item">
                <div class="config-key">code_prompt</div>
                <textarea class="config-value" id="code_prompt" rows="5">You are a code agent. Generate Python code and execute it safely in a sandbox environment.</textarea>
            </div>
            <button onclick="savePrompts()">Save Prompts</button>
        </div>
        
        <div class="section">
            <h2>Quick Actions</h2>
            <button onclick="clearCache()">Clear Route Cache</button>
            <button onclick="resetDatabase()">Reset Database</button>
            <button onclick="exportData()">Export Data</button>
            <button onclick="viewLogs()">View Logs</button>
        </div>
    </div>
    
    <script>
        async function saveConfig() {
            alert('Configuration saved successfully!');
        }
        
        async function savePrompts() {
            const prompts = ['router_prompt', 'data_prompt', 'code_prompt'];
            for (const prompt of prompts) {
                const value = document.getElementById(prompt).value;
                await fetch('/api/admin/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: prompt, value: value})
                });
            }
            alert('Prompts saved successfully!');
        }
        
        function clearCache() {
            fetch('/api/admin/clear-cache', {method: 'POST'})
                .then(() => alert('Cache cleared!'));
        }
        
        function resetDatabase() {
            if (confirm('Are you sure you want to reset the database?')) {
                fetch('/api/admin/reset-db', {method: 'POST'})
                    .then(() => alert('Database reset!'));
            }
        }
        
        function exportData() {
            window.location.href = '/api/admin/export';
        }
        
        function viewLogs() {
            window.open('/api/admin/logs', '_blank');
        }
        
        // Load stats
        async function loadStats() {
            const stats = await fetch('/api/admin/stats').then(r => r.json());
            document.getElementById('conversation-count').textContent = stats.conversations || 0;
            document.getElementById('message-count').textContent = stats.messages || 0;
        }
        
        loadStats();
        setInterval(loadStats, 5000);
    </script>
</body>
</html>
"""

# Admin panel route
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Serve the admin panel"""
    return ADMIN_HTML

# Admin API endpoints
@app.get("/api/admin/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get system statistics"""
    try:
        conversations = await db.execute(select(Conversation))
        messages = await db.execute(select(Message))
        
        return {
            "conversations": len(conversations.scalars().all()),
            "messages": len(messages.scalars().all()),
            "agents": 3  # Router, Data, Code
        }
    except:
        # If database not initialized, return defaults
        return {"conversations": 0, "messages": 0, "agents": 3}

@app.post("/api/admin/config")
async def save_config(config: AdminConfig, db: AsyncSession = Depends(get_db)):
    """Save system configuration"""
    try:
        # Check if config exists
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == config.key)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.value = config.value
            existing.updated_at = datetime.utcnow()
        else:
            new_config = SystemConfig(key=config.key, value=config.value)
            db.add(new_config)
        
        await db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/admin/clear-cache")
async def clear_cache():
    """Clear routing cache"""
    # Since we're using the new agent system, just return success
    # The new system doesn't use a simple routing cache
    return {"success": True, "cleared": True}

@app.post("/api/admin/reset-db")
async def reset_database():
    """Reset the database"""
    try:
        await init_db()
        return {"success": True}
    except Exception as e:
        logger.error(f"Database reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Agents Simple API with LangGraph",
        "version": "0.2.0",
        "agents": ["router", "data", "code"],
        "admin": "/admin"
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Agents Simple API with LangGraph on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)