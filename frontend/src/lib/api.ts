import { fetchEventSource } from '@microsoft/fetch-event-source';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// JWT token logic (placeholder for real auth state)
export const getToken = () => localStorage.getItem("jwt_token") || "test_token";

// Interfaces mirroring Pydantic schemas
export interface Task {
    task_id: string;
    workflow_id: string;
    run_id: string;
    agent: string;
    tool?: string;
    status: string;
    input_data: Record<string, any>;
    output_data?: Record<string, any>;
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
    sanitized_metadata: Record<string, any>;
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
    tool_arguments: Record<string, any>;
}

// API methods
export async function submitGoal(goal: string): Promise<{ run_id: string, status: string }> {
    const res = await fetch(`${API_BASE}/intent`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getToken()}`
        },
        body: JSON.stringify({ goal })
    });
    if (!res.ok) throw new Error("Failed to submit goal");
    return res.json();
}

export async function getWorkflow(runId: string): Promise<WorkflowRun> {
    const res = await fetch(`${API_BASE}/workflows/${runId}`, {
        headers: { "Authorization": `Bearer ${getToken()}` }
    });
    if (!res.ok) throw new Error("Failed to load workflow");
    return res.json();
}

export function subscribeWorkflowEvents(runId: string, onMessage: (event: WorkflowEvent) => void, onOpen?: () => void, onError?: (err: any) => void) {
    const controller = new AbortController();
    
    fetchEventSource(`${API_BASE}/workflows/${runId}/events`, {
        headers: { "Authorization": `Bearer ${getToken()}` },
        signal: controller.signal,
        onopen: async (res) => {
            if (res.ok && res.status === 200) {
                if (onOpen) onOpen();
            } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
                throw new Error(`Failed to establish SSE: ${res.status}`);
            }
        },
        onmessage: (msg) => {
            if (msg.event === 'FatalError') {
                throw new Error(msg.data);
            }
            if (msg.data) {
                try {
                    const event: WorkflowEvent = JSON.parse(msg.data);
                    onMessage(event);
                } catch (e) {
                    console.error("Failed to parse event", e);
                }
            }
        },
        onclose: () => {
            // Can handle close if needed
        },
        onerror: (err) => {
            if (onError) onError(err);
            // Default fetchEventSource will retry on error unless we throw
        }
    });
    
    return () => controller.abort();
}

export async function listApprovals(): Promise<ApprovalRequest[]> {
    const res = await fetch(`http://localhost:8000/approvals`, {
        headers: { "Authorization": `Bearer ${getToken()}` }
    });
    if (!res.ok) throw new Error("Failed to list approvals");
    return res.json();
}

export async function resolveApproval(approvalId: string, action: "approve" | "reject"): Promise<void> {
    const res = await fetch(`http://localhost:8000/approvals/${approvalId}/${action}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${getToken()}` }
    });
    if (!res.ok) throw new Error(`Failed to ${action} approval`);
}
