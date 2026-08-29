"use client";

import { useEffect, useRef, useState, CSSProperties } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getWorkflow, getWorkflowThread, subscribeWorkflowEvents, cancelWorkflow, retryWorkflow,
  resumeWorkflow, WorkflowRun, WorkflowEvent, Task,
} from "@/lib/api";
import ChatComposer from "@/components/ChatComposer";
import WorkflowGraph from "@/components/WorkflowGraph";
import ExecutionTimeline from "@/components/ExecutionTimeline";

function bubbleStyle(role: "user" | "agent"): CSSProperties {
  if (role === "user") {
    return {
      alignSelf: "flex-end", maxWidth: "min(640px, 92%)",
      background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
      color: "white", borderRadius: "18px 18px 4px 18px", padding: "12px 16px",
    };
  }
  return {
    alignSelf: "flex-start", maxWidth: "min(720px, 96%)",
    background: "var(--bg-card)", border: "1px solid var(--border-primary)",
    borderRadius: "18px 18px 18px 4px", padding: "12px 16px",
    backdropFilter: "blur(20px)",
  };
}

function assistantText(task: Task): string | null {
  const out = task.output_data;
  if (!out || typeof out !== "object") return null;
  for (const key of ["reply", "message", "result", "summary"]) {
    const value = out[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  if (Array.isArray(out.tools)) {
    const names = (out.tools as { name?: string }[]).map((t) => t?.name).filter(Boolean).join(", ");
    const mcp = typeof out.mcp_id === "string" ? out.mcp_id : "";
    return `Integration generated${names ? ` with ${names}` : ""}.${mcp ? `\nmcp_id: ${mcp}` : ""}`;
  }
  if (typeof out.status_code === "number") {
    const data = out.data;
    const snippet = typeof data === "string" ? data.slice(0, 800) : JSON.stringify(data, null, 2).slice(0, 800);
    return `Live response · HTTP ${out.status_code}${snippet ? `\n\n${snippet}` : ""}`;
  }
  if (out.ok === true || out.reachable === true || out.sent === true) {
    return JSON.stringify(out, null, 2);
  }
  try {
    const pretty = JSON.stringify(out, null, 2);
    if (pretty && pretty !== "{}" && pretty.length < 1200) return pretty;
  } catch { /* ignore */ }
  return null;
}

function isTerminal(status?: string) {
  return ["COMPLETED", "FAILED", "CANCELLED"].includes(status || "");
}

function isWaitingHuman(workflow: WorkflowRun) {
  return (workflow.tasks || []).some((t) => t.status === "WAITING_APPROVAL");
}

function TurnView({ workflow }: { workflow: WorkflowRun }) {
  const replies = (workflow.tasks || [])
    .map((t) => ({ task: t, text: t.status === "COMPLETED" ? assistantText(t) : null }))
    .filter((x) => x.text);
  const failed = (workflow.tasks || []).filter((t) => t.status === "FAILED");
  const inFlight = (workflow.tasks || []).some((t) =>
    t.status === "RUNNING" || t.status === "PENDING" || t.status === "WAITING" || t.status === "RETRYING"
  );
  const busy = (!isTerminal(workflow.status) || inFlight) && replies.length === 0 && failed.length === 0;

  return (
    <>
      <div style={bubbleStyle("user")}>
        <div style={{ fontSize: 11, opacity: 0.85, marginBottom: 4 }}>You</div>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{workflow.goal}</div>
      </div>
      {replies.map(({ task, text }) => (
        <div key={`${workflow.run_id}-out-${task.task_id}`} style={bubbleStyle("agent")}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 6 }}>AgentOS</div>
          <div style={{ fontSize: 15, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>{text}</div>
        </div>
      ))}
      {failed.map((t) => (
        <div key={`${workflow.run_id}-fail-${t.task_id}`} style={bubbleStyle("agent")}>
          <div style={{ fontSize: 11, color: "var(--error)", marginBottom: 6 }}>AgentOS</div>
          <div style={{ fontSize: 14, lineHeight: 1.55 }}>{t.error || "That step failed. Try again or rephrase the goal."}</div>
        </div>
      ))}
      {(workflow.tasks || []).filter((t) => t.status === "WAITING_APPROVAL").map((t) => (
        <div key={`${workflow.run_id}-wait-${t.task_id}`} style={bubbleStyle("agent")}>
          <div style={{ fontSize: 11, color: "var(--warning, #b45309)", marginBottom: 6 }}>Waiting on you</div>
          <div style={{ fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
            {typeof t.output_data?.message === "string"
              ? t.output_data.message
              : "Complete the CAPTCHA, OTP, or MFA in the browser window, then click Resume. AgentOS will not fill those fields."}
          </div>
        </div>
      ))}
      {busy && (
        <div style={bubbleStyle("agent")}>
          <span className="spinner" style={{ width: 16, height: 16, display: "inline-block", verticalAlign: "middle", marginRight: 8 }} />
          Thinking…
        </div>
      )}
      {isTerminal(workflow.status) && workflow.status === "FAILED" && replies.length === 0 && failed.length === 0 && (
        <div style={bubbleStyle("agent")}>
          <div style={{ fontSize: 11, color: "var(--error)", marginBottom: 6 }}>AgentOS</div>
          <div style={{ fontSize: 14, lineHeight: 1.55 }}>That run failed before a reply was written. Try sending again.</div>
        </div>
      )}
    </>
  );
}

export default function WorkspaceChatPage() {
  const params = useParams();
  const runId = params.run_id as string;
  const [turns, setTurns] = useState<WorkflowRun[]>([]);
  const [threadId, setThreadId] = useState(runId);
  const [error, setError] = useState("");
  const [showGraph, setShowGraph] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);
  const [stopping, setStopping] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  async function loadThread(anchorId: string) {
    try {
      const data = await getWorkflowThread(anchorId);
      if (data.workflows?.length) {
        setTurns(data.workflows);
        setThreadId(data.thread_id || anchorId);
        return;
      }
    } catch { /* older backends without /thread */ }
    const wf = await getWorkflow(anchorId);
    setTurns([wf]);
    setThreadId(wf.thread_id || wf.run_id);
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadThread(runId);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load run");
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  useEffect(() => {
    let cancelled = false;
    let failCount = 0;
    const tick = async () => {
      try {
        const ids = Array.from(new Set([runId, ...turns.map((t) => t.run_id)]));
        const fresh = await Promise.all(ids.map((id) => getWorkflow(id)));
        if (cancelled) return;
        failCount = 0;
        setError("");
        setTurns((prev) => {
          const byId = new Map(fresh.map((w) => [w.run_id, w]));
          const next = prev.map((w) => byId.get(w.run_id) || w);
          for (const w of fresh) {
            if (!next.some((p) => p.run_id === w.run_id)) next.push(w);
          }
          return next;
        });
      } catch (e) {
        failCount += 1;
        if (!cancelled && failCount >= 3) {
          setError(e instanceof Error ? e.message : "Could not refresh run status");
        }
      }
    };
    const active =
      turns.length === 0 ||
      turns.some((t) => !isTerminal(t.status) || isWaitingHuman(t));
    if (!active) return;
    void tick();
    const id = window.setInterval(() => { void tick(); }, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, turns.map((t) => `${t.run_id}:${t.status}`).join("|")]);

  useEffect(() => {
    const unsubs = turns.map((turn) => subscribeWorkflowEvents(turn.run_id, (event: WorkflowEvent) => {
      setEvents((prev) => {
        if (prev.some((e) => e.event_id && e.event_id === event.event_id)) return prev;
        return [...prev, event];
      });
      setTurns((prev) => prev.map((wf) => {
        if (wf.run_id !== turn.run_id) return wf;
        const updated = { ...wf, tasks: [...wf.tasks] };
        if (event.type === "WORKFLOW_COMPLETED") updated.status = "COMPLETED";
        if (event.type === "WORKFLOW_FAILED") updated.status = "FAILED";
        if (event.type === "WORKFLOW_CANCELLED") updated.status = "CANCELLED";
        if (event.task_id) {
          const i = updated.tasks.findIndex((t) => t.task_id === event.task_id);
          if (i >= 0) {
            const task = { ...updated.tasks[i] };
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
            if (event.type === "APPROVAL_REQUIRED") {
              task.status = "WAITING_APPROVAL";
              task.output_data = {
                ...(task.output_data || {}),
                message: event.summary,
                ...(event.sanitized_metadata || {}),
              };
            }
            updated.tasks[i] = task;
          }
        }
        return updated;
      }));
    }));
    return () => { unsubs.forEach((u) => u()); };
  }, [turns.map((t) => t.run_id).join("|")]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const latest = turns[turns.length - 1];
  const waitingHuman = turns.some(isWaitingHuman);
  const busy = turns.some((t) => !isTerminal(t.status) && !isWaitingHuman(t));
  const latestFailed = latest?.status === "FAILED";

  async function handleResume() {
    if (!latest || resuming) return;
    setResuming(true);
    try {
      await resumeWorkflow(latest.run_id);
      await loadThread(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resume");
    } finally {
      setResuming(false);
    }
  }

  async function handleStop() {
    if (stopping || !latest || isTerminal(latest.status)) return;
    setStopping(true);
    try {
      await cancelWorkflow(latest.run_id);
      await loadThread(runId);
    } catch {
      /* already finished */
    } finally {
      setStopping(false);
    }
  }

  return (
    <div className="workspace-chat animate-fade-in-up">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
        <div>
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: 0.6 }}>Workspace</p>
          <h1 style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 700 }}>Chat</h1>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowGraph((v) => !v)}>
            {showGraph ? "Hide graph" : "Show graph"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowTimeline((v) => !v)}>
            {showTimeline ? "Hide timeline" : "Show timeline"}
          </button>
          {latest && <Link href={`/dashboard/workflows/${latest.run_id}`} className="btn btn-ghost btn-sm">Details</Link>}
          {waitingHuman && (
            <button className="btn btn-primary btn-sm" onClick={() => void handleResume()} disabled={resuming}>
              {resuming ? "Resuming…" : "Resume after challenge"}
            </button>
          )}
          {latest && !isTerminal(latest.status) && (
            <button className="btn btn-ghost btn-sm" onClick={() => void handleStop()} disabled={stopping}>
              {stopping ? "Stopping…" : "Stop"}
            </button>
          )}
          {latestFailed && (
            <button className="btn btn-secondary btn-sm" onClick={() => retryWorkflow(latest.run_id)}>Retry</button>
          )}
        </div>
      </div>

      {error && <p style={{ color: "var(--error)" }}>{error}</p>}

      {waitingHuman && (
        <div className="glass-panel animate-fade-in" style={{ padding: 14, marginBottom: 12, border: "1px solid rgba(245,158,11,0.4)" }}>
          Complete CAPTCHA, OTP, or MFA in the browser window AgentOS opened. It will not fill those fields. Then click Resume.
        </div>
      )}

      <div className="chat-thread hide-scrollbar">
        {turns.map((wf) => (
          <TurnView key={wf.run_id} workflow={wf} />
        ))}
        <div ref={endRef} />
      </div>

      {showTimeline && events.length > 0 && (
        <div className="glass-card" style={{ padding: 12, maxHeight: 280, overflow: "auto" }}>
          <ExecutionTimeline events={events} />
        </div>
      )}

      {showGraph && latest && (
        <div className="glass-card graph-sheet" style={{ padding: 12 }}>
          <WorkflowGraph workflow={latest} />
        </div>
      )}

      <div className="workspace-composer-dock">
        {waitingHuman && (
          <p className="composer-hint" style={{ textAlign: "center", marginBottom: 8 }}>
            Paused for a human security check. Resume when you have finished it.
          </p>
        )}
        {busy && (
          <p className="composer-hint" style={{ textAlign: "center", marginBottom: 8 }}>AgentOS is working on this. You can send the next message when it finishes.</p>
        )}
        <ChatComposer
          compact
          disabled={busy}
          threadId={threadId}
          parentRunId={latest?.run_id || runId}
          onRunCreated={() => {
            void (async () => {
              await new Promise((r) => setTimeout(r, 280));
              await loadThread(runId);
            })();
          }}
        />
      </div>
    </div>
  );
}
