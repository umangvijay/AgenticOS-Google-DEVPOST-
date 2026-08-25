"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { isAuthenticated, user, logout } = useAuth();

  if (!isAuthenticated) return null;

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{
        padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: "1px solid var(--border-primary)", backdropFilter: "blur(12px)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: "8px",
            background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, fontWeight: 800, color: "white",
            boxShadow: "0 0 15px rgba(236, 72, 153, 0.4)"
          }}>
            A
          </div>
          <span style={{ fontSize: 20, fontWeight: 700 }} className="gradient-text">
            AgentOS Workspace
          </span>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          <Link href="/dashboard" className="btn btn-ghost">Dashboard</Link>
          <button onClick={logout} className="btn btn-secondary">Sign Out</button>
        </div>
      </header>

      <main style={{ flex: 1, padding: "60px 40px", maxWidth: 800, margin: "0 auto", width: "100%" }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 40 }}>Workspace Settings</h1>

        <div className="glass-card" style={{ padding: 32, marginBottom: 24 }}>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Profile Information</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Email Address</label>
              <input type="email" className="input" defaultValue={user?.email} disabled style={{ opacity: 0.7 }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Role</label>
              <div className="badge badge-info">{user?.role}</div>
            </div>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 32, marginBottom: 24 }}>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Security & Authentication</h3>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 16, borderBottom: "1px solid var(--border-primary)" }}>
            <div>
              <div style={{ fontWeight: 600 }}>Two-Factor Authentication (TOTP)</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Secure your account using an authenticator app.</div>
            </div>
            <button className="btn btn-primary btn-sm">Enable 2FA</button>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 16 }}>
            <div>
              <div style={{ fontWeight: 600 }}>Active Sessions</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Manage devices logged into your account.</div>
            </div>
            <button className="btn btn-secondary btn-sm">Revoke All</button>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 32 }}>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Agent Preferences</h3>
          
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Default Autonomy Level</label>
            <select className="input" style={{ appearance: "none" }}>
              <option value="L0">L0 - Suggest Only</option>
              <option value="L1">L1 - Wait for Approval</option>
              <option value="L2">L2 - Auto-run Reads, Wait for Writes</option>
              <option value="L3">L3 - Fully Autonomous</option>
            </select>
          </div>
        </div>

      </main>
    </div>
  );
}
