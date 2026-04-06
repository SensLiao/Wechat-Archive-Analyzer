import { useState, useEffect } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { checkSessionRecovery } from './lib/api'
import Home from './pages/Home'
import Search from './pages/Search'
import Workspace from './pages/Workspace'
import Exports from './pages/Exports'
import Settings from './pages/Settings'

function App() {
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    const msg = checkSessionRecovery()
    if (msg) {
      setToast(msg)
      setTimeout(() => setToast(null), 5000)
    }
  }, [])

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">W</span>
          <span className="sidebar-brand-text">wxtools</span>
        </div>
        <NavLink to="/" className="nav-item" end>工作台</NavLink>
        <NavLink to="/search" className="nav-item">搜索</NavLink>
        <NavLink to="/workspace" className="nav-item">工作区</NavLink>
        <NavLink to="/exports" className="nav-item">导出</NavLink>
        <div className="sidebar-spacer" />
        <NavLink to="/settings" className="nav-item">设置</NavLink>
      </nav>
      <main className="main-content">
        {toast && (
          <div className="toast-bar" onClick={() => setToast(null)}>
            {toast}
          </div>
        )}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/exports" element={<Exports />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
