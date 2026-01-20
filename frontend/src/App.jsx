import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import {
  MessageCircle,
  X,
  Send,
  Image,
  Video,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Wrench,
  ChevronDown,
  Upload,
  Home,
  ClipboardCheck
} from 'lucide-react'

// Default API URL - can be overridden via config
const DEFAULT_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App({ config = {}, shadowRoot }) {
  const apiUrl = config.apiUrl || DEFAULT_API_URL
  const position = config.position || 'bottom-right'

  // Widget state
  const [isOpen, setIsOpen] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  // Chat state
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: "Hi! I'm Fix-It AI 🔧 I can help diagnose maintenance issues or conduct move-in/move-out video audits. What can I help you with today?",
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationHistory, setConversationHistory] = useState([])

  // Image/Video state
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [selectedVideo, setSelectedVideo] = useState(null)

  // Audit mode state
  const [auditMode, setAuditMode] = useState(null) // 'move-in' | 'move-out' | null
  const [unitId, setUnitId] = useState('')
  const [showAuditPanel, setShowAuditPanel] = useState(false)

  // Refs
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const videoInputRef = useRef(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle widget open/close
  const openWidget = () => {
    setIsOpen(true)
    setIsClosing(false)
  }

  const closeWidget = () => {
    setIsClosing(true)
    setTimeout(() => {
      setIsOpen(false)
      setIsClosing(false)
    }, 200)
  }

  // Handle image selection
  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file && file.type.startsWith('image/')) {
      setSelectedImage(file)
      setImagePreview(URL.createObjectURL(file))
    }
  }

  // Handle video selection
  const handleVideoSelect = (e) => {
    const file = e.target.files[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedVideo(file)
    }
  }

  // Clear selected media
  const clearImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const clearVideo = () => {
    setSelectedVideo(null)
    if (videoInputRef.current) videoInputRef.current.value = ''
  }

  // Send chat message
  const sendMessage = async () => {
    if (!inputValue.trim() && !selectedImage) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputValue,
      image: imagePreview,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    // Update conversation history for API
    const newHistory = [...conversationHistory, { role: 'user', content: inputValue }]

    try {
      const formData = new FormData()
      formData.append('message', inputValue)
      formData.append('conversation_history', JSON.stringify(newHistory))

      if (selectedImage) {
        formData.append('image', selectedImage)
      }

      const response = await axios.post(`${apiUrl}/chat`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const { response: aiResponse, diagnosis, risk_level, needs_more_info } = response.data

      // Add AI response to messages
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: aiResponse,
        diagnosis,
        riskLevel: risk_level,
        needsMoreInfo: needs_more_info,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])

      // Update conversation history
      setConversationHistory([
        ...newHistory,
        { role: 'assistant', content: aiResponse }
      ])

      clearImage()
    } catch (err) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        isError: true,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // Handle video audit submission
  const submitVideoAudit = async () => {
    if (!selectedVideo || !unitId.trim() || !auditMode) return

    const loadingMessage = {
      id: Date.now(),
      role: 'assistant',
      content: `Processing ${auditMode} video audit for Unit ${unitId}... This may take a minute.`,
      isLoading: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, loadingMessage])
    setShowAuditPanel(false)
    setIsLoading(true)

    try {
      const formData = new FormData()
      formData.append('video', selectedVideo)
      formData.append('unit_id', unitId)

      const endpoint = auditMode === 'move-in' ? '/audit/move-in' : '/audit/move-out'
      const response = await axios.post(`${apiUrl}${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      // Remove loading message and add result
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== loadingMessage.id)
        return [
          ...filtered,
          {
            id: Date.now() + 1,
            role: 'assistant',
            content: auditMode === 'move-in'
              ? `✅ Move-in audit complete for Unit ${unitId}! I've documented the baseline condition.`
              : `✅ Move-out audit complete for Unit ${unitId}!`,
            auditResult: response.data,
            auditMode,
            timestamp: new Date()
          }
        ]
      })

      // Reset audit state
      clearVideo()
      setUnitId('')
      setAuditMode(null)
    } catch (err) {
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== loadingMessage.id)
        return [
          ...filtered,
          {
            id: Date.now() + 1,
            role: 'assistant',
            content: err.response?.data?.detail || 'Failed to process video audit. Please try again.',
            isError: true,
            timestamp: new Date()
          }
        ]
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Handle enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Get risk level styling
  const getRiskBadge = (level) => {
    const styles = {
      Green: 'bg-green-100 text-green-700 border-green-200',
      Yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      Red: 'bg-red-100 text-red-700 border-red-200'
    }
    return styles[level] || 'bg-gray-100 text-gray-700 border-gray-200'
  }

  return (
    <div className="fixed bottom-4 sm:bottom-6 z-[9999]" style={{ [position === 'bottom-left' ? 'left' : 'right']: '16px' }}>
      {/* Chat Window */}
      {isOpen && (
        <div
          className={`mb-4 w-[360px] sm:w-[400px] h-[600px] max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200 ${isClosing ? 'widget-close' : 'widget-open'}`}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <Wrench className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Fix-It AI</h3>
                <p className="text-xs text-blue-100">Maintenance Assistant</p>
              </div>
            </div>
            <button
              onClick={closeWidget}
              className="p-2 hover:bg-white/10 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-md'
                      : message.isError
                        ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-md'
                        : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md'
                  }`}
                >
                  {/* User's image preview */}
                  {message.image && (
                    <img
                      src={message.image}
                      alt="Uploaded"
                      className="rounded-lg mb-2 max-h-40 object-cover"
                    />
                  )}

                  {/* Message content */}
                  {message.isLoading ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">{message.content}</span>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}

                  {/* Diagnosis card */}
                  {message.diagnosis && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-xl border border-gray-200">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getRiskBadge(message.riskLevel)}`}>
                          {message.riskLevel} Risk
                        </span>
                        {message.diagnosis.severity && (
                          <span className="text-xs text-gray-500">
                            {message.diagnosis.severity} Severity
                          </span>
                        )}
                      </div>
                      <h4 className="font-medium text-sm text-gray-900">{message.diagnosis.issue_title}</h4>
                      {message.diagnosis.estimated_cost_range && (
                        <p className="text-xs text-gray-600 mt-1">
                          Est. Cost: {message.diagnosis.estimated_cost_range}
                        </p>
                      )}
                      {message.diagnosis.recommended_action && (
                        <p className="text-xs text-blue-600 mt-2 flex items-start gap-1">
                          <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          {message.diagnosis.recommended_action}
                        </p>
                      )}
                      {message.diagnosis.safety_warning && message.diagnosis.safety_warning !== 'None' && (
                        <p className="text-xs text-red-600 mt-2 flex items-start gap-1">
                          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          {message.diagnosis.safety_warning}
                        </p>
                      )}
                      {message.diagnosis.can_diy && message.diagnosis.diy_instructions && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <p className="text-xs text-green-600 font-medium">✓ DIY Possible</p>
                          <p className="text-xs text-gray-600 mt-1">{message.diagnosis.diy_instructions}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Audit result card */}
                  {message.auditResult && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-xl border border-gray-200">
                      <div className="flex items-center gap-2 mb-2">
                        <ClipboardCheck className="w-4 h-4 text-green-600" />
                        <span className="text-xs font-medium text-gray-700">
                          {message.auditMode === 'move-in' ? 'Move-In Baseline' : 'Move-Out Report'}
                        </span>
                      </div>
                      {message.auditResult.unit_summary && (
                        <p className="text-xs text-gray-600">{message.auditResult.unit_summary}</p>
                      )}
                      {message.auditResult.existing_damage && message.auditResult.existing_damage.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-amber-600">
                            {message.auditResult.existing_damage.length} pre-existing item(s) noted
                          </p>
                        </div>
                      )}
                      {message.auditResult.new_damages && message.auditResult.new_damages.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-600">
                            {message.auditResult.new_damages.length} new damage(s) found
                          </p>
                          <ul className="mt-1 space-y-1">
                            {message.auditResult.new_damages.slice(0, 3).map((damage, idx) => (
                              <li key={idx} className="text-xs text-gray-600">
                                • {damage.location}: {damage.description}
                              </li>
                            ))}
                            {message.auditResult.new_damages.length > 3 && (
                              <li className="text-xs text-gray-400">
                                +{message.auditResult.new_damages.length - 3} more...
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                      {message.auditResult.total_estimated_deductions && (
                        <p className="text-xs text-gray-700 mt-2 font-medium">
                          Est. Deductions: {message.auditResult.total_estimated_deductions}
                        </p>
                      )}
                      {message.auditResult.comparison_result && (
                        <p className="text-xs text-gray-500 mt-1">
                          Overall: {message.auditResult.comparison_result}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && !messages.some(m => m.isLoading) && (
              <div className="flex justify-start">
                <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-sm border border-gray-100">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Audit Panel */}
          {showAuditPanel && (
            <div className="p-4 bg-blue-50 border-t border-blue-100 flex-shrink-0">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-800">Video Audit</h4>
                <button
                  onClick={() => {
                    setShowAuditPanel(false)
                    clearVideo()
                    setAuditMode(null)
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Audit type selection */}
              <div className="flex gap-2 mb-3">
                <button
                  onClick={() => setAuditMode('move-in')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    auditMode === 'move-in'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <Home className="w-3.5 h-3.5" />
                  Move-In
                </button>
                <button
                  onClick={() => setAuditMode('move-out')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    auditMode === 'move-out'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <ClipboardCheck className="w-3.5 h-3.5" />
                  Move-Out
                </button>
              </div>

              {/* Unit ID input */}
              <input
                type="text"
                value={unitId}
                onChange={(e) => setUnitId(e.target.value)}
                placeholder="Enter Unit ID (e.g., APT-101)"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              />

              {/* Video upload */}
              <div className="mb-3">
                <input
                  ref={videoInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleVideoSelect}
                  className="hidden"
                />
                <button
                  onClick={() => videoInputRef.current?.click()}
                  className="w-full py-2.5 px-4 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-blue-400 hover:bg-white transition-colors flex items-center justify-center gap-2 bg-white/50"
                >
                  <Video className="w-4 h-4" />
                  {selectedVideo ? selectedVideo.name : 'Select Video File'}
                </button>
              </div>

              {/* Submit button */}
              <button
                onClick={submitVideoAudit}
                disabled={!selectedVideo || !unitId.trim() || !auditMode || isLoading}
                className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Start Audit
                  </>
                )}
              </button>
            </div>
          )}

          {/* Image Preview */}
          {imagePreview && (
            <div className="px-4 py-2 bg-gray-100 border-t border-gray-200 flex-shrink-0">
              <div className="relative inline-block">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="h-16 rounded-lg object-cover"
                />
                <button
                  onClick={clearImage}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="p-3 bg-white border-t border-gray-200 flex-shrink-0">
            <div className="flex items-end gap-2">
              {/* Attachment buttons */}
              <div className="flex gap-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleImageSelect}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Attach image"
                >
                  <Image className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setShowAuditPanel(!showAuditPanel)}
                  className={`p-2 rounded-lg transition-colors ${
                    showAuditPanel
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'
                  }`}
                  title="Video audit"
                >
                  <Video className="w-5 h-5" />
                </button>
              </div>

              {/* Text input */}
              <div className="flex-1 relative">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Describe your issue..."
                  rows={1}
                  className="w-full px-4 py-2.5 pr-12 bg-gray-100 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"
                  style={{ maxHeight: '120px' }}
                />
              </div>

              {/* Send button */}
              <button
                onClick={sendMessage}
                disabled={(!inputValue.trim() && !selectedImage) || isLoading}
                className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={isOpen ? closeWidget : openWidget}
        className={`w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 ${
          isOpen
            ? 'bg-gray-700 hover:bg-gray-800 rotate-0'
            : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 fab-pulse'
        }`}
      >
        {isOpen ? (
          <ChevronDown className="w-6 h-6 text-white" />
        ) : (
          <MessageCircle className="w-6 h-6 text-white" />
        )}
      </button>
    </div>
  )
}

export default App
    }
  }

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return <AlertTriangle className="w-4 h-4" />
      case 'medium':
        return <Shield className="w-4 h-4" />
      default:
        return <CheckCircle className="w-4 h-4" />
    }
  }

  const getTradeIcon = (category) => {
    const cat = category?.toLowerCase() || ''
    if (cat.includes('plumb')) return <Droplets className="w-5 h-5" />
    if (cat.includes('electr')) return <Zap className="w-5 h-5" />
    if (cat.includes('hvac') || cat.includes('heat')) return <Flame className="w-5 h-5" />
    return <Wrench className="w-5 h-5" />
  }

  // Format date for admin dashboard
  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // ==================== ADMIN DASHBOARD VIEW ====================
  if (isAdminMode) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-100 to-slate-200">
        {/* Admin Header */}
        <header className="bg-slate-800 shadow-lg">
          <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Fix-It AI Admin</h1>
                <p className="text-slate-400 text-sm">Lead Dashboard</p>
              </div>
            </div>
            <button
              onClick={fetchLeads}
              disabled={isLoadingLeads}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingLeads ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-8">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-xl shadow-md p-6">
              <p className="text-slate-500 text-sm uppercase tracking-wide">Total Leads</p>
              <p className="text-3xl font-bold text-slate-800">{leads.length}</p>
            </div>
            <div className="bg-white rounded-xl shadow-md p-6">
              <p className="text-slate-500 text-sm uppercase tracking-wide">This Week</p>
              <p className="text-3xl font-bold text-blue-600">
                {leads.filter(l => {
                  const date = new Date(l.timestamp)
                  const weekAgo = new Date()
                  weekAgo.setDate(weekAgo.getDate() - 7)
                  return date > weekAgo
                }).length}
              </p>
            </div>
            <div className="bg-white rounded-xl shadow-md p-6">
              <p className="text-slate-500 text-sm uppercase tracking-wide">Today</p>
              <p className="text-3xl font-bold text-green-600">
                {leads.filter(l => {
                  const date = new Date(l.timestamp)
                  const today = new Date()
                  return date.toDateString() === today.toDateString()
                }).length}
              </p>
            </div>
          </div>

          {/* Error Display */}
          {adminError && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">Error Loading Leads</h4>
                <p className="text-red-600 text-sm">{adminError}</p>
              </div>
            </div>
          )}

          {/* Leads Table */}
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h2 className="text-lg font-semibold text-slate-800">All Leads</h2>
            </div>
            
            {isLoadingLeads ? (
              <div className="p-12 text-center">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
                <p className="text-slate-500">Loading leads...</p>
              </div>
            ) : leads.length === 0 ? (
              <div className="p-12 text-center">
                <Database className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No leads yet. They will appear here when users submit the form.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Phone</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Postal Code</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Issue</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Est. Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {leads.map((lead) => (
                      <tr key={lead.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2 text-slate-600 text-sm">
                            <Calendar className="w-4 h-4 text-slate-400" />
                            {formatDate(lead.timestamp)}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="font-medium text-slate-800">{lead.name}</p>
                        </td>
                        <td className="px-6 py-4">
                          <a href={`tel:${lead.phone}`} className="text-blue-600 hover:underline">{lead.phone}</a>
                        </td>
                        <td className="px-6 py-4">
                          <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-sm font-mono">
                            {lead.postal_code}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-medium text-slate-800">{lead.issue_title || 'N/A'}</p>
                            <p className="text-slate-500 text-sm">{lead.issue_category || 'General'}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-green-700 font-medium">{lead.ai_estimated_cost || 'N/A'}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>

        {/* Admin Footer */}
        <footer className="bg-slate-800 mt-16">
          <div className="max-w-6xl mx-auto px-4 py-6 text-center">
            <p className="text-slate-400 text-sm">Fix-It AI Admin Dashboard • {leads.length} total leads</p>
          </div>
        </footer>
      </div>
    )
  }

  // ==================== MAIN APP VIEW ====================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Wrench className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-800">Fix-It AI</span>
          </div>
          <span className="text-sm text-slate-500 hidden sm:block">Smart Home Repair Triage</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <section className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-800 mb-4">
            AI Repair Triage
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Upload a photo of your home repair issue and get an instant AI-powered diagnosis 
            with cost estimates and professional recommendations.
          </p>
        </section>

        {/* Context Input Section */}
        <section className="mb-6 bg-white rounded-2xl shadow-md border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Wrench className="w-5 h-5 text-blue-600" />
            Describe Your Issue (Optional)
          </h2>
          <div className="space-y-4">
            {/* Category Dropdown */}
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-slate-700 mb-2">
                Issue Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full p-3 border border-slate-300 rounded-xl bg-white text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              >
                <option value="">Select a category...</option>
                <option value="Plumbing">🔧 Plumbing</option>
                <option value="Electrical">⚡ Electrical</option>
                <option value="HVAC">🌡️ HVAC (Heating/Cooling)</option>
                <option value="Appliance">🔌 Appliance</option>
                <option value="Structural">🏠 Structural</option>
                <option value="Roofing">🏗️ Roofing</option>
                <option value="Other">❓ Other</option>
              </select>
            </div>

            {/* Description Textarea */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-2">
                Issue Description
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the problem you're experiencing (e.g., 'Water leaking from under the sink when faucet is running')..."
                rows={3}
                className="w-full p-3 border border-slate-300 rounded-xl text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all resize-none"
              />
            </div>
          </div>
        </section>

        {/* Upload Section */}
        <section className="mb-8">
          <div 
            className={`relative border-2 border-dashed rounded-2xl p-8 transition-all duration-300 ${
              imagePreview 
                ? 'border-blue-300 bg-blue-50' 
                : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            {!imagePreview ? (
              <div className="text-center">
                <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Camera className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-700 mb-2">
                  Upload a Photo (Optional)
                </h3>
                <p className="text-slate-500 mb-4">
                  Add an image for better accuracy, or just describe your issue above
                </p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-xl transition-colors duration-200 flex items-center gap-2 mx-auto"
                >
                  <Upload className="w-5 h-5" />
                  Select Image
                </button>
                <p className="text-xs text-slate-400 mt-4">
                  Supports: JPG, PNG, WebP, GIF
                </p>
                {/* Analyze button when no image but has description/category */}
                {(description || category) && (
                  <div className="mt-6 pt-6 border-t border-slate-200">
                    <button
                      onClick={analyzeImage}
                      disabled={isAnalyzing}
                      className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold px-8 py-3 rounded-xl transition-colors duration-200 flex items-center gap-2 mx-auto shadow-lg shadow-green-200"
                    >
                      {isAnalyzing ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Zap className="w-5 h-5" />
                          Analyze Without Photo
                        </>
                      )}
                    </button>
                    <p className="text-xs text-gray-400 mt-3 text-center">
                      Disclaimer: AI estimates are for informational purposes only. Always consult a licensed professional before attempting repairs. Fix-It AI is not liable for damages.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="relative">
                <button
                  onClick={clearImage}
                  className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white p-1.5 rounded-full shadow-lg z-10 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
                <img
                  src={imagePreview}
                  alt="Selected repair issue"
                  className="max-h-80 mx-auto rounded-xl shadow-lg object-contain"
                />
                <div className="mt-6 text-center">
                  <button
                    onClick={analyzeImage}
                    disabled={isAnalyzing}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold px-8 py-3 rounded-xl transition-colors duration-200 flex items-center gap-2 mx-auto shadow-lg shadow-blue-200"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Zap className="w-5 h-5" />
                        Analyze Issue
                      </>
                    )}
                  </button>
                  <p className="text-xs text-gray-400 mt-3 text-center">
                    Disclaimer: AI estimates are for informational purposes only. Always consult a licensed professional before attempting repairs. Fix-It AI is not liable for damages.
                  </p>
                </div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              className="hidden"
            />
          </div>
        </section>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-red-800">Analysis Failed</h4>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Results Card */}
        {analysisResult && (
          <section className="mb-8 animate-in fade-in duration-500">
            <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
              {/* Results Header */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="bg-white/20 p-2 rounded-lg">
                      {getTradeIcon(analysisResult.trade_category)}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white">
                        {analysisResult.issue_title}
                      </h2>
                      <p className="text-blue-100 text-sm">
                        {analysisResult.trade_category}
                      </p>
                    </div>
                  </div>
                  {/* Copy Report Button */}
                  <button
                    onClick={copyReport}
                    className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 text-white text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
                    title="Copy report to clipboard"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Copy Report
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Results Body */}
              <div className="p-6">
                <div className="grid sm:grid-cols-2 gap-4 mb-6">
                  {/* Severity */}
                  <div className={`rounded-xl p-4 border ${getSeverityColor(analysisResult.severity)}`}>
                    <div className="flex items-center gap-2 mb-1">
                      {getSeverityIcon(analysisResult.severity)}
                      <span className="font-medium text-sm uppercase tracking-wide">Severity</span>
                    </div>
                    <p className="text-lg font-bold">{analysisResult.severity}</p>
                  </div>

                  {/* Cost Estimate */}
                  <div className="rounded-xl p-4 border border-slate-200 bg-slate-50">
                    <div className="flex items-center gap-2 mb-1 text-slate-600">
                      <DollarSign className="w-4 h-4" />
                      <span className="font-medium text-sm uppercase tracking-wide">Est. Cost</span>
                    </div>
                    <p className="text-lg font-bold text-slate-800">
                      {analysisResult.estimated_cost_range}
                    </p>
                  </div>
                </div>

                {/* Diagnosis Explanation */}
                {analysisResult.diagnosis_explanation && (
                  <div className="bg-slate-100 rounded-xl p-4 mb-4">
                    <h4 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-blue-600" />
                      Diagnosis
                    </h4>
                    <p className="text-slate-700 leading-relaxed">
                      {analysisResult.diagnosis_explanation}
                    </p>
                  </div>
                )}

                {/* Recommended Action */}
                {analysisResult.recommended_action && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
                    <h4 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      Recommended Action
                    </h4>
                    <p className="text-blue-700 font-medium">
                      {analysisResult.recommended_action}
                    </p>
                  </div>
                )}

                {/* Safety Warning */}
                {analysisResult.safety_warning && analysisResult.safety_warning.toLowerCase() !== 'none' && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-semibold text-amber-800 mb-1">Safety Warning</h4>
                        <p className="text-amber-700 text-sm">{analysisResult.safety_warning}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Lead Capture Form - Only shows after successful analysis */}
        {analysisResult && (
          <section className="animate-in fade-in duration-500 delay-200">
            <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
              {!leadSubmitted ? (
                <>
                  <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-4">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                      <Wrench className="w-6 h-6" />
                      Need a Pro in Vancouver? Get 3 Free Quotes.
                    </h2>
                    <p className="text-green-100 text-sm mt-1">
                      Connect with verified local {analysisResult.trade_category} professionals in minutes
                    </p>
                  </div>
                  <form onSubmit={handleLeadSubmit} className="p-6">
                    <div className="grid sm:grid-cols-3 gap-4 mb-6">
                      {/* Name Input */}
                      <div>
                        <label htmlFor="leadName" className="block text-sm font-medium text-slate-700 mb-2">
                          Your Name
                        </label>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                          <input
                            type="text"
                            id="leadName"
                            value={leadName}
                            onChange={(e) => setLeadName(e.target.value)}
                            placeholder="John Doe"
                            required
                            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-xl text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                          />
                        </div>
                      </div>

                      {/* Phone Input */}
                      <div>
                        <label htmlFor="leadPhone" className="block text-sm font-medium text-slate-700 mb-2">
                          Phone Number
                        </label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                          <input
                            type="tel"
                            id="leadPhone"
                            value={leadPhone}
                            onChange={(e) => setLeadPhone(e.target.value)}
                            placeholder="(555) 123-4567"
                            required
                            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-xl text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                          />
                        </div>
                      </div>

                      {/* Postal Code Input */}
                      <div>
                        <label htmlFor="leadZip" className="block text-sm font-medium text-slate-700 mb-2">
                          Postal Code (e.g. V6B 1A1)
                        </label>
                        <div className="relative">
                          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                          <input
                            type="text"
                            id="leadZip"
                            value={leadZip}
                            onChange={(e) => setLeadZip(e.target.value.toUpperCase())}
                            placeholder="V6B 1A1"
                            required
                            maxLength={7}
                            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-xl text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all uppercase"
                          />
                        </div>
                        <p className="text-xs text-gray-400 mt-1.5">
                          We use this to find pros who are currently available in your specific neighborhood.
                        </p>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmittingLead}
                      className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-4 rounded-xl transition-colors duration-200 flex items-center justify-center gap-2 shadow-lg shadow-green-200"
                    >
                      {isSubmittingLead ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <Phone className="w-5 h-5" />
                          Connect Me
                        </>
                      )}
                    </button>
                  </form>
                </>
              ) : (
                <div className="p-8 text-center">
                  <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-bold text-green-700 mb-2">
                    Success!
                  </h3>
                  <p className="text-slate-600">
                    We are now matching your request with top-rated professionals in <span className="font-semibold">{leadZip}</span>.
                  </p>
                  <p className="text-slate-600 mt-2">
                    You will receive your quotes shortly.
                  </p>
                  <p className="text-slate-500 text-sm mt-4">
                    Expect a call within 24 hours from up to 3 qualified {analysisResult.trade_category} professionals in your area.
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Empty State - Before analysis */}
        {!analysisResult && !isAnalyzing && (
          <section className="text-center py-8">
            <div className="bg-slate-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
              <ImageIcon className="w-10 h-10 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-600 mb-2">
              No analysis yet
            </h3>
            <p className="text-slate-500 max-w-md mx-auto">
              Upload a photo of a leaky pipe, cracked wall, electrical issue, or any home 
              repair problem to get started.
            </p>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <p className="text-slate-500 text-sm">© 2026 Fix-It AI. Powered by Google Gemini.</p>
          <p className="text-xs text-gray-400 mt-2">
            Disclaimer: AI estimates are for informational purposes only. Always consult a licensed professional before attempting repairs. Fix-It AI is not liable for damages.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
