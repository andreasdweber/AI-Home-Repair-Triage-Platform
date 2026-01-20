import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

// Import Tailwind CSS as string for Shadow DOM injection
import tailwindStyles from './index.css?inline'

/**
 * Mount Fix-It AI widget with Shadow DOM isolation.
 * Self-mounting: Creates container if it doesn't exist.
 */
function mountWidget(containerId = 'fixit-widget-container', config = {}) {
  // Self-mounting: Create container if it doesn't exist
  let container = document.getElementById(containerId)
  
  if (!container) {
    console.log(`[Fix-It AI] Creating container #${containerId}`)
    container = document.createElement('div')
    container.id = containerId
    document.body.appendChild(container)
  }
  
  // Check if already mounted (prevent double-mounting)
  if (container.shadowRoot) {
    console.log('[Fix-It AI] Widget already mounted')
    return null
  }
  
  // Create Shadow DOM for style isolation
  const shadowRoot = container.attachShadow({ mode: 'open' })
  
  // Inject Tailwind + custom styles into Shadow DOM
  const style = document.createElement('style')
  style.textContent = tailwindStyles + `
    :host {
      all: initial;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes bounce {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-25%); }
    }
    
    .animate-slideUp {
      animation: slideUp 0.2s ease-out;
    }
    
    .animate-bounce {
      animation: bounce 1s infinite;
    }
  `
  shadowRoot.appendChild(style)
  
  // Create mount point for React
  const mountPoint = document.createElement('div')
  shadowRoot.appendChild(mountPoint)
  
  // Render React app into Shadow DOM
  const root = createRoot(mountPoint)
  root.render(
    <StrictMode>
      <App config={config} />
    </StrictMode>
  )
  
  console.log('[Fix-It AI] Widget mounted successfully ✅')
  
  return { unmount: () => root.unmount(), shadowRoot }
}

/**
 * Auto-mount on page load.
 * Creates its own container - works on ANY page without HTML modifications.
 */
function autoMount() {
  // Always create/use our standard container
  mountWidget('fixit-widget-container', {})
}

// Run auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoMount)
} else {
  // DOM already loaded
  autoMount()
}

// Expose to global scope for manual mounting and configuration
window.FixItAI = { mountWidget }

export { mountWidget }
