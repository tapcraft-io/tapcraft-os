import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

export interface WorkflowNodeData {
  label: string;
  kind: 'trigger' | 'activity_operation' | 'primitive' | 'logic';
  primitiveType?: string | null;
  [key: string]: unknown;
}

const kindIcons: Record<string, string> = {
  trigger: 'bolt',
  activity_operation: 'apps',
  primitive: 'code',
  logic: 'call_split',
};

const primitiveIcons: Record<string, string> = {
  http_request: 'http',
  delay: 'schedule',
  log: 'terminal',
  browse: 'travel_explore',
};

const kindColors: Record<string, string> = {
  trigger: 'text-amber-400',
  activity_operation: 'text-sky-400',
  primitive: 'text-emerald-400',
  logic: 'text-violet-400',
};

function WorkflowNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as WorkflowNodeData;
  const icon = kindIcons[nodeData.kind] || 'help';
  const subIcon = nodeData.primitiveType ? primitiveIcons[nodeData.primitiveType] : null;
  const colorClass = kindColors[nodeData.kind] || 'text-zinc-400';

  return (
    <>
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-zinc-500 !border-zinc-700 !-top-1" />
      <div
        className={`
          px-4 py-3 rounded-xl bg-surface-light border min-w-[140px]
          transition-all duration-150
          ${selected
            ? 'border-primary shadow-[0_0_12px_rgba(238,140,43,0.3)]'
            : 'border-border-dark hover:border-zinc-500'}
        `}
      >
        <div className="flex items-center gap-2.5">
          <div className={`flex items-center justify-center w-7 h-7 rounded-lg bg-zinc-800 ${colorClass}`}>
            <span className="material-symbols-outlined text-[16px]">{subIcon || icon}</span>
          </div>
          <span className="text-sm font-medium text-zinc-200 truncate max-w-[120px]">
            {nodeData.label}
          </span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-zinc-500 !border-zinc-700 !-bottom-1" />
    </>
  );
}

export default memo(WorkflowNode);
