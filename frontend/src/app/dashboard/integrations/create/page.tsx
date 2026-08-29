"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  buildIntegrationFromURL,
  buildIntegrationFromPrompt,
  buildIntegrationFromWebsite,
  buildIntegrationFromSpec,
  getIntegrationBuild,
  storeCredential,
} from "@/lib/api";

type Method = "url" | "spec" | "website" | "prompt";

export default function CreateIntegrationPage() {
  const router = useRouter();
  const [method, setMethod] = useState<Method>("url");
  const [name, setName] = useState("");
  const [input, setInput] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [success, setSuccess] = useState(false);

  const labels: Record<Method, string> = {
    url: "OpenAPI / docs URL",
    spec: "Paste OpenAPI JSON or YAML",
    website: "Website URL (no public API — browser MCP)",
    prompt: "Describe the app and endpoints",
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setError("");
    setLoading(true);
    setLogs(["Initializing MCP Factory Agent...", `Building from ${method}...`]);
    setSuccess(false);

    try {
      let res;
      if (method === "url") {
        res = await buildIntegrationFromURL(input, name);
      } else if (method === "website") {
        res = await buildIntegrationFromWebsite(input, name, "Create browser tools for this site. Do not invent a REST API.");
      } else if (method === "spec") {
        res = await buildIntegrationFromSpec(input, name);
      } else {
        res = await buildIntegrationFromPrompt(input, name);
      }

      const buildId = res.build_id;
      if (buildId) {
        for (let i = 0; i < 120; i++) {
          const build = await getIntegrationBuild(buildId);
          setLogs(build.logs?.length ? build.logs : [`Stage: ${build.stage}`]);
          if (build.status === "success") {
            setLogs((prev) => [...build.logs, "✅ " + (build.message || res.message || "Registered")]);
            if (apiKey.trim() && name.trim()) {
              await storeCredential(name.trim().replace(/\s+/g, "-").toLowerCase(), { api_key: apiKey.trim() });
              setLogs((prev) => [...prev, "🔑 API key stored in Vault (names only; value encrypted)."]);
            }
            setSuccess(true);
            return;
          }
          if (build.status === "error") {
            throw new Error(build.error || build.message || "Factory failed");
          }
          await new Promise((r) => setTimeout(r, 1000));
        }
        throw new Error("Build timed out");
      }

      setLogs((prev) => [...prev, "✅ " + res.message]);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Factory failed to build integration");
      setLogs((prev) => [...prev, "❌ Build Failed"]);
    } finally {
      setLoading(false);
    }
  };

  const tabs: { id: Method; label: string }[] = [
    { id: "url", label: "From URL" },
    { id: "spec", label: "Paste spec" },
    { id: "website", label: "Website" },
    { id: "prompt", label: "I don't see my app" },
  ];

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: "0 auto", display: "flex", gap: 32, flexWrap: "wrap" }}>
      <div style={{ flex: "1 1 400px" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Build New Integration</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: 32 }}>
          HTTP APIs become MCP tools from OpenAPI. Sites without an API get origin-locked browser tools — not a hidden REST API.
        </p>

        <div className="glass-card glass-lift" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexWrap: "wrap", background: "var(--bg-tertiary)", padding: 4, borderRadius: "var(--radius-md)", marginBottom: 24, gap: 4 }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className="btn btn-ghost"
                style={{ flex: "1 1 110px", background: method === tab.id ? "var(--bg-card)" : "transparent", color: method === tab.id ? "var(--text-primary)" : "var(--text-secondary)" }}
                onClick={() => { setMethod(tab.id); setInput(""); }}
                type="button"
              >
                {tab.label}
              </button>
            ))}
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
                placeholder="e.g. GitHub, Open-Meteo, example.com"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading || success}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                {labels[method]}
              </label>
              {method === "url" || method === "website" ? (
                <input
                  type="url"
                  className="input"
                  placeholder={method === "website" ? "https://example.com" : "https://pokeapi.co/api/v2"}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                  disabled={loading || success}
                />
              ) : (
                <textarea
                  className="input"
                  placeholder={method === "spec" ? "{ \"openapi\": \"3.0.0\", ... }" : "GitHub REST — list public repos for a user"}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                  style={{ minHeight: 140, resize: "vertical" }}
                  disabled={loading || success}
                />
              )}
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                Attach API key (optional, stored in Vault)
              </label>
              <input
                type="password"
                className="input"
                placeholder="Leave empty for public APIs"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={loading || success}
                autoComplete="off"
              />
            </div>

            {!success ? (
              <>
                {method === "url" && (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ width: "100%", marginBottom: 8 }}
                    disabled={loading}
                    onClick={() => setInput("https://raw.githubusercontent.com/PokeAPI/pokeapi/master/openapi.yml")}
                  >
                    Use PokeAPI OpenAPI
                  </button>
                )}
                {method === "website" && (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ width: "100%", marginBottom: 8 }}
                    disabled={loading}
                    onClick={() => setInput("https://example.com")}
                  >
                    Use example.com
                  </button>
                )}
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
              </>
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

      <div style={{ flex: "1 1 400px", display: "flex", flexDirection: "column" }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Factory Terminal
        </h2>
        <div className="glass-card" style={{
          flex: 1, minHeight: 400, background: "#050505", border: "1px solid #333",
          borderRadius: "var(--radius-lg)", overflow: "hidden", display: "flex", flexDirection: "column"
        }}>
          <div style={{
            height: 32, background: "#111", borderBottom: "1px solid #333",
            display: "flex", alignItems: "center", padding: "0 12px", gap: 6
          }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f56" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ffbd2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#27c93f" }} />
            <div style={{ flex: 1, textAlign: "center", color: "#666", fontSize: 11, fontFamily: "var(--font-sans)" }}>mcp-factory-agent</div>
          </div>
          <div style={{
            padding: 16, fontFamily: "var(--font-mono)", fontSize: 13,
            color: "#a0a0a0", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 6
          }}>
            <div style={{ color: "#555", marginBottom: 12 }}>AgentOS MCP Factory</div>
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
