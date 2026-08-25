/**
 * AgentOS — Typed API Client (PRODUCTION)
 *
 * No hardcoded tokens. Uses real JWT from auth state.
 * Auto-refreshes expired tokens. All endpoints typed.
 */

import { fetchEventSource } from "@microsoft/fetch-event-source";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Token management ─────────────────────────────────────────────

function getAuthData(): { accessToken: string | null; refreshToken: string | null } {
  if (typeof window === "undefined") return { accessToken: null, refreshToken: null };
  try {
    const stored = localStorage.getItem("agentos_auth");
    if (!stored) return { accessToken: null, refreshToken: null };
    const parsed = JSON.parse(stored);
    return {
      accessToken: parsed.accessToken || null,
      refreshToken: parsed.refreshToken || null,
    };
  } catch {
    return { accessToken: null, refreshToken: null };
  }
}

function getToken(): string | null {
  return getAuthData().accessToken;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Generic fetcher with auth ────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Try refresh
    const { refreshToken } = getAuthData();
    if (refreshToken) {
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        const stored = JSON.parse(localStorage.getItem("agentos_auth") || "{}");
        stored.accessToken = data.access_token;
        stored.refreshToken = data.refresh_token;
        stored.user = data.user;
        localStorage.setItem("agentos_auth", JSON.stringify(stored));

        // Retry original request
        headers.Authorization = `Bearer ${data.access_token}`;
        const retry = await fetch(`${API_BASE}${path}`, { ...options, headers });
        if (!retry.ok) {
          const errData = await retry.json().catch(() => ({}));
          throw new Error(errData.detail || `API error: ${retry.status}`);
        }
        return retry.json();
      } else {
        localStorage.removeItem("agentos_auth");
        window.location.href = "/login";
        return new Promise(() => {}) as Promise<T>;
      }
    }
    localStorage.removeItem("agentos_auth");
    window.location.href = "/login";
    return new Promise(() => {}) as Promise<T>;
  }

  if (res.status === 204) return {} as T;

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ── Interfaces ───────────────────────────────────────────────────

export interface Task {
  task_id: string;
  workflow_id: string;
  run_id: string;
  agent: string;
  tool?: string;
  status: string;
  input_data: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  dependencies: string[];
  started_at?: string;
  completed_at?: string;
  error?: string;
  error_type?: string;
  attempt: number;
}

export interface WorkflowRun {
  run_id: string;
  workflow_id: string;
  user_id: string;
  goal: string;
  status: string;
  tasks: Task[];
  created_at: string;
}

export interface WorkflowEvent {
  event_id: string;
  timestamp: string;
  type: string;
  workflow_id: string;
  run_id: string;
  task_id?: string;
  status?: string;
  summary: string;
  sanitized_metadata: Record<string, unknown>;
}

export interface Integration {
  mcp_id: string;
  name: string;
  description?: string;
  trust_tier: string;
  is_enabled: boolean;
  health?: string;
  tool_count: number;
  circuit_breaker: {
    state: string;
    failure_count: number;
    total_successes: number;
    total_failures: number;
    retry_in_seconds?: number;
  };
  created_at?: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Schedule {
  schedule_id: string;
  name: string;
  goal: string;
  cron_expression: string;
  timezone: string;
  is_enabled: boolean;
  next_run_at?: string;
  created_at: string;
}

export interface ApprovalRequest {
  approval_id: string;
  workflow_id: string;
  run_id: string;
  task_id: string;
  user_id: string;
  status: string;
  requested_at: string;
  expires_at: string;
  risk_level: string;
  reason: string;
  tool_name: string;
  tool_arguments: Record<string, unknown>;
}

export interface UserSettings {
  theme: string;
  autonomy_level: number;
  default_model: string;
  notifications_enabled: boolean;
  daily_token_limit: number;
  auto_approve_low_risk: boolean;
}

// ── Workflows ────────────────────────────────────────────────────

export async function submitGoal(goal: string) {
  return apiFetch<{ run_id: string; workflow_id: string; status: string; task_count: number }>(
    "/workflows",
    { method: "POST", body: JSON.stringify({ goal }) }
  );
}

export async function listWorkflows(limit = 50, offset = 0) {
  return apiFetch<{ workflows: WorkflowRun[]; count: number }>(
    `/workflows?limit=${limit}&offset=${offset}`
  );
}

export async function getWorkflow(runId: string) {
  return apiFetch<WorkflowRun>(`/workflows/${runId}`);
}

export async function cancelWorkflow(runId: string) {
  return apiFetch<{ run_id: string; status: string }>(
    `/workflows/${runId}/cancel`,
    { method: "POST" }
  );
}

export async function retryWorkflow(runId: string) {
  return apiFetch<{ run_id: string; status: string; retried_tasks: number }>(
    `/workflows/${runId}/retry`,
    { method: "POST" }
  );
}

export function subscribeWorkflowEvents(
  runId: string,
  onMessage: (event: WorkflowEvent) => void,
  onOpen?: () => void,
  onError?: (err: unknown) => void
) {
  const controller = new AbortController();

  fetchEventSource(`${API_BASE}/workflows/${runId}/events`, {
    headers: authHeaders(),
    signal: controller.signal,
    onopen: async (res) => {
      if (res.ok && res.status === 200) {
        if (onOpen) onOpen();
      } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
        throw new Error(`SSE failed: ${res.status}`);
      }
    },
    onmessage: (msg) => {
      if (msg.data) {
        try {
          onMessage(JSON.parse(msg.data));
        } catch (e) {
          console.error("Failed to parse SSE event", e);
        }
      }
    },
    onerror: (err) => {
      if (onError) onError(err);
    },
  });

