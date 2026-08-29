import PublicNavbar from "@/components/PublicNavbar";

export const metadata = { title: "Community" };

export default function CommunityPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-20 flex-1 flex flex-col items-center">
        <div style={{ maxWidth: 640, width: "100%", textAlign: "center" }}>
          <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }} className="gradient-text">
            Join the Community
          </h1>
          <p style={{ fontSize: 20, color: "var(--text-secondary)", marginBottom: 48, maxWidth: 600, margin: "0 auto 64px" }}>
            AgentOS is open source. Issues, PRs, and discussion live on GitHub.
          </p>

          <div className="glass-card" style={{ padding: 40, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#333", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24, fontSize: 24, color: "white", fontWeight: "bold" }}>
              G
            </div>
            <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>GitHub</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: 24, lineHeight: 1.6 }}>
              Contribute to the AgentOS engine, MCP factory, and Cloud Run deploy docs.
            </p>
            <a
              href="https://github.com/umangvijay/AgenticOS-Google-DEVPOST"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary w-full"
              style={{ justifyContent: "center" }}
            >
              View GitHub
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
