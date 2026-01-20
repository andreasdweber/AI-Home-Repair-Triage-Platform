import { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://ai-home-repair-triage-platform.onrender.com'

export default function App() {
  // ─────────────────────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────────────────────
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState('chat') // 'chat' | 'audit'
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: "Hi! I'm Fix-It AI 🔧 Describe your issue or attach a photo. If DIY doesn't work, I'll connect you with a pro!" }
  ])
  const [input, setInput] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => `s_${Date.now()}`)
  
  // Escalation state
  const [escalationMode, setEscalationMode] = useState(false)
  const [contactInfo, setContactInfo] = useState({})
  
  // Audit state
  const [auditType, setAuditType] = useState(null) // 'move-in' | 'move-out'
  const [unitId, setUnitId] = useState('')
  const [auditResults, setAuditResults] = useState(null)
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const auditFileInputRef = useRef(null)

  // ─────────────────────────────────────────────────────────────────────────────
  // DEEP LINKING - Expose widget controls to parent page
  // ─────────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    window.FixItWidget = {
      open: () => setIsOpen(true),
      close: () => setIsOpen(false),
      openChat: () => {
        setMode('chat')
        setIsOpen(true)
      },
      openAudit: () => {
        setMode('audit')
        setIsOpen(true)
      },
      setMode: (newMode) => {
        if (newMode === 'chat' || newMode === 'audit') {
          setMode(newMode)
        }
      }
    }
    
    return () => {
      delete window.FixItWidget
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ─────────────────────────────────────────────────────────────────────────────
  // CHAT HANDLERS
  // ─────────────────────────────────────────────────────────────────────────────
  const isVideoFile = (f) => f && f.type.startsWith('video/')
  const isImageFile = (f) => f && f.type.startsWith('image/')

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() && !file) return
    if (isVideoFile(file)) {
      // Switch to audit mode for videos
      setMode('audit')
      return
    }

    const userMsg = { id: Date.now(), role: 'user', text: input, file: file?.name }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('text', input)
      formData.append('escalation_mode', escalationMode)
      formData.append('contact_info', JSON.stringify(contactInfo))
      if (file && isImageFile(file)) formData.append('file', file)

      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      if (data.session_id) setSessionId(data.session_id)
      if (data.escalation_mode !== undefined) setEscalationMode(data.escalation_mode)
      if (data.contact_info) setContactInfo(data.contact_info)

      // Handle CREATE_TICKET action - show success card
      if (data.action === 'CREATE_TICKET') {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          text: data.response,
          ticketCreated: true,
          ticketId: data.ticket_id,
          ticketSummary: data.ticket_summary
        }])
        // Reset escalation state
        setEscalationMode(false)
        setContactInfo({})
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          text: data.response || 'No response',
          risk: data.risk,
          action: data.action,
          category: data.category
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: '⚠️ Error connecting to server. Please wait 30 seconds and try again.',
        error: true
      }])
    } finally {
      setLoading(false)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // AUDIT HANDLERS
  // ─────────────────────────────────────────────────────────────────────────────
  const handleAuditFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && isVideoFile(selectedFile)) {
      setFile(selectedFile)
    }
  }

  const startAudit = async () => {
    if (!file || !unitId.trim() || !auditType) return

    setLoading(true)
    setAuditResults(null)

    try {
      const formData = new FormData()
      formData.append('unit_id', unitId)
      formData.append('mode', auditType)
      formData.append('file', file)

      const res = await fetch(`${API_URL}/audit`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      if (data.success) {
        setAuditResults(data)
      } else {
        setAuditResults({ error: data.error || data.detail || 'Audit failed' })
      }
    } catch (err) {
      setAuditResults({ error: 'Error connecting to server. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  const resetAudit = () => {
    setFile(null)
    setUnitId('')
    setAuditType(null)
    setAuditResults(null)
    if (auditFileInputRef.current) auditFileInputRef.current.value = ''
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER HELPERS
  // ─────────────────────────────────────────────────────────────────────────────
  const riskColors = {
    Green: 'bg-green-100 text-green-700 border-green-200',
    Yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    Red: 'bg-red-100 text-red-700 border-red-200'
  }

  const renderTicketCard = (msg) => (
    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mt-2">
      <div className="flex items-center gap-2 text-green-700 font-medium">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Ticket #{msg.ticketId} Created
      </div>
      <p className="text-sm text-green-600 mt-1">A vendor has been notified and will contact you soon.</p>
      {msg.ticketSummary && (
        <p className="text-xs text-gray-600 mt-2 bg-white p-2 rounded border">
          📋 {msg.ticketSummary}
        </p>
      )}
    </div>
  )

  const renderAuditResults = () => {
    if (!auditResults) return null

    if (auditResults.error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-medium">❌ Error</p>
          <p className="text-sm">{auditResults.error}</p>
        </div>
      )
    }

    const items = auditResults.items || []
    const newDamages = items.filter(i => i.is_new)

    return (
      <div className="space-y-3">
        {/* Summary Card */}
        <div className={`rounded-lg p-4 ${auditType === 'move-in' ? 'bg-blue-50 border border-blue-200' : newDamages.length > 0 ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
          <div className="flex items-center gap-2 font-medium">
            {auditType === 'move-in' ? (
              <>📥 Move-In Baseline Created</>
            ) : newDamages.length > 0 ? (
              <>⚠️ {newDamages.length} New Damages Found</>
            ) : (
              <>✅ No New Damages Found</>
            )}
          </div>
          <p className="text-sm mt-1 opacity-80">{auditResults.summary}</p>
          {auditResults.total_estimated_cost > 0 && (
            <p className="text-sm font-medium mt-2">
              💰 Estimated Cost: ${auditResults.total_estimated_cost}
            </p>
          )}
        </div>

        {/* Items List */}
        {items.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 font-medium text-sm">
              📋 Detected Items ({items.length})
            </div>
            <div className="max-h-48 overflow-y-auto">
              {items.map((item, idx) => (
                <div key={idx} className={`px-3 py-2 border-b border-gray-100 text-sm ${item.is_new ? 'bg-red-50' : ''}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-medium">{item.item}</span>
                      {item.room && <span className="text-gray-500 text-xs ml-2">({item.room})</span>}
                    </div>
                    {item.is_new && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">NEW</span>
                    )}
                  </div>
                  <p className="text-gray-600 text-xs mt-0.5">{item.condition}</p>
                  <div className="flex gap-3 text-xs text-gray-400 mt-1">
                    {item.timestamp && <span>⏱️ {item.timestamp}</span>}
                    {item.estimated_cost > 0 && <span>💵 ${item.estimated_cost}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Reset Button */}
        <button
          onClick={resetAudit}
          className="w-full py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition"
        >
          ← Start New Audit
        </button>
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="fixed bottom-5 right-5 z-[9999] font-sans" style={{ zIndex: 9999 }}>
      {/* Main Widget Window */}
      {isOpen && (
        <div className="mb-3 w-80 sm:w-96 h-[32rem] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          {/* Header with Mode Tabs */}
          <div className="bg-blue-600 text-white flex-shrink-0">
            <div className="px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔧</span>
                <span className="font-semibold">Fix-It AI</span>
              </div>
              <button onClick={() => setIsOpen(false)} className="hover:bg-blue-500 rounded p-1">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {/* Mode Tabs */}
            <div className="flex border-t border-blue-500">
              <button
                onClick={() => setMode('chat')}
                className={`flex-1 py-2 text-sm font-medium transition ${mode === 'chat' ? 'bg-white text-blue-600' : 'text-blue-100 hover:bg-blue-500'}`}
              >
                💬 Chat
              </button>
              <button
                onClick={() => setMode('audit')}
                className={`flex-1 py-2 text-sm font-medium transition ${mode === 'audit' ? 'bg-white text-blue-600' : 'text-blue-100 hover:bg-blue-500'}`}
              >
                🎥 Audit
              </button>
            </div>
          </div>

          {/* ─── CHAT MODE ─── */}
          {mode === 'chat' && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : msg.error 
                          ? 'bg-red-50 text-red-700 border border-red-200'
                          : 'bg-white text-gray-800 border border-gray-200'
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                      {msg.file && <p className="text-xs mt-1 opacity-70">📎 {msg.file}</p>}
                      {msg.risk && (
                        <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded border ${riskColors[msg.risk] || 'bg-gray-100'}`}>
                          {msg.risk} {msg.category && `• ${msg.category}`}
                        </span>
                      )}
                      {msg.ticketCreated && renderTicketCard(msg)}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Image Preview */}
              {file && isImageFile(file) && (
                <div className="px-3 py-2 bg-blue-50 border-t border-blue-100 flex items-center justify-between">
                  <span className="text-xs text-blue-700 truncate">📎 {file.name}</span>
                  <button onClick={() => { setFile(null); fileInputRef.current.value = '' }} className="text-blue-600 hover:text-blue-800">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Input */}
              <div className="p-3 border-t border-gray-200 bg-white flex-shrink-0">
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept="image/*"
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                    title="Attach photo"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </button>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={escalationMode ? "Enter phone or access info..." : "Describe the issue..."}
                    className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400"
                    disabled={loading}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={loading || (!input.trim() && !file)}
                    className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </div>
              </div>
            </>
          )}

          {/* ─── AUDIT MODE ─── */}
          {mode === 'audit' && (
            <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
              {auditResults ? (
                renderAuditResults()
              ) : (
                <div className="space-y-4">
                  {/* Audit Type Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Audit Type
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => setAuditType('move-in')}
                        className={`p-3 rounded-lg border-2 transition text-center ${
                          auditType === 'move-in'
                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-2xl mb-1">📥</div>
                        <div className="font-medium">Move-In</div>
                        <div className="text-xs text-gray-500">Create baseline</div>
                      </button>
                      <button
                        onClick={() => setAuditType('move-out')}
                        className={`p-3 rounded-lg border-2 transition text-center ${
                          auditType === 'move-out'
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-2xl mb-1">📤</div>
                        <div className="font-medium">Move-Out</div>
                        <div className="text-xs text-gray-500">Compare damages</div>
                      </button>
                    </div>
                  </div>

                  {/* Unit ID Input */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Unit ID
                    </label>
                    <input
                      type="text"
                      value={unitId}
                      onChange={(e) => setUnitId(e.target.value)}
                      placeholder="e.g., APT-101, Unit-5B"
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400"
                    />
                  </div>

                  {/* Video Upload */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Walkthrough Video
                    </label>
                    <input
                      type="file"
                      ref={auditFileInputRef}
                      onChange={handleAuditFileSelect}
                      accept="video/*"
                      className="hidden"
                    />
                    {file ? (
                      <div className="flex items-center justify-between p-3 bg-purple-50 border border-purple-200 rounded-lg">
                        <div className="flex items-center gap-2 text-purple-700">
                          <span>🎥</span>
                          <span className="text-sm truncate max-w-[200px]">{file.name}</span>
                        </div>
                        <button
                          onClick={() => { setFile(null); auditFileInputRef.current.value = '' }}
                          className="text-purple-600 hover:text-purple-800"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => auditFileInputRef.current?.click()}
                        className="w-full p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition text-center"
                      >
                        <div className="text-3xl mb-2">📹</div>
                        <div className="text-sm text-gray-600">Click to upload video</div>
                        <div className="text-xs text-gray-400">MP4, MOV, WebM</div>
                      </button>
                    )}
                  </div>

                  {/* Start Audit Button */}
                  <button
                    onClick={startAudit}
                    disabled={loading || !file || !unitId.trim() || !auditType}
                    className={`w-full py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${
                      auditType === 'move-out'
                        ? 'bg-purple-600 hover:bg-purple-700 text-white'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Processing Video...
                      </span>
                    ) : (
                      `Start ${auditType === 'move-out' ? 'Move-Out' : 'Move-In'} Audit`
                    )}
                  </button>

                  {/* Help Text */}
                  <p className="text-xs text-gray-500 text-center">
                    {auditType === 'move-out' 
                      ? 'We\'ll compare against the move-in baseline to find new damages.'
                      : 'Record a walkthrough to document the current condition.'}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* FAB Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition hover:scale-105"
          style={{ zIndex: 9999 }}
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      )}
    </div>
  )
}
