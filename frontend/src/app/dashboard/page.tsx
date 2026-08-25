"use client";

import { useState, FormEvent, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { submitGoal, listWorkflows, WorkflowRun } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [recentWorkflows, setRecentWorkflows] = useState<WorkflowRun[]>([]);
  const [isLoadingWorkflows, setIsLoadingWorkflows] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const { workflows } = await listWorkflows(3);
        setRecentWorkflows(workflows);
      } catch (err) {
        console.error("Failed to load recent workflows", err);
      } finally {
        setIsLoadingWorkflows(false);
      }
    }
    loadData();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    
    setError("");
    setLoading(true);
    try {
      const res = await submitGoal(goal);
      router.push(`/dashboard/workflows/${res.run_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create workflow");
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
          Welcome back, {user?.name?.split(" ")[0] || "User"}
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>What would you like to build today?</p>
      </div>

      {/* Primary Goal Input */}
      <div className="glass-card" style={{ padding: "32px", marginBottom: 40 }}>
        <form onSubmit={handleSubmit}>
          {error && (
            <div style={{
              padding: "12px 16px", marginBottom: 20,
              background: "var(--error-subtle)", borderRadius: "var(--radius-md)",
              color: "var(--error)", fontSize: 14,
            }}>
              {error}
            </div>
          )}
          
          <div style={{ position: "relative" }}>
            <textarea
              className="input input-lg"
              placeholder="E.g., Find senior React developer jobs on YC, filter for remote, and email me a summary table..."
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              style={{
                minHeight: 120, resize: "vertical", 
                paddingBottom: 60, fontSize: 16,
                background: "var(--bg-tertiary)",
                width: "100%"
              }}
              disabled={loading}
              autoFocus
            />
            <div style={{ position: "absolute", bottom: 12, right: 12 }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!goal.trim() || loading}
                style={{ borderRadius: "100px", padding: "8px 20px" }}
              >
                {loading ? (
                  <span className="spinner" style={{ width: 16, height: 16 }} />
                ) : (
                  <>
                    <span>Execute</span>
                    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
        
        {/* Quick suggestions */}
        <div style={{ marginTop: 20, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)", paddingTop: 4 }}>Suggestions:</span>
          {[
            "Review my resume against this job description",
            "Research latest advancements in Quantum Computing",
            "Generate an MCP connector for Stripe API"
          ].map(suggestion => (
            <button
              key={suggestion}
              onClick={() => setGoal(suggestion)}
              className="badge badge-neutral"
              style={{ textTransform: "none", cursor: "pointer", border: "1px solid var(--border-primary)" }}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Dashboard Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
        
        {/* Recent Workflows */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>Recent Workflows</h2>
            <Link href="/dashboard/workflows" style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>View all</Link>
          </div>
          
          {isLoadingWorkflows ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="skeleton" style={{ height: 60 }} />
              <div className="skeleton" style={{ height: 60 }} />
            </div>
          ) : recentWorkflows.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {recentWorkflows.map(wf => (
                <Link
                  key={wf.run_id}
                  href={`/dashboard/workflows/${wf.run_id}`}
                  style={{
                    display: "block", padding: 12, borderRadius: "var(--radius-md)",
                    background: "var(--bg-tertiary)", textDecoration: "none",
                    border: "1px solid var(--border-primary)"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }} className="truncate">
                      {wf.goal.substring(0, 40)}{wf.goal.length > 40 ? "..." : ""}
                    </span>
                    <span className={`badge ${
                      wf.status === "COMPLETED" ? "badge-success" :
                      wf.status === "FAILED" ? "badge-error" :
                      wf.status === "RUNNING" ? "badge-info" : "badge-neutral"
                    }`}>
                      {wf.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    {new Date(wf.created_at).toLocaleString()} • {wf.tasks.length} tasks
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: "30px 0" }}>
              <p style={{ fontSize: 14 }}>No recent workflows.</p>
            </div>
          )}
        </div>
        
        {/* Quick Actions / Stats */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Quick Actions</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Link href="/dashboard/integrations/create" className="btn btn-secondary" style={{ height: "100px", flexDirection: "column" }}>
              <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ marginBottom: 8, color: "var(--accent)" }}>
                <path d="M12 4v16m8-8H4" />
              </svg>
              Build MCP
            </Link>
            <Link href="/dashboard/resume" className="btn btn-secondary" style={{ height: "100px", flexDirection: "column" }}>
              <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ marginBottom: 8, color: "var(--info)" }}>
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
              ATS Scanner
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
