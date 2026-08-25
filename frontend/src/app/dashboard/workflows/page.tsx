"use client";

import { useState, useEffect } from "react";
import { listWorkflows, WorkflowRun } from "@/lib/api";
import Link from "next/link";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const { workflows } = await listWorkflows(50);
        setWorkflows(workflows);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load workflows");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="animate-fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>Workflows</h1>
          <p style={{ color: "var(--text-secondary)" }}>View and manage your autonomous tasks.</p>
        </div>
        <Link href="/dashboard" className="btn btn-primary">New Workflow</Link>
      </div>

      {error && (
        <div style={{
          padding: "12px 16px", marginBottom: 20,
          background: "var(--error-subtle)", borderRadius: "var(--radius-md)",
          color: "var(--error)", fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="skeleton" style={{ height: 80 }} />
          <div className="skeleton" style={{ height: 80 }} />
          <div className="skeleton" style={{ height: 80 }} />
        </div>
      ) : workflows.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {workflows.map(wf => (
            <Link
              key={wf.run_id}
              href={`/dashboard/workflows/${wf.run_id}`}
              className="glass-card"
              style={{ padding: 20, textDecoration: "none", display: "block" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    {wf.goal}
                  </h3>
                  <div style={{ fontSize: 13, color: "var(--text-tertiary)", display: "flex", gap: 16 }}>
                    <span>ID: {wf.run_id.substring(0, 8)}</span>
                    <span>Started: {new Date(wf.created_at).toLocaleString()}</span>
                  </div>
                </div>
                <span className={`badge ${
                  wf.status === "COMPLETED" ? "badge-success" :
                  wf.status === "FAILED" ? "badge-error" :
                  wf.status === "RUNNING" ? "badge-info" : "badge-neutral"
                }`}>
                  {wf.status}
                </span>
              </div>
              
              {/* Task progress bar (simple) */}
              <div style={{ display: "flex", gap: 4, marginTop: 16 }}>
                {wf.tasks.map(t => (
                  <div key={t.task_id} style={{
                    flex: 1, height: 4, borderRadius: 2,
                    background: 
                      t.status === "COMPLETED" ? "var(--success)" :
                      t.status === "FAILED" ? "var(--error)" :
                      t.status === "RUNNING" ? "var(--info)" :
                      "var(--bg-tertiary)"
                  }} title={`${t.agent}: ${t.status}`} />
                ))}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="glass-card empty-state">
          <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <h3 style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>No workflows yet</h3>
          <p style={{ marginBottom: 24 }}>Start by giving AgentOS a goal.</p>
          <Link href="/dashboard" className="btn btn-primary">Create Workflow</Link>
        </div>
      )}
    </div>
  );
}
