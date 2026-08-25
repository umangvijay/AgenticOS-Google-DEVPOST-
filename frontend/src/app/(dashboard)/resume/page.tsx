"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export default function ResumePlatformPage() {
  const { isAuthenticated } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [score, setScore] = useState<number | null>(null);

  if (!isAuthenticated) return null;

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar */}
      <header style={{
        padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: "1px solid var(--border-primary)", backdropFilter: "blur(12px)"
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
          <span style={{ fontSize: 20, fontWeight: 700 }} className="gradient-text">
            AgentOS Workspace
          </span>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          <Link href="/dashboard" className="btn btn-ghost">Dashboard</Link>
          <Link href="/agents" className="btn btn-ghost">Agents</Link>
        </div>
      </header>

      {/* Content */}
      <main style={{ flex: 1, padding: "60px 40px", maxWidth: 1000, margin: "0 auto", width: "100%" }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 8 }}>Smart Resume & ATS Platform</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: 40 }}>
          Upload your master resume and a Job Description. Our vector-based engine will parse, score against ATS systems, and tailor a perfectly formatted PDF without fabricating experience.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          
          {/* Upload Section */}
          <div className="glass-card" style={{ padding: 32 }}>
            <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>1. Master Resume</h3>
            <div style={{
              border: "2px dashed var(--border-hover)", borderRadius: 12, padding: 40,
              textAlign: "center", background: "var(--bg-input)", cursor: "pointer", transition: "all 0.3s"
            }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📄</div>
              <div style={{ fontWeight: 600 }}>Drag and drop your PDF here</div>
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", marginTop: 4 }}>or click to browse</div>
            </div>

            <h3 style={{ fontSize: 20, fontWeight: 700, marginTop: 32, marginBottom: 16 }}>2. Target Job Description</h3>
            <textarea className="input" rows={6} placeholder="Paste the job description or enter a URL..." style={{ resize: "none" }}></textarea>

            <button className="btn btn-primary" style={{ width: "100%", marginTop: 24 }} onClick={() => setScore(87)}>
              Analyze & Tailor Resume
            </button>
          </div>

          {/* Results Section */}
          <div className="glass-card" style={{ padding: 32, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>ATS Analysis Results</h3>
            
            {!score ? (
              <div className="empty-state" style={{ flex: 1 }}>
                <div style={{ fontSize: 40, marginBottom: 16 }}>🎯</div>
                <p>Upload a resume and JD to see your match score.</p>
              </div>
            ) : (
              <div className="animate-fade-in-up" style={{ flex: 1 }}>
                
                <div style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 32 }}>
                  <div style={{
                    width: 100, height: 100, borderRadius: "50%",
                    border: "8px solid var(--success)", display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: 28, fontWeight: 800, color: "var(--success)",
                    boxShadow: "0 0 20px rgba(16, 185, 129, 0.2)"
                  }}>
                    {score}%
                  </div>
                  <div>
                    <h4 style={{ fontSize: 18, fontWeight: 700 }}>Excellent Match</h4>
                    <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Your experience strongly aligns with the core requirements.</p>
                  </div>
                </div>

                <div style={{ marginBottom: 24 }}>
                  <h5 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 8, textTransform: "uppercase" }}>Key Findings</h5>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <span className="badge badge-success">Python</span>
                    <span className="badge badge-success">Distributed Systems</span>
                    <span className="badge badge-warning">Missing: Kubernetes</span>
                  </div>
                </div>

                <div style={{ marginTop: "auto", display: "flex", gap: 16 }}>
                  <button className="btn btn-secondary" style={{ flex: 1 }}>View LaTeX Source</button>
                  <button className="btn btn-primary" style={{ flex: 1 }}>Download Tailored PDF</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
