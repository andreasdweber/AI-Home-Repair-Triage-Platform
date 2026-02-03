import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TenantWidget from './TenantWidget'
import AdminPortal from './AdminPortal'

/**
 * Fix-It AI - Main App with Routing
 * 
 * Routes:
 * - / : Tenant chat widget (embeddable)
 * - /admin : Property manager admin portal
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Tenant Widget - Chat only, embeddable */}
        <Route path="/" element={<TenantWidget />} />
        
        {/* Admin Portal - Full dashboard for property managers */}
        <Route path="/admin" element={<AdminPortal />} />
        <Route path="/admin/*" element={<AdminPortal />} />
      </Routes>
    </BrowserRouter>
  )
}
