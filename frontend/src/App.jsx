import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { 
  Upload, 
  Camera, 
  AlertTriangle, 
  DollarSign, 
  Wrench, 
  Shield,
  Phone,
  CheckCircle,
  Loader2,
  ImageIcon,
  X,
  Zap,
  Droplets,
  Flame,
  Hammer,
  Copy,
  Check,
  MapPin,
  User,
  Calendar,
  RefreshCw,
  Database
} from 'lucide-react'

// Backend API URL - uses environment variable in production
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [error, setError] = useState(null)
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const fileInputRef = useRef(null)

  // Lead form state
  const [leadName, setLeadName] = useState('')
  const [leadPhone, setLeadPhone] = useState('')
  const [leadZip, setLeadZip] = useState('')
  const [leadSubmitted, setLeadSubmitted] = useState(false)
  const [isSubmittingLead, setIsSubmittingLead] = useState(false)

  // Copy to clipboard state
  const [copied, setCopied] = useState(false)

  // Admin dashboard state
  const [isAdminMode, setIsAdminMode] = useState(false)
  const [leads, setLeads] = useState([])
  const [isLoadingLeads, setIsLoadingLeads] = useState(false)
  const [adminError, setAdminError] = useState(null)

  // Check for admin mode on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('admin') === 'true') {
      setIsAdminMode(true)
      fetchLeads()
    }
  }, [])

  // Fetch leads for admin dashboard
  const fetchLeads = async () => {
    setIsLoadingLeads(true)
    setAdminError(null)
    try {
      const response = await axios.get(`${API_URL}/leads?admin_key=secret123`)
      setLeads(response.data.leads || [])
    } catch (err) {
      setAdminError(err.response?.data?.detail || 'Failed to fetch leads')
    } finally {
      setIsLoadingLeads(false)
    }
  }

  // Handle lead form submission - now sends to backend
  const handleLeadSubmit = async (e) => {
    e.preventDefault()
    if (!leadName || !leadPhone || !leadZip) return

    setIsSubmittingLead(true)
    try {
      await axios.post(`${API_URL}/leads`, {
        name: leadName,
        phone: leadPhone,
        postal_code: leadZip,
        issue_category: analysisResult?.trade_category || category || null,
        issue_title: analysisResult?.issue_title || null,
        issue_description: description || null,
        ai_estimated_cost: analysisResult?.estimated_cost_range || null,
        ai_severity: analysisResult?.severity || null,
        ai_recommended_action: analysisResult?.recommended_action || null
      })
      setLeadSubmitted(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit request. Please try again.')
    } finally {
      setIsSubmittingLead(false)
    }
  }

  // Copy report to clipboard
  const copyReport = async () => {
    if (!analysisResult) return
    
    const reportText = `[Fix-It AI Report - Vancouver]
Issue: ${analysisResult.issue_title}
Severity: ${analysisResult.severity}
Est. Cost: ${analysisResult.estimated_cost_range}
Action: ${analysisResult.recommended_action || 'N/A'}`
    
    try {
      await navigator.clipboard.writeText(reportText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleImageSelect = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSelectedImage(file)
      setImagePreview(URL.createObjectURL(file))
      setAnalysisResult(null)
      setError(null)
    }
  }

  const handleDrop = (event) => {
    event.preventDefault()
    const file = event.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      setSelectedImage(file)
      setImagePreview(URL.createObjectURL(file))
      setAnalysisResult(null)
      setError(null)
    }
  }

  const handleDragOver = (event) => {
    event.preventDefault()
  }

  const clearImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    setAnalysisResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const analyzeImage = async () => {
    // Allow submission if we have an image OR a description/category
    if (!selectedImage && !description && !category) {
      setError('Please provide an image, description, or select a category to analyze.')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    const formData = new FormData()
    if (selectedImage) {
      formData.append('image', selectedImage)
    }
    formData.append('description', description)
    formData.append('category', category)

    try {
      const response = await axios.post(`${API_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      setAnalysisResult(response.data.analysis)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
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
