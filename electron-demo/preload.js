const { contextBridge, ipcRenderer } = require('electron');

// 向渲染进程暴露安全的 API
contextBridge.exposeInMainWorld('electronAPI', {
  // 发送消息到主进程
  sendPing: () => {
    ipcRenderer.send('ping');
  },
  // 接收主进程的消息
  onPong: (callback) => {
    ipcRenderer.on('pong', (event, message) => callback(message));
  },
  // 接收文件打开事件
  onFileOpened: (callback) => {
    ipcRenderer.on('file-opened', (event, filePath) => callback(filePath));
  }
});