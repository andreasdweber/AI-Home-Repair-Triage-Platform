import { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://ai-home-repair-triage-platform.onrender.com'

/**
 * AdminPortal - Property Manager Dashboard
 * Features: Dashboard, Tickets, Audits, Units
 */
export default function AdminPortal() {
  // ─────────────────────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('dashboard')
  
  // Data state
  const [tickets, setTickets] = useState([])
  const [units, setUnits] = useState([])
  const [stats, setStats] = useState({ total: 0, open: 0, dispatched: 0, emergency: 0 })
  const [loading, setLoading] = useState(false)
  
  // Audit state
  const [auditType, setAuditType] = useState(null)
  const [unitId, setUnitId] = useState('')
  const [auditFile, setAuditFile] = useState(null)
  const [auditResults, setAuditResults] = useState(null)
  const [auditLoading, setAuditLoading] = useState(false)
  
  // Selected ticket for detail view
  const [selectedTicket, setSelectedTicket] = useState(null)
  
  const auditFileInputRef = useRef(null)

  // Load data on mount
  useEffect(() => {
    loadData()
  }, [])

  // ─────────────────────────────────────────────────────────────────────────────
  // DATA LOADING
  // ─────────────────────────────────────────────────────────────────────────────
  const loadData = async () => {
    setLoading(true)
    try {
      // Load tickets
      const ticketsRes = await fetch(`${API_URL}/admin/tickets`)
      if (ticketsRes.ok) {
        const ticketsData = await ticketsRes.json()
        setTickets(ticketsData.tickets || [])
        setStats(ticketsData.stats || { total: 0, open: 0, dispatched: 0, emergency: 0 })
      }
      
      // Load units
      const unitsRes = await fetch(`${API_URL}/admin/units`)
      if (unitsRes.ok) {
        const unitsData = await unitsRes.json()
        setUnits(unitsData.units || [])
      }
    } catch (err) {
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // AUDIT HANDLERS
  // ─────────────────────────────────────────────────────────────────────────────
  const handleAuditFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type.startsWith('video/')) {
      setAuditFile(selectedFile)
    }
  }

  const startAudit = async () => {
    if (!auditFile || !unitId.trim() || !auditType) return

    setAuditLoading(true)
    setAuditResults(null)

    try {
      const formData = new FormData()
      formData.append('unit_id', unitId)
      formData.append('mode', auditType)
      formData.append('file', auditFile)

      const res = await fetch(`${API_URL}/audit`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()

      if (data.success) {
        setAuditResults(data)
        // Refresh units list to show new baseline
        loadData()
      } else {
        setAuditResults({ error: data.error || data.detail || 'Audit failed' })
      }
    } catch (err) {
      setAuditResults({ error: 'Error connecting to server. Please try again.' })
    } finally {
      setAuditLoading(false)
    }
  }

  const resetAudit = () => {
    setAuditFile(null)
    setUnitId('')
    setAuditType(null)
    setAuditResults(null)
    if (auditFileInputRef.current) auditFileInputRef.current.value = ''
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: DASHBOARD TAB
  // ─────────────────────────────────────────────────────────────────────────────
  const renderDashboard = () => (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Tickets</p>
              <p className="text-3xl font-bold text-gray-800">{stats.total}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Open</p>
              <p className="text-3xl font-bold text-yellow-600">{stats.open}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Dispatched</p>
              <p className="text-3xl font-bold text-green-600">{stats.dispatched}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Emergency</p>
              <p className="text-3xl font-bold text-red-600">{stats.emergency}</p>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      {/* Recent Tickets */}
      <div className="bg-white rounded-xl shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Recent Tickets</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {tickets.slice(0, 5).map((ticket) => (
            <div 
              key={ticket.id} 
              className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition"
              onClick={() => { setSelectedTicket(ticket); setActiveTab('tickets') }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">#{ticket.id} - {ticket.issue_title || ticket.category || 'Maintenance Request'}</p>
                  <p className="text-sm text-gray-500">{ticket.name} • {ticket.unit_id || 'No unit'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 text-xs rounded ${
                    ticket.priority === 'Red' ? 'bg-red-100 text-red-700' :
                    ticket.priority === 'Yellow' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {ticket.priority || 'Green'}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded ${
                    ticket.status === 'Dispatched' ? 'bg-blue-100 text-blue-700' :
                    ticket.status === 'Escalated' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {ticket.status || 'Open'}
                  </span>
                </div>
              </div>
            </div>
          ))}
          {tickets.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No tickets yet. Tickets will appear here when tenants report issues.
            </div>
          )}
        </div>
      </div>
    </div>
  )

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: TICKETS TAB
  // ─────────────────────────────────────────────────────────────────────────────
  const renderTickets = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Tickets List */}
      <div className="lg:col-span-2 bg-white rounded-xl shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">All Tickets</h2>
          <button 
            onClick={loadData}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Refresh
          </button>
        </div>
        <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
          {tickets.map((ticket) => (
            <div 
              key={ticket.id} 
              className={`px-6 py-4 hover:bg-gray-50 cursor-pointer transition ${selectedTicket?.id === ticket.id ? 'bg-blue-50' : ''}`}
              onClick={() => setSelectedTicket(ticket)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">#{ticket.id} - {ticket.issue_title || ticket.category || 'Maintenance Request'}</p>
                  <p className="text-sm text-gray-500">{ticket.name} • {ticket.phone}</p>
                  {ticket.summary && <p className="text-xs text-gray-400 mt-1 truncate max-w-md">{ticket.summary}</p>}
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={`px-2 py-1 text-xs rounded ${
                    ticket.priority === 'Red' ? 'bg-red-100 text-red-700' :
                    ticket.priority === 'Yellow' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {ticket.priority || 'Green'}
                  </span>
                  <span className="text-xs text-gray-400">
                    {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : ''}
                  </span>
                </div>
              </div>
            </div>
          ))}
          {tickets.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No tickets found.
            </div>
          )}
        </div>
      </div>
      
      {/* Ticket Detail */}
      <div className="bg-white rounded-xl shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Ticket Details</h2>
        </div>
        {selectedTicket ? (
          <div className="p-6 space-y-4">
            <div>
              <p className="text-sm text-gray-500">Ticket #</p>
              <p className="font-medium">{selectedTicket.id}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Tenant</p>
              <p className="font-medium">{selectedTicket.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Contact</p>
              <p className="font-medium">{selectedTicket.phone}</p>
            </div>
            {selectedTicket.unit_id && (
              <div>
                <p className="text-sm text-gray-500">Unit</p>
                <p className="font-medium">{selectedTicket.unit_id}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500">Category</p>
              <p className="font-medium">{selectedTicket.category || 'Other'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span className={`inline-block px-2 py-1 text-xs rounded ${
                selectedTicket.status === 'Dispatched' ? 'bg-blue-100 text-blue-700' :
                selectedTicket.status === 'Escalated' ? 'bg-purple-100 text-purple-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {selectedTicket.status || 'Open'}
              </span>
            </div>
            {selectedTicket.summary && (
              <div>
                <p className="text-sm text-gray-500">Summary</p>
                <p className="text-sm bg-gray-50 p-2 rounded">{selectedTicket.summary}</p>
              </div>
            )}
            {selectedTicket.contact_info && Object.keys(selectedTicket.contact_info).length > 0 && (
              <div>
                <p className="text-sm text-gray-500">Collected Info</p>
                <div className="text-sm bg-gray-50 p-2 rounded space-y-1">
                  {Object.entries(selectedTicket.contact_info).map(([key, value]) => (
                    value && <p key={key}><strong>{key}:</strong> {value}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            Select a ticket to view details
          </div>
        )}
      </div>
    </div>
  )

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: AUDITS TAB
  // ─────────────────────────────────────────────────────────────────────────────
  const renderAudits = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Audit Form */}
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Video Audit</h2>
        
        {auditResults ? (
          <div className="space-y-4">
            {auditResults.error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                <p className="font-medium">❌ Error</p>
                <p className="text-sm">{auditResults.error}</p>
              </div>
            ) : (
              <>
                <div className={`rounded-lg p-4 ${
                  auditType === 'move-in' ? 'bg-blue-50 border border-blue-200' :
                  (auditResults.items?.filter(i => i.is_new)?.length > 0) ? 'bg-red-50 border border-red-200' :
                  'bg-green-50 border border-green-200'
                }`}>
                  <div className="flex items-center gap-2 font-medium">
                    {auditType === 'move-in' ? (
                      <><svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" /></svg> Move-In Baseline Created</>
                    ) : (auditResults.items?.filter(i => i.is_new)?.length > 0) ? (
                      <><svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg> {auditResults.items?.filter(i => i.is_new)?.length} New Damages Found</>
                    ) : (
                      <><svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> No New Damages Found</>
                    )}
                  </div>
                  <p className="text-sm mt-1 opacity-80">{auditResults.summary}</p>
                  {auditResults.total_estimated_cost > 0 && (
                    <p className="text-sm font-medium mt-2 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      Estimated Cost: ${auditResults.total_estimated_cost}
                    </p>
                  )}
                </div>
                
                {/* Items List */}
                {auditResults.items?.length > 0 && (
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 font-medium text-sm flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      Detected Items ({auditResults.items.length})
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {auditResults.items.map((item, idx) => (
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
                            {item.timestamp && <span className="flex items-center gap-1"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>{item.timestamp}</span>}
                            {item.estimated_cost > 0 && <span className="flex items-center gap-1"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>${item.estimated_cost}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
            
            <button
              onClick={resetAudit}
              className="w-full py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              Start New Audit
            </button>
          </div>
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
                  className={`p-4 rounded-lg border-2 transition text-center ${
                    auditType === 'move-in'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-3xl mb-1">📥</div>
                  <div className="font-medium">Move-In</div>
                  <div className="text-xs text-gray-500">Create baseline</div>
                </button>
                <button
                  onClick={() => setAuditType('move-out')}
                  className={`p-4 rounded-lg border-2 transition text-center ${
                    auditType === 'move-out'
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-3xl mb-1">📤</div>
                  <div className="font-medium">Move-Out</div>
                  <div className="text-xs text-gray-500">Compare damages</div>
                </button>
              </div>
            </div>

            {/* Unit ID */}
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
              {auditFile ? (
                <div className="flex items-center justify-between p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="flex items-center gap-2 text-purple-700">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm truncate max-w-[200px]">{auditFile.name}</span>
                  </div>
                  <button
                    onClick={() => { setAuditFile(null); auditFileInputRef.current.value = '' }}
                    className="text-purple-600 hover:text-purple-800"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => auditFileInputRef.current?.click()}
                  className="w-full p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition text-center"
                >
                  <div className="w-12 h-12 mx-auto mb-2 bg-gray-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="text-sm text-gray-600">Click to upload video</div>
                  <div className="text-xs text-gray-400">MP4, MOV, WebM</div>
                </button>
              )}
            </div>

            {/* Start Button */}
            <button
              onClick={startAudit}
              disabled={auditLoading || !auditFile || !unitId.trim() || !auditType}
              className={`w-full py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${
                auditType === 'move-out'
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {auditLoading ? (
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
          </div>
        )}
      </div>
      
      {/* Units with Baselines */}
      <div className="bg-white rounded-xl shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Units with Baselines</h2>
        </div>
        <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
          {units.map((unit) => (
            <div key={unit.id} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">{unit.unit_id}</p>
                  <p className="text-sm text-gray-500">
                    Baseline: {unit.last_updated ? new Date(unit.last_updated).toLocaleDateString() : 'Available'}
                  </p>
                </div>
                <button
                  onClick={() => { setUnitId(unit.unit_id); setAuditType('move-out') }}
                  className="text-sm text-purple-600 hover:text-purple-700"
                >
                  Run Move-Out →
                </button>
              </div>
            </div>
          ))}
          {units.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No unit baselines yet. Run a move-in audit to create one.
            </div>
          )}
        </div>
      </div>
    </div>
  )

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: MAIN
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-800">Fix-It AI Admin</h1>
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
                activeTab === 'dashboard'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('tickets')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
                activeTab === 'tickets'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Tickets
            </button>
            <button
              onClick={() => setActiveTab('audits')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
                activeTab === 'audits'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Audits
            </button>
          </nav>
        </div>
      </div>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && renderDashboard()}
            {activeTab === 'tickets' && renderTickets()}
            {activeTab === 'audits' && renderAudits()}
          </>
        )}
      </main>
    </div>
  )
}
