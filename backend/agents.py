"""
Consolidated Agent System using LangChain and LangGraph
Simplified to 3 core agents: Router, Data/MCP, and Code
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import litellm
import os
import json
import logging
from datetime import datetime
import pandas as pd
from z2data_client import Z2DataClient
from code_sandbox import CodeSandbox

logger = logging.getLogger(__name__)

# State definition for LangGraph
class WorkflowState(TypedDict):
    messages: List[BaseMessage]
    route: str
    agent_type: str
    response: str
    metadata: Dict[str, Any]
    error: Optional[str]

class RouterAgent:
    """Routes messages to appropriate agents using LLM"""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a routing agent. Analyze the user's message and determine which agent should handle it.
            
Available agents:
- data: Handles Z2Data API calls, part searches, BOM analysis, market data, supply chain info
- code: Handles code generation, Python execution, data analysis, calculations
- chat: General conversation, greetings, explanations

Examples:
"search for LM317" → data
"find resistors by Vishay" → data
"analyze this BOM file" → data
"write a python function" → code
"calculate the total cost" → code
"hello" → chat
"explain how this works" → chat

Respond with only the agent name: data, code, or chat"""),
            ("human", "{message}")
        ])
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
        elif os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        else:
            # Fallback to litellm
            return None
    
    def route(self, state: WorkflowState) -> WorkflowState:
        """Route the message to appropriate agent"""
        try:
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            if self.llm:
                response = self.llm.invoke(self.prompt.format_messages(message=last_message))
                route = response.content.strip().lower()
            else:
                # Fallback routing with litellm
                response = litellm.completion(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": f"Route this message to data, code, or chat agent: {last_message}"}],
                    temperature=0
                )
                route = response.choices[0].message.content.strip().lower()
            
            # Validate route
            if route not in ["data", "code", "chat"]:
                route = "chat"
            
            state["route"] = route
            state["agent_type"] = route
            logger.info(f"Routed to {route} agent")
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            state["route"] = "chat"
            state["agent_type"] = "chat"
        
        return state

class DataAgent:
    """Handles all data-related operations including Z2Data API calls"""
    
    def __init__(self):
        self.z2_client = Z2DataClient()
        self.llm = self._get_llm()
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-sonnet-20240229")
        elif os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-4")
        else:
            return None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process data-related requests"""
        try:
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            # Determine the type of data request
            if any(word in last_message.lower() for word in ["search", "find", "lookup", "part"]):
                # Part search
                response = await self._search_parts(last_message)
            elif any(word in last_message.lower() for word in ["bom", "bill of materials", "analyze"]):
                # BOM analysis
                response = await self._analyze_bom(last_message)
            elif any(word in last_message.lower() for word in ["market", "availability", "stock"]):
                # Market data
                response = await self._get_market_data(last_message)
            else:
                # General data query
                response = await self._general_data_query(last_message)
            
            state["response"] = response
            state["messages"].append(AIMessage(content=response))
            
        except Exception as e:
            logger.error(f"Data agent error: {e}")
            state["error"] = str(e)
            state["response"] = f"Error processing data request: {e}"
        
        return state
    
    async def _search_parts(self, query: str) -> str:
        """Search for parts using Z2Data API"""
        try:
            # Extract part number from query
            # This is simplified - in production, use NER or better parsing
            parts = query.split()
            part_number = None
            for part in parts:
                if len(part) > 3 and any(c.isdigit() for c in part):
                    part_number = part
                    break
            
            if part_number:
                result = await self.z2_client.search_part(part_number)
                if result:
                    return self._format_part_results(result)
            
            return "No parts found. Please provide a specific part number."
            
        except Exception as e:
            return f"Error searching parts: {e}"
    
    async def _analyze_bom(self, query: str) -> str:
        """Analyze BOM data"""
        # Placeholder - implement BOM analysis logic
        return "BOM analysis functionality will be implemented with file upload feature."
    
    async def _get_market_data(self, query: str) -> str:
        """Get market availability data"""
        # Placeholder - implement market data logic
        return "Market data functionality coming soon."
    
    async def _general_data_query(self, query: str) -> str:
        """Handle general data queries"""
        return f"Processing data query: {query}"
    
    def _format_part_results(self, results: Dict) -> str:
        """Format part search results"""
        if not results:
            return "No results found."
        
        formatted = "**Part Search Results:**\n\n"
        # Format results based on actual API response structure
        formatted += json.dumps(results, indent=2)
        return formatted

class CodeAgent:
    """Handles code generation and execution"""
    
    def __init__(self):
        self.sandbox = CodeSandbox()
        self.llm = self._get_llm()
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-sonnet-20240229")
        elif os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-4")
        else:
            return None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process code-related requests"""
        try:
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            # Generate code if requested
            if any(word in last_message.lower() for word in ["write", "create", "generate", "code"]):
                code = await self._generate_code(last_message)
                # Execute if it's a complete script
                if code and "def " in code or "import " in code:
                    result = await self.sandbox.execute(code)
                    response = f"**Generated Code:**\n```python\n{code}\n```\n\n**Execution Result:**\n{result}"
                else:
                    response = f"**Generated Code:**\n```python\n{code}\n```"
            else:
                # Direct execution request
                response = await self._execute_code(last_message)
            
            state["response"] = response
            state["messages"].append(AIMessage(content=response))
            
        except Exception as e:
            logger.error(f"Code agent error: {e}")
            state["error"] = str(e)
            state["response"] = f"Error processing code request: {e}"
        
        return state
    
    async def _generate_code(self, request: str) -> str:
        """Generate code based on request"""
        if self.llm:
            prompt = f"Generate Python code for: {request}\nOnly return the code, no explanations."
            response = self.llm.invoke(prompt)
            return response.content
        else:
            # Use litellm as fallback
            response = litellm.completion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Generate Python code for: {request}"}]
            )
            return response.choices[0].message.content
    
    async def _execute_code(self, code: str) -> str:
        """Execute provided code"""
        result = await self.sandbox.execute(code)
        return f"**Execution Result:**\n{result}"

