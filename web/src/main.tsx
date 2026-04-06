import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/app.css'

// Extract token from URL BEFORE React mounts — prevents race condition
// where stale localStorage token triggers 401 before getToken() runs.
;(function initToken() {
  const params = new URLSearchParams(window.location.search)
  const urlToken = params.get('token')
  if (urlToken) {
    localStorage.setItem('wxtools_token', urlToken)
    // Clean URL to hide token
    window.history.replaceState({}, '', window.location.pathname)
  }
})()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
