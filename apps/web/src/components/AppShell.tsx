import { ReactNode } from "react";

type AppShellProps = {
  userEmail: string;
  onLogout: () => Promise<void>;
  children: ReactNode;
};

export function AppShell({ userEmail, onLogout, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>FocusFlow</h1>
          <p>Welcome, {userEmail}</p>
        </div>
        <button type="button" onClick={onLogout}>
          Log out
        </button>
      </header>
      <div className="app-body">{children}</div>
    </div>
  );
}
