import { useMemo, useEffect, useState } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  MarkerType,
  useNodesState,
  useEdgesState,
  Position,
  Node,
  Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { WorkflowRun, Task } from '@/lib/api';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 250;
const nodeHeight = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;
    // Shift dagre node position (anchor=center) to match React Flow (anchor=top-left)
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
    return node;
  });

  return { nodes, edges };
};

export default function WorkflowGraph({ workflow }: { workflow: WorkflowRun }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  useEffect(() => {
    if (!workflow) return;

    const initialNodes: Node[] = workflow.tasks.map((task) => {
      // Determine node color based on status
      let borderColor = 'var(--border-primary)';
      let bgColor = 'var(--bg-tertiary)';
      let icon = '⏳';
      
      if (task.status === 'COMPLETED') {
        borderColor = 'var(--success)';
        bgColor = 'rgba(16, 185, 129, 0.1)';
        icon = '✅';
      } else if (task.status === 'RUNNING') {
        borderColor = 'var(--info)';
        bgColor = 'rgba(59, 130, 246, 0.1)';
        icon = '🔄';
      } else if (task.status === 'FAILED') {
        borderColor = 'var(--error)';
        bgColor = 'rgba(239, 68, 68, 0.1)';
        icon = '❌';
      } else if (task.status === 'WAITING_APPROVAL') {
        borderColor = 'var(--warning)';
        bgColor = 'rgba(245, 158, 11, 0.1)';
        icon = '⚠️';
      }

      return {
        id: task.task_id,
        position: { x: 0, y: 0 },
        data: { 
          label: (
            <div style={{ padding: '8px', textAlign: 'left' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>{icon} {task.agent}</strong>
                <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{task.status}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
                {task.tool || 'No tool specified'}
              </div>
            </div>
          )
        },
        style: {
          background: bgColor,
          border: `1px solid ${borderColor}`,
          borderRadius: '8px',
          width: nodeWidth,
          color: 'var(--text-primary)',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
        }
      };
    });

    const initialEdges: Edge[] = [];
    workflow.tasks.forEach((task) => {
      if (task.dependencies && task.dependencies.length > 0) {
        task.dependencies.forEach((depId) => {
          initialEdges.push({
            id: `e-${depId}-${task.task_id}`,
            source: depId,
            target: task.task_id,
            animated: task.status === 'RUNNING' || task.status === 'PENDING',
            style: { stroke: 'var(--accent)', strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: 'var(--accent)',
            },
          });
        });
      }
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges);
    
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [workflow, setNodes, setEdges]);

  const onNodeClick = (event: React.MouseEvent, node: Node) => {
    const task = workflow.tasks.find(t => t.task_id === node.id);
    if (task) setSelectedTask(task);
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%', minHeight: '400px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-primary)' }}>
      {/* React Flow Canvas */}
      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          attributionPosition="bottom-right"
          colorMode="light"
        >
          <Background gap={16} />
          <Controls style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)', fill: 'var(--text-primary)' }} />
        </ReactFlow>
      </div>

      {/* Slide-out Panel for Node Details */}
      {selectedTask && (
        <div style={{
          width: 400,
          background: 'var(--bg-primary)',
          borderLeft: '1px solid var(--border-primary)',
          display: 'flex',
          flexDirection: 'column',
          animation: 'fadeInRight 0.3s forwards',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.05)'
        }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-secondary)' }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Execution Details</h3>
            <button onClick={() => setSelectedTask(null)} className="btn btn-ghost btn-sm" style={{ padding: 4 }}>
              ✕
            </button>
          </div>
          
          <div style={{ padding: '20px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Agent</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{selectedTask.agent}</div>
            </div>

            <div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Status</div>
              <div style={{ 
                display: 'inline-block', padding: '4px 12px', borderRadius: 100, fontSize: 12, fontWeight: 600,
                background: selectedTask.status === 'COMPLETED' ? 'rgba(16, 185, 129, 0.1)' : 
                            selectedTask.status === 'FAILED' ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-tertiary)',
                color: selectedTask.status === 'COMPLETED' ? 'var(--success)' : 
                       selectedTask.status === 'FAILED' ? 'var(--error)' : 'var(--text-secondary)'
              }}>
                {selectedTask.status}
              </div>
            </div>

            {selectedTask.tool && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Tool Executed</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--accent)', background: 'var(--bg-tertiary)', padding: '8px 12px', borderRadius: 6 }}>
                  {selectedTask.tool}
                </div>
              </div>
            )}

            {selectedTask.error && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--error)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, fontWeight: 600 }}>Error Message</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--error)', background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: 6 }}>
                  {selectedTask.error}
                </div>
              </div>
            )}

            {selectedTask.input_data && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Pipeline In (JSON)</div>
                <pre style={{ margin: 0, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)', overflowX: 'auto' }}>
                  {JSON.stringify(selectedTask.input_data, null, 2)}
                </pre>
              </div>
            )}

            {selectedTask.output_data && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Pipeline Out (JSON)</div>
                <pre style={{ margin: 0, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)', overflowX: 'auto' }}>
                  {JSON.stringify(selectedTask.output_data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
