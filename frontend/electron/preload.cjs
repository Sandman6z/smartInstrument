// preload.cjs
const { contextBridge } = require('electron')

// 向渲染进程暴露API
contextBridge.exposeInMainWorld('electronAPI', {
  // 这里可以添加需要在前端访问的Electron API
})
