"use client";

import { FormEvent, useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { listSchedules, deleteSchedule, toggleSchedulePause, runScheduleNow, createSchedule, Schedule } from "@/lib/api";

export default function SchedulesPage() {
  const { user } = useAuth();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [cron, setCron] = useState("0 9 * * 1");
  const [timezone, setTimezone] = useState("UTC");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await listSchedules();
      setSchedules(res.schedules || []);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load schedules");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await createSchedule({
        name: name.trim(),
        goal: goal.trim(),
        cron_expression: cron.trim(),
        timezone: timezone.trim() || "UTC",
      });
      setModalOpen(false);
      setName("");
      setGoal("");
      setCron("0 9 * * 1");
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create schedule");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this schedule?")) return;
    try {
      await deleteSchedule(id);
      setSchedules(prev => prev.filter(s => s.schedule_id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete schedule");
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const res: { is_enabled?: boolean } = await toggleSchedulePause(id);
      setSchedules(prev => prev.map(s => s.schedule_id === id ? { ...s, is_enabled: Boolean(res.is_enabled) } : s));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to toggle schedule");
    }
  };

  const handleRunNow = async (id: string) => {
    try {
      await runScheduleNow(id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run schedule");
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Schedules</h1>
          <p style={{ color: "var(--text-secondary)" }}>Automate your workflows on a recurring basis.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ marginRight: 8 }}>
            <path d="M12 4v16m8-8H4" />
          </svg>
          New Schedule
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "var(--error-subtle)", color: "var(--error)", borderRadius: "var(--radius-md)", marginBottom: 24 }}>
          {error}
        </div>
      )}

      {modalOpen && (
        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Create schedule</h2>
          <form onSubmit={handleCreate} style={{ display: "grid", gap: 12 }}>
            <input className="input" required placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <textarea className="input" required rows={4} placeholder="Goal the agent should run" value={goal} onChange={(e) => setGoal(e.target.value)} />
            <input className="input" required placeholder="Cron (e.g. 0 9 * * 1)" value={cron} onChange={(e) => setCron(e.target.value)} />
            <input className="input" placeholder="Timezone (UTC)" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={saving || !user}>
                {saving ? "Creating…" : "Create schedule"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setModalOpen(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="glass-card" style={{ padding: 24 }}>
        {isLoading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="skeleton" style={{ height: 80 }} />
            <div className="skeleton" style={{ height: 80 }} />
            <div className="skeleton" style={{ height: 80 }} />
          </div>
        ) : schedules.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {schedules.map(schedule => (
              <div key={schedule.schedule_id} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "16px 20px", borderRadius: "var(--radius-md)",
                background: "var(--bg-tertiary)", border: "1px solid var(--border-primary)"
              }}>
                <div style={{ flex: 1, paddingRight: 24 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{schedule.name}</h3>
                    <span className={`badge ${schedule.is_enabled ? 'badge-success' : 'badge-neutral'}`}>
                      {schedule.is_enabled ? 'Active' : 'Paused'}
                    </span>
                    <span className="badge badge-info" style={{ fontFamily: "var(--font-mono)", textTransform: "none" }}>
                      {schedule.cron_expression}
                    </span>
                  </div>
                  <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.5 }}>
                    {schedule.goal}
                  </p>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    Next run: {schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : "Not scheduled"}
                  </div>
                </div>
                
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleRunNow(schedule.schedule_id)} title="Run Now">
                    <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M5 3l14 9-14 9V3z" />
                    </svg>
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleToggle(schedule.schedule_id)} title={schedule.is_enabled ? "Pause" : "Resume"}>
                    {schedule.is_enabled ? (
                      <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M10 4H6v16h4V4zM18 4h-4v16h4V4z" />
                      </svg>
                    ) : (
                      <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M14.752 11.168l-3.197-2.132A 1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </button>
                  <button className="btn btn-ghost btn-sm" style={{ color: "var(--error)" }} onClick={() => handleDelete(schedule.schedule_id)} title="Delete">
                    <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            <h3 style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>No schedules yet</h3>
            <p style={{ marginBottom: 24 }}>Set up recurring workflows using cron expressions.</p>
            <button className="btn btn-primary" onClick={() => setModalOpen(true)}>Create Schedule</button>
          </div>
        )}
      </div>
    </div>
  );
}
