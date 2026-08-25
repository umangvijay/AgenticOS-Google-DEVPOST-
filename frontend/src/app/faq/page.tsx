"use client";

import Link from "next/link";
import { useState } from "react";

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      q: "What is AgentOS?",
      a: "AgentOS is an autonomous workflow engine that allows you to automate complex tasks by defining goals. Instead of manually connecting nodes, you just tell AgentOS what you want, and it builds the workflow dynamically using AI."
    },
    {
      q: "How does it compare to traditional automation tools?",
      a: "Unlike traditional automation platforms that require you to drag and drop logical blocks, AgentOS is goal-oriented. It acts as an autonomous AI agent that figures out the required steps, API calls, and logic automatically."
    },
    {
      q: "What happens if an integration is missing?",
      a: "This is our superpower. If you request a workflow that requires an API we don't natively support, AgentOS's MCP Factory Agent will search the web, read the API documentation, and dynamically write the connection code for you on the fly."
    },
    {
      q: "Is my data secure?",
      a: "Yes. All integrations are executed in sandboxed environments, and we use strict CSP headers, OAuth integrations, and AES-256 encryption to keep your workflow data safe."
    },
    {
      q: "Can I self-host AgentOS?",
      a: "Currently, AgentOS is available as a managed cloud service to leverage our high-performance GPU infrastructure for the AI agents. Self-hosting options for the execution engine will be available for Enterprise customers."
    }
  ];

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
          <Link href="/pricing" className="hover:text-primary transition-colors" style={{ color: "var(--text-secondary)", fontWeight: 600 }}>Pricing</Link>
          <Link href="/login" className="btn btn-ghost">Sign In</Link>
          <Link href="/get-started" className="btn btn-primary">Get Started</Link>
        </div>
      </header>

      <main style={{ flex: 1, padding: "80px 20px" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <h1 className="animate-fade-in-up" style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 900, marginBottom: 24, color: "var(--text-primary)" }}>
              Frequently Asked Questions
            </h1>
            <p className="animate-fade-in-up" style={{ fontSize: 20, color: "var(--text-secondary)", animationDelay: "0.1s" }}>
              Everything you need to know about the future of automation.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {faqs.map((faq, i) => (
              <div 
                key={i}
                className="glass-card animate-fade-in-up" 
                style={{ animationDelay: `${0.2 + i * 0.1}s`, cursor: "pointer" }}
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
              >
                <div style={{ padding: "24px 32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                    {faq.q}
                  </h3>
                  <span style={{ fontSize: 24, color: "var(--text-secondary)", transform: openIndex === i ? "rotate(45deg)" : "none", transition: "transform 0.3s" }}>
                    +
                  </span>
                </div>
                {openIndex === i && (
                  <div style={{ padding: "0 32px 32px", color: "var(--text-secondary)", fontSize: 16, lineHeight: 1.6, animation: "fadeInUp 0.3s forwards" }}>
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 80 }} className="animate-fade-in-up">
            <p style={{ fontSize: 18, color: "var(--text-secondary)", marginBottom: 24 }}>
              Still have questions?
            </p>
            <Link href="/contact" className="btn btn-secondary btn-lg">
              Contact our Team
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
