const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')

let mainWindow = null
let backendProcess = null
let connectionInfo = null

/**
 * Resolve the path to the wxtools-backend executable.
 *
 * In development:  Falls back to running Python directly.
 * In production:   Uses the bundled PyInstaller executable from extraResources.
 */
function getBackendPath() {
  if (app.isPackaged) {
    // Production: PyInstaller output is in extraResources/wxtools-backend/
    const resourcePath = process.resourcesPath
    return path.join(resourcePath, 'wxtools-backend', 'wxtools-backend.exe')
  }
  // Development: return null to signal "use python directly"
  return null
}

/**
 * Start the Python backend as a sidecar process.
 *
 * The backend prints a single JSON line to stdout with connection info:
 *   {"host": "127.0.0.1", "port": 8808, "token": "..."}
 *
 * We parse that line and resolve the promise with the connection info.
 */
function startBackend() {
  return new Promise((resolve, reject) => {
    const backendExe = getBackendPath()

    let proc
    if (backendExe) {
      // Production: spawn the bundled executable
      proc = spawn(backendExe, [], {
        stdio: ['pipe', 'pipe', 'pipe'],
        // Prevent console window flash on Windows
        windowsHide: true,
      })
    } else {
      // Development: run via Python
      proc = spawn('python', [
        '-X', 'utf8',
        '-m', 'wxtools.interfaces.desktop',
      ], {
        stdio: ['pipe', 'pipe', 'pipe'],
      })
    }

    backendProcess = proc

    let stdoutBuffer = ''
    let resolved = false

    proc.stdout.on('data', (data) => {
      stdoutBuffer += data.toString()

      // The backend prints a JSON line as its first stdout output
      if (!resolved) {
        const lines = stdoutBuffer.split('\n')
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          try {
            connectionInfo = JSON.parse(trimmed)
            resolved = true
            resolve(connectionInfo)
            break
          } catch {
            // Not JSON yet — might be a partial line or log prefix.
            // Also handle the v5 format: "Session token: <token>"
            const tokenMatch = trimmed.match(/Session token: (\S+)/)
            if (tokenMatch) {
              connectionInfo = {
                host: '127.0.0.1',
                port: 8808,
                token: tokenMatch[1],
              }
              resolved = true
              resolve(connectionInfo)
              break
            }
          }
        }
      }
    })

    proc.stderr.on('data', (data) => {
      // Forward backend stderr to Electron's console for debugging
      console.error('[backend]', data.toString().trimEnd())
    })

    proc.on('error', (err) => {
      if (!resolved) {
        resolved = true
        reject(err)
      }
    })

    proc.on('exit', (code) => {
      if (!resolved && code !== 0 && code !== null) {
        resolved = true
        reject(new Error(`Backend exited with code ${code}`))
      }
    })

    // Timeout: if backend doesn't produce connection info within 30 seconds
    setTimeout(() => {
      if (!resolved) {
        resolved = true
        reject(new Error(
          'Backend did not produce connection info within 30 seconds.\n' +
          `stdout so far: ${stdoutBuffer.slice(0, 500)}`
        ))
      }
    }, 30_000)
  })
}

/**
 * Create the main application window pointing to the backend URL.
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: 'wxtools',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  const { host, port, token } = connectionInfo || {}
  const baseUrl = `http://${host || '127.0.0.1'}:${port || 8808}`
  const url = token ? `${baseUrl}?token=${token}` : baseUrl

  mainWindow.loadURL(url)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

/**
 * Gracefully shut down the backend process.
 */
function killBackend() {
  if (backendProcess) {
    // On Windows, kill() sends SIGTERM which doesn't work for all processes.
    // Use tree-kill pattern: kill the process group.
    try {
      // Send SIGTERM first for graceful shutdown
      backendProcess.kill('SIGTERM')
    } catch {
      // Process may already be dead
    }

    // Force kill after 5 seconds if still alive
    const forceKillTimer = setTimeout(() => {
      try {
        backendProcess.kill('SIGKILL')
      } catch {
        // Already dead
      }
    }, 5000)

    backendProcess.on('exit', () => {
      clearTimeout(forceKillTimer)
    })

    backendProcess = null
  }
}

// --- App lifecycle ---

app.on('ready', async () => {
  try {
    await startBackend()
    createWindow()
  } catch (err) {
    const isPackaged = app.isPackaged
    const hint = isPackaged
      ? 'The bundled backend failed to start. Try reinstalling.'
      : 'Make sure Python and wxtools are installed:\n  pip install -e .'

    dialog.showErrorBox(
      'wxtools Startup Error',
      `Failed to start backend:\n\n${err.message}\n\n${hint}`
    )
    app.quit()
  }
})

app.on('window-all-closed', () => {
  killBackend()
  app.quit()
})

app.on('before-quit', () => {
  killBackend()
})
