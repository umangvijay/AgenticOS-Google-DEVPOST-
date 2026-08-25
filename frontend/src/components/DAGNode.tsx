import { Handle, Position } from "@xyflow/react";
import { CheckCircle2, Clock, PlayCircle, AlertCircle, RefreshCw, XCircle, ShieldAlert } from "lucide-react";
import clsx from "clsx";

export default function DAGNode({ data }: { data: Record<string, unknown> }) {
  const { label, status } = data;

  const getStatusConfig = () => {
    switch (status) {
      case "PENDING":
      case "WAITING":
        return { icon: Clock, color: "text-muted-foreground", border: "border-muted" };
      case "RUNNING":
        return { icon: PlayCircle, color: "text-blue-400", border: "border-blue-500", animate: "animate-pulse" };
      case "COMPLETED":
        return { icon: CheckCircle2, color: "text-green-400", border: "border-green-500" };
      case "FAILED":
      case "BLOCKED":
        return { icon: XCircle, color: "text-destructive", border: "border-destructive" };
      case "WAITING_APPROVAL":
        return { icon: ShieldAlert, color: "text-amber-500", border: "border-amber-500", animate: "animate-pulse" };
      case "RECOVERING":
      case "RETRYING":
        return { icon: RefreshCw, color: "text-purple-400", border: "border-purple-500", animate: "animate-spin" };
      default:
        return { icon: AlertCircle, color: "text-muted-foreground", border: "border-border" };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div className={clsx("min-w-[180px] bg-card p-3 rounded-lg border-2 shadow-lg flex flex-col items-center space-y-2", config.border)}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-muted-foreground" />
      
      <div className="flex items-center justify-between w-full space-x-2">
        <Icon className={clsx("w-5 h-5", config.color, config.animate)} />
        <span className="text-sm font-semibold truncate flex-1 text-center">{String(label)}</span>
      </div>
      
      <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">
        {String(status)}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-muted-foreground" />
    </div>
  );
}
