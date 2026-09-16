const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('ioViewer', { openInBrowser: file => ipcRenderer.invoke('viewer-open-in-browser', file) });
