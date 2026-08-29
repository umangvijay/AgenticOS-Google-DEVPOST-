"use client";

import { useState, FormEvent, useEffect } from "react";
import PublicNavbar from "@/components/PublicNavbar";

const TEAM_EMAIL = "godumang35@gmail.com";

export default function ContactPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "saved" | "error">("idle");
  const [info, setInfo] = useState("");
  const [smtpReady, setSmtpReady] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/contact")
      .then((r) => r.json())
      .then((d) => setSmtpReady(Boolean(d.smtp_configured)))
      .catch(() => setSmtpReady(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setInfo("");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || data.detail || "Could not send message");
      }
      setInfo(data.message || `Message sent to ${TEAM_EMAIL}`);
      if (data.delivered) {
        setStatus("success");
        setEmail("");
        setName("");
        setMessage("");
      } else if (data.saved) {
        setStatus("saved");
      } else {
        setStatus("error");
      }
    } catch (err: unknown) {
      setStatus("error");
      setInfo(err instanceof Error ? err.message : "Failed to send. Please email us directly.");
    }
  }

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-20 max-w-5xl mx-auto w-full flex-1">
        <div className="text-center mb-16 animate-fade-in-up">
          <p className="eyebrow">Contact</p>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold mb-6 gradient-text">
            Get in Touch
          </h1>
          <p className="text-lg md:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
            Have a question about AgentOS, or want to discuss enterprise deployments?
            Messages go to <a href={`mailto:${TEAM_EMAIL}`} style={{ color: "var(--accent)" }}>{TEAM_EMAIL}</a>.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start">
          <div className="glass-panel glass-lift p-6 md:p-10 border-t-4 border-[var(--accent-pink)] animate-fade-in-up">
            <h2 className="text-xl md:text-2xl font-bold mb-6">Connect with us</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Umang Vijay</h3>
                <p style={{ color: "var(--accent)", fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Co-Founder & CTO</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <a href={`mailto:${TEAM_EMAIL}`} style={{ color: "var(--text-secondary)", textDecoration: "none" }}>{TEAM_EMAIL}</a>
                  <a href="https://www.linkedin.com/in/umangvijay/" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>LinkedIn</a>
                  <a href="https://github.com/umangvijay" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>GitHub</a>
                </div>
              </div>
              <div style={{ height: 1, background: "var(--border-primary)" }} />
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Ashmit Rana</h3>
                <p style={{ color: "var(--accent)", fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Co-Founder & CEO</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <a href="https://www.linkedin.com/in/ashmit-rana-43351628b" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>LinkedIn</a>
                  <a href="https://github.com/Ash1971-sys" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>GitHub</a>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel glass-lift p-6 md:p-10 border-t-4 border-[var(--accent-purple)] animate-fade-in-up" style={{ animationDelay: "80ms" }}>
            <h2 className="text-xl md:text-2xl font-bold mb-6">Send a Message</h2>
            {smtpReady === false && (
              <div style={{ padding: 12, marginBottom: 16, background: "var(--warning-subtle, rgba(245,158,11,0.12))", color: "var(--text-secondary)", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>
                Mail is not sending yet because <code>CONTACT_SMTP_PASSWORD</code> is empty.
                Open the project-root <code>.env</code> (same folder as README), create a Gmail App Password at{" "}
                <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>myaccount.google.com/apppasswords</a>
                {" "}(2-Step Verification on), paste it as <code>CONTACT_SMTP_PASSWORD=xxxx xxxx xxxx xxxx</code>, save, then send again. No restart needed.
              </div>
            )}
            {status === "success" ? (
              <div className="animate-fade-in" style={{ padding: 32, textAlign: "center", background: "var(--success-subtle)", borderRadius: 16 }}>
                <h3 style={{ fontSize: 20, color: "var(--success)", marginBottom: 8 }}>Message emailed</h3>
                <p style={{ color: "var(--text-secondary)" }}>{info}</p>
                <button onClick={() => setStatus("idle")} className="btn btn-secondary" style={{ marginTop: 24 }}>Send another</button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {status === "error" && (
                  <div style={{ padding: 12, background: "var(--error-subtle)", color: "var(--error)", borderRadius: 12 }}>{info}</div>
                )}
                {status === "saved" && (
                  <div style={{ padding: 12, background: "var(--warning-subtle, rgba(245,158,11,0.12))", color: "var(--warning, #b45309)", borderRadius: 12 }}>
                    {info} You can also mail us directly at {TEAM_EMAIL}.
                  </div>
                )}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Your name</label>
                  <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Lovelace" style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Your email</label>
                  <input type="email" className="input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Message</label>
                  <textarea className="input" placeholder="How can AgentOS help you?" value={message} onChange={(e) => setMessage(e.target.value)} required style={{ width: "100%", minHeight: 150, resize: "vertical" }} />
                </div>
                <button type="submit" className="btn btn-primary btn-lg" disabled={status === "sending"} style={{ width: "100%" }}>
                  {status === "sending" ? <span className="spinner" /> : "Send message"}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