  return () => controller.abort();
}

// ── Integrations ─────────────────────────────────────────────────

export async function listIntegrations() {
  return apiFetch<{ integrations: Integration[]; count: number }>("/integrations");
}

export async function getIntegration(mcpId: string) {
  return apiFetch<Integration & { tools: unknown[] }>(`/integrations/${mcpId}`);
}

export async function buildIntegrationFromURL(url: string, name?: string) {
  return apiFetch<{ status: string; message: string }>(
    "/integrations/build-from-url",
    { method: "POST", body: JSON.stringify({ url, name }) }
  );
}

export async function buildIntegrationFromPrompt(prompt: string, name?: string) {
  return apiFetch<{ status: string; message: string }>(
    "/integrations/build-from-prompt",
    { method: "POST", body: JSON.stringify({ prompt, name }) }
  );
}

export async function testIntegration(mcpId: string) {
  return apiFetch<{ status: string }>(`/integrations/${mcpId}/test`, { method: "POST" });
}

export async function enableIntegration(mcpId: string) {
  return apiFetch(`/integrations/${mcpId}/enable`, { method: "POST" });
}

export async function disableIntegration(mcpId: string) {
  return apiFetch(`/integrations/${mcpId}/disable`, { method: "POST" });
}

export async function deleteIntegration(mcpId: string) {
  return apiFetch(`/integrations/${mcpId}`, { method: "DELETE" });
}

// ── Notifications ────────────────────────────────────────────────

export async function listNotifications(unreadOnly = false, limit = 50) {
  return apiFetch<{ notifications: Notification[]; unread_count: number }>(
    `/notifications?unread_only=${unreadOnly}&limit=${limit}`
  );
}

export async function getUnreadCount() {
  return apiFetch<{ unread_count: number }>("/notifications/unread");
}

export async function markNotificationRead(id: string) {
  return apiFetch(`/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  return apiFetch("/notifications/read-all", { method: "POST" });
}

// ── Schedules ────────────────────────────────────────────────────

export async function listSchedules() {
  return apiFetch<{ schedules: Schedule[]; count: number }>("/schedules");
}

export async function createSchedule(data: {
  name: string;
  goal: string;
  cron_expression: string;
  timezone?: string;
}) {
  return apiFetch<Schedule>("/schedules", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteSchedule(id: string) {
  return apiFetch(`/schedules/${id}`, { method: "DELETE" });
}

export async function runScheduleNow(id: string) {
  return apiFetch(`/schedules/${id}/run`, { method: "POST" });
}

export async function toggleSchedulePause(id: string) {
  return apiFetch(`/schedules/${id}/pause`, { method: "POST" });
}

// ── Settings ─────────────────────────────────────────────────────

export async function getSettings() {
  return apiFetch<{ settings: UserSettings }>("/settings");
}

export async function updateSettings(data: Partial<UserSettings>) {
  return apiFetch<{ settings: UserSettings }>("/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ── Memory ───────────────────────────────────────────────────────

export async function addMemory(content: string, memory_type = "semantic") {
  return apiFetch<{ memory_id: string }>("/memory", {
    method: "POST",
    body: JSON.stringify({ content, memory_type }),
  });
}

export async function searchMemory(query: string, limit = 10) {
  return apiFetch<{ results: unknown[] }>("/memory/search", {
    method: "POST",
    body: JSON.stringify({ query, limit }),
  });
}

// ── Approvals ────────────────────────────────────────────────────

export async function listApprovals() {
  return apiFetch<ApprovalRequest[]>("/approvals");
}

export async function resolveApproval(approvalId: string, action: "approve" | "reject") {
  return apiFetch(`/approvals/${approvalId}/${action}`, { method: "POST" });
}

// ── Health ───────────────────────────────────────────────────────

export async function healthCheck() {
  const res = await fetch(`${API_BASE.replace("/api/v1", "")}/health`);
  return res.json();
}
