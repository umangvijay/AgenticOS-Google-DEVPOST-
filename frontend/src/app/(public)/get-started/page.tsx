"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function GetStartedPage() {
  const router = useRouter();
  const { loginAsGuest, isAuthenticated } = useAuth();
  const [error, setError] = useState("");
  const hasRun = useRef(false);

  useEffect(() => {
    let mounted = true;
    
    async function initGuest() {
      if (hasRun.current) return;
      hasRun.current = true;
      
      if (isAuthenticated) {
        router.push("/dashboard");
        return;
      }
      
      try {
        await loginAsGuest();
        if (mounted) {
          router.push("/dashboard");
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || "Failed to initialize session");
        }
      }
    }
    
    initGuest();
    
    return () => {
      mounted = false;
    };
  }, [isAuthenticated, loginAsGuest, router]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-primary)" }}>
      <div style={{ textAlign: "center" }}>
        {error ? (
          <div>
            <div style={{ color: "var(--error)", marginBottom: 16 }}>{error}</div>
            <button className="btn btn-primary" onClick={() => router.push("/")}>Return Home</button>
          </div>
        ) : (
          <div>
            <div style={{ margin: "0 auto 24px", width: 40, height: 40, borderRadius: "50%", border: "3px solid var(--border-primary)", borderTopColor: "var(--accent)", animation: "spin 1s linear infinite" }} />
            <h2 style={{ fontSize: 24, fontWeight: 700 }}>Provisioning your workspace...</h2>
            <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>This will only take a second.</p>
          </div>
        )}
      </div>
    </div>
  );
}
