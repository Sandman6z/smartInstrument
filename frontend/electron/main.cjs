const { app, BrowserWindow } = require('electron')
const path = require('path')

// 禁用硬件加速（可能有助于解决某些系统上的崩溃问题）
app.disableHardwareAcceleration()

// 创建主窗口
function createWindow () {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false // 禁用 web 安全策略，允许加载本地文件
    },
    title: '智能仪器测试系统',
    // 禁用自动更新检查
    autoHideMenuBar: true
  })

  // 加载前端页面
  mainWindow.loadURL('http://localhost:3000')

  // 打开开发者工具（可选）
  // mainWindow.webContents.openDevTools()
}

// 应用启动时创建窗口
app.whenReady().then(() => {
  createWindow()

  // macOS 特殊处理
  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// 关闭所有窗口时退出应用
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  console.error('未捕获的异常:', error)
})

