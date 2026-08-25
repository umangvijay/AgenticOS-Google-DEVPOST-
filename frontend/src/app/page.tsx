import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Splash Screen */}
      <div className="splash-screen">
        <h1 className="splash-text">A G E N T O S</h1>
      </div>

      {/* Navbar */}
      <header style={{
        padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: "1px solid var(--border-primary)", backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100
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
          <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.5px" }} className="gradient-text">
            AgentOS
          </span>
        </div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          <nav style={{ display: "flex", gap: 32, fontSize: 14, fontWeight: 600, color: "var(--text-secondary)" }}>
            <Link href="/about" className="hover:text-primary transition-colors" style={{ color: "var(--text-primary)" }}>About Us</Link>
            <Link href="/features" className="hover:text-primary transition-colors">Features</Link>
            <Link href="/integrations" className="hover:text-primary transition-colors">Marketplace</Link>
            <Link href="/contact" className="hover:text-primary transition-colors">Contact Us</Link>
          </nav>
          <div style={{ display: "flex", gap: 16 }}>
            <Link href="/login" className="btn btn-ghost">Sign In</Link>
            <Link href="/get-started" className="btn btn-primary">Get Started</Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "100px 20px", textAlign: "center", position: "relative" }}>
        
        {/* Floating Background SVG paths */}
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none", opacity: 0.5 }}>
          <svg width="100%" height="100%" style={{ position: "absolute" }}>
            <path d="M -100 200 C 300 200, 400 600, 1000 400" stroke="var(--border-hover)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 15" />
            <path d="M -100 600 C 500 500, 600 100, 1200 300" stroke="var(--border-hover)" strokeWidth="1" fill="none" className="animate-dash" strokeDasharray="5 15" style={{ animationDuration: "30s" }} />
          </svg>
        </div>

        <div style={{ zIndex: 10 }}>
          <div className="badge animate-fade-in-up" style={{ marginBottom: 32, padding: "6px 16px", background: "rgba(236, 72, 153, 0.1)", color: "var(--accent-pink)", border: "1px solid rgba(236, 72, 153, 0.3)", borderRadius: 100 }}>
            Production Ready v2.0
          </div>
          <h1 className="animate-fade-in-up" style={{
            fontSize: "clamp(48px, 8vw, 84px)", fontWeight: 900, lineHeight: 1.05,
            letterSpacing: "-0.04em", marginBottom: 24, maxWidth: 1000
          }}>
            The autonomous workspace that <br/>
            <span className="gradient-text">builds its own tools.</span>
          </h1>
          <p className="animate-fade-in-up" style={{
            fontSize: "clamp(18px, 2.5vw, 24px)", color: "var(--text-secondary)",
            marginBottom: 48, maxWidth: 700, animationDelay: "0.1s", margin: "0 auto 48px", fontWeight: 400
          }}>
            Give AgentOS a goal. It plans the workflow, executes the tasks, and if an integration is missing, it dynamically generates and deploys it.
          </p>
          <div className="animate-fade-in-up" style={{ display: "flex", gap: 16, justifyContent: "center", animationDelay: "0.2s" }}>
            <Link href="/get-started" className="btn btn-primary btn-lg">Start Building Free</Link>
            <a href="#demo" className="btn btn-secondary btn-lg">Watch how it works</a>
          </div>
        </div>

        {/* Animated Node Demo */}
        <div id="demo" className="animate-fade-in-up glass-card" style={{
          marginTop: 80, width: "100%", maxWidth: 1000, height: 450,
          background: "var(--bg-secondary)", animationDelay: "0.3s", position: "relative",
          zIndex: 10
        }}>
          {/* Header */}
          <div style={{
            height: 48, borderBottom: "1px solid var(--border-primary)",
            display: "flex", alignItems: "center", padding: "0 16px", gap: 8,
            background: "rgba(0,0,0,0.2)"
          }}>
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--error)" }} />
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--warning)" }} />
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--success)" }} />
            <span style={{ marginLeft: 16, fontSize: 13, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>workflow-engine-active</span>
          </div>

          {/* SVG Connections */}
          <svg style={{ position: "absolute", top: 48, left: 0, width: "100%", height: "calc(100% - 48px)", pointerEvents: "none" }}>
            {/* Curved Path 1 */}
            <path d="M 230 150 C 350 150, 400 100, 500 100" stroke="var(--accent-pink)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 230 150 C 350 150, 400 100, 500 100" stroke="var(--accent-pink)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />
            
            {/* Curved Path 2 */}
            <path d="M 230 150 C 350 150, 350 250, 500 250" stroke="var(--accent-purple)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 230 150 C 350 150, 350 250, 500 250" stroke="var(--accent-purple)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />

            {/* Curved Path 3 */}
            <path d="M 720 100 C 800 100, 800 150, 850 150" stroke="var(--accent)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 720 100 C 800 100, 800 150, 850 150" stroke="var(--accent)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />
          </svg>

          {/* Nodes */}
          <div style={{ position: "absolute", top: 48, left: 0, width: "100%", height: "calc(100% - 48px)" }}>
            
            {/* Trigger Node */}
            <div className="node-card animate-float" style={{ position: "absolute", left: 60, top: 120, width: 170 }}>
              <div style={{ fontSize: 24 }}>⚡</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>User Intent</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Trigger</div>
              </div>
              <div className="node-port right"></div>
            </div>

            {/* MCP Factory Node */}
            <div className="node-card animate-float" style={{ position: "absolute", left: 500, top: 70, width: 220, animationDelay: "1s" }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>🛠️</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>MCP Factory</div>
                <div style={{ fontSize: 11, color: "var(--accent-pink)", fontWeight: 600 }}>Building Notion API...</div>
              </div>
              <div className="node-port right"></div>
            </div>

            {/* Web Search Node */}
            <div className="node-card animate-float" style={{ position: "absolute", left: 500, top: 220, width: 220, animationDelay: "2s", opacity: 0.7 }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>🌐</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>Web Search</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Completed</div>
              </div>
            </div>

            {/* Execution Node */}
            <div className="node-card animate-float" style={{ position: "absolute", left: 850, top: 120, width: 170, animationDelay: "1.5s" }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>✅</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>Notion Sync</div>
                <div style={{ fontSize: 11, color: "var(--success)" }}>Data inserted</div>
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* App Integrations Marquee Showcase */}
      <section style={{ padding: "60px 0", background: "var(--bg-primary)", position: "relative", overflow: "hidden" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-tertiary)", letterSpacing: 2, textTransform: "uppercase" }}>
            Connects with your favorite tools
          </p>
        </div>
        <div className="marquee-container animate-fade-in-up">
          <div className="marquee-content" style={{ display: "flex", gap: 64, alignItems: "center" }}>
            {/* Repeated logos for infinite scroll effect */}
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} style={{ display: "flex", gap: 64, alignItems: "center" }}>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Stripe</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Slack</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Notion</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>GitHub</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Gmail</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Discord</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Jira</span>
                <span style={{ fontSize: 32, fontWeight: 700, color: "var(--text-secondary)" }}>Salesforce</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section style={{ padding: "120px 20px", background: "var(--bg-primary)", position: "relative" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 80 }}>
            <h2 className="animate-fade-in-up" style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }}>
              Everything you need to <span className="gradient-text">automate anything.</span>
            </h2>
            <p style={{ fontSize: 20, color: "var(--text-secondary)", maxWidth: 600, margin: "0 auto" }}>
              AgentOS combines the power of LLMs with deterministic workflow execution.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 32 }}>
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, borderTop: "2px solid var(--accent-pink)" }}>
              <div style={{ fontSize: 40, marginBottom: 24 }}>🧠</div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Autonomous Planning</h3>
              <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Give AgentOS a high-level goal, and it will break it down into a DAG of executable tasks, routing them to specialized sub-agents.
              </p>
            </div>
            
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, borderTop: "2px solid var(--accent-purple)", animationDelay: "0.1s" }}>
              <div style={{ fontSize: 40, marginBottom: 24 }}>🛠️</div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Dynamic MCP Builder</h3>
              <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Missing an API connector? AgentOS will search the web, read the docs, and write the Python MCP connector from scratch.
              </p>
            </div>
            
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, borderTop: "2px solid var(--accent)", animationDelay: "0.2s" }}>
              <div style={{ fontSize: 40, marginBottom: 24 }}>🔒</div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Enterprise Security</h3>
              <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Built with full AST static analysis, sandboxed Docker execution, Google OAuth, and strict CSP headers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section style={{ padding: "120px 20px", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, background: "linear-gradient(180deg, var(--bg-primary) 0%, rgba(139, 92, 246, 0.05) 100%)", zIndex: -1 }} />
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 80 }}>
            <h2 style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }}>
              How AgentOS Works
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 64 }}>
            {/* Step 1 */}
            <div style={{ display: "flex", gap: 40, alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 400px" }}>
                <div style={{ fontSize: 80, fontWeight: 900, color: "var(--border-hover)", lineHeight: 1, marginBottom: 24 }}>01</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Define your Intent</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  Start by typing what you want to achieve. No coding required. The Intent Agent parses your request and maps it to the necessary systems.
                </p>
              </div>
              <div className="glass-card" style={{ flex: "1 1 400px", padding: 32, background: "rgba(0,0,0,0.4)" }}>
                <div style={{ fontFamily: "var(--font-mono)", color: "var(--success)" }}>
                  &gt; Goal: Analyze our latest Stripe transactions and generate a PDF report.
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div style={{ display: "flex", gap: 40, alignItems: "center", flexWrap: "wrap", flexDirection: "row-reverse" }}>
              <div style={{ flex: "1 1 400px" }}>
                <div style={{ fontSize: 80, fontWeight: 900, color: "var(--border-hover)", lineHeight: 1, marginBottom: 24 }}>02</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Dynamic Assembly</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  If a tool doesn't exist, the platform automatically writes and validates the Model Context Protocol (MCP) server for the integration on-the-fly.
                </p>
              </div>
              <div className="glass-card" style={{ flex: "1 1 400px", padding: 32, background: "rgba(0,0,0,0.4)" }}>
                <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                  <div className="spinner" style={{ width: 24, height: 24, borderColor: "var(--accent-pink) transparent transparent transparent" }} />
                  <span style={{ color: "var(--accent-pink)", fontFamily: "var(--font-mono)" }}>Building Stripe MCP...</span>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div style={{ display: "flex", gap: 40, alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 400px" }}>
                <div style={{ fontSize: 80, fontWeight: 900, color: "var(--border-hover)", lineHeight: 1, marginBottom: 24 }}>03</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Execute & Monitor</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  The Orchestrator executes the workflow, handling retries, circuit breakers, and human-in-the-loop approvals automatically.
                </p>
              </div>
              <div className="glass-card" style={{ flex: "1 1 400px", padding: 32, background: "rgba(0,0,0,0.4)" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-primary)", paddingBottom: 8 }}>
                    <span>Fetch Data</span> <span style={{ color: "var(--success)" }}>DONE</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-primary)", paddingBottom: 8 }}>
                    <span>Generate PDF</span> <span style={{ color: "var(--success)" }}>DONE</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Email User</span> <span style={{ color: "var(--success)" }}>DONE</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section style={{ padding: "120px 20px", textAlign: "center", background: "var(--bg-secondary)", position: "relative" }}>
        <div style={{ position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)", width: "100%", maxWidth: 800, height: 1, background: "linear-gradient(90deg, transparent, var(--accent), transparent)" }} />
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <h2 style={{ fontSize: "clamp(36px, 6vw, 64px)", fontWeight: 900, marginBottom: 32 }}>
            Ready to build the future?
          </h2>
          <p style={{ fontSize: 24, color: "var(--text-secondary)", marginBottom: 48 }}>
            Join thousands of developers automating their workflows with AgentOS.
          </p>
          <Link href="/signup" className="btn btn-primary btn-lg" style={{ transform: "scale(1.1)" }}>
            Get Started for Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: "64px 40px", borderTop: "1px solid var(--border-primary)", background: "var(--bg-primary)" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 48 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
              <div style={{
                width: 24, height: 24, borderRadius: "6px",
                background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 800, color: "white"
              }}>A</div>
              <span style={{ fontSize: 18, fontWeight: 800 }}>AgentOS</span>
            </div>
            <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>
              The open-source autonomous workflow engine for the AI era.
            </p>
          </div>
          <div>
            <h4 style={{ fontWeight: 600, marginBottom: 16 }}>Product</h4>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/features" style={{ color: "inherit", textDecoration: "none" }}>Features</Link></li>
              <li><Link href="/integrations" style={{ color: "inherit", textDecoration: "none" }}>Integrations</Link></li>
              <li><Link href="/pricing" style={{ color: "inherit", textDecoration: "none" }}>Pricing</Link></li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontWeight: 600, marginBottom: 16 }}>Resources</h4>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/docs" style={{ color: "inherit", textDecoration: "none" }}>Documentation</Link></li>
              <li><Link href="/blog" style={{ color: "inherit", textDecoration: "none" }}>Blog</Link></li>
              <li><Link href="/community" style={{ color: "inherit", textDecoration: "none" }}>Community</Link></li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontWeight: 600, marginBottom: 16 }}>Legal</h4>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/privacy" style={{ color: "inherit", textDecoration: "none" }}>Privacy Policy</Link></li>
              <li><Link href="/terms" style={{ color: "inherit", textDecoration: "none" }}>Terms of Service</Link></li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}
