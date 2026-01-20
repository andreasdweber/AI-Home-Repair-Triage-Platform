import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

// Import Tailwind CSS as string for Shadow DOM injection
import tailwindStyles from './index.css?inline'

/**
 * Mount Fix-It AI widget with Shadow DOM isolation
 */
function mountWidget(containerId = 'fixit-widget', config = {}) {
  const container = document.getElementById(containerId)
  
  if (!container) {
    console.error(`[Fix-It AI] Container #${containerId} not found`)
    return null
  }
  
  // Create Shadow DOM
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
    
    .animate-slideUp {
      animation: slideUp 0.2s ease-out;
    }
  `
  shadowRoot.appendChild(style)
  
  // Create mount point
  const mountPoint = document.createElement('div')
  shadowRoot.appendChild(mountPoint)
  
  // Render React app
  const root = createRoot(mountPoint)
  root.render(
    <StrictMode>
      <App config={config} />
    </StrictMode>
  )
  
  return { unmount: () => root.unmount(), shadowRoot }
}

// Auto-mount on DOM ready
const autoMount = () => {
  const target = document.getElementById('fixit-widget') || document.getElementById('root')
  if (target) mountWidget(target.id)
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoMount)
} else {
  autoMount()
}

// Expose for manual mounting
window.FixItAI = { mountWidget }

export { mountWidget }
