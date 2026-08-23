"use client";

import { Task } from "@/lib/api";

export default function TaskDetailsPanel({ task }: { task: Task | null }) {
  if (!task) {
    return (
      <div className="bg-card border border-border rounded-xl p-4 h-full flex flex-col items-center justify-center text-center space-y-2">
        <p className="text-muted-foreground italic text-sm">Select a node to view details</p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-4 h-full flex flex-col space-y-4">
      <div>
        <h3 className="font-semibold text-lg">{task.task_id}</h3>
        <p className="text-sm text-muted-foreground">Agent: {task.agent}</p>
        {task.tool && <p className="text-sm text-muted-foreground">Tool: {task.tool}</p>}
      </div>

      <div className="flex items-center space-x-2 text-sm">
        <span className="font-semibold">Status:</span>
        <span className="px-2 py-0.5 rounded bg-muted text-foreground">{task.status}</span>
      </div>

      <div className="space-y-1">
        <span className="text-sm font-semibold text-foreground">Attempts:</span>
        <span className="text-sm text-muted-foreground ml-2">{task.attempt}</span>
      </div>

      {task.error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-xs font-semibold text-destructive uppercase tracking-wider mb-1">{task.error_type || 'Error'}</p>
          <p className="text-sm text-destructive font-mono break-words">{task.error}</p>
        </div>
      )}

      {task.output_data && (
        <div className="space-y-1">
          <p className="text-sm font-semibold">Result:</p>
          <pre className="p-2 bg-black border border-border rounded text-xs font-mono text-gray-300 overflow-x-auto break-words whitespace-pre-wrap">
            {JSON.stringify(task.output_data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
