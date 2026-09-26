const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('keySettings', {
  status: () => ipcRenderer.invoke('openrouter-key-status'),
  save: key => ipcRenderer.invoke('openrouter-key-save', key),
  remove: () => ipcRenderer.invoke('openrouter-key-remove'),
});