class ChatAgent:
    """Handles general conversation"""
    
    def __init__(self):
        self.llm = self._get_llm()
    
    def _get_llm(self):
        """Get the appropriate LLM based on environment"""
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-haiku-20240307")
        elif os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-3.5-turbo")
        else:
            return None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process general chat requests"""
        try:
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            if self.llm:
                response = self.llm.invoke(last_message)
                content = response.content
            else:
                # Use litellm as fallback
                response = litellm.completion(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": last_message}]
                )
                content = response.choices[0].message.content
            
            state["response"] = content
            state["messages"].append(AIMessage(content=content))
            
        except Exception as e:
            logger.error(f"Chat agent error: {e}")
            state["error"] = str(e)
            state["response"] = f"Error in chat: {e}"
        
        return state

class AgentWorkflow:
    """Main workflow orchestrator using LangGraph"""
    
    def __init__(self):
        self.router = RouterAgent()
        self.data_agent = DataAgent()
        self.code_agent = CodeAgent()
        self.chat_agent = ChatAgent()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("router", self.router.route)
        workflow.add_node("data_agent", self.data_agent.process)
        workflow.add_node("code_agent", self.code_agent.process)
        workflow.add_node("chat_agent", self.chat_agent.process)
        
        # Add edges
        workflow.set_entry_point("router")
        
        # Conditional routing based on router decision
        def route_condition(state: WorkflowState) -> str:
            route = state.get("route", "chat")
            if route == "data":
                return "data_agent"
            elif route == "code":
                return "code_agent"
            else:
                return "chat_agent"
        
        workflow.add_conditional_edges(
            "router",
            route_condition,
            {
                "data_agent": "data_agent",
                "code_agent": "code_agent",
                "chat_agent": "chat_agent"
            }
        )
        
        # All agents go to END
        workflow.add_edge("data_agent", END)
        workflow.add_edge("code_agent", END)
        workflow.add_edge("chat_agent", END)
        
        return workflow.compile()
    
    async def process_message(self, message: str, conversation_id: str) -> Dict[str, Any]:
        """Process a message through the workflow"""
        initial_state = WorkflowState(
            messages=[HumanMessage(content=message)],
            route="",
            agent_type="",
            response="",
            metadata={"conversation_id": conversation_id},
            error=None
        )
        
        # Run the workflow
        result = await self.workflow.ainvoke(initial_state)
        
        return {
            "response": result.get("response", ""),
            "agent_type": result.get("agent_type", "chat"),
            "error": result.get("error"),
            "metadata": result.get("metadata", {})
        }

# Singleton instance
agent_workflow = AgentWorkflow()