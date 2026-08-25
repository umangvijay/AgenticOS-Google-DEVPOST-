"use client";

import Link from "next/link";

export default function PricingPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar (Minimal) */}
      <header style={{
        padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: "1px solid var(--border-primary)", backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100
      }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "8px",
              background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: "white"
            }}>A</div>
            <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.5px", color: "var(--text-primary)" }}>
              AgentOS
            </span>
          </div>
        </Link>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          <Link href="/faq" className="hover:text-primary transition-colors" style={{ color: "var(--text-secondary)", fontWeight: 600 }}>FAQ</Link>
          <Link href="/login" className="btn btn-ghost">Sign In</Link>
          <Link href="/get-started" className="btn btn-primary">Get Started</Link>
        </div>
      </header>

      <main style={{ flex: 1, padding: "80px 20px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 80 }}>
            <div className="badge animate-fade-in-up" style={{ marginBottom: 24, padding: "6px 16px", background: "rgba(216, 133, 143, 0.1)", color: "var(--accent-pink)", border: "1px solid rgba(216, 133, 143, 0.3)", borderRadius: 100, display: "inline-block" }}>
              Pricing Plans
            </div>
            <h1 className="animate-fade-in-up" style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 900, marginBottom: 24, color: "var(--text-primary)" }}>
              Simple, transparent pricing.
            </h1>
            <p className="animate-fade-in-up" style={{ fontSize: 20, color: "var(--text-secondary)", animationDelay: "0.1s" }}>
              Start for free, upgrade when you need more power.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 32, alignItems: "center" }}>
            
            {/* Starter Plan */}
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, animationDelay: "0.2s" }}>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Starter</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>Perfect for individuals exploring automation.</p>
              <div style={{ fontSize: 48, fontWeight: 800, marginBottom: 24 }}>₹0<span style={{ fontSize: 16, color: "var(--text-tertiary)", fontWeight: 400 }}>/mo</span></div>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 32, display: "flex", flexDirection: "column", gap: 12 }}>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> 100 Workflow runs/mo</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> 5 Custom MCPs</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Community Support</li>
              </ul>
              <Link href="/signup" className="btn btn-secondary" style={{ width: "100%" }}>Get Started</Link>
            </div>

            {/* Pro Plan */}
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, border: "2px solid var(--accent)", position: "relative", animationDelay: "0.3s", transform: "scale(1.05)" }}>
              <div style={{ position: "absolute", top: -14, left: "50%", transform: "translateX(-50%)", background: "var(--accent)", color: "white", padding: "4px 16px", borderRadius: 100, fontSize: 12, fontWeight: 700, letterSpacing: 1 }}>
                MOST POPULAR
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Professional</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>For teams building production AI workflows.</p>
              <div style={{ fontSize: 48, fontWeight: 800, marginBottom: 24, color: "var(--accent)" }}>₹999<span style={{ fontSize: 16, color: "var(--text-tertiary)", fontWeight: 400 }}>/mo</span></div>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 32, display: "flex", flexDirection: "column", gap: 12 }}>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Unlimited Workflow runs</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Unlimited Custom MCPs</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> GPT-4o & Claude 3.5 Sonnet Support</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Priority Email Support</li>
              </ul>
              <Link href="/signup" className="btn btn-primary" style={{ width: "100%" }}>Upgrade to Pro</Link>
            </div>

            {/* Enterprise Plan */}
            <div className="glass-card animate-fade-in-up" style={{ padding: 40, animationDelay: "0.4s" }}>
              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Enterprise</h3>
              <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>Custom solutions for large organizations.</p>
              <div style={{ fontSize: 48, fontWeight: 800, marginBottom: 24 }}>₹4999<span style={{ fontSize: 16, color: "var(--text-tertiary)", fontWeight: 400 }}>/mo</span></div>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 32, display: "flex", flexDirection: "column", gap: 12 }}>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Dedicated Infrastructure</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> VPC Peering & SOC2 Compliance</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> Dedicated Success Manager</li>
                <li style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--success)" }}>✓</span> 99.99% Uptime SLA</li>
              </ul>
              <Link href="/contact" className="btn btn-secondary" style={{ width: "100%" }}>Contact Sales</Link>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
