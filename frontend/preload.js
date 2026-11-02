const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  toggleOverlay: () => ipcRenderer.send('toggle-overlay'),
  isOverlayVisible: () => ipcRenderer.invoke('is-overlay-visible'),
  onOverlayToggled: (callback) => ipcRenderer.on('overlay-status', (_event, value) => callback(value))
});

