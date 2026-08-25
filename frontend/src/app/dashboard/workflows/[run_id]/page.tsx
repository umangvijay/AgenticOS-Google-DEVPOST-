"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { getWorkflow, subscribeWorkflowEvents, cancelWorkflow, retryWorkflow, WorkflowRun, WorkflowEvent } from "@/lib/api";
import WorkflowGraph from "@/components/WorkflowGraph";

// Assuming we would have an API function like this in the real api.ts
const respondToApproval = async (taskId: string, approved: boolean, modifiedArgs?: Record<string, any>) => {
  // Mock API call since this is frontend-focused
  console.log(`Responding to approval for task ${taskId}:`, { approved, modifiedArgs });
};

export default function WorkflowExecutionPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.run_id as string;

  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Load initial state
  useEffect(() => {
    async function load() {
      try {
        const wf = await getWorkflow(runId);
        setWorkflow(wf);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load workflow");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  // Subscribe to SSE
  useEffect(() => {
    if (!workflow || ["COMPLETED", "FAILED", "CANCELLED"].includes(workflow.status)) {
      // Don't subscribe if already in terminal state (though we could for history if API supported it)
      // For now, if we want live updates, we subscribe
    }

    const unsubscribe = subscribeWorkflowEvents(
      runId,
      (event) => {
        setEvents(prev => [...prev, event]);
        // Update local workflow state based on event
        setWorkflow(prev => {
          if (!prev) return prev;
          const updated = { ...prev };
          
          if (event.type === "WORKFLOW_COMPLETED") updated.status = "COMPLETED";
          if (event.type === "WORKFLOW_FAILED") updated.status = "FAILED";
          if (event.type === "WORKFLOW_CANCELLED") updated.status = "CANCELLED";
          
          if (event.task_id) {
            const taskIndex = updated.tasks.findIndex(t => t.task_id === event.task_id);
            if (taskIndex >= 0) {
              const task = { ...updated.tasks[taskIndex] };
              if (event.type === "TASK_STARTED") task.status = "RUNNING";
              if (event.type === "TASK_COMPLETED") {
                task.status = "COMPLETED";
                if (event.sanitized_metadata?.output) {
                   task.output_data = event.sanitized_metadata.output as Record<string, unknown>;
                }
              }
              if (event.type === "TASK_FAILED") {
                 task.status = "FAILED";
                 task.error = event.summary;
              }
              updated.tasks[taskIndex] = task;
            }
          }
          return updated;
        });
      },
      () => console.log("SSE connected"),
      (err) => console.error("SSE error", err)
    );

    return () => unsubscribe();
  }, [runId, workflow?.status]);

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this workflow?")) return;
    try {
      await cancelWorkflow(runId);
      const wf = await getWorkflow(runId);
      setWorkflow(wf);
    } catch (err) {
      alert("Failed to cancel: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleRetry = async () => {
    try {
      await retryWorkflow(runId);
      const wf = await getWorkflow(runId);
      setWorkflow(wf);
      setEvents([]); // Clear old events on retry
    } catch (err) {
      alert("Failed to retry: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 100 }}>
      <div className="spinner" />
    </div>
  );

  if (error || !workflow) return (
    <div className="empty-state">
      <div style={{ color: "var(--error)", marginBottom: 16 }}>{error || "Workflow not found"}</div>
      <button className="btn btn-secondary" onClick={() => router.push("/dashboard/workflows")}>Back</button>
    </div>
  );

  const isTerminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(workflow.status);

  return (
    <div className="animate-fade-in" style={{ display: "flex", gap: 24, height: "calc(100vh - 120px)" }}>
      
      {/* Left Column: DAG & Details (2/3 width) */}
      <div style={{ flex: 2, display: "flex", flexDirection: "column", gap: 24, overflowY: "auto", paddingRight: 8 }}>
        
        {/* Header Card */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Workflow Execution</h1>
            <span className={`badge ${
              workflow.status === "COMPLETED" ? "badge-success" :
              workflow.status === "FAILED" ? "badge-error" :
              workflow.status === "CANCELLED" ? "badge-neutral" :
              "badge-info"
            }`}>
              {workflow.status}
            </span>
          </div>
          
          <div style={{ background: "var(--bg-tertiary)", padding: 16, borderRadius: "var(--radius-md)", marginBottom: 16 }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block", marginBottom: 4 }}>Goal</span>
            <p style={{ fontSize: 15, fontWeight: 500 }}>{workflow.goal}</p>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            {!isTerminal && (
              <button className="btn btn-danger btn-sm" onClick={handleCancel}>Cancel Workflow</button>
            )}
            {["FAILED", "CANCELLED"].includes(workflow.status) && (
              <button className="btn btn-primary btn-sm" onClick={handleRetry}>Retry Failed Tasks</button>
            )}
          </div>
        </div>

        {/* DAG Visualization */}
        <div className="glass-card" style={{ padding: 24, flex: 1, display: "flex", flexDirection: "column" }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Execution Plan</h2>
          
          <div style={{ flex: 1, minHeight: 400 }}>
            <WorkflowGraph workflow={workflow} />
          </div>

          {/* ── RICH APPROVAL MODAL BLOCK ── */}
          {workflow.tasks.filter(t => t.status === "WAITING_APPROVAL").map(task => (
            <div key={task.task_id} className="glass-card animate-slide-in" style={{ 
              marginTop: 24, padding: 20, border: "1px solid var(--warning)", 
              background: "rgba(255, 189, 46, 0.05)" 
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 18 }}>⚠️</span>
                <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--warning)" }}>Human Intervention Required for {task.agent}</h4>
              </div>
              
              <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 16 }}>
                The agent is attempting to execute a potentially destructive or high-risk action using tool: <strong>{task.tool}</strong>. Please review the payload below.
              </p>

              <div style={{ background: "#111", padding: 16, borderRadius: 8, marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                  Pending Payload
                </div>
                <pre style={{ margin: 0, fontSize: 13, color: "#27c93f", fontFamily: "var(--font-mono)", overflowX: "auto" }}>
                  {JSON.stringify(task.input_data, null, 2)}
                </pre>
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <button 
                  className="btn btn-primary" 
                  style={{ background: "var(--success)", borderColor: "var(--success)", padding: "10px 24px" }}
                  onClick={() => {
                    respondToApproval(task.task_id, true);
                    setWorkflow(prev => {
                      if (!prev) return prev;
                      const updated = { ...prev };
                      const idx = updated.tasks.findIndex(t => t.task_id === task.task_id);
                      if (idx >= 0) updated.tasks[idx].status = "RUNNING";
                      return updated;
                    });
                  }}
                >
                  Approve Action
                </button>
                <button 
                  className="btn btn-secondary"
                  style={{ padding: "10px 24px" }}
                  onClick={() => {
                    respondToApproval(task.task_id, false);
                    setWorkflow(prev => {
                      if (!prev) return prev;
                      const updated = { ...prev };
                      const idx = updated.tasks.findIndex(t => t.task_id === task.task_id);
                      if (idx >= 0) {
                        updated.tasks[idx].status = "FAILED";
                        updated.tasks[idx].error = "User rejected the action.";
                      }
                      return updated;
                    });
                  }}
                >
                  Reject Action
                </button>
                <span style={{ fontSize: 13, color: "var(--text-tertiary)", marginLeft: "auto" }}>
                  Risk Level: High
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Column: Live Event Stream (1/3 width) */}
      <div className="glass-card" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-primary)", background: "var(--bg-tertiary)" }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
            <span className={`status-dot ${!isTerminal ? 'active' : 'inactive'}`} />
            Live Event Stream
          </h2>
        </div>
        
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
          {events.length === 0 ? (
             <div style={{ color: "var(--text-tertiary)", fontSize: 13, textAlign: "center", marginTop: 40 }}>
               Waiting for events...
             </div>
          ) : (
            events.map(ev => (
              <div key={ev.event_id} style={{
                padding: 12, borderRadius: "var(--radius-md)",
                background: "var(--bg-input)", border: "1px solid var(--border-primary)",
                fontSize: 13, fontFamily: "var(--font-mono)"
              }}>
                <div style={{ color: "var(--accent)", marginBottom: 4, fontSize: 11 }}>
                  {new Date(ev.timestamp).toLocaleTimeString()} — {ev.type}
                </div>
                <div style={{ color: "var(--text-primary)" }}>{ev.summary}</div>
              </div>
            ))
          )}
          <div ref={eventsEndRef} />
        </div>
      </div>

    </div>
  );
}
