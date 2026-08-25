"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getIntegration, enableIntegration, disableIntegration, deleteIntegration, testIntegration, Integration } from "@/lib/api";

export default function IntegrationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const mcpId = params.mcp_id as string;

  const [mcp, setMcp] = useState<Integration & { tools: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testing, setTesting] = useState(false);

  async function load() {
    try {
      const data = await getIntegration(mcpId);
      setMcp(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load integration");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [mcpId]);

  const handleToggle = async () => {
    if (!mcp) return;
    try {
      if (mcp.is_enabled) {
        await disableIntegration(mcpId);
      } else {
        await enableIntegration(mcpId);
      }
      await load();
    } catch (err) {
      alert("Failed to toggle state: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      await testIntegration(mcpId);
      await load();
    } catch (err) {
      alert("Test failed: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this integration? This will break workflows depending on it.")) return;
    try {
      await deleteIntegration(mcpId);
      router.push("/dashboard/integrations");
    } catch (err) {
      alert("Delete failed: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 100 }}>
      <div className="spinner" />
    </div>
  );

  if (error || !mcp) return (
    <div className="empty-state">
      <div style={{ color: "var(--error)", marginBottom: 16 }}>{error || "Integration not found"}</div>
      <button className="btn btn-secondary" onClick={() => router.push("/dashboard/integrations")}>Back</button>
    </div>
  );

  return (
    <div className="animate-fade-in" style={{ maxWidth: 900, margin: "0 auto" }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: 32, marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>{mcp.name}</h1>
            <span className={`badge ${
              mcp.circuit_breaker?.state === "OPEN" ? "badge-error" : 
              !mcp.is_enabled ? "badge-neutral" : "badge-success"
            }`}>
              {mcp.circuit_breaker?.state === "OPEN" ? "Outage" : mcp.is_enabled ? "Active" : "Disabled"}
            </span>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>{mcp.description || "No description provided."}</p>
        </div>
        
        <div style={{ display: "flex", gap: 12 }}>
          <button className="btn btn-secondary" onClick={handleTest} disabled={testing}>
            {testing ? <span className="spinner" style={{ width: 14, height: 14 }}/> : "Run Test"}
          </button>
          <button className={mcp.is_enabled ? "btn btn-secondary" : "btn btn-primary"} onClick={handleToggle}>
            {mcp.is_enabled ? "Disable" : "Enable"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24 }}>
        {/* Main Content */}
        <div style={{ flex: 2, display: "flex", flexDirection: "column", gap: 24 }}>
          <div className="glass-card" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Available Tools ({mcp.tools?.length || 0})</h2>
            
            {mcp.tools && mcp.tools.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {mcp.tools.map(tool => (
                  <div key={tool.name} style={{
                    padding: 16, background: "var(--bg-tertiary)", 
                    borderRadius: "var(--radius-md)", border: "1px solid var(--border-primary)"
                  }}>
                    <div style={{ fontWeight: 600, fontSize: 15, color: "var(--accent)", fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                      {tool.name}
                    </div>
                    <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 12 }}>
                      {tool.description}
                    </div>
                    {tool.inputSchema && (
                      <details style={{ fontSize: 13 }}>
                        <summary style={{ cursor: "pointer", color: "var(--text-tertiary)" }}>View Input Schema</summary>
                        <pre style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 4, marginTop: 8, overflowX: "auto" }}>
                          {JSON.stringify(tool.inputSchema, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No tools discovered yet. Try running a test.</div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>
          
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Circuit Breaker
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>State</span>
                <span style={{ fontWeight: 600, color: mcp.circuit_breaker?.state === "CLOSED" ? "var(--success)" : mcp.circuit_breaker?.state === "OPEN" ? "var(--error)" : "var(--warning)" }}>
                  {mcp.circuit_breaker?.state || "UNKNOWN"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Recent Failures</span>
                <span>{mcp.circuit_breaker?.failure_count || 0}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Total Successes</span>
                <span style={{ color: "var(--success)" }}>{mcp.circuit_breaker?.total_successes || 0}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Total Failures</span>
                <span style={{ color: "var(--error)" }}>{mcp.circuit_breaker?.total_failures || 0}</span>
              </div>
              {mcp.circuit_breaker?.retry_in_seconds !== undefined && mcp.circuit_breaker.retry_in_seconds > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border-primary)" }}>
                  <span style={{ color: "var(--text-tertiary)" }}>Recovery Test In</span>
                  <span style={{ color: "var(--warning)" }}>{mcp.circuit_breaker.retry_in_seconds}s</span>
                </div>
              )}
            </div>
          </div>

          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--error)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Danger Zone
            </h3>
            <button className="btn btn-danger" style={{ width: "100%" }} onClick={handleDelete}>
              Delete Integration
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
