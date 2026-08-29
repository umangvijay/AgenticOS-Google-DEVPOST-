"use client";

import Link from "next/link";
import { useState } from "react";
import PublicNavbar from "@/components/PublicNavbar";

const GROUPS = [
  {
    title: "Getting started",
    faqs: [
      { q: "What is AgentOS?", a: "AgentOS is an autonomous workspace. You describe a goal; it plans a DAG, builds any missing HTTP tools (MCP), and executes against live systems. The UI is chat-shaped like ChatGPT, but the engine is a planner plus factory plus executor — not a canned Q&A bot." },
      { q: "How do I try it for free?", a: "Click Get started for free or Start building free. That creates a guest session and opens the dashboard. Use Back to home on Sign in if you landed on login by mistake." },
      { q: "Why did Get started used to hang?", a: "Guest provisioning now waits for auth, times out, and offers retry. If it still fails, Sign in or Create an account." },
    ],
  },
  {
    title: "Integrations and MCP",
    faqs: [
      { q: "What happens if an integration is missing?", a: "The MCP factory builds it from an OpenAPI spec, a docs URL, or a description. It probes the public API live, registers tools, then the agent can call them in the same run." },
      { q: "Is this limited to Stripe or one vendor?", a: "No. Brand names on the homepage are examples. Any HTTP API is in scope." },
      { q: "Where is the integrations page?", a: "Public overview: /integrations. Your connected MCPs: Dashboard → Integrations. Create MCP is the factory UI." },
    ],
  },
  {
    title: "Keys, security, email",
    faqs: [
      { q: "Can I use my own Gemini API key?", a: "Yes. Settings → Your Gemini API key, or Vault with name gemini and field api_key. It is encrypted and used for your runs so you are not blocked by the shared quota." },
      { q: "Is my data secure?", a: "Credentials use AES-256-GCM. Values are never returned after save. Browser automation stays on the starting domain. CSRF, JWT (RS256), and sandboxed MCP generation are on by default." },
      { q: "Does Contact actually email you?", a: "It is always stored. It is emailed to godumang35@gmail.com only when CONTACT_SMTP_PASSWORD is set to a Gmail App Password (smtp_configured: true). If mail is not configured, the contact page says so and does not claim the message was sent. Privacy questions: godumang35@gmail.com." },
    ],
  },
  {
    title: "Runs and quota",
    faqs: [
      { q: "Site health works but chat fails with 429?", a: "Gemini free-tier quota is exhausted for planner/LLM paths. Site health and OpenAPI MCP builds can still run. Add your own key, or retry after quota resets." },
      { q: "Does the dashboard hide when I scroll?", a: "No. The sidebar and top bar stay pinned like ChatGPT. Only the main pane scrolls." },
    ],
  },
];

export default function FAQPage() {
  const [open, setOpen] = useState("0-0");

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />
      <main className="flex-1 py-12 px-4 md:py-20" style={{ maxWidth: 860, margin: "0 auto", width: "100%" }}>
        <p className="eyebrow" style={{ textAlign: "center" }}>FAQs</p>
        <h1 className="apple-hero" style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 900, marginBottom: 12, textAlign: "center" }}>
          Answers, not a wall of text.
        </h1>
        <p style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: 18, marginBottom: 48 }}>
          Workspace, MCP factory, vault, and quota. Deeper diagrams live in <Link href="/docs" style={{ color: "var(--accent)" }}>Docs</Link>.
        </p>
        {GROUPS.map((group, gi) => (
          <section key={group.title} style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 14, letterSpacing: 0.12, textTransform: "uppercase", color: "var(--accent)", marginBottom: 12 }}>{group.title}</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {group.faqs.map((faq, i) => {
                const id = `${gi}-${i}`;
                const isOpen = open === id;
                return (
                  <div key={id} className="glass-panel" style={{ overflow: "hidden" }}>
                    <button
                      type="button"
                      onClick={() => setOpen(isOpen ? "" : id)}
                      style={{
                        width: "100%", textAlign: "left", background: "transparent", border: "none",
                        padding: "18px 22px", display: "flex", justifyContent: "space-between", gap: 12,
                        cursor: "pointer", fontSize: 16, fontWeight: 600, color: "var(--text-primary)",
                      }}
                    >
                      {faq.q}
                      <span style={{ transform: isOpen ? "rotate(45deg)" : "none", transition: "transform 0.2s" }}>+</span>
                    </button>
                    {isOpen && (
                      <div style={{ padding: "0 22px 20px", color: "var(--text-secondary)", lineHeight: 1.65 }}>{faq.a}</div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
        <div style={{ textAlign: "center", marginTop: 48 }}>
          <Link href="/contact" className="btn btn-primary btn-lg">Contact the team</Link>
        </div>
      </main>
    </div>
  );
}
