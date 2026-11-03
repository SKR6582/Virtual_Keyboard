const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { spawn, spawnSync } = require('child_process');
const net = require('net');

let mainWindow = null;
let overlayWindow = null;
let pythonProcess = null;

function resolvePythonPath(projectRoot) {
  if (process.env.PYTHON_PATH && fs.existsSync(process.env.PYTHON_PATH)) {
    return process.env.PYTHON_PATH;
  }

  const homedir = os.homedir();
  const isWin = process.platform === 'win32';
  const binName = isWin ? 'python.exe' : 'python3';
  const scriptsBinName = isWin ? 'python.exe' : 'python';

  const candidates = [
    path.join(projectRoot, '.venv', isWin ? 'Scripts' : 'bin', scriptsBinName),
    path.join(projectRoot, 'venv', isWin ? 'Scripts' : 'bin', scriptsBinName),
    process.env.CONDA_PREFIX ? path.join(process.env.CONDA_PREFIX, isWin ? 'python.exe' : 'bin/python3') : null,
    '/opt/anaconda3/bin/python3',
    path.join(homedir, 'anaconda3', 'bin', 'python3'),
    path.join(homedir, 'miniconda3', 'bin', 'python3'),
    path.join(homedir, 'miniforge3', 'bin', 'python3'),
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    isWin ? 'python' : 'python3'
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (path.isAbsolute(candidate) && !fs.existsSync(candidate)) {
      continue;
    }
    try {
      const res = spawnSync(candidate, ['-c', 'import mediapipe as mp; assert hasattr(mp, "solutions")'], {
        stdio: 'ignore',
        timeout: 2500
      });
      if (res.status === 0) {
        console.log(`Auto-detected compatible Python interpreter: ${candidate}`);
        return candidate;
      }
    } catch {
      // Continue search
    }
  }

  console.warn('Could not verify mediapipe solutions API on candidate interpreters; defaulting to system python.');
  return isWin ? 'python' : 'python3';
}

function checkPortInUse(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(800);
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => {
      resolve(false);
    });
    socket.connect(port, host);
  });
}

async function startPythonBackend() {
  const isRunning = await checkPortInUse(8765);
  if (isRunning) {
    console.log('Python backend already running on port 8765.');
    return;
  }

  const projectRoot = path.join(__dirname, '..');
  const pythonCmd = resolvePythonPath(projectRoot);

  console.log(`Spawning Python backend using: ${pythonCmd}...`);
  pythonProcess = spawn(pythonCmd, ['-m', 'backend.app'], {
    cwd: projectRoot,
    stdio: 'inherit'
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python backend:', err);
  });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1300,
    height: 880,
    minWidth: 1000,
    minHeight: 700,
    title: 'CV-Type Virtual Keyboard',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (overlayWindow) {
      overlayWindow.close();
    }
  });
}

function createOverlayWindow() {
  overlayWindow = new BrowserWindow({
    width: 480,
    height: 280,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  overlayWindow.loadFile(path.join(__dirname, 'src', 'overlay.html'));
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  overlayWindow.setAlwaysOnTop(true, 'screen-saver');

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });
}

function toggleOverlay() {
  if (!overlayWindow) {
    createOverlayWindow();
    return true;
  }
  if (overlayWindow.isVisible()) {
    overlayWindow.hide();
    return false;
  } else {
    overlayWindow.show();
    return true;
  }
}

app.whenReady().then(async () => {
  await startPythonBackend();
  createMainWindow();
  createOverlayWindow();

  // Global hotkey to toggle HUD overlay
  globalShortcut.register('CommandOrControl+Shift+O', () => {
    const isVisible = toggleOverlay();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('overlay-status', isVisible);
    }
  });

  ipcMain.on('toggle-overlay', () => {
    const isVisible = toggleOverlay();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('overlay-status', isVisible);
    }
  });

  ipcMain.handle('is-overlay-visible', () => {
    return overlayWindow ? overlayWindow.isVisible() : false;
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    console.log('Terminating Python backend process...');
    pythonProcess.kill();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

