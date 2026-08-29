import PublicNavbar from "@/components/PublicNavbar";

export default function TermsPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-24 flex-1 flex flex-col items-center">
        <div style={{ maxWidth: 800, width: "100%", textAlign: "left" }}>
          <div style={{ marginBottom: 64 }}>
            <h1 style={{ fontSize: "clamp(40px, 5vw, 56px)", fontWeight: 900, marginBottom: 16, letterSpacing: "-0.02em" }} className="gradient-text">
              Terms of Service
            </h1>
            <p style={{ color: "var(--text-tertiary)", fontSize: 16, fontFamily: "var(--font-mono)" }}>
              Last Updated: August 27, 2026
            </p>
          </div>

          <div className="glass-card" style={{ padding: "48px 40px", display: "flex", flexDirection: "column", gap: 48, color: "var(--text-secondary)", lineHeight: 1.8, fontSize: 18 }}>
            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>01</span>
                Acceptance of Terms
              </h2>
              <p>
                By accessing or using the AgentOS platform, you agree to be bound by these Terms of Service. If you do not agree to all the terms and conditions, you must not use our services.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>02</span>
                Description of Service
              </h2>
              <p>
                AgentOS provides a platform for building, deploying, and managing autonomous AI agents and workflows. You understand and agree that the Service is provided "AS-IS" and that AgentOS assumes no responsibility for the timeliness, deletion, or failure to store any user configurations or communications.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>03</span>
                User Conduct
              </h2>
              <p>
                You agree not to use the Service to build agents or workflows that violate any local, state, national, or international law, or to deploy malicious code, spam, or abusive automated systems.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>04</span>
                Limitation of Liability
              </h2>
              <p>
                In no event shall AgentOS be liable for any direct, indirect, incidental, special, consequential, or exemplary damages resulting from the use or the inability to use the Service.
              </p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
