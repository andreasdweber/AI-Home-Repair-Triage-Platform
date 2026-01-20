import { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://ai-home-repair-triage-platform.onrender.com'

export default function App() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: "Hi! I'm Fix-It AI 🔧 Describe your issue, attach a photo, or upload a move-in/move-out video for audit." }
  ])
  const [input, setInput] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => `s_${Date.now()}`)
  const [auditMode, setAuditMode] = useState(null) // 'move-in' | 'move-out' | null
  const [unitId, setUnitId] = useState('')
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Check if file is a video
  const isVideoFile = (file) => {
    return file && file.type.startsWith('video/')
  }

  // Handle file selection
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      // If video, prompt for audit mode
      if (isVideoFile(selectedFile)) {
        setAuditMode('move-in') // Default to move-in
      }
    }
  }

  // Send chat message or audit request
  const sendMessage = async () => {
    // For video audit, need unit ID
    if (isVideoFile(file)) {
      if (!unitId.trim()) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'assistant',
          text: '⚠️ Please enter a Unit ID for the video audit.',
          error: true
        }])
        return
      }
      return sendAudit()
    }

    if (!input.trim() && !file) return

    // Add user message
    const userMsg = { id: Date.now(), role: 'user', text: input, file: file?.name }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('text', input)
      if (file) formData.append('file', file)

      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      if (data.session_id) setSessionId(data.session_id)

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: data.response || 'No response',
        risk: data.risk,
        action: data.action
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: '⚠️ Error connecting to server. The server may be waking up (free tier). Please wait 30 seconds and try again.',
        error: true
      }])
    } finally {
      setLoading(false)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // Send video audit request
  const sendAudit = async () => {
    if (!file || !unitId.trim() || !auditMode) return

    const userMsg = { 
      id: Date.now(), 
      role: 'user', 
      text: `🎥 ${auditMode === 'move-in' ? 'Move-In' : 'Move-Out'} Audit for Unit: ${unitId}`,
      file: file.name 
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('unit_id', unitId)
      formData.append('mode', auditMode)
      formData.append('file', file)

      const res = await fetch(`${API_URL}/audit`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      let responseText = ''
      if (data.success) {
        if (auditMode === 'move-in') {
          responseText = `✅ **Move-In Audit Complete**\n\n**Unit:** ${unitId}\n\n**Baseline Summary:**\n${data.summary || 'Documented'}\n\n**Rooms Inspected:** ${data.rooms?.join(', ') || 'N/A'}`
        } else {
          responseText = `✅ **Move-Out Audit Complete**\n\n**Unit:** ${unitId}\n\n**Summary:**\n${data.summary || 'Completed'}\n\n**New Damages:** ${data.new_damages?.length || 0}\n${data.new_damages?.map(d => `• ${d}`).join('\n') || 'None found'}\n\n**Estimated Cost:** $${data.total_estimated_cost || 0}`
        }
      } else {
        responseText = `❌ Audit failed: ${data.error || 'Unknown error'}`
      }

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: responseText,
        auditResult: data
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: '⚠️ Error processing video audit. The server may be waking up. Please wait 30-60 seconds and try again.',
        error: true
      }])
    } finally {
      setLoading(false)
      setFile(null)
      setUnitId('')
      setAuditMode(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const riskColors = {
    Green: 'bg-green-100 text-green-700',
    Yellow: 'bg-yellow-100 text-yellow-700',
    Red: 'bg-red-100 text-red-700'
  }

  return (
    <div className="fixed bottom-5 right-5 z-[9999] font-sans" style={{ zIndex: 9999 }}>
      {/* Chat Window */}
      {isOpen && (
        <div className="mb-3 w-80 sm:w-96 h-[32rem] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden border border-gray-200 animate-slideUp">
          {/* Header */}
          <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
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
                    <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded ${riskColors[msg.risk] || 'bg-gray-100'}`}>
                      {msg.risk}
                    </span>
                  )}
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

          {/* Video Audit Panel */}
          {file && isVideoFile(file) && (
            <div className="px-3 py-2 bg-purple-50 border-t border-purple-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-purple-700 font-medium">🎥 Video Audit Mode</span>
                <button onClick={() => { setFile(null); setAuditMode(null); setUnitId(''); fileInputRef.current.value = '' }} className="text-purple-600 hover:text-purple-800">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <input
                type="text"
                value={unitId}
                onChange={(e) => setUnitId(e.target.value)}
                placeholder="Enter Unit ID (e.g., APT-101)"
                className="w-full px-2 py-1 text-sm border border-purple-200 rounded focus:outline-none focus:border-purple-400"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => setAuditMode('move-in')}
                  className={`flex-1 px-2 py-1 text-xs rounded ${auditMode === 'move-in' ? 'bg-purple-600 text-white' : 'bg-white text-purple-600 border border-purple-300'}`}
                >
                  Move-In
                </button>
                <button
                  onClick={() => setAuditMode('move-out')}
                  className={`flex-1 px-2 py-1 text-xs rounded ${auditMode === 'move-out' ? 'bg-purple-600 text-white' : 'bg-white text-purple-600 border border-purple-300'}`}
                >
                  Move-Out
                </button>
              </div>
              <p className="text-xs text-purple-600 truncate">📁 {file.name}</p>
              <button
                onClick={sendMessage}
                disabled={loading || !unitId.trim()}
                className="w-full py-2 bg-purple-600 text-white text-sm font-medium rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {loading ? 'Processing Video...' : `Start ${auditMode === 'move-out' ? 'Move-Out' : 'Move-In'} Audit`}
              </button>
            </div>
          )}

          {/* Image File preview */}
          {file && !isVideoFile(file) && (
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
                accept="image/*,video/*"
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                title="Attach image or video"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isVideoFile(file) ? "Video selected - click Send" : "Describe the issue..."}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400"
                disabled={loading || isVideoFile(file)}
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
        </div>
      )}

      {/* FAB Button - z-index 9999 */}
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
