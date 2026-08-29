import Link from "next/link";
import PublicNavbar from "@/components/PublicNavbar";
import { DiagramScaler } from "@/components/DiagramScaler";

export default function LandingPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
        <PublicNavbar />

      <main className="px-4 pb-12 md:py-24" style={{ paddingTop: 32, textAlign: "center", position: "relative" }}>
        <div style={{ zIndex: 10, width: "100%" }}>
          <p className="eyebrow">Autonomous workspace</p>
          <h1 className="mt-4 md:mt-10 apple-hero" style={{
            fontSize: "clamp(36px, 8vw, 84px)", fontWeight: 900, lineHeight: 1.05,
            letterSpacing: "-0.04em", marginBottom: 24, maxWidth: 1000, marginInline: "auto"
          }}>
            Meet AgentOS.<br className="hidden md:block" />
            <span className="gradient-text">One workspace for all your apps.</span>
          </h1>
          <p style={{
            fontSize: "clamp(18px, 2.5vw, 24px)", color: "var(--text-secondary)",
            marginBottom: 48, maxWidth: 700, margin: "0 auto 48px", fontWeight: 400
          }}>
            Tell it what you want. It plans the work, builds missing MCP tools, and executes across live APIs — not just chat.
          </p>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap", marginBottom: 24 }}>
            <Link href="/login" className="btn btn-primary btn-lg">Sign In</Link>
            <Link href="/get-started" className="btn btn-secondary btn-lg">Start Building Free</Link>
            <Link href="/docs" className="btn btn-ghost btn-lg">Read the docs</Link>
          </div>
        </div>

        <div style={{ marginTop: 80, zIndex: 10 }}>
          <DiagramScaler>
            <div id="demo" style={{ background: "var(--bg-secondary)", borderRadius: 16, border: "1px solid var(--border-primary)", boxShadow: "var(--shadow-lg)", overflow: "hidden", width: "100%", height: "100%", position: "relative" }}>
          <div style={{
            height: 48, borderBottom: "1px solid var(--border-primary)",
            display: "flex", alignItems: "center", padding: "0 16px", gap: 8,
            background: "rgba(0,0,0,0.05)"
          }}>
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--error)" }} />
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--warning)" }} />
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--success)" }} />
            <span style={{ marginLeft: 16, fontSize: 13, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>workflow-engine-active</span>
          </div>
          <svg style={{ position: "absolute", top: 48, left: 0, width: "100%", height: "calc(100% - 48px)", pointerEvents: "none" }}>
            <path d="M 210 150 C 310 150, 360 100, 460 100" stroke="var(--accent-pink)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 210 150 C 310 150, 360 100, 460 100" stroke="var(--accent-pink)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />
            <path d="M 210 150 C 310 150, 310 250, 460 250" stroke="var(--accent-purple)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 210 150 C 310 150, 310 250, 460 250" stroke="var(--accent-purple)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />
            <path d="M 680 100 C 715 100, 715 150, 750 150" stroke="var(--accent)" strokeWidth="3" fill="none" strokeOpacity="0.3" />
            <path d="M 680 100 C 715 100, 715 150, 750 150" stroke="var(--accent)" strokeWidth="2" fill="none" className="animate-dash" strokeDasharray="10 20" />
          </svg>
          <div style={{ position: "absolute", top: 48, left: 0, width: "100%", height: "calc(100% - 48px)" }}>
            <div className="node-card" style={{ position: "absolute", left: 40, top: 120, width: 170 }}>
              <div style={{ fontSize: 24 }}>⚡</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>User Intent</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Trigger</div>
              </div>
              <div className="node-port right"></div>
            </div>
            <div className="node-card" style={{ position: "absolute", left: 460, top: 70, width: 220, animationDelay: "1s" }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>🛠️</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>MCP Factory</div>
                <div style={{ fontSize: 11, color: "var(--accent-pink)", fontWeight: 600 }}>Building tools…</div>
              </div>
              <div className="node-port right"></div>
            </div>
            <div className="node-card" style={{ position: "absolute", left: 460, top: 220, width: 220, animationDelay: "2s", opacity: 0.7 }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>🌐</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>Web Search</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Completed</div>
              </div>
            </div>
            <div className="node-card" style={{ position: "absolute", left: 750, top: 120, width: 200, animationDelay: "1.5s" }}>
              <div className="node-port left"></div>
              <div style={{ fontSize: 24 }}>✅</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>Live execution</div>
                <div style={{ fontSize: 11, color: "var(--success)" }}>Result returned</div>
              </div>
            </div>
          </div>
          </div>
          </DiagramScaler>
        </div>
      </main>

      <section className="py-20 md:py-28 px-5">
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <p className="eyebrow" style={{ textAlign: "center" }}>Why we exist</p>
          <h2 style={{ textAlign: "center", fontSize: "clamp(32px, 5vw, 52px)", fontWeight: 800, marginBottom: 48, letterSpacing: "-0.03em" }}>
            Vision and mission
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="glass-panel p-8 md:p-10">
              <h3 style={{ fontSize: 28, fontFamily: "var(--font-serif)", marginBottom: 16 }}>Vision</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: 18, lineHeight: 1.7 }}>
                A workspace where you describe the outcome — and the system grows the tools it needs.
                No frozen integration catalog. No waiting for a vendor plugin. Any app with an API, or a site you can log into, becomes usable the moment you ask.
              </p>
            </div>
            <div className="glass-panel p-8 md:p-10">
              <h3 style={{ fontSize: 28, fontFamily: "var(--font-serif)", marginBottom: 16 }}>Mission</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: 18, lineHeight: 1.7 }}>
                Give people an autonomous agent that plans, builds missing MCP tools, and executes in real time —
                with encrypted vaults, human approvals, and the option to bring your own Gemini key.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section style={{ padding: "60px 0", background: "var(--bg-primary)", position: "relative", overflow: "hidden" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-tertiary)", letterSpacing: 2, textTransform: "uppercase" }}>
            Connects with any HTTP API
          </p>
        </div>
        <div className="marquee-container animate-fade-in-up">
          <div className="marquee-content" style={{ display: "flex", gap: 64, alignItems: "center" }}>
            {Array.from({ length: 2 }).map((_, i) => (
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

      <section className="py-20 md:py-28 px-5">
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <p className="eyebrow" style={{ textAlign: "center" }}>Automation pipeline</p>
          <h2 className="apple-hero" style={{ textAlign: "center", fontSize: "clamp(32px, 5vw, 48px)", marginBottom: 40 }}>
            AI that executes work, not just chat.
          </h2>
          <div className="pipeline-steps">
            {[
              ["01", "Intent", "Parse the goal, the target app, and constraints from plain language."],
              ["02", "Plan", "Break the goal into a DAG of tasks the engine can run."],
              ["03", "Build tools", "If an API is missing, the MCP factory writes and probes it live."],
              ["04", "Execute", "HTTP, health, email, browser, and generated tools run in order."],
              ["05", "Recover", "Retries, circuit breakers, and human approvals when risk is high."],
              ["06", "Report", "The workspace thread shows events and real task output."],
            ].map(([n, t, d]) => (
              <div key={n} className="glass-panel pipeline-step">
                <div className="gradient-text" style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>{n}</div>
                <h3 style={{ fontSize: 20, margin: "0 0 8px" }}>{t}</h3>
                <p style={{ margin: 0, color: "var(--text-secondary)", lineHeight: 1.6 }}>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 md:py-32 px-5 relative" style={{ background: "var(--bg-primary)" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 80 }}>
            <h2 className="animate-fade-in-up" style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }}>
              Everything you need to <span className="gradient-text">automate anything.</span>
            </h2>
            <p style={{ fontSize: 20, color: "var(--text-secondary)", maxWidth: 600, margin: "0 auto" }}>
              AgentOS combines live model reasoning with deterministic workflow execution.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="glass-panel animate-fade-in-up p-6 md:p-8 border-t-2 border-[var(--accent-pink)]">
              <h3 className="text-xl md:text-2xl font-bold mb-4">Autonomous Planning</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed">
                Give AgentOS a high-level goal. It breaks it into a DAG of tasks and routes them to specialized agents.
              </p>
            </div>
            <div className="glass-panel animate-fade-in-up p-6 md:p-8 border-t-2 border-[var(--accent-purple)]">
              <h3 className="text-xl md:text-2xl font-bold mb-4">Dynamic MCP Builder</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed">
                Missing an API connector? AgentOS reads the docs and registers tools it can call in the same run.
              </p>
            </div>
            <div className="glass-panel animate-fade-in-up p-6 md:p-8 border-t-2 border-[var(--accent)]">
              <h3 className="text-xl md:text-2xl font-bold mb-4">Your keys, your quota</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed">
                Bring a Gemini API key in Settings. It is encrypted in the vault and used for your runs.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 md:py-32 px-5 relative overflow-hidden">
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 80 }}>
            <h2 style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, marginBottom: 24 }}>How AgentOS Works</h2>
          </div>
          <div className="flex flex-col gap-16 md:gap-24">
            <div className="flex flex-col lg:flex-row gap-10 items-center">
              <div className="flex-1 w-full">
                <div className="gradient-text" style={{ fontSize: 80, fontWeight: 900, lineHeight: 1, marginBottom: 24, opacity: 0.8 }}>01</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Define your intent</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  Type what you want. The intent agent maps it onto the tools you already have — or the ones it will build.
                </p>
              </div>
              <div className="glass-panel flex-1 w-full p-8" style={{ background: "rgba(43,42,39,0.92)", color: "white" }}>
                <div style={{ fontFamily: "var(--font-mono)", color: "var(--success)" }}>
                  &gt; Goal: Check health of https://example.com and report the status code.
                </div>
              </div>
            </div>
            <div className="flex flex-col lg:flex-row-reverse gap-10 items-center">
              <div className="flex-1 w-full">
                <div className="gradient-text" style={{ fontSize: 80, fontWeight: 900, lineHeight: 1, marginBottom: 24, opacity: 0.8 }}>02</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Build missing tools</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  From OpenAPI, a docs URL, or a description, the MCP factory probes live and registers tools.
                </p>
              </div>
              <div className="glass-panel flex-1 w-full p-8">
                <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                  <div className="spinner" style={{ width: 24, height: 24 }} />
                  <span style={{ color: "var(--accent-pink)", fontFamily: "var(--font-mono)" }}>Building MCP…</span>
                </div>
              </div>
            </div>
            <div className="flex flex-col lg:flex-row gap-10 items-center">
              <div className="flex-1 w-full">
                <div className="gradient-text" style={{ fontSize: 80, fontWeight: 900, lineHeight: 1, marginBottom: 24, opacity: 0.8 }}>03</div>
                <h3 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Execute and watch</h3>
                <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  The orchestrator runs the DAG with retries, circuit breakers, and approvals. You see it as a chat.
                </p>
              </div>
              <div className="glass-panel flex-1 w-full p-8" style={{ fontFamily: "var(--font-mono)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-primary)", paddingBottom: 8, marginBottom: 8 }}>
                  <span>Site health</span> <span style={{ color: "var(--success)" }}>DONE</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Report</span> <span style={{ color: "var(--success)" }}>DONE</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 md:py-32 px-5 text-center relative" style={{ background: "var(--bg-secondary)" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <h2 style={{ fontSize: "clamp(36px, 6vw, 64px)", fontWeight: 900, marginBottom: 32, letterSpacing: "-0.03em" }}>
            Ready to try it?
          </h2>
          <p style={{ fontSize: "clamp(18px, 4vw, 24px)", color: "var(--text-secondary)", marginBottom: 48 }}>
            Open a free guest workspace. No credit card. Bring your own API key whenever you want.
          </p>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/login" className="btn btn-primary btn-lg">Sign In</Link>
            <Link href="/get-started" className="btn btn-secondary btn-lg">Get Started for Free</Link>
          </div>
        </div>
      </section>

      <footer className="pt-16 pb-8 px-5" style={{ borderTop: "1px solid var(--border-primary)", background: "var(--bg-primary)" }}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-10 md:gap-12" style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div className="col-span-2 lg:col-span-1 mb-2 lg:mb-0">
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 24, height: 24, borderRadius: "6px",
                background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 800, color: "white"
              }}>A</div>
              <span style={{ fontSize: 18, fontWeight: 800 }}>AgentOS</span>
            </div>
            <p style={{ color: "var(--text-tertiary)", fontSize: 14, lineHeight: 1.6 }}>
              The autonomous workspace that builds its own tools.
            </p>
          </div>
          <div>
            <h2 style={{ fontWeight: 600, marginBottom: 16, fontSize: 15 }}>Product</h2>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/features">Features</Link></li>
              <li><Link href="/integrations">Integrations</Link></li>
              <li><Link href="/pricing">Pricing</Link></li>
            </ul>
          </div>
          <div>
            <h2 style={{ fontWeight: 600, marginBottom: 16, fontSize: 15 }}>Resources</h2>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/docs">Documentation</Link></li>
              <li><Link href="/faq">FAQs</Link></li>
              <li><Link href="/blog">Blog</Link></li>
              <li><Link href="/community">Community</Link></li>
            </ul>
          </div>
          <div>
            <h2 style={{ fontWeight: 600, marginBottom: 16, fontSize: 15 }}>Legal</h2>
            <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 12, color: "var(--text-secondary)", fontSize: 14 }}>
              <li><Link href="/privacy">Privacy Policy</Link></li>
              <li><Link href="/terms">Terms of Service</Link></li>
              <li><Link href="/contact">Contact</Link></li>
            </ul>
          </div>
        </div>
        <div style={{ maxWidth: 1200, margin: "48px auto 0", paddingTop: 32, borderTop: "1px solid var(--border-primary)" }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>© 2026 AgentOS Inc. All rights reserved.</p>
        </div>
      </footer>
      </div>
    </div>
  );
}
