const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');

// 创建主窗口
function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // 加载 HTML 文件
  mainWindow.loadFile('index.html');

  // 创建应用菜单
  const menuTemplate = [
    {
      label: '文件',
      submenu: [
        {
          label: '打开文件',
          click: () => {
            dialog.showOpenDialog(mainWindow, {
              properties: ['openFile'],
              filters: [
                { name: '文本文件', extensions: ['txt'] },
                { name: '所有文件', extensions: ['*'] }
              ]
            }).then(result => {
              if (!result.canceled) {
                mainWindow.webContents.send('file-opened', result.filePaths[0]);
              }
            });
          }
        },
        {
          label: '退出',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => app.quit()
        }
      ]
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              title: '关于',
              message: 'Electron 示例应用',
              detail: '版本 1.0.0\n基于 Electron 构建',
              buttons: ['确定']
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  // 开发模式下打开开发者工具
  // mainWindow.webContents.openDevTools();
}

// 应用就绪后创建窗口
app.whenReady().then(() => {
  createWindow();

  // macOS 下点击dock图标重新创建窗口
  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// 关闭所有窗口时退出应用（Windows & Linux）
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// 处理来自渲染进程的消息
ipcMain.on('ping', (event) => {
  event.reply('pong', '来自主进程的响应');
});