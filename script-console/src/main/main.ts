import path from "node:path";
import { app, BrowserWindow, dialog } from "electron";
import { APP_NAME } from "@shared/constants";
import { AppKernel } from "./services/app-kernel";

let mainWindow: BrowserWindow | null = null;
let kernel: AppKernel | null = null;
let isQuitting = false;

function getRendererEntry(): string {
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    return devServerUrl;
  }
  return path.join(__dirname, "../dist/index.html");
}

async function createWindow(): Promise<void> {
  kernel ??= new AppKernel();

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    show: false,
    backgroundColor: "#09111c",
    title: APP_NAME,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    await mainWindow.loadURL(getRendererEntry());
  } else {
    await mainWindow.loadFile(getRendererEntry());
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  kernel.registerIpc(mainWindow);
  kernel.initialize();
  kernel.trayService.create(mainWindow, {
    onToggleWindow: () => {
      if (!mainWindow) return;
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    },
    onRescan: () => {
      kernel?.scanWorkspace();
    },
    onQuit: () => {
      isQuitting = true;
      app.quit();
    },
  });

  mainWindow.on("close", async (event) => {
    if (isQuitting || !mainWindow || !kernel) {
      return;
    }
    const settings = kernel.settings.get();
    if (settings.closeBehavior === "exit") {
      return;
    }

    event.preventDefault();
    if (settings.closeBehavior === "minimize-to-tray") {
      mainWindow.hide();
      return;
    }

    const choice = await dialog.showMessageBox(mainWindow, {
      type: "question",
      title: "关闭确认",
      message: "要退出脚本中控台吗？",
      detail: "选择“最小化到托盘”可继续在后台监控脚本。",
      buttons: ["最小化到托盘", "退出应用", "取消"],
      defaultId: 0,
      cancelId: 2,
    });

    if (choice.response === 0) {
      mainWindow.hide();
      return;
    }
    if (choice.response === 1) {
      isQuitting = true;
      app.quit();
    }
  });
}

const lock = app.requestSingleInstanceLock();
if (!lock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (!mainWindow.isVisible()) {
        mainWindow.show();
      }
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });
}

app.whenReady().then(async () => {
  await createWindow();
  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("before-quit", () => {
  isQuitting = true;
  kernel?.shutdown();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
