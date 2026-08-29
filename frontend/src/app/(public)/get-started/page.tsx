"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function GetStartedPage() {
  const router = useRouter();
  const { loginAsGuest, isAuthenticated, isLoading } = useAuth();
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.replace("/dashboard");
      return;
    }
    if (started.current) return;
    started.current = true;
    let cancelled = false;

    (async () => {
      try {
        await loginAsGuest();
        if (!cancelled) router.replace("/dashboard");
      } catch (err: unknown) {
        started.current = false;
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to initialize session";
        setError(message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isLoading, loginAsGuest, router]);

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div className="glass-panel animate-fade-in-up" style={{ textAlign: "center", maxWidth: 440, padding: 40 }}>
        {error ? (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Could not open workspace</h2>
            <p style={{ color: "var(--error)", marginBottom: 24 }}>{error}</p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <button className="btn btn-primary" onClick={() => { setError(""); started.current = false; window.location.reload(); }}>
                Try again
              </button>
              <Link href="/signup" className="btn btn-secondary">Create an account</Link>
              <Link href="/" className="btn btn-ghost">Return home</Link>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ margin: "0 auto 24px", width: 44, height: 44, borderRadius: "50%", border: "3px solid var(--border-primary)", borderTopColor: "var(--accent)", animation: "spin 1s linear infinite" }} />
            <h2 style={{ fontSize: 24, fontWeight: 700 }}>Get Started</h2>
            <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>Opening your workspace — creating a free guest session. This only takes a moment.</p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 24 }}>
              <Link href="/login" className="btn btn-secondary">Sign in</Link>
              <Link href="/" className="btn btn-ghost">Cancel</Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
