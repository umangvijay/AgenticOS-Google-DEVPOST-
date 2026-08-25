import Link from "next/link";

export default function FeaturesPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar */}
      <header style={{
        padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: "1px solid var(--border-primary)", backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, var(--accent), #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: "white",
            }}>
              A
            </div>
            <span style={{ fontSize: 20, fontWeight: 700 }} className="gradient-text">
              AgentOS
            </span>
          </Link>
        </div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          <nav style={{ display: "flex", gap: 24, fontSize: 14, fontWeight: 500, color: "var(--text-secondary)" }}>
            <Link href="/about" className="hover:text-primary transition-colors">About Us</Link>
            <Link href="/features" className="hover:text-primary transition-colors" style={{ color: "var(--text-primary)" }}>Features</Link>
            <Link href="/contact" className="hover:text-primary transition-colors">Contact Us</Link>
          </nav>
          <div style={{ display: "flex", gap: 16 }}>
            <Link href="/login" className="btn btn-ghost">Sign In</Link>
            <Link href="/get-started" className="btn btn-primary">Get Started</Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main style={{ flex: 1, padding: "80px 20px", maxWidth: 1200, margin: "0 auto", textAlign: "center" }}>
        <h1 style={{ fontSize: "clamp(40px, 6vw, 64px)", fontWeight: 800, marginBottom: 24 }} className="gradient-text">
          Features
        </h1>
        <p style={{ fontSize: 20, color: "var(--text-secondary)", marginBottom: 80, lineHeight: 1.6, maxWidth: 800, margin: "0 auto 80px" }}>
          AgentOS represents a paradigm shift from deterministic workflow engines to autonomous goal-oriented systems.
          Explore the architecture that makes it possible.
        </p>

        {/* Dynamic Builder */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 64, marginBottom: 100, textAlign: "left", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 16 }}>The Dynamic Builder</h2>
            <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 24 }}>
              Say goodbye to missing integrations. When you ask AgentOS to interact with an API it doesn't recognize, 
              it dispatches a sub-agent to find the API documentation, understand the authentication requirements, 
              and write a Python Model Context Protocol (MCP) server from scratch.
            </p>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)" }}>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>Google Search Grounding for accurate API specs</span></li>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>AST Static Analysis prevents malicious code execution</span></li>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>Automated Docker containerization</span></li>
            </ul>
          </div>
          <div className="glass-card" style={{ padding: 40, height: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 64, marginBottom: 16 }}>🏭</div>
              <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-pink)" }}>Building MCP Tool...</div>
            </div>
          </div>
        </div>

        {/* Multi-Agent Orchestration */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 64, marginBottom: 100, textAlign: "left", alignItems: "center", flexDirection: "row-reverse" }}>
          <div className="glass-card" style={{ padding: 40, height: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 64, marginBottom: 16 }}>🤖</div>
              <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-purple)" }}>Routing to Specialized Agents...</div>
            </div>
          </div>
          <div>
            <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 16 }}>Multi-Agent Orchestration</h2>
            <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 24 }}>
              AgentOS doesn't rely on a single massive prompt. It utilizes a topology of specialized agents powered by Google's ADK.
              The Intent Agent plans, the Orchestrator executes, the Research Agent gathers context, and the Recovery Agent handles failures.
            </p>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)" }}>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>Powered by Google Gemini 1.5 Pro</span></li>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>Circuit breakers for API rate limits</span></li>
              <li style={{ display: "flex", gap: 12 }}><span style={{ color: "var(--success)" }}>✓</span> <span>Human-in-the-loop approval requests</span></li>
            </ul>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{ padding: "64px 40px", borderTop: "1px solid var(--border-primary)", background: "var(--bg-primary)" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", textAlign: "center", color: "var(--text-secondary)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 24 }}>
            <div style={{
              width: 24, height: 24, borderRadius: "6px",
              background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 800, color: "white"
            }}>A</div>
            <span style={{ fontSize: 18, fontWeight: 800 }}>AgentOS</span>
          </div>
          <p>© 2026 AgentOS Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
