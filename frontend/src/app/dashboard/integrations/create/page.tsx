"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { buildIntegrationFromURL, buildIntegrationFromPrompt } from "@/lib/api";

export default function CreateIntegrationPage() {
  const router = useRouter();
  const [method, setMethod] = useState<"url" | "prompt">("url");
  const [name, setName] = useState("");
  const [input, setInput] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setError("");
    setLoading(true);
    setLogs(["Initializing MCP Factory Agent...", `Building from ${method}...`]);
    setSuccess(false);

    try {
      // Simulate real-time logs for the UI experience
      const logInterval = setInterval(() => {
        setLogs(prev => [
          ...prev,
          method === "url" ? "Analyzing API documentation..." : "Designing OpenAPI schema from prompt...",
          "Generating Python MCP server code...",
          "Running static security analysis...",
          "Executing sandbox connectivity tests..."
        ]);
      }, 1500);

      let res;
      if (method === "url") {
        res = await buildIntegrationFromURL(input, name);
      } else {
        res = await buildIntegrationFromPrompt(input, name);
      }

      clearInterval(logInterval);
      setLogs(prev => [...prev, "✅ " + res.message]);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Factory failed to build integration");
      setLogs(prev => [...prev, "❌ Build Failed"]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: "0 auto", display: "flex", gap: 32, flexWrap: "wrap" }}>
      
      {/* Left Column: Form */}
      <div style={{ flex: "1 1 400px" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Build New Integration</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: 32 }}>
          AgentOS can automatically build Model Context Protocol (MCP) servers from API documentation or descriptions.
        </p>

        <div className="glass-card" style={{ padding: 24 }}>
          {/* Method Tabs */}
          <div style={{ display: "flex", background: "var(--bg-tertiary)", padding: 4, borderRadius: "var(--radius-md)", marginBottom: 24 }}>
            <button
              className="btn btn-ghost"
              style={{ flex: 1, background: method === "url" ? "var(--bg-card)" : "transparent", color: method === "url" ? "var(--text-primary)" : "var(--text-secondary)" }}
              onClick={() => setMethod("url")}
              type="button"
            >
              From URL
            </button>
            <button
              className="btn btn-ghost"
              style={{ flex: 1, background: method === "prompt" ? "var(--bg-card)" : "transparent", color: method === "prompt" ? "var(--text-primary)" : "var(--text-secondary)" }}
              onClick={() => setMethod("prompt")}
              type="button"
            >
              From Description
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{
                padding: "12px 16px", marginBottom: 20,
                background: "var(--error-subtle)", borderRadius: "var(--radius-md)",
                color: "var(--error)", fontSize: 14,
              }}>
                {error}
              </div>
            )}

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                Integration Name (Optional)
              </label>
              <input
                type="text"
                className="input"
                placeholder="e.g., Stripe API, Notion Connector"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading || success}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                {method === "url" ? "API Docs URL or OpenAPI Spec" : "Describe the tool and its endpoints"}
              </label>
              {method === "url" ? (
                <input
                  type="url"
                  className="input"
                  placeholder="https://api.example.com/docs"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                  disabled={loading || success}
                />
              ) : (
                <textarea
                  className="input"
                  placeholder="I need a tool that can interact with the GitHub API to list repositories and create issues..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                  style={{ minHeight: 120, resize: "vertical" }}
                  disabled={loading || success}
                />
              )}
            </div>

            {!success ? (
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: "100%" }}
                disabled={loading || !input.trim()}
              >
                {loading ? (
                  <span className="spinner" style={{ width: 16, height: 16 }} />
                ) : (
                  "Generate Integration"
                )}
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: "100%" }}
                onClick={() => router.push("/dashboard/integrations")}
              >
                View Integrations
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Right Column: Live Terminal Output */}
      <div style={{ flex: "1 1 400px", display: "flex", flexDirection: "column" }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Factory Terminal
        </h2>
        <div className="glass-card" style={{
          flex: 1, minHeight: 400, background: "#050505", border: "1px solid #333",
          borderRadius: "var(--radius-lg)", overflow: "hidden", display: "flex", flexDirection: "column"
        }}>
          {/* Terminal Header */}
          <div style={{
            height: 32, background: "#111", borderBottom: "1px solid #333",
            display: "flex", alignItems: "center", padding: "0 12px", gap: 6
          }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f56" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ffbd2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#27c93f" }} />
            <div style={{ flex: 1, textAlign: "center", color: "#666", fontSize: 11, fontFamily: "var(--font-sans)" }}>mcp-factory-agent</div>
          </div>
          
          {/* Terminal Body */}
          <div style={{
            padding: 16, fontFamily: "var(--font-mono)", fontSize: 13,
            color: "#a0a0a0", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 6
          }}>
            <div style={{ color: "#555", marginBottom: 12 }}>AgentOS MCP Factory v2.0.0</div>
            {logs.map((log, i) => (
              <div key={i} className="animate-slide-in">
                <span style={{ color: "#27c93f", marginRight: 8 }}>➜</span>
                <span style={{ 
                  color: log.includes("❌") ? "#ff5f56" : 
                         log.includes("✅") ? "#27c93f" : 
                         log.includes("Security") ? "#ffbd2e" : "#d0d0d0"
                }}>{log}</span>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                <span style={{ color: "#27c93f" }}>➜</span>
                <span className="spinner" style={{ width: 12, height: 12, borderTopColor: "#fff" }} />
              </div>
            )}
            {!loading && logs.length === 0 && (
              <div style={{ color: "#555", fontStyle: "italic" }}>Waiting for input...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
