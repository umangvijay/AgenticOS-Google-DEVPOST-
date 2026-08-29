import PublicNavbar from "@/components/PublicNavbar";

export const metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-24 flex-1 flex flex-col items-center">
        <div style={{ maxWidth: 800, width: "100%", textAlign: "left" }}>
          <div style={{ marginBottom: 64 }}>
            <h1 style={{ fontSize: "clamp(40px, 5vw, 56px)", fontWeight: 900, marginBottom: 16, letterSpacing: "-0.02em" }} className="gradient-text">
              Privacy Policy
            </h1>
            <p style={{ color: "var(--text-tertiary)", fontSize: 16, fontFamily: "var(--font-mono)" }}>
              Last Updated: August 29, 2026
            </p>
          </div>

          <div className="glass-card" style={{ padding: "48px 40px", display: "flex", flexDirection: "column", gap: 48, color: "var(--text-secondary)", lineHeight: 1.8, fontSize: 18 }}>
            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>01</span>
                Introduction
              </h2>
              <p>
                At AgentOS, we take your privacy seriously. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website and use our autonomous workflow engine platform.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>02</span>
                Data We Collect
              </h2>
              <p>
                We may collect personal identification information, such as your name, email address, and company details when you register for an account. We also collect usage data, workflow configurations, and integration logs necessary to execute your autonomous agents.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>03</span>
                How We Use Your Data
              </h2>
              <p>
                We use the information we collect primarily to provide, maintain, and improve the AgentOS platform. Your workflow data is securely isolated and is never used to train generalized AI models without your explicit, opt-in consent.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>04</span>
                Encryption and security
              </h2>
              <p>
                Passwords are stored with bcrypt. API keys and credentials in the vault are encrypted with AES-256-GCM;
                the vault key is derived with PBKDF2 (480,000 iterations). Sessions use RS256-signed JWTs.
                CSRF cookies are required for browser state-changing requests. We never return vault secrets in API responses,
                and we never log API keys. You can bring your own Gemini key; it stays encrypted at rest in your vault.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--accent-pink)", fontSize: 16, fontFamily: "var(--font-mono)", background: "rgba(236,72,153,0.1)", padding: "4px 12px", borderRadius: 20 }}>05</span>
                Contact Us
              </h2>
              <p>
                If you have any questions or concerns about this Privacy Policy, please contact our legal team at <a href="mailto:godumang35@gmail.com" style={{ color: "var(--accent)", textDecoration: "underline" }}>godumang35@gmail.com</a>.
              </p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
