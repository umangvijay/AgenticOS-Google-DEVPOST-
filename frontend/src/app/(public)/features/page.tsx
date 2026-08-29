import Link from "next/link";
import Image from "next/image";
import PublicNavbar from "@/components/PublicNavbar";

export default function FeaturesPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar */}
      <PublicNavbar />

      {/* Content */}
      <main className="px-4 py-12 md:py-20" style={{ flex: 1, maxWidth: 1200, margin: "0 auto", textAlign: "center" }}>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold mb-6 gradient-text">
          Features
        </h1>
        <p className="text-lg md:text-xl text-[var(--text-secondary)] leading-relaxed max-w-3xl mx-auto mb-16 md:mb-20">
          AgentOS represents a paradigm shift from deterministic workflow engines to autonomous goal-oriented systems.
          Explore the architecture that makes it possible.
        </p>

        {/* Dynamic Builder */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 mb-20 md:mb-24 text-left items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-extrabold mb-4">The Dynamic Builder</h2>
            <p className="text-base md:text-lg text-[var(--text-secondary)] leading-relaxed mb-6">
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
          <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
            <div className="glass-card" style={{ padding: 12, width: "100%", height: "auto", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 12 }}>
              <Image src="/images/workflow-sketch.png" alt="Workflow Sketch" width={600} height={400} style={{ width: "100%", height: "auto", objectFit: "contain", filter: "invert(1) opacity(0.8)", borderRadius: 6 }} />
            </div>
            <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-pink)", textAlign: "center" }}>Building MCP Tool...</div>
          </div>
        </div>

        {/* Multi-Agent Orchestration */}
        <div className="flex flex-col-reverse md:flex-row gap-10 md:gap-16 mb-20 md:mb-24 text-left items-center">
          <div className="flex flex-col gap-4 items-center w-full md:w-1/2">
            <div className="glass-card p-3 w-full h-auto flex items-center justify-center rounded-xl">
              <Image src="/images/network-sketch.png" alt="Network Sketch" width={600} height={400} className="w-full h-auto object-contain rounded-md" style={{ filter: "invert(1) opacity(0.8)" }} />
            </div>
            <div className="font-mono text-[var(--accent-purple)] text-center text-sm md:text-base">Routing to Specialized Agents...</div>
          </div>
          <div className="w-full md:w-1/2">
            <h2 className="text-3xl md:text-4xl font-extrabold mb-4">Multi-Agent Orchestration</h2>
            <p className="text-base md:text-lg text-[var(--text-secondary)] leading-relaxed mb-6">
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
      <footer className="py-12 px-6 md:py-16 md:px-10 border-t border-[var(--border-primary)] bg-[var(--bg-primary)] mt-12 md:mt-20">
        <div className="max-w-6xl mx-auto text-center text-[var(--text-secondary)]">
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
