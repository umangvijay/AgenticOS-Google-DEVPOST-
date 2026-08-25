"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";

export default function ContactPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("sending");
    
    // Simulate sending email to godumang35@gmail.com
    setTimeout(() => {
      setStatus("success");
      setEmail("");
      setMessage("");
    }, 1500);
  }

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
            <Link href="/features" className="hover:text-primary transition-colors">Features</Link>
            <Link href="/contact" className="hover:text-primary transition-colors" style={{ color: "var(--text-primary)" }}>Contact Us</Link>
          </nav>
          <div style={{ display: "flex", gap: 16 }}>
            <Link href="/login" className="btn btn-ghost">Sign In</Link>
            <Link href="/get-started" className="btn btn-primary">Get Started</Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main style={{ flex: 1, padding: "80px 20px", maxWidth: 1000, margin: "0 auto", width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 60 }}>
          <h1 style={{ fontSize: "clamp(40px, 6vw, 64px)", fontWeight: 800, marginBottom: 24 }} className="gradient-text">
            Get in Touch
          </h1>
          <p style={{ fontSize: 20, color: "var(--text-secondary)", maxWidth: 600, margin: "0 auto" }}>
            Have a question about AgentOS, or want to discuss enterprise deployments? 
            Reach out to our founding team directly.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: 48, alignItems: "start" }}>
          {/* Contact Details */}
          <div className="glass-card" style={{ padding: 40, borderTop: "4px solid var(--accent-pink)" }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Connect with us</h2>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>Umang Vijay</h3>
                <p style={{ color: "var(--accent)", fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Co-Founder & CTO</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <a href="mailto:godumang35@gmail.com" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none" }} className="hover:text-primary">
                    <span style={{ fontSize: 20 }}>✉️</span> godumang35@gmail.com
                  </a>
                  <a href="https://www.linkedin.com/in/umangvijay/" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none" }} className="hover:text-primary">
                    <span style={{ fontSize: 20 }}>🔗</span> LinkedIn Profile
                  </a>
                  <a href="https://github.com/umangvijay" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none" }} className="hover:text-primary">
                    <span style={{ fontSize: 20 }}>💻</span> GitHub Repository
                  </a>
                </div>
              </div>

              <div style={{ height: 1, background: "var(--border-primary)" }} />

              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>Ashmit Rana</h3>
                <p style={{ color: "var(--accent)", fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Co-Founder & CEO</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <a href="https://www.linkedin.com/in/ashmit-rana-43351628b" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none" }} className="hover:text-primary">
                    <span style={{ fontSize: 20 }}>🔗</span> LinkedIn Profile
                  </a>
                  <a href="https://github.com/Ash1971-sys" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none" }} className="hover:text-primary">
                    <span style={{ fontSize: 20 }}>💻</span> GitHub Repository
                  </a>
                  <span style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", marginTop: 4 }}>
                    <span style={{ fontSize: 20 }}>🏢</span> AgentOS Headquarters
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <div className="glass-card" style={{ padding: 40, borderTop: "4px solid var(--accent-purple)" }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Send a Message</h2>
            
            {status === "success" ? (
              <div style={{ padding: 32, textAlign: "center", background: "var(--success-subtle)", borderRadius: "var(--radius-md)", border: "1px solid var(--success)" }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
                <h3 style={{ fontSize: 20, color: "var(--success)", marginBottom: 8 }}>Message Sent!</h3>
                <p style={{ color: "var(--text-secondary)" }}>Thank you for reaching out. Umang will receive this directly at godumang35@gmail.com.</p>
                <button onClick={() => setStatus("idle")} className="btn btn-secondary" style={{ marginTop: 24 }}>
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                    Your Email Address
                  </label>
                  <input
                    type="email"
                    className="input"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={{ width: "100%" }}
                  />
                </div>
                
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                    Your Message
                  </label>
                  <textarea
                    className="input"
                    placeholder="How can we help you automate your business?"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    required
                    style={{ width: "100%", minHeight: 150, resize: "vertical" }}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary btn-lg"
                  disabled={status === "sending"}
                  style={{ width: "100%", marginTop: 8 }}
                >
                  {status === "sending" ? <span className="spinner" /> : "Send to godumang35@gmail.com"}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{ padding: "64px 40px", borderTop: "1px solid var(--border-primary)", background: "var(--bg-primary)", marginTop: 80 }}>
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
