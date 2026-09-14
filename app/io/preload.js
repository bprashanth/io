const { contextBridge, ipcRenderer } = require('electron');
// What the page may ask the shell for. Terminal bytes and status strings cross this bridge;
// paths, ports and credentials are decided on the other side.
contextBridge.exposeInMainWorld('io', {
  pickFolder: () => ipcRenderer.invoke('pick-folder'),
  openExternal: url => ipcRenderer.invoke('open-external', url),
  codex: {
    status: () => ipcRenderer.invoke('codex-status'),
    login: mode => ipcRenderer.invoke('codex-login', mode),
    cancelLogin: () => ipcRenderer.invoke('codex-login-cancel'),
    logout: () => ipcRenderer.invoke('codex-logout'),
    start: opts => ipcRenderer.invoke('codex-start', opts),
    stop: () => ipcRenderer.invoke('codex-stop'),
    input: data => ipcRenderer.send('codex-input', data),
    resize: (cols, rows) => ipcRenderer.send('codex-resize', { cols, rows }),
    onData: fn => { ipcRenderer.removeAllListeners('codex-data'); ipcRenderer.on('codex-data', (_e, d) => fn(d)); },
    onExit: fn => { ipcRenderer.removeAllListeners('codex-exit'); ipcRenderer.on('codex-exit', (_e, d) => fn(d)); },
    onLoginEvent: fn => { ipcRenderer.removeAllListeners('codex-login-event'); ipcRenderer.on('codex-login-event', (_e, d) => fn(d)); },
  },
});
