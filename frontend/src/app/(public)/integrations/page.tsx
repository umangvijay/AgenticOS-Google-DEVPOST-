import PublicNavbar from "@/components/PublicNavbar";
import Link from "next/link";

const APPS = [
  { name: "JSONPlaceholder", use: "REST APIs from OpenAPI or a docs URL" },
  { name: "GitHub", use: "Repos, issues, and pull requests from a description" },
  { name: "HTTPBin", use: "Live probe any public HTTP service" },
  { name: "Gmail / SMTP", use: "Send mail with a vault-stored SMTP login" },
  { name: "Any SaaS", use: "If it has an HTTP API, AgentOS can build the tools" },
];

export default function PublicIntegrationsPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh" }}>
      <PublicNavbar />
      <main className="px-4 py-16 md:py-24" style={{ maxWidth: 960, margin: "0 auto" }}>
        <p className="eyebrow">Integrations</p>
        <h1 className="gradient-text" style={{ fontSize: "clamp(36px, 6vw, 64px)", fontWeight: 800, letterSpacing: "-0.04em", marginBottom: 16 }}>
          Tools for any app. Built when you need them.
        </h1>
        <p style={{ fontSize: 20, color: "var(--text-secondary)", maxWidth: 680, marginBottom: 40, lineHeight: 1.6 }}>
          AgentOS does not ship a fixed catalog. Describe an API, paste a docs URL, or drop an OpenAPI spec.
          The MCP factory normalizes, probes live, registers tools, and the automation agent can call them in the same run.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 56 }}>
          <Link href="/get-started" className="btn btn-primary btn-lg">Open workspace</Link>
          <Link href="/dashboard/integrations/create" className="btn btn-secondary btn-lg">Create an MCP</Link>
        </div>

        <div className="flow-diagram glass-panel" style={{ padding: 28, marginBottom: 48 }}>
          <div className="flow-row">
            {["Docs / spec / prompt", "Normalize", "Live probe", "Register MCP", "Agent uses tools"].map((step, i) => (
              <div key={step} className="flow-node">
                <span className="flow-index">0{i + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {APPS.map((app) => (
            <div key={app.name} className="glass-panel" style={{ padding: 24 }}>
              <h2 style={{ fontSize: 20, margin: "0 0 8px" }}>{app.name}</h2>
              <p style={{ margin: 0, color: "var(--text-secondary)" }}>{app.use}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
