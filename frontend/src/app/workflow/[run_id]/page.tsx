"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ReactFlow, Node, Edge, Background, Controls } from "@xyflow/react";
import '@xyflow/react/dist/style.css';

import { getWorkflow, subscribeWorkflowEvents, WorkflowRun, WorkflowEvent, listApprovals, ApprovalRequest, resolveApproval } from "@/lib/api";
import DAGNode from "@/components/DAGNode";
import { getLayoutedElements } from "@/components/DAGLayout";
import ExecutionTimeline from "@/components/ExecutionTimeline";
import TaskDetailsPanel from "@/components/TaskDetailsPanel";
import { Loader2, ArrowLeft, ShieldAlert, Check, X, XCircle } from "lucide-react";
import clsx from "clsx";

const nodeTypes = {
  custom: DAGNode,
};

export default function WorkflowExecutionPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.run_id as string;

  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reconnecting, setReconnecting] = useState(false);

  const fetchWorkflowState = useCallback(async () => {
    try {
      const data = await getWorkflow(runId);
      setWorkflow(data);
      
      const pendingApprovals = await listApprovals();
      setApprovals(pendingApprovals.filter(a => a.run_id === runId));
      
      setError("");
      return data;
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load workflow state";
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    let unsubscribe: () => void;

    const init = async () => {
      const initialData = await fetchWorkflowState();
      if (!initialData) return;

      unsubscribe = subscribeWorkflowEvents(
        runId,
        (event) => {
          setEvents(prev => [...prev, event]);
          
          // Only refresh state for critical transitions
          if (["TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED", "APPROVAL_REQUIRED", "WORKFLOW_COMPLETED", "WORKFLOW_FAILED"].includes(event.type)) {
            fetchWorkflowState();
          }
        },
        () => setReconnecting(false),
        (err: unknown) => {
          console.error(err);
          setReconnecting(true);
        }
      );
    };

    init();
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [runId, fetchWorkflowState]);

  // Update Graph layout when workflow state changes
  useEffect(() => {
    if (!workflow) return;

    const initialNodes: Node[] = workflow.tasks.map(t => ({
      id: t.task_id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: { label: t.task_id, status: t.status, type: t.agent }
    }));

    const initialEdges: Edge[] = [];
    workflow.tasks.forEach(t => {
      t.dependencies.forEach(dep => {
        initialEdges.push({
          id: `${dep}->${t.task_id}`,
          source: dep,
          target: t.task_id,
          animated: t.status === "RUNNING" || t.status === "PENDING" || t.status === "WAITING"
        });
      });
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges);
    setTimeout(() => {
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }, 0);
  }, [workflow]);

  const handleNodeClick = (event: React.MouseEvent, node: Node) => {
    setSelectedTaskId(node.id);
  };

  const handleApprovalAction = async (approvalId: string, action: "approve" | "reject") => {
    try {
      await resolveApproval(approvalId, action);
      // Wait a moment then refetch
      setTimeout(fetchWorkflowState, 500);
    } catch (err) {
      console.error(err);
    }
  };

  const selectedTask = useMemo(() => {
    if (!workflow || !selectedTaskId) return null;
    return workflow.tasks.find(t => t.task_id === selectedTaskId) || null;
  }, [workflow, selectedTaskId]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
        <p className="text-muted-foreground animate-pulse">Loading workflow state...</p>
      </div>
    );
  }

  if (error && !workflow) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="p-6 bg-destructive/10 border border-destructive rounded-xl text-center space-y-4">
          <XCircle className="w-12 h-12 text-destructive mx-auto" />
          <h2 className="text-xl font-bold text-destructive">Failed to Load</h2>
          <p className="text-muted-foreground">{error}</p>
          <button onClick={() => router.push("/")} className="mt-4 px-4 py-2 bg-background border border-border rounded hover:bg-muted">Return to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden relative">
      {reconnecting && (
        <div className="absolute top-0 left-0 right-0 bg-amber-500/90 text-amber-950 px-4 py-1 flex items-center justify-center text-xs font-semibold z-[100] space-x-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>Connection lost. Reconnecting to execution stream...</span>
        </div>
      )}

      {/* Header */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-card/30 z-10">
        <div className="flex items-center space-x-4">
          <button onClick={() => router.push("/")} className="p-2 rounded hover:bg-muted transition-colors group">
            <ArrowLeft className="w-5 h-5 text-muted-foreground group-hover:text-foreground" />
          </button>
          <div>
            <h2 className="font-semibold truncate max-w-md">{workflow?.goal}</h2>
            <p className="text-xs text-muted-foreground font-mono">Run: {runId}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium">Status:</span>
          <span className={clsx("px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider", 
            workflow?.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
            workflow?.status === 'FAILED' ? 'bg-destructive/20 text-destructive' :
            'bg-blue-500/20 text-blue-400 animate-pulse'
          )}>
            {workflow?.status}
          </span>
        </div>
      </header>

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden">
        
        {/* Graph Area */}
        <div className="lg:col-span-7 xl:col-span-8 relative bg-black/40 border-r border-border">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            className="bg-transparent"
            colorMode="dark"
          >
            <Background gap={24} size={1} color="rgba(255,255,255,0.05)" />
            <Controls className="!bg-card !border-border !fill-foreground" />
          </ReactFlow>
        </div>

        {/* Side Panels */}
        <div className="lg:col-span-5 xl:col-span-4 flex flex-col p-4 space-y-4 overflow-hidden h-full bg-card/10">
          
          {/* Approvals (if any) */}
          {approvals.length > 0 && (
            <div className="bg-amber-500/10 border-2 border-amber-500/50 rounded-xl p-4 shadow-lg shadow-amber-500/5 flex-shrink-0 animate-in slide-in-from-top-4">
              <div className="flex items-center space-x-2 text-amber-500 mb-3">
                <ShieldAlert className="w-5 h-5 animate-pulse" />
                <h3 className="font-bold">Human Approval Required</h3>
              </div>
              
              <div className="space-y-4">
                {approvals.map(app => (
                  <div key={app.approval_id} className="bg-background rounded-lg border border-amber-500/30 p-3 space-y-3">
                    <div>
                      <p className="text-sm font-semibold">{app.tool_name}</p>
                      <p className="text-xs text-muted-foreground">{app.reason}</p>
                    </div>
                    
                    <div className="bg-black/50 p-2 rounded text-xs font-mono text-gray-300 break-words">
                      {JSON.stringify(app.tool_arguments, null, 2)}
                    </div>
                    
                    <div className="flex space-x-2 pt-1">
                      <button 
                        onClick={() => handleApprovalAction(app.approval_id, "approve")}
                        className="flex-1 flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-500 text-white py-1.5 rounded text-sm font-medium transition-colors"
                      >
                        <Check className="w-4 h-4" />
                        <span>Approve Exact Action</span>
                      </button>
                      <button 
                        onClick={() => handleApprovalAction(app.approval_id, "reject")}
                        className="flex items-center justify-center p-1.5 px-3 bg-destructive hover:bg-destructive/80 text-white rounded transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Execution Timeline (takes remaining upper space if approvals exist, or half) */}
          <div className="flex-1 min-h-[30%]">
            <ExecutionTimeline events={events} />
          </div>

          {/* Task Details Panel */}
          <div className="flex-1 min-h-[40%]">
            <TaskDetailsPanel task={selectedTask} />
          </div>
          
        </div>
      </div>
    </div>
  );
}
