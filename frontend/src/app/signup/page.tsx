"use client";

import { useState, FormEvent, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useGoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const GOOGLE_ENABLED = Boolean(GOOGLE_CLIENT_ID) && GOOGLE_CLIENT_ID !== "dummy-client-id";

function passwordIssues(password: string): string | null {
  if (password.length < 8) return "Password must be at least 8 characters.";
  if (!/[A-Z]/.test(password)) return "Password must include an uppercase letter.";
  if (!/[a-z]/.test(password)) return "Password must include a lowercase letter.";
  if (!/\d/.test(password)) return "Password must include a number.";
  if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) return "Password must include a special character.";
  return null;
}

function GoogleSignupButton({ disabled }: { disabled: boolean }) {
  const { loginWithGoogle } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const googleLogin = useGoogleLogin({
    onSuccess: async (codeResponse) => {
      try {
        setBusy(true);
        await loginWithGoogle(undefined, codeResponse.code);
        router.push("/dashboard");
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Google signup failed");
        setBusy(false);
      }
    },
    flow: "auth-code",
  });

  return (
    <>
      {error && <p style={{ color: "var(--error)", fontSize: 13, marginBottom: 8 }}>{error}</p>}
      <button type="button" className="btn btn-secondary btn-lg" style={{ width: "100%", marginBottom: 12 }} onClick={() => googleLogin()} disabled={disabled || busy}>
        <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
        Sign up with Google
      </button>
    </>
  );
}

function SignupContent() {
  const { signup, isAuthenticated, isLoading, loginAsGuest, user } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isGuest = user?.role === "guest";

  useEffect(() => {
    document.title = "Sign up · AgentOS";
  }, []);

  useEffect(() => {
    if (!isLoading && isAuthenticated && !isGuest) router.replace("/dashboard");
  }, [isAuthenticated, isLoading, isGuest, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const issue = passwordIssues(password);
    if (issue) {
      setError(issue);
      return;
    }
    setError("");
    setLoading(true);
    try {
      await signup(email, password, name);
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Signup failed";
      setError(message.includes("already registered") ? "That email is already registered. Sign in instead." : message);
      setLoading(false);
    }
  }

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="animate-fade-in-up" style={{ width: "100%", maxWidth: 440, padding: "0 20px" }}>
        <Link href="/" className="btn btn-ghost" style={{ marginBottom: 16 }}>← Back to home</Link>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 36, fontWeight: 800, marginBottom: 8 }}>
            <span className="gradient-text">AgentOS</span>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
            Create your autonomous workspace
          </p>
        </div>

        <div className="glass-card glass-lift" style={{ padding: 32 }}>
          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{ padding: "10px 14px", marginBottom: 16, background: "var(--error-subtle)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: 13 }}>
                {error}{" "}
                {error.includes("Sign in") && <Link href="/login" style={{ color: "var(--accent)", fontWeight: 600 }}>Sign in</Link>}
              </div>
            )}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Full Name</label>
              <input type="text" className="input" placeholder="Ada Lovelace" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Email</label>
              <input type="email" className="input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Password</label>
              <input type="password" className="input" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>Must be at least 8 characters, with uppercase, lowercase, number, and special character.</div>
            </div>
            <button type="submit" className="btn btn-primary btn-lg" style={{ width: "100%", marginBottom: 16 }} disabled={loading}>
              {loading ? <span className="spinner" /> : "Create Account"}
            </button>
          </form>

          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "16px 0", color: "var(--text-tertiary)", fontSize: 12 }}>
            <div style={{ flex: 1, height: 1, background: "var(--border-primary)" }} /> OR <div style={{ flex: 1, height: 1, background: "var(--border-primary)" }} />
          </div>

          {GOOGLE_ENABLED && <GoogleSignupButton disabled={loading} />}

          <button type="button" className="btn btn-ghost btn-lg" style={{ width: "100%", border: "1px solid var(--border-primary)" }} onClick={async () => {
            try {
              setLoading(true);
              setError("");
              await loginAsGuest();
              router.push("/dashboard");
            } catch (err: unknown) {
              setError(err instanceof Error ? err.message : "Guest login failed");
              setLoading(false);
            }
          }} disabled={loading}>
            Continue as Guest (Free Trial)
          </button>
        </div>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 14, color: "var(--text-secondary)" }}>
          Already have an account? <Link href="/login" style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 500 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}

export default function SignupPage() {
  if (GOOGLE_ENABLED) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <SignupContent />
      </GoogleOAuthProvider>
    );
  }
  return <SignupContent />;
}
