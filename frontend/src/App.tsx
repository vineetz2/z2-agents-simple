import React, { useState, useEffect, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import TanStackDataTable from './TanStackDataTable'
import PartDetailsDisplay from './PartDetailsDisplay'
import MarketAvailabilityDisplay from './MarketAvailabilityDisplay'
import AdminPanel from './AdminPanel'
import axios from 'axios'
import './App.css'

interface Message {
  role: 'user' | 'assistant'
  content: string | any  // Can be string or structured data
  agent_type?: string
  timestamp?: string
  isLoading?: boolean
  statusMessage?: string
}

function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState(() => `conv-${Date.now()}`)

  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // WebSocket connection
  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;
    let isCleaningUp = false;

    const connectWebSocket = () => {
      if (isCleaningUp) return;

      const ws = new WebSocket(`ws://localhost:8003/ws/${conversationId}`)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'status') {
            // Update the loading message with status
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1]
              if (lastMessage && lastMessage.isLoading) {
                // Update the existing loading message
                return [...prev.slice(0, -1), {
                  ...lastMessage,
                  statusMessage: data.message
                }]
              } else {
                // Create a new loading message
                return [...prev, {
                  role: 'assistant',
                  content: '',
                  isLoading: true,
                  statusMessage: data.message,
                  timestamp: new Date().toISOString()
                }]
              }
            })
          } else if (data.type === 'response') {
            // Replace the loading message with actual response
            setMessages(prev => {
              const filtered = prev.filter(m => !m.isLoading)
              return [...filtered, {
                role: 'assistant',
                content: data.content,
                agent_type: data.agent_type,
                timestamp: new Date().toISOString()
              }]
            })
            setIsLoading(false)
          }
        } catch (e) {
          console.error('Error parsing message:', e)
        }
      }

      ws.onerror = (error) => {
        if (!isCleaningUp) {
          console.warn('WebSocket connection error - will retry')
        }
        setIsConnected(false)
      }

      ws.onclose = () => {
        if (!isCleaningUp) {
          console.log('WebSocket disconnected - reconnecting in 3s...')
          setIsConnected(false)
          // Reconnect after 3 seconds
          reconnectTimeout = setTimeout(connectWebSocket, 3000)
        }
      }

      wsRef.current = ws
    }

    connectWebSocket()

    return () => {
      isCleaningUp = true;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }
  }, [conversationId])

  const startFreshChat = () => {
    // Clear messages and generate new conversation ID
    setMessages([])
    setConversationId(`conv_${Date.now()}`)
    setInput('')
  }

  const sendMessage = (messageText?: string) => {
    const textToSend = messageText || input
    if (!textToSend.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    const userMessage: Message = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    // Send via WebSocket
    wsRef.current.send(JSON.stringify({
      content: textToSend
    }))

    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }


  const handleFileProcessed = (data: any) => {
    // Add file processing result as a message
    const fileMessage: Message = {
      role: 'assistant',
      content: data,
      agent_type: 'data',
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, fileMessage])
  }

  const handleBOMEnrichment = async () => {
    try {
      // Fetch the sample BOM file from public folder
      const response = await fetch('/sample_bom.csv')
      const blob = await response.blob()
      const file = new File([blob], 'sample_bom.csv', { type: 'text/csv' })

      // Create form data and upload
      const formData = new FormData()
      formData.append('file', file)

      // Show user message
      const uploadMessage: Message = {
        role: 'user',
        content: 'Data enrich this BOM with digikey pricing',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, uploadMessage])
      setIsLoading(true)

      // Upload the file
      const uploadResponse = await axios.post('http://localhost:8003/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // Process the response
      if (uploadResponse.data.preview) {
        handleFileProcessed(uploadResponse.data)

        // Send enrichment request via WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            content: 'Enrich this data with digikey pricing'
          }))
        }
      }
    } catch (error) {
      console.error('Error handling BOM enrichment:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error loading sample BOM file. Please upload your BOM file manually.',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      // Show user message about upload
      const uploadMessage: Message = {
        role: 'user',
        content: `Uploading file: ${file.name}`,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, uploadMessage])
      setIsLoading(true)

      const response = await axios.post('http://localhost:8003/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // Show result with automatic enrichment prompt
      const resultMessage: Message = {
        role: 'assistant',
        content: `File uploaded successfully! ${response.data.rows} rows with columns: ${response.data.columns.join(', ')}.\n\nWould you like me to enrich this data with:\n- Lifecycle status\n- Market availability\n- Pricing information\n- Alternative parts\n\nJust say "enrich this data" or specify what information you'd like to add.`,
        agent_type: 'data',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, resultMessage])

      // Store file data for potential enrichment in WebSocket context
      if (response.data.preview) {
        handleFileProcessed(response.data)

        // Auto-enrich if the file has part numbers
        const hasPartNumbers = response.data.columns.some((col: string) =>
          col.toLowerCase().includes('part') ||
          col.toLowerCase().includes('mpn')
        )

        if (hasPartNumbers) {
          // Automatically enrich the data
          setTimeout(async () => {
            const enrichRequest = {
              file_content: JSON.stringify(response.data.preview)
            }

            try {
              const enrichResponse = await axios.post('http://localhost:8003/api/enrich', enrichRequest)

              if (enrichResponse.data.table_response) {
                const enrichMessage: Message = {
                  role: 'assistant',
                  content: enrichResponse.data.table_response,
                  agent_type: 'data',
                  timestamp: new Date().toISOString()
                }
                setMessages(prev => [...prev, enrichMessage])
              }
            } catch (err) {
              console.error('Auto-enrichment failed:', err)
            }
          }, 1000)
        }
      }

      setIsLoading(false)
    } catch (error) {
      console.error('Upload error:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error uploading file. Please try again.',
        agent_type: 'data',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
      setIsLoading(false)
    }

    // Reset file input
    event.target.value = ''
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-container">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img
              src="https://agents.ztwo.app/img/z2-symbol.png"
              alt="Z2"
              className="header-logo"
              onClick={startFreshChat}
              style={{ cursor: 'pointer' }}
            />
            <span className="header-title">Chat</span>
          </div>
          <Link
            to="/admin"
            title="Admin Panel"
            className="admin-link"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          </Link>
        </div>
      </header>

      <main className="chat-container">
        {messages.length === 0 ? (
          <div className="landing-page">
            <div className="landing-content">
              <div className="landing-input-wrapper">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask something..."
                  className="landing-input"
                  disabled={!isConnected}
                  autoFocus
                />
                <label className="landing-attachment-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                  </svg>
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                    disabled={!isConnected}
                  />
                </label>
                <button
                  className="landing-send-button"
                  onClick={() => sendMessage()}
                  disabled={!isConnected || !input.trim()}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                </button>
              </div>
              <div className="landing-examples">
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('recent supply chain events for TI')}
                >
                  recent supply chain events for TI
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('RoHS compliance TPS62840')}
                >
                  RoHS compliance TPS62840
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('cross references for LM317 by ti')}
                >
                  cross references for LM317 by ti
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('BAV99')}
                >
                  BAV99
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('LM317-W Texas Instruments Incorporated')}
                >
                  LM317-W Texas Instruments Incorporated
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('lm317 pricing from digikey')}
                >
                  lm317 pricing from digikey
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('LM317T by onsemi market availability')}
                >
                  LM317T by onsemi market availability
                </button>
                <button
                  className="landing-example-button"
                  onClick={() => sendMessage('Toshiba litigations')}
                >
                  Toshiba litigations
                </button>
                <button
                  className="landing-example-button"
                  onClick={handleBOMEnrichment}
                >
                  Add digikey pricing to BOM
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role} ${msg.isLoading ? 'loading' : ''}`}>
                {msg.isLoading ? (
                  <div className="loading-message">
                    {msg.statusMessage && (
                      <div className="status-text">{msg.statusMessage}</div>
                    )}
                    <div className="loading-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                ) : (
                  <div className={`message-content ${msg.role === 'assistant' && typeof msg.content === 'object' && (msg.content?.type === 'table' || msg.content?.type === 'part_details' || msg.content?.type === 'search_results' || msg.content?.type === 'market_availability') ? 'with-table' : ''}`}>
                    {msg.role === 'assistant' ? (
                    // Check if content is structured data
                    typeof msg.content === 'object' && msg.content?.type === 'part_details' ? (
                      // Use the PartDetailsDisplay component for rich part details
                      <PartDetailsDisplay
                        data={msg.content.data || msg.content}
                        userQuery={msg.content.query}
                      />
                    ) : typeof msg.content === 'object' && msg.content?.type === 'market_availability' ? (
                      // Display market availability with seller cards and info table
                      <MarketAvailabilityDisplay
                        data={msg.content.data}
                        part_number={msg.content.part_number}
                        manufacturer={msg.content.manufacturer}
                      />
                    ) : typeof msg.content === 'object' && msg.content?.type === 'search_results' ? (
                      // Display search results in a TanStack table
                      msg.content.success ? (
                        <div>
                          {msg.content.message && (
                            <div style={{ marginBottom: '10px', fontSize: '14px', color: '#4b5563' }}>
                              {msg.content.message}
                            </div>
                          )}
                          <TanStackDataTable
                            data={msg.content.data}
                            title={`Search Results: ${msg.content.query || 'Parts'}`}
                            toolName="part_search"
                          />
                        </div>
                      ) : (
                        <div style={{ color: '#374151', padding: '12px', backgroundColor: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
                          <div style={{ fontSize: '14px', marginBottom: '4px', fontWeight: '500' }}>Search Results</div>
                          <div style={{ fontSize: '13px', color: '#6b7280' }}>
                            {msg.content.error || 'No results found'}
                          </div>
                        </div>
                      )
                    ) : typeof msg.content === 'object' && msg.content?.type === 'table' ? (
                      <TanStackDataTable
                        data={msg.content.data}
                        title={msg.content.title}
                        toolName={msg.content.toolName}
                      />
                    ) : typeof msg.content === 'object' && msg.content?.type === 'error' ? (
                      <div style={{ color: '#374151', padding: '12px', backgroundColor: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: '14px', marginBottom: '4px', fontWeight: '500' }}>Unable to find part information</div>
                        <div style={{ fontSize: '13px', color: '#6b7280' }}>
                          {msg.content.content.replace('Error: ', '').replace('Part not found: ', 'Part "').replace(' by ', '" from manufacturer "') + '" was not found in our database.'}
                        </div>
                      </div>
                    ) : typeof msg.content === 'string' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <pre>{JSON.stringify(msg.content, null, 2)}</pre>
                    )
                  ) : (
                    <p>{msg.content}</p>
                  )}
                  </div>
                )}
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
        )}

        {messages.length > 0 && (
          <div className="input-container">
            <div className="input-wrapper">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type your message..."
                className="message-input"
                disabled={!isConnected}
                autoFocus
              />
              <label
                className="attachment-icon"
                title="Upload file for enrichment"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                  disabled={!isConnected}
                />
              </label>
              <button
                onClick={() => sendMessage()}
                disabled={!isConnected || !input.trim() || isLoading}
                className="send-button"
              >
                Send
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatInterface />} />
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Router>
  )
}

export default App