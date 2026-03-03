import { useCallback, useMemo, type DragEvent } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node as RFNode,
  type Edge as RFEdge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeTypes,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import WorkflowNode from './WorkflowNode';
import type { PaletteItem } from './NodePalette';
import type { Node, Edge, Graph } from '../../types/tapcraft';

interface WorkflowCanvasProps {
  graph: Graph;
  onNodeSelect: (node: RFNode | null) => void;
  onNodeDragStop: (nodeId: string, position: { x: number; y: number }) => void;
  onEdgeConnect: (from: number, to: number) => void;
  onDrop: (item: PaletteItem, position: { x: number; y: number }) => void;
  onNodesDelete: (nodeIds: string[]) => void;
  onEdgesDelete: (edgeIds: string[]) => void;
}

const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode,
};

function parsePosition(uiPosition: string): { x: number; y: number } {
  try {
    const parsed = JSON.parse(uiPosition);
    return { x: parsed.x ?? 0, y: parsed.y ?? 0 };
  } catch {
    return { x: 0, y: 0 };
  }
}

function parseConfig(config: string): Record<string, unknown> {
  try {
    return JSON.parse(config);
  } catch {
    return {};
  }
}

function toReactFlowNodes(nodes: Node[]): RFNode[] {
  return nodes.map((node) => ({
    id: String(node.id),
    type: 'workflowNode',
    position: parsePosition(node.ui_position),
    data: {
      label: node.label,
      kind: node.kind,
      primitiveType: node.primitive_type,
      configData: parseConfig(node.config),
      configSchema: parseConfig(node.config_schema),
      dbId: node.id,
    },
  }));
}

function toReactFlowEdges(edges: Edge[]): RFEdge[] {
  return edges.map((edge) => ({
    id: String(edge.id),
    source: String(edge.from_node_id),
    target: String(edge.to_node_id),
    label: edge.label ?? undefined,
    style: { stroke: '#52525b', strokeWidth: 2 },
    type: 'smoothstep',
    animated: false,
  }));
}

export default function WorkflowCanvas({
  graph,
  onNodeSelect,
  onNodeDragStop,
  onEdgeConnect,
  onDrop,
  onNodesDelete,
  onEdgesDelete,
}: WorkflowCanvasProps) {
  const initialNodes = useMemo(() => toReactFlowNodes(graph.nodes), [graph.nodes]);
  const initialEdges = useMemo(() => toReactFlowEdges(graph.edges), [graph.edges]);

  const [nodes, setNodes, onNodesChangeHandler] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeHandler] = useEdgesState(initialEdges);

  // Sync when graph data changes from API
  useMemo(() => {
    setNodes(toReactFlowNodes(graph.nodes));
    setEdges(toReactFlowEdges(graph.edges));
  }, [graph.nodes, graph.edges]);

  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChangeHandler(changes);
    },
    [onNodesChangeHandler]
  );

  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChangeHandler(changes);
    },
    [onEdgesChangeHandler]
  );

  const handleConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        onEdgeConnect(Number(connection.source), Number(connection.target));
      }
    },
    [onEdgeConnect]
  );

  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: RFNode) => {
      onNodeDragStop(node.id, node.position);
    },
    [onNodeDragStop]
  );

  const handleSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: RFNode[] }) => {
      onNodeSelect(selectedNodes.length === 1 ? selectedNodes[0] : null);
    },
    [onNodeSelect]
  );

  const handleNodesDelete = useCallback(
    (deletedNodes: RFNode[]) => {
      onNodesDelete(deletedNodes.map((n) => n.id));
    },
    [onNodesDelete]
  );

  const handleEdgesDelete = useCallback(
    (deletedEdges: RFEdge[]) => {
      onEdgesDelete(deletedEdges.map((e) => e.id));
    },
    [onEdgesDelete]
  );

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      const data = event.dataTransfer.getData('application/tapcraft-node');
      if (!data) return;

      const item: PaletteItem = JSON.parse(data);

      // Get the canvas bounding rect from the drop target
      const reactFlowBounds = (event.target as HTMLElement).closest('.react-flow')?.getBoundingClientRect();
      if (!reactFlowBounds) return;

      const position = {
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      };

      onDrop(item, position);
    },
    [onDrop]
  );

  return (
    <div className="flex-1 h-full" onDragOver={handleDragOver} onDrop={handleDrop}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeDragStop={handleNodeDragStop}
        onSelectionChange={handleSelectionChange}
        onNodesDelete={handleNodesDelete}
        onEdgesDelete={handleEdgesDelete}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{
          style: { stroke: '#52525b', strokeWidth: 2 },
          type: 'smoothstep',
        }}
        className="bg-background-dark"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#27272a" />
        <Controls
          className="!bg-surface-dark !border-border-dark !rounded-lg !shadow-lg [&>button]:!bg-surface-dark [&>button]:!border-border-dark [&>button]:!text-zinc-400 [&>button:hover]:!bg-zinc-800"
        />
      </ReactFlow>
    </div>
  );
}
