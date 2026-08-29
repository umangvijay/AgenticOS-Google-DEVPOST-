import PublicNavbar from "@/components/PublicNavbar";
import Link from "next/link";

export default function CommunityPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-20 flex-1 flex flex-col items-center">
        <div style={{ maxWidth: 1000, width: "100%", textAlign: "center" }}>
          <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }} className="gradient-text">
            Join the Community
          </h1>
          <p style={{ fontSize: 20, color: "var(--text-secondary)", marginBottom: 48, maxWidth: 600, margin: "0 auto 64px" }}>
            Connect with thousands of developers building the future of autonomous workflows.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 32 }}>
            <div className="glass-card" style={{ padding: 40, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#5865F2", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24, fontSize: 24, color: "white", fontWeight: "bold" }}>
                D
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Discord</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24, lineHeight: 1.6 }}>
                Chat with the core team, get help, and share what you're building.
              </p>
              <Link href="#" className="btn btn-primary w-full" style={{ justifyContent: "center" }}>
                Join Discord
              </Link>
            </div>

            <div className="glass-card" style={{ padding: 40, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#333", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24, fontSize: 24, color: "white", fontWeight: "bold" }}>
                G
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>GitHub</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24, lineHeight: 1.6 }}>
                Contribute to the open-source AgentOS engine and core MCP servers.
              </p>
              <Link href="#" className="btn btn-ghost w-full border border-[var(--border-primary)]" style={{ justifyContent: "center" }}>
                View GitHub
              </Link>
            </div>
            
            <div className="glass-card" style={{ padding: 40, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#1DA1F2", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24, fontSize: 24, color: "white", fontWeight: "bold" }}>
                X
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Twitter / X</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24, lineHeight: 1.6 }}>
                Follow us for the latest platform updates, announcements, and tips.
              </p>
              <Link href="#" className="btn btn-ghost w-full border border-[var(--border-primary)]" style={{ justifyContent: "center" }}>
                Follow Us
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
