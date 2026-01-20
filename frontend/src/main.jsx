import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

// Tailwind CSS styles - will be injected into Shadow DOM
import tailwindStyles from './index.css?inline'

/**
 * Mount the Fix-It AI widget into a container using Shadow DOM.
 * This prevents CSS from bleeding into or from the host site.
 * 
 * @param {string} containerId - The ID of the container element (default: 'fixit-widget')
 * @param {object} config - Optional configuration
 * @param {string} config.apiUrl - Backend API URL
 * @param {string} config.position - Widget position ('bottom-right', 'bottom-left')
 * @param {string} config.primaryColor - Primary theme color
 */
function mountWidget(containerId = 'fixit-widget', config = {}) {
  const container = document.getElementById(containerId)
  
  if (!container) {
    console.error(`[Fix-It AI] Container element #${containerId} not found.`)
    return null
  }
  
  // Create Shadow DOM for style isolation
  const shadowRoot = container.attachShadow({ mode: 'open' })
  
  // Create style element with Tailwind CSS
  const styleElement = document.createElement('style')
  styleElement.textContent = tailwindStyles + `
    /* Widget-specific styles */
    :host {
      all: initial;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    /* Custom scrollbar for widget */
    ::-webkit-scrollbar {
      width: 6px;
    }
    
    ::-webkit-scrollbar-track {
      background: #f1f5f9;
      border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }
    
    /* Animations */
    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(20px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
    
    @keyframes slideDown {
      from {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
      to {
        opacity: 0;
        transform: translateY(20px) scale(0.95);
      }
    }
    
    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
      }
      50% {
        transform: scale(1.05);
      }
    }
    
    @keyframes bounce {
      0%, 100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(-4px);
      }
    }
    
    .widget-open {
      animation: slideUp 0.3s ease-out forwards;
    }
    
    .widget-close {
      animation: slideDown 0.2s ease-in forwards;
    }
    
    .fab-pulse {
      animation: pulse 2s ease-in-out infinite;
    }
    
    .typing-dot {
      animation: bounce 1.4s ease-in-out infinite;
    }
    
    .typing-dot:nth-child(2) {
      animation-delay: 0.2s;
    }
    
    .typing-dot:nth-child(3) {
      animation-delay: 0.4s;
    }
  `
  shadowRoot.appendChild(styleElement)
  
  // Create mount point for React
  const mountPoint = document.createElement('div')
  mountPoint.id = 'fixit-root'
  shadowRoot.appendChild(mountPoint)
  
  // Render React app into Shadow DOM
  const root = createRoot(mountPoint)
  root.render(
    <StrictMode>
      <App config={config} shadowRoot={shadowRoot} />
    </StrictMode>
  )
  
  return {
    unmount: () => root.unmount(),
    shadowRoot
  }
}

// Auto-mount if default container exists
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('fixit-widget')) {
      mountWidget()
    } else if (document.getElementById('root')) {
      // Fallback for development - mount to #root
      mountWidget('root')
    }
  })
} else {
  if (document.getElementById('fixit-widget')) {
    mountWidget()
  } else if (document.getElementById('root')) {
    mountWidget('root')
  }
}

// Expose to global scope for manual mounting
window.FixItAI = { mountWidget }

export { mountWidget }
