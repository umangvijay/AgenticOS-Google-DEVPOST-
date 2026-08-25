"use client";

import { WorkflowEvent } from "@/lib/api";
import { format } from "date-fns";
import { CheckCircle2, PlayCircle, AlertCircle, RefreshCw, XCircle, ShieldAlert } from "lucide-react";

export default function ExecutionTimeline({ events }: { events: WorkflowEvent[] }) {
  const getIcon = (type: string) => {
    switch (type) {
      case "WORKFLOW_STARTED":
      case "TASK_STARTED":
      case "TOOL_INVOKED":
        return <PlayCircle className="w-5 h-5 text-blue-400" />;
      case "WORKFLOW_COMPLETED":
      case "TASK_COMPLETED":
      case "TOOL_COMPLETED":
        return <CheckCircle2 className="w-5 h-5 text-green-400" />;
      case "WORKFLOW_FAILED":
      case "TASK_FAILED":
        return <XCircle className="w-5 h-5 text-destructive" />;
      case "APPROVAL_REQUIRED":
        return <ShieldAlert className="w-5 h-5 text-amber-500" />;
      case "TASK_RECOVERING":
      case "TASK_RETRYING":
        return <RefreshCw className="w-5 h-5 text-purple-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-muted-foreground" />;
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4 h-full flex flex-col">
      <h3 className="font-semibold text-lg mb-4">Execution Timeline</h3>
      <div className="flex-1 overflow-y-auto pr-2 space-y-4">
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No events yet.</p>
        ) : (
          events.map((event, idx) => (
            <div key={event.event_id || idx} className="flex space-x-3 items-start animate-in slide-in-from-left-2 duration-300">
              <div className="mt-0.5">{getIcon(event.type)}</div>
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium leading-none text-foreground">{event.summary}</p>
                <div className="flex items-center text-xs text-muted-foreground space-x-2">
                  <span>{format(new Date(event.timestamp), "HH:mm:ss.SSS")}</span>
                  {event.task_id && <span className="px-1.5 py-0.5 bg-muted rounded font-mono text-[10px]">{event.task_id}</span>}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
