import { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://ai-home-repair-triage-platform.onrender.com'

/**
 * TenantWidget - Demo landing page with centered chat for maintenance triage
 */
export default function TenantWidget() {
  // ─────────────────────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: "Hi! I'm Fix-It AI 🔧 Describe your issue or attach a photo. I'll help create a complete work order for your property manager." }
  ])
  const [input, setInput] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => `s_${Date.now()}`)
  
  // Slot-filling state
  const [filledSlots, setFilledSlots] = useState({})
  const [missingInfo, setMissingInfo] = useState([])
  const [requestPhoto, setRequestPhoto] = useState(false)
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false)
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Reset function for new conversation
  const resetConversation = () => {
    setMessages([{ id: 1, role: 'assistant', text: "Hi! I'm Fix-It AI 🔧 Describe your issue or attach a photo. I'll help create a complete work order for your property manager." }])
    setSessionId(`s_${Date.now()}`)
    setFilledSlots({})
    setMissingInfo([])
    setRequestPhoto(false)
    setAwaitingConfirmation(false)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ─────────────────────────────────────────────────────────────────────────────
  // CHAT HANDLERS
  // ─────────────────────────────────────────────────────────────────────────────
  const isImageFile = (f) => f && f.type.startsWith('image/')

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && isImageFile(selectedFile)) {
      setFile(selectedFile)
      setRequestPhoto(false) // Clear photo request once uploaded
    }
  }

  const sendMessage = async () => {
    if (!input.trim() && !file) return

    const userMsg = { id: Date.now(), role: 'user', text: input, file: file?.name }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('text', input)
      formData.append('escalation_mode', 'false')
      formData.append('contact_info', JSON.stringify({}))
      if (file && isImageFile(file)) formData.append('file', file)

      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      if (data.session_id) setSessionId(data.session_id)
      if (data.filled_slots) setFilledSlots(data.filled_slots)
      if (data.missing_info) setMissingInfo(data.missing_info)
      if (data.request_photo) setRequestPhoto(data.request_photo)
      if (data.awaiting_confirmation) setAwaitingConfirmation(data.awaiting_confirmation)

      // Handle CREATE_TICKET action - show success card
      if (data.action === 'CREATE_TICKET') {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          text: data.response,
          ticketCreated: true,
          ticketId: data.ticket_id,
          ticketData: data.ticket_data
        }])
        // Reset state for new conversation
        setFilledSlots({})
        setMissingInfo([])
        setAwaitingConfirmation(false)
      } else if (data.action === 'EMERGENCY') {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          text: data.response,
          risk: 'Red',
          isEmergency: true
        }])
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          text: data.response || 'No response',
          risk: data.risk,
          action: data.action,
          category: data.category,
          requestPhoto: data.request_photo
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
      <p className="text-sm text-green-600 mt-1">A maintenance professional will contact you soon.</p>
      {msg.ticketData && (
        <div className="text-xs text-gray-600 mt-2 bg-white p-2 rounded border space-y-1">
          {msg.ticketData.issue && <p>📋 <strong>Issue:</strong> {msg.ticketData.issue}</p>}
          {msg.ticketData.location && <p>📍 <strong>Location:</strong> {msg.ticketData.location}</p>}
          {msg.ticketData.unit && <p>🏠 <strong>Unit:</strong> {msg.ticketData.unit}</p>}
        </div>
      )}
    </div>
  )

  const renderProgressBar = () => {
    const totalSlots = 7
    const filledCount = Object.values(filledSlots).filter(v => v !== null && v !== undefined).length
    const progress = (filledCount / totalSlots) * 100
    
    if (filledCount === 0) return null
    
    return (
      <div className="px-3 py-2 bg-blue-50 border-b border-blue-100">
        <div className="flex items-center justify-between text-xs text-blue-700 mb-1">
          <span>Work order progress</span>
          <span>{filledCount}/{totalSlots} details collected</span>
        </div>
        <div className="w-full bg-blue-200 rounded-full h-1.5">
          <div 
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-300" 
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {/* Hero Section */}
      <div className="pt-12 pb-6 px-4 text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <span className="text-5xl">🔧</span>
          <h1 className="text-4xl font-bold text-gray-800">Fix-It AI</h1>
        </div>
        <p className="text-xl text-gray-600 mb-2">AI-Powered Maintenance Triage</p>
        <p className="text-gray-500 max-w-md mx-auto">
          Report issues in seconds. Our AI collects all the details your property manager needs.
        </p>
      </div>

      {/* Centered Chat Widget */}
      <div className="flex justify-center px-4 pb-8">
        <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl flex flex-col overflow-hidden border border-gray-200" style={{ height: '500px' }}>
          {/* Header */}
          <div className="bg-blue-600 text-white flex-shrink-0">
            <div className="px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">💬</span>
                <span className="font-semibold">Maintenance Chat</span>
              </div>
              <button 
                onClick={resetConversation}
                className="text-xs bg-blue-500 hover:bg-blue-400 px-3 py-1 rounded-full transition"
              >
                New Report
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {renderProgressBar()}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : msg.error 
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : msg.isEmergency
                        ? 'bg-red-100 text-red-800 border border-red-300'
                        : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.file && <p className="text-xs mt-1 opacity-70">📎 {msg.file}</p>}
                  {msg.risk && !msg.ticketCreated && (
                    <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded border ${riskColors[msg.risk] || 'bg-gray-100'}`}>
                      {msg.risk} {msg.category && `• ${msg.category}`}
                    </span>
                  )}
                  {msg.requestPhoto && (
                    <div className="mt-2 p-2 bg-yellow-50 rounded border border-yellow-200 text-xs text-yellow-700">
                      📷 A photo would help assess this issue
                    </div>
                  )}
                  {msg.ticketCreated && renderTicketCard(msg)}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
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

          {/* Photo Request Banner */}
          {requestPhoto && !file && (
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-yellow-50 border-t border-yellow-200 flex items-center justify-between cursor-pointer hover:bg-yellow-100 transition"
            >
              <span className="text-sm text-yellow-700">📷 Tap to add a photo of the issue</span>
              <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
          )}

          {/* Image Preview */}
          {file && isImageFile(file) && (
            <div className="px-4 py-2 bg-blue-50 border-t border-blue-100 flex items-center justify-between">
              <span className="text-sm text-blue-700 truncate">📎 {file.name}</span>
              <button onClick={() => { setFile(null); fileInputRef.current.value = '' }} className="text-blue-600 hover:text-blue-800">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-gray-200 bg-white flex-shrink-0">
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
                className={`p-2.5 rounded-lg transition ${requestPhoto ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100' : 'text-gray-500 hover:text-blue-600 hover:bg-blue-50'}`}
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
                placeholder={awaitingConfirmation ? "Type 'yes' to confirm..." : "Describe your issue..."}
                className="flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || (!input.trim() && !file)}
                className="p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Highlights */}
      <div className="max-w-3xl mx-auto px-4 pb-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">🎯</div>
            <div className="text-sm font-medium text-gray-800">Smart Triage</div>
            <div className="text-xs text-gray-500">AI categorizes urgency</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">📷</div>
            <div className="text-sm font-medium text-gray-800">Photo Support</div>
            <div className="text-xs text-gray-500">Attach images</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">⚡</div>
            <div className="text-sm font-medium text-gray-800">Instant Tickets</div>
            <div className="text-xs text-gray-500">Complete work orders</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">🔒</div>
            <div className="text-sm font-medium text-gray-800">Secure</div>
            <div className="text-xs text-gray-500">Data protected</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center pb-8 text-xs text-gray-400">
        Powered by Fix-It AI • Property Maintenance Made Simple
      </div>
    </div>
  )
}
