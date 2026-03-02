import { useState } from "react";
import { login } from "../../api/auth";

interface LoginPageProps {
  onSuccess: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(password);
      onSuccess();
    } catch {
      setError("Invalid password.");
      setPassword("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "var(--bg-base)",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          width: "320px",
          padding: "2.5rem",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-accent)",
          borderRadius: "12px",
        }}
      >
        <div
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "1.5rem",
            fontWeight: 500,
            letterSpacing: "0.18em",
            color: "var(--accent)",
            textAlign: "center",
            marginBottom: "0.5rem",
          }}
        >
          ISTARI
        </div>

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          style={{
            padding: "0.625rem 0.875rem",
            background: "var(--bg-input)",
            border: "1px solid var(--border-default)",
            borderRadius: "6px",
            color: "var(--text-primary)",
            fontSize: "0.9375rem",
            outline: "none",
          }}
        />

        {error && (
          <div
            style={{
              color: "var(--danger)",
              fontSize: "0.8125rem",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          style={{
            padding: "0.625rem",
            background: loading ? "var(--bg-elevated)" : "var(--accent-dim)",
            border: "1px solid var(--border-accent)",
            borderRadius: "6px",
            color: loading ? "var(--text-muted)" : "var(--accent)",
            fontFamily: "'Cinzel', serif",
            fontSize: "0.875rem",
            letterSpacing: "0.1em",
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
