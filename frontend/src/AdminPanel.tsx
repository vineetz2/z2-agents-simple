import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './AdminPanel.css'

interface Stats {
  conversations: number
  messages: number
  agents: number
}

function AdminPanel() {
  const [stats, setStats] = useState<Stats>({ conversations: 0, messages: 0, agents: 3 })
  const [prompts, setPrompts] = useState({
    router_prompt: `You are an intelligent routing agent that analyzes user messages and determines the best agent to handle them.

AVAILABLE AGENTS:
1. data: Electronic components, Z2Data APIs, market intelligence
   - Part searches, BOM analysis, market availability
   - Supply chain info, manufacturer details
   - File data enrichment (CSV/Excel)

2. code: Python code generation and execution
   - Writing functions, data analysis, calculations
   - Algorithm implementation, automation scripts

3. chat: General conversation and explanations

ROUTING RULES:
- Part numbers, manufacturers → data
- "enrich", "add columns" → data  
- Python, code, script → code
- Hello, explain, general → chat

Respond with ONLY: data, code, or chat`,
    data_prompt: `You are a specialized data agent for electronic components and supply chain intelligence.

CAPABILITIES:
1. Part Search & Details - specifications, lifecycle, compliance
2. Market Intelligence - availability, pricing, lead times  
3. Supply Chain Analysis - manufacturers, risks, locations
4. Data Enrichment - enhance CSV/Excel with part data
5. BOM Analysis - validation, risk assessment, optimization

When enriching data:
- Add lifecycle status, market availability
- Include pricing trends, alternatives
- Identify supply chain risks

Provide structured, actionable data.`,
    code_prompt: `You are an expert Python code generation and execution agent.

CAPABILITIES:
1. Code Generation - functions, scripts, algorithms
2. Safe Execution - sandboxed environment, 10 sec timeout
3. Data Processing - transformations, calculations, validation

SAFETY:
- No file system access or network calls
- Limited to: math, random, datetime, json, statistics

Generate clean, efficient Python code with error handling.`
  })

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const response = await axios.get('http://localhost:8002/api/admin/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const savePrompts = async () => {
    try {
      for (const [key, value] of Object.entries(prompts)) {
        await axios.post('http://localhost:8002/api/admin/config', { key, value })
      }
      alert('Prompts saved successfully!')
    } catch (error) {
      console.error('Failed to save prompts:', error)
      alert('Failed to save prompts')
    }
  }

  const clearCache = async () => {
    try {
      await axios.post('http://localhost:8002/api/admin/clear-cache')
      alert('Cache cleared!')
    } catch (error) {
      console.error('Failed to clear cache:', error)
    }
  }

  const resetDatabase = async () => {
    if (window.confirm('Are you sure you want to reset the database?')) {
      try {
        await axios.post('http://localhost:8002/api/admin/reset-db')
        alert('Database reset!')
      } catch (error) {
        console.error('Failed to reset database:', error)
      }
    }
  }

  return (
    <div className="admin-container">
      <h1>Admin Panel - Simplified Agent System</h1>
      
      <div className="admin-section">
        <h2>System Status</h2>
        <div className="stats">
          <div className="stat-card">
            <div className="stat-value">{stats.agents}</div>
            <div className="stat-label">Active Agents</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.conversations}</div>
            <div className="stat-label">Conversations</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.messages}</div>
            <div className="stat-label">Messages</div>
          </div>
        </div>
      </div>
      
      <div className="admin-section">
        <h2>Agent Configuration</h2>
        <div className="config-item">
          <div className="config-key">Router Agent</div>
          <textarea 
            className="config-value" 
            rows={4} 
            value="Routes messages to appropriate agents based on intent analysis. Determines whether queries need data operations (parts/Z2Data), code execution (Python), or general chat. Uses pattern matching and context understanding for accurate routing."
            readOnly
          />
        </div>
        <div className="config-item">
          <div className="config-key">Data Agent</div>
          <textarea 
            className="config-value" 
            rows={4} 
            value="Specialized for electronic components and supply chain intelligence. Handles Z2Data API integration for part searches, BOM analysis, market pricing, availability checks, and CSV/Excel file enrichment with lifecycle status, compliance data, and alternatives."
            readOnly
          />
        </div>
        <div className="config-item">
          <div className="config-key">Code Agent</div>
          <textarea 
            className="config-value" 
            rows={4} 
            value="Generates and safely executes Python code in a sandboxed environment. Handles data processing, mathematical computations, algorithm implementation, and automation scripts. Limited to safe libraries with 10-second execution timeout."
            readOnly
          />
        </div>
      </div>
      
      <div className="admin-section">
        <h2>System Prompts</h2>
        <div className="config-item">
          <div className="config-key">router_prompt</div>
          <textarea 
            className="config-value" 
            rows={8}
            value={prompts.router_prompt}
            onChange={(e) => setPrompts({...prompts, router_prompt: e.target.value})}
          />
        </div>
        <div className="config-item">
          <div className="config-key">data_prompt</div>
          <textarea 
            className="config-value" 
            rows={8}
            value={prompts.data_prompt}
            onChange={(e) => setPrompts({...prompts, data_prompt: e.target.value})}
          />
        </div>
        <div className="config-item">
          <div className="config-key">code_prompt</div>
          <textarea 
            className="config-value" 
            rows={8}
            value={prompts.code_prompt}
            onChange={(e) => setPrompts({...prompts, code_prompt: e.target.value})}
          />
        </div>
        <button onClick={savePrompts}>Save Prompts</button>
      </div>
      
      <div className="admin-section">
        <h2>Quick Actions</h2>
        <button onClick={clearCache}>Clear Route Cache</button>
        <button onClick={resetDatabase}>Reset Database</button>
        <button onClick={() => window.location.href = 'http://localhost:8002/api/admin/export'}>Export Data</button>
        <button onClick={() => window.open('http://localhost:8002/api/admin/logs', '_blank')}>View Logs</button>
      </div>
    </div>
  )
}

export default AdminPanel