import { BrowserWindow, Menu, Tray, nativeImage } from "electron";

function createTrayImage() {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="6" y="6" width="52" height="52" rx="12" fill="#0f172a"/>
      <path d="M20 20h24v6H20zm0 12h24v6H20zm0 12h16v6H20z" fill="#60a5fa"/>
      <circle cx="47" cy="47" r="5" fill="#34d399"/>
    </svg>
  `;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`);
}

export class TrayService {
  private tray?: Tray;

  create(
    window: BrowserWindow,
    callbacks: {
      onToggleWindow: () => void;
      onRescan: () => void;
      onQuit: () => void;
    },
  ): void {
    this.tray?.destroy();
    this.tray = new Tray(createTrayImage());
    this.tray.setToolTip("Script Console");
    const buildMenu = () =>
      Menu.buildFromTemplate([
        {
          label: window.isVisible() ? "隐藏窗口" : "显示窗口",
          click: callbacks.onToggleWindow,
        },
        {
          label: "重新扫描脚本",
          click: callbacks.onRescan,
        },
        { type: "separator" },
        {
          label: "退出",
          click: callbacks.onQuit,
        },
      ]);

    this.tray.setContextMenu(buildMenu());
    this.tray.on("click", () => {
      callbacks.onToggleWindow();
      this.tray?.setContextMenu(buildMenu());
    });
  }

  destroy(): void {
    this.tray?.destroy();
    this.tray = undefined;
  }
}
