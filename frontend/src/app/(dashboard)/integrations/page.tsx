"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { listIntegrations, Integration } from "@/lib/api";

export default function IntegrationsPage() {
  const { isAuthenticated } = useAuth();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    listIntegrations()
      .then((data) => setIntegrations(data.integrations))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar (Dashboard Style) */}
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
          <Link href="/agents" className="btn btn-ghost">Agents</Link>
        </div>
      </header>

      {/* Content */}
      <main style={{ flex: 1, padding: "60px 40px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
          <div>
            <h1 style={{ fontSize: 32, fontWeight: 800 }}>Integration Marketplace</h1>
            <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>Manage your active MCP connectors or generate new ones dynamically.</p>
          </div>
          <Link href="/integrations/create" className="btn btn-primary btn-lg">
            + Generate New Integration
          </Link>
        </div>

        {loading ? (
          <div className="empty-state">
            <div className="spinner"></div>
            <p style={{ marginTop: 16 }}>Loading integrations...</p>
          </div>
        ) : integrations.length === 0 ? (
          <div className="empty-state glass-card" style={{ padding: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔌</div>
            <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>No integrations yet</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>AgentOS will dynamically build them when needed, or you can create one manually.</p>
            <Link href="/integrations/create" className="btn btn-primary">Generate Integration</Link>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 24 }}>
            {integrations.map((integration) => (
              <div key={integration.mcp_id} className="node-card" style={{ flexDirection: "column", alignItems: "flex-start", padding: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: 16 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ fontSize: 24 }}>🛠️</div>
                    <div>
                      <h3 style={{ fontSize: 18, fontWeight: 700 }}>{integration.name}</h3>
                      <div className="badge badge-success" style={{ marginTop: 4 }}>{integration.trust_tier}</div>
                    </div>
                  </div>
                  <div className={`status-dot ${integration.is_enabled ? "active" : "inactive"}`} />
                </div>
                
                <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20, minHeight: 40 }}>
                  {integration.description || "Dynamically generated MCP connector."}
                </p>

                <div style={{ display: "flex", gap: 12, width: "100%" }}>
                  <button className="btn btn-secondary" style={{ flex: 1 }}>Configure</button>
                  <button className="btn btn-ghost" style={{ padding: "10px" }}>⚙️</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
