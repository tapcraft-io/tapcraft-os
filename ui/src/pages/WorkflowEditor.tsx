import { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Node as RFNode } from '@xyflow/react';
import type { PaletteItem } from '../components/graph/NodePalette';
import {
  useWorkflow,
  useWorkflowGraph,
  useWorkflowCode,
  useUpdateNode,
  useCreateNode,
  useDeleteNode,
  useCreateEdge,
  useDeleteEdge,
  useRegenerateCode,
} from '../hooks/useTapcraft';
import { useToast } from '../components/Toast';
import WorkflowCanvas from '../components/graph/WorkflowCanvas';
import NodePalette from '../components/graph/NodePalette';
import NodeInspector from '../components/graph/NodeInspector';
import EditorToolbar from '../components/graph/EditorToolbar';

export default function WorkflowEditor() {
  const { id } = useParams<{ id: string }>();
  const workflowId = Number(id);
  const [selectedNode, setSelectedNode] = useState<RFNode | null>(null);
  const [showCode, setShowCode] = useState(false);

  const { data: workflow, isLoading: workflowLoading } = useWorkflow(workflowId);
  const graphId = workflow?.graph_id ?? 0;
  const { data: graph, isLoading: graphLoading } = useWorkflowGraph(graphId);

  const updateNode = useUpdateNode(graphId);
  const createNode = useCreateNode(graphId);
  const deleteNode = useDeleteNode(graphId);
  const createEdge = useCreateEdge(graphId);
  const deleteEdge = useDeleteEdge(graphId);
  const regenerateCode = useRegenerateCode();
  const { data: codeData } = useWorkflowCode(workflowId);
  const { addToast } = useToast();

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (workflowId) {
          regenerateCode.mutate(workflowId, {
            onSuccess: () => addToast('success', 'Code regenerated'),
            onError: () => addToast('error', 'Code regeneration failed'),
          });
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [workflowId, regenerateCode, addToast]);

  const handleNodeSelect = useCallback((node: RFNode | null) => {
    setSelectedNode(node);
  }, []);

  const handleNodeDragStop = useCallback(
    (nodeId: string, position: { x: number; y: number }) => {
      updateNode.mutate({
        nodeId: Number(nodeId),
        data: { ui_position: JSON.stringify(position) },
      });
    },
    [updateNode]
  );

  const handleEdgeConnect = useCallback(
    (from: number, to: number) => {
      createEdge.mutate(
        { from_node_id: from, to_node_id: to },
        { onSuccess: () => regenerateCode.mutate(workflowId) }
      );
    },
    [createEdge, regenerateCode, workflowId]
  );

  const handleDrop = useCallback(
    (item: PaletteItem, position: { x: number; y: number }) => {
      createNode.mutate(
        {
          kind: item.kind,
          label: item.label,
          config: JSON.stringify(item.defaultConfig ?? {}),
          config_schema: JSON.stringify(item.configSchema ?? {}),
          ui_position: JSON.stringify(position),
          primitive_type: item.primitiveType ?? null,
          activity_operation_id: item.activityOperationId ?? null,
        },
        { onSuccess: () => regenerateCode.mutate(workflowId) }
      );
    },
    [createNode, regenerateCode, workflowId]
  );

  const handleNodesDelete = useCallback(
    (nodeIds: string[]) => {
      let remaining = nodeIds.length;
      nodeIds.forEach((id) =>
        deleteNode.mutate(Number(id), {
          onSuccess: () => {
            remaining--;
            if (remaining === 0) regenerateCode.mutate(workflowId);
          },
        })
      );
    },
    [deleteNode, regenerateCode, workflowId]
  );

  const handleEdgesDelete = useCallback(
    (edgeIds: string[]) => {
      let remaining = edgeIds.length;
      edgeIds.forEach((id) =>
        deleteEdge.mutate(Number(id), {
          onSuccess: () => {
            remaining--;
            if (remaining === 0) regenerateCode.mutate(workflowId);
          },
        })
      );
    },
    [deleteEdge, regenerateCode, workflowId]
  );

  const handleUpdateNode = useCallback(
    (nodeId: number, data: { label?: string; config?: string }) => {
      updateNode.mutate(
        { nodeId, data },
        { onSuccess: () => regenerateCode.mutate(workflowId) }
      );
    },
    [updateNode, regenerateCode, workflowId]
  );

  if (workflowLoading || graphLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          Loading workflow...
        </div>
      </div>
    );
  }

  if (!workflow || !graph) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <span className="material-symbols-outlined text-4xl text-zinc-700">error</span>
          <p className="text-zinc-400 text-sm mt-2">Workflow not found</p>
          <Link to="/workflows" className="text-primary text-sm mt-2 inline-block hover:underline">
            Back to workflows
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar with workflow name */}
      <header className="h-11 px-4 flex items-center gap-3 border-b border-border-dark bg-surface-dark shrink-0">
        <Link to="/workflows" className="text-zinc-500 hover:text-zinc-300 transition-colors">
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
        </Link>
        <span className="text-zinc-600">|</span>
        <span className="material-symbols-outlined text-[16px] text-primary">account_tree</span>
        <span className="text-sm font-medium text-zinc-200">{workflow.name}</span>
        <span className="text-xs text-zinc-500 font-mono">{workflow.slug}</span>
      </header>

      {/* 3-pane layout */}
      <div className="flex flex-1 min-h-0">
        <NodePalette />
        <WorkflowCanvas
          graph={graph}
          onNodeSelect={handleNodeSelect}
          onNodeDragStop={handleNodeDragStop}
          onEdgeConnect={handleEdgeConnect}
          onDrop={handleDrop}
          onNodesDelete={handleNodesDelete}
          onEdgesDelete={handleEdgesDelete}
        />
        {selectedNode && (
          <NodeInspector
            selectedNode={selectedNode}
            workflow={workflow}
            onUpdateNode={handleUpdateNode}
          />
        )}
        {showCode && (
          <div className="w-[480px] border-l border-border-dark bg-zinc-950 flex flex-col shrink-0">
            <div className="flex items-center justify-between px-4 h-10 border-b border-border-dark bg-surface-dark shrink-0">
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span className="material-symbols-outlined text-[14px]">code</span>
                <span className="font-medium">Generated Code</span>
                <span className="text-zinc-600 font-mono">{workflow.slug}.py</span>
              </div>
              <button
                onClick={() => setShowCode(false)}
                className="text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            </div>
            <div className="flex-1 overflow-auto">
              {codeData?.code ? (
                <pre className="p-4 text-[13px] text-zinc-300 font-mono leading-relaxed whitespace-pre">
                  {codeData.code}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <span className="material-symbols-outlined text-3xl mb-2">code_off</span>
                  <p className="text-sm">No code generated yet</p>
                  <p className="text-xs text-zinc-600 mt-1">Add nodes and edges to generate code</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <EditorToolbar
        workflowId={workflowId}
        codeStatus={regenerateCode.status}
        showCode={showCode}
        onToggleCode={() => setShowCode(!showCode)}
      />
    </div>
  );
}
