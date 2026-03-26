import { FormEvent, useMemo, useState } from "react";
import { ErrorBanner } from "../../components/ErrorBanner";

type AuthValues = {
  email: string;
  password: string;
};

type AuthPageProps = {
  pending: boolean;
  error: string | null;
  onLogin: (payload: AuthValues) => Promise<void>;
  onRegister: (payload: AuthValues) => Promise<void>;
};

export function AuthPage({ pending, error, onLogin, onRegister }: AuthPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submitText = mode === "login" ? "Log in" : "Register";
  const cardTitle = useMemo(
    () => (mode === "login" ? "Welcome back to FocusFlow" : "Create your FocusFlow account"),
    [mode]
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload = {
      email: email.trim(),
      password
    };

    if (!payload.email || !payload.password) {
      return;
    }

    try {
      if (mode === "login") {
        await onLogin(payload);
        return;
      }
      await onRegister(payload);
    } catch {
      return;
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card" aria-live="polite">
        <h1>{cardTitle}</h1>
        <p>Plan your projects, move tasks across stages, and stay focused.</p>
        {error ? <ErrorBanner message={error} /> : null}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button type="submit" disabled={pending}>
            {pending ? "Please wait..." : submitText}
          </button>
        </form>

        {mode === "login" ? (
          <button type="button" className="link-button" onClick={() => setMode("register")}>
            Create account
          </button>
        ) : (
          <button type="button" className="link-button" onClick={() => setMode("login")}>
            Already have an account
          </button>
        )}
      </section>
    </main>
  );
}
