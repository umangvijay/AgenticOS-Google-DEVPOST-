"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function AgentsPage() {
  const { isAuthenticated } = useAuth();

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
          <Link href="/integrations" className="btn btn-ghost">Integrations</Link>
        </div>
      </header>

      <main style={{ flex: 1, padding: "60px 40px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 8 }}>Agent Topology & Health</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: 40 }}>
          Monitor the specialized sub-agents currently active in your ADK runtime.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
          
          <div className="node-card" style={{ flexDirection: "column", alignItems: "flex-start", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ fontSize: 24 }}>🧠</div>
                <h3 style={{ fontSize: 18, fontWeight: 700 }}>PlannerAgent</h3>
              </div>
              <div className="status-dot active" />
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Converts natural language intents into a DAG of executable tasks.</p>
            <div style={{ marginTop: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Model: gemini-3.5-flash</div>
          </div>

          <div className="node-card" style={{ flexDirection: "column", alignItems: "flex-start", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ fontSize: 24 }}>⚡</div>
                <h3 style={{ fontSize: 18, fontWeight: 700 }}>OrchestratorAgent</h3>
              </div>
              <div className="status-dot active" />
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Claims tasks atomically, handles rate limits, and applies deterministic verification.</p>
            <div style={{ marginTop: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Model: gemini-3.5-flash</div>
          </div>

          <div className="node-card" style={{ flexDirection: "column", alignItems: "flex-start", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ fontSize: 24 }}>🌐</div>
                <h3 style={{ fontSize: 18, fontWeight: 700 }}>ResearchAgent</h3>
              </div>
              <div className="status-dot active" />
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Bounded web research with Google Search grounding and max-hop limits.</p>
            <div style={{ marginTop: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Model: gemini-3.1-pro</div>
          </div>

          <div className="node-card" style={{ flexDirection: "column", alignItems: "flex-start", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ fontSize: 24 }}>🛠️</div>
                <h3 style={{ fontSize: 18, fontWeight: 700 }}>MCPBuilderAgent</h3>
              </div>
              <div className="status-dot inactive" />
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Dynamically writes MCP Python servers from scratch using OpenAPI specs or natural language.</p>
            <div style={{ marginTop: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Status: Standby</div>
          </div>

        </div>
      </main>
    </div>
  );
}
