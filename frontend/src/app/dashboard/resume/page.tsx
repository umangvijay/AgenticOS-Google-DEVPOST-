"use client";

import { useState } from "react";

export default function ResumePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{
    score: number;
    keywords_found: string[];
    keywords_missing: string[];
    suggestions: string[];
  } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !jobDescription.trim()) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("jobDescription", jobDescription);

      const token = localStorage.getItem("agentos_auth");
      const res = await fetch("http://localhost:8000/api/v1/resume/scan", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze resume. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Resume & ATS Scanner</h1>
        <p style={{ color: "var(--text-secondary)" }}>Analyze your resume against a job description and generate tailored versions.</p>
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        {/* Left Column: Input */}
        <div style={{ flex: "1 1 400px" }}>
          <div className="glass-card" style={{ padding: 24 }}>
            <form onSubmit={handleScan}>
              
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 8 }}>
                  Master Resume (PDF/Markdown)
                </label>
                <div style={{
                  border: "2px dashed var(--border-primary)", borderRadius: "var(--radius-md)",
                  padding: 32, textAlign: "center", background: "var(--bg-tertiary)",
                  cursor: "pointer", position: "relative"
                }}>
                  <input
                    type="file"
                    accept=".pdf,.md,.txt"
                    onChange={handleFileChange}
                    style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }}
                    disabled={loading}
                  />
                  <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ margin: "0 auto 12px", color: "var(--text-tertiary)" }}>
                    <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {file ? (
                    <div style={{ color: "var(--accent)", fontWeight: 500 }}>{file.name}</div>
                  ) : (
                    <div>
                      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Click to upload</span>
                      <span style={{ color: "var(--text-tertiary)" }}> or drag and drop</span>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginBottom: 24 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 8 }}>
                  Job Description
                </label>
                <textarea
                  className="input"
                  placeholder="Paste the job description here..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  style={{ minHeight: 160, resize: "vertical" }}
                  required
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: "100%" }}
                disabled={loading || !file || !jobDescription.trim()}
              >
                {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : "Scan & Analyze"}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Results */}
        <div style={{ flex: "1 1 400px", display: "flex", flexDirection: "column" }}>
          {results ? (
            <div className="glass-card animate-slide-in" style={{ padding: 24, flex: 1 }}>
              <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 24 }}>Analysis Results</h2>
              
              <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 32 }}>
                {/* Score Gauge */}
                <div style={{ position: "relative", width: 100, height: 100 }}>
                  <svg viewBox="0 0 100 100" width="100" height="100">
                    <circle cx="50" cy="50" r="45" fill="none" stroke="var(--bg-tertiary)" strokeWidth="10" />
                    <circle cx="50" cy="50" r="45" fill="none" 
                      stroke={results.score >= 80 ? "var(--success)" : results.score >= 60 ? "var(--warning)" : "var(--error)"} 
                      strokeWidth="10" 
                      strokeDasharray={`${(results.score / 100) * 283} 283`}
                      strokeLinecap="round"
                      transform="rotate(-90 50 50)"
                      style={{ transition: "stroke-dasharray 1s ease-out" }}
                    />
                  </svg>
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 700 }}>
                    {results.score}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)" }}>ATS Match Score</div>
                  <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                    {results.score >= 80 ? "Great match! You have a high chance of passing." : 
                     results.score >= 60 ? "Good start, but missing some key requirements." : 
                     "Significant gaps detected. Major tailoring needed."}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
                <div style={{ flex: 1, padding: 16, background: "var(--success-subtle)", borderRadius: "var(--radius-md)", border: "1px solid rgba(16,185,129,0.2)" }}>
                  <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--success)", marginBottom: 8 }}>Found Keywords</h4>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 13, color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 4 }}>
                    {results.keywords_found.map(k => <li key={k}>{k}</li>)}
                  </ul>
                </div>
                <div style={{ flex: 1, padding: 16, background: "var(--error-subtle)", borderRadius: "var(--radius-md)", border: "1px solid rgba(239,68,68,0.2)" }}>
                  <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--error)", marginBottom: 8 }}>Missing Keywords</h4>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 13, color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 4 }}>
                    {results.keywords_missing.map(k => <li key={k}>{k}</li>)}
                  </ul>
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Suggestions</h3>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
                  {results.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>

              <div style={{ marginTop: 24, paddingTop: 24, borderTop: "1px solid var(--border-primary)" }}>
                <button className="btn btn-secondary" style={{ width: "100%" }}>
                  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M12 4v16m8-8H4" />
                  </svg>
                  Generate Tailored Resume
                </button>
              </div>

            </div>
          ) : (
            <div className="glass-card empty-state" style={{ flex: 1 }}>
              <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
                <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>Analysis Pending</h3>
              <p style={{ maxWidth: 250 }}>Upload your resume and a job description to get started.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
