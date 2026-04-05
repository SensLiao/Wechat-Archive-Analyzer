const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const path = require('path')

let mainWindow = null
let pythonProcess = null
let sessionToken = null

function startBackend() {
  return new Promise((resolve, reject) => {
    const py = spawn('python', ['-X', 'utf8', '-m', 'wxtools', 'app', 'start', '--no-open', '--port', '8808'], {
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    pythonProcess = py

    let output = ''
    py.stdout.on('data', (data) => {
      output += data.toString()
      // Parse token from output: "Session token: <token>"
      const match = output.match(/Session token: (\S+)/)
      if (match) {
        sessionToken = match[1]
      }
    })

    py.stderr.on('data', (data) => {
      console.error('Python:', data.toString())
    })

    py.on('error', reject)
    py.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        reject(new Error(`Python exited with code ${code}`))
      }
    })

    // Wait for health check
    waitForHealth(resolve, reject, 30) // 30 retries = ~15 seconds
  })
}

function waitForHealth(resolve, reject, retries) {
  if (retries <= 0) {
    reject(new Error('Backend failed to start within timeout'))
    return
  }

  const req = http.get('http://127.0.0.1:8808/api/health', (res) => {
    if (res.statusCode === 200) {
      resolve()
    } else {
      setTimeout(() => waitForHealth(resolve, reject, retries - 1), 500)
    }
  })

  req.on('error', () => {
    setTimeout(() => waitForHealth(resolve, reject, retries - 1), 500)
  })
}

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

  const url = sessionToken
    ? `http://127.0.0.1:8808?token=${sessionToken}`
    : 'http://127.0.0.1:8808'
  mainWindow.loadURL(url)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.on('ready', async () => {
  try {
    await startBackend()
    createWindow()
  } catch (err) {
    dialog.showErrorBox(
      'wxtools Startup Error',
      `Failed to start backend:\n${err.message}\n\nMake sure Python and wxtools are installed.`
    )
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  app.quit()
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
})
