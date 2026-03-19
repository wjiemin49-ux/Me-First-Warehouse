import { app } from "electron";

export class StartupService {
  isEnabled(): boolean {
    return app.getLoginItemSettings().openAtLogin;
  }

  setEnabled(enabled: boolean): void {
    app.setLoginItemSettings({
      openAtLogin: enabled,
      path: process.execPath,
      args: [],
    });
  }
}
