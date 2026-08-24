const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('io', { pickFolder: () => ipcRenderer.invoke('pick-folder') });
