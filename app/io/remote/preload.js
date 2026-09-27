const { contextBridge, ipcRenderer } = require('electron');

const on = (channel, fn) => {
  ipcRenderer.removeAllListeners(channel);
  ipcRenderer.on(channel, (_event, data) => fn(data));
};

contextBridge.exposeInMainWorld('remote', {
  status: () => ipcRenderer.invoke('remote-status'),
  logout: () => ipcRenderer.invoke('remote-logout'),
  login: method => ipcRenderer.invoke('remote-login', method),
  start: opts => ipcRenderer.invoke('remote-start', opts),
  input: data => ipcRenderer.send('remote-input', data),
  resize: (cols, rows) => ipcRenderer.send('remote-resize', { cols, rows }),
  interrupt: () => ipcRenderer.invoke('remote-interrupt'),
  stop: () => ipcRenderer.invoke('remote-stop'),
  end: () => ipcRenderer.invoke('remote-end'),
  files: () => ipcRenderer.invoke('remote-files'),
  attach: () => ipcRenderer.invoke('remote-attach'),
  download: name => ipcRenderer.invoke('remote-download', name),
  openExternal: url => ipcRenderer.invoke('remote-open-external', url),
  onEvent: fn => on('remote-event', fn),
  onStatus: fn => on('remote-status', fn),
  onError: fn => on('remote-error', fn),
});
