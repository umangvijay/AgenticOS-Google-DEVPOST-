"use client";

import { useState, useEffect } from "react";
import { listIntegrations, Integration } from "@/lib/api";
import Link from "next/link";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const { integrations } = await listIntegrations();
        setIntegrations(integrations);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load integrations");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="animate-fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>Integrations & MCPs</h1>
          <p style={{ color: "var(--text-secondary)" }}>Manage the tools your agents can use.</p>
        </div>
        <Link href="/dashboard/integrations/create" className="btn btn-primary">
          Build New Integration
        </Link>
      </div>

      {error && (
        <div style={{
          padding: "12px 16px", marginBottom: 20,
          background: "var(--error-subtle)", borderRadius: "var(--radius-md)",
          color: "var(--error)", fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 20 }}>
          <div className="skeleton" style={{ height: 160 }} />
          <div className="skeleton" style={{ height: 160 }} />
          <div className="skeleton" style={{ height: 160 }} />
        </div>
      ) : integrations.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 20 }}>
          {integrations.map(mcp => (
            <Link
              key={mcp.mcp_id}
              href={`/dashboard/integrations/${mcp.mcp_id}`}
              className="glass-card"
              style={{ padding: 20, textDecoration: "none", display: "flex", flexDirection: "column" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                  {mcp.name}
                </h3>
                <span className={`badge ${
                  mcp.circuit_breaker?.state === "OPEN" ? "badge-error" : 
                  !mcp.is_enabled ? "badge-neutral" : "badge-success"
                }`}>
                  {mcp.circuit_breaker?.state === "OPEN" ? "Outage" : mcp.is_enabled ? "Active" : "Disabled"}
                </span>
              </div>
              
              <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 20, flex: 1 }}>
                {mcp.description || "No description provided."}
              </p>
              
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-primary)", paddingTop: 16 }}>
                <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                  {mcp.tool_count} tools available
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: mcp.trust_tier === 'verified' ? "var(--success)" : "var(--warning)" }}>
                  Tier: {mcp.trust_tier}
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="glass-card empty-state">
          <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
            <path d="M12 4v16m8-8H4" />
          </svg>
          <h3 style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>No integrations</h3>
          <p style={{ marginBottom: 24 }}>Connect AgentOS to external services by building an MCP.</p>
          <Link href="/dashboard/integrations/create" className="btn btn-primary">Build Integration</Link>
        </div>
      )}
    </div>
  );
}
