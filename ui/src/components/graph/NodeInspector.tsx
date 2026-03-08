import { useState, useEffect, useRef, useCallback } from 'react';
import type { Node as RFNode } from '@xyflow/react';
import type { Workflow } from '../../types/tapcraft';
import type { WorkflowNodeData } from './WorkflowNode';

// Fallback schemas for primitive nodes created before config_schema was populated.
// Fallback schemas for built-in primitive node types.
const PRIMITIVE_FALLBACK_SCHEMAS: Record<string, Record<string, unknown>> = {
  http_request: {
    type: 'object',
    properties: {
      method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], description: 'HTTP method' },
      url: { type: 'string', description: 'Request URL' },
      headers: { type: 'object', description: 'Request headers (JSON)' },
      body: { type: 'string', description: 'Request body' },
    },
    required: ['method', 'url'],
  },
  delay: {
    type: 'object',
    properties: {
      seconds: { type: 'integer', description: 'Seconds to wait' },
    },
    required: ['seconds'],
  },
  log: {
    type: 'object',
    properties: {
      message: { type: 'string', description: 'Log message' },
      level: { type: 'string', enum: ['info', 'warning', 'error'], description: 'Log level' },
    },
    required: ['message'],
  },
  browse: {
    type: 'object',
    properties: {
      url: { type: 'string', description: 'URL to navigate to' },
      actions: { type: 'array', description: 'Browser actions (JSON array)' },
    },
    required: ['url', 'actions'],
  },
};

function getEffectiveSchema(
  configSchema: Record<string, unknown> | undefined,
  kind: string,
  primitiveType: string | null | undefined,
): Record<string, unknown> {
  // If the node has a populated schema, use it
  const props = (configSchema as { properties?: Record<string, unknown> })?.properties;
  if (props && Object.keys(props).length > 0) {
    return configSchema!;
  }
  // Fallback for primitive nodes with known types
  if (kind === 'primitive' && primitiveType && PRIMITIVE_FALLBACK_SCHEMAS[primitiveType]) {
    return PRIMITIVE_FALLBACK_SCHEMAS[primitiveType];
  }
  return configSchema ?? {};
}

interface NodeInspectorProps {
  selectedNode: RFNode | null;
  workflow: Workflow;
  onUpdateNode: (nodeId: number, data: { label?: string; config?: string }) => void;
}

function ConfigForm({ configSchema, config, onSave }: {
  configSchema: Record<string, unknown>;
  config: Record<string, unknown>;
  onSave: (newConfig: Record<string, unknown>) => void;
}) {
  const properties = (configSchema as { properties?: Record<string, { type?: string; description?: string; enum?: string[] }> }).properties;
  if (!properties || Object.keys(properties).length === 0) {
    return <p className="text-xs text-zinc-500 italic">No configurable properties</p>;
  }

  // Local state for form editing - saves on blur, not on every keystroke
  const [localConfig, setLocalConfig] = useState(config);
  const prevConfigRef = useRef(config);

  useEffect(() => {
    if (config !== prevConfigRef.current) {
      setLocalConfig(config);
      prevConfigRef.current = config;
    }
  }, [config]);

  const handleChange = (key: string, value: unknown) => {
    setLocalConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleBlur = () => {
    if (JSON.stringify(localConfig) !== JSON.stringify(config)) {
      onSave(localConfig);
    }
  };

  // For booleans and selects, save immediately since they're single-action changes
  const handleImmediateChange = (key: string, value: unknown) => {
    const newConfig = { ...localConfig, [key]: value };
    setLocalConfig(newConfig);
    onSave(newConfig);
  };

  return (
    <div className="space-y-3">
      {Object.entries(properties).map(([key, schema]) => {
        const value = localConfig[key] ?? '';
        const type = schema.type || 'string';

        if (type === 'boolean') {
          return (
            <label key={key} className="flex items-center justify-between gap-2">
              <span className="text-xs text-zinc-400 capitalize">{key.replace(/_/g, ' ')}</span>
              <button
                type="button"
                onClick={() => handleImmediateChange(key, !value)}
                className={`relative w-9 h-5 rounded-full transition-colors ${value ? 'bg-primary' : 'bg-zinc-700'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${value ? 'translate-x-4' : ''}`} />
              </button>
            </label>
          );
        }

        // Enum -> select dropdown
        if (schema.enum && schema.enum.length > 0) {
          return (
            <div key={key}>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</label>
              {schema.description && <p className="text-xs text-zinc-600 mt-0.5">{schema.description}</p>}
              <select
                value={value as string ?? ''}
                onChange={(e) => handleImmediateChange(key, e.target.value)}
                className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                  text-zinc-200 focus:outline-none focus:border-primary/50"
              >
                <option value="">Select...</option>
                {schema.enum.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
          );
        }

        if (type === 'number' || type === 'integer') {
          return (
            <div key={key}>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</label>
              {schema.description && <p className="text-xs text-zinc-600 mt-0.5">{schema.description}</p>}
              <input
                type="number"
                value={value as number ?? ''}
                onChange={(e) => handleChange(key, Number(e.target.value))}
                onBlur={handleBlur}
                className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                  text-zinc-200 focus:outline-none focus:border-primary/50"
              />
            </div>
          );
        }

        if (type === 'object' || type === 'array') {
          return (
            <div key={key}>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</label>
              {schema.description && <p className="text-xs text-zinc-600 mt-0.5">{schema.description}</p>}
              <textarea
                value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                onChange={(e) => {
                  try { handleChange(key, JSON.parse(e.target.value)); }
                  catch { handleChange(key, e.target.value); }
                }}
                onBlur={handleBlur}
                rows={4}
                className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                  text-zinc-200 font-mono focus:outline-none focus:border-primary/50 resize-y"
              />
            </div>
          );
        }

        // Default: string
        return (
          <div key={key}>
            <label className="text-xs text-zinc-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</label>
            {schema.description && <p className="text-xs text-zinc-600 mt-0.5">{schema.description}</p>}
            <input
              type="text"
              value={value as string ?? ''}
              onChange={(e) => handleChange(key, e.target.value)}
              onBlur={handleBlur}
              className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                text-zinc-200 focus:outline-none focus:border-primary/50"
            />
          </div>
        );
      })}
    </div>
  );
}

// Error handling field definitions
const ERROR_HANDLING_FIELDS = [
  { key: '_retry_max_attempts', label: 'Max Retry Attempts', default: 3, description: 'Maximum number of retry attempts' },
  { key: '_retry_initial_interval', label: 'Initial Retry Interval', default: 1, description: 'Initial retry interval in seconds' },
  { key: '_retry_backoff_coefficient', label: 'Backoff Coefficient', default: 2.0, description: 'Multiplier for retry interval', step: 0.1 },
  { key: '_retry_max_interval', label: 'Max Retry Interval', default: 60, description: 'Maximum retry interval in seconds' },
  { key: '_start_to_close_timeout', label: 'Start-to-Close Timeout', default: 300, description: 'Timeout in seconds for activity execution' },
  { key: '_schedule_to_close_timeout', label: 'Schedule-to-Close Timeout', default: undefined as number | undefined, description: 'Overall timeout in seconds (optional)' },
] as const;

/** Returns true if the node kind/type supports error handling configuration. */
function supportsErrorHandling(kind: string, primitiveType: string | null | undefined): boolean {
  if (kind === 'activity_operation') return true;
  if (kind === 'primitive' && (primitiveType === 'http_request' || primitiveType === 'browse')) return true;
  return false;
}

function ErrorHandlingSection({ config, onSave, isOpen, onToggle }: {
  config: Record<string, unknown>;
  onSave: (newConfig: Record<string, unknown>) => void;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const [localValues, setLocalValues] = useState<Record<string, unknown>>({});
  const prevConfigRef = useRef(config);

  useEffect(() => {
    if (config !== prevConfigRef.current) {
      const vals: Record<string, unknown> = {};
      for (const field of ERROR_HANDLING_FIELDS) {
        if (config[field.key] !== undefined) {
          vals[field.key] = config[field.key];
        }
      }
      setLocalValues(vals);
      prevConfigRef.current = config;
    }
  }, [config]);

  // Initialize local values from config on mount
  useEffect(() => {
    const vals: Record<string, unknown> = {};
    for (const field of ERROR_HANDLING_FIELDS) {
      if (config[field.key] !== undefined) {
        vals[field.key] = config[field.key];
      }
    }
    setLocalValues(vals);
  }, []);

  const handleChange = (key: string, rawValue: string) => {
    const value = rawValue === '' ? undefined : Number(rawValue);
    setLocalValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleBlur = () => {
    // Merge error handling values into the full config
    const merged = { ...config };
    for (const field of ERROR_HANDLING_FIELDS) {
      const val = localValues[field.key];
      if (val !== undefined && val !== null && !Number.isNaN(val as number)) {
        merged[field.key] = val;
      } else {
        delete merged[field.key];
      }
    }
    if (JSON.stringify(merged) !== JSON.stringify(config)) {
      onSave(merged);
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-1 text-xs text-zinc-500 uppercase tracking-wider w-full mb-2"
      >
        <span
          className="material-symbols-outlined text-[14px] transition-transform"
          style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
        >
          chevron_right
        </span>
        Error Handling
      </button>
      {isOpen && (
        <div className="space-y-3">
          {ERROR_HANDLING_FIELDS.map((field) => {
            const value = localValues[field.key] ?? '';
            return (
              <div key={field.key}>
                <label className="text-xs text-zinc-500 uppercase tracking-wider">{field.label}</label>
                <p className="text-xs text-zinc-600 mt-0.5">{field.description}</p>
                <input
                  type="number"
                  step={'step' in field ? field.step : 1}
                  placeholder={field.default !== undefined ? String(field.default) : ''}
                  value={value as number | ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                  className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                    text-zinc-200 focus:outline-none focus:border-primary/50"
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function NodeInspector({ selectedNode, workflow, onUpdateNode }: NodeInspectorProps) {
  const [tab, setTab] = useState<'node' | 'workflow'>('node');
  const [label, setLabel] = useState('');
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [errorHandlingOpen, setErrorHandlingOpen] = useState(false);

  const nodeData = selectedNode?.data as unknown as (WorkflowNodeData & { configData?: Record<string, unknown>; configSchema?: Record<string, unknown>; dbId?: number }) | null;

  useEffect(() => {
    if (nodeData) {
      setLabel(nodeData.label);
      setConfig(nodeData.configData ?? {});
      setTab('node');
    }
  }, [selectedNode?.id]);

  const handleLabelBlur = () => {
    if (nodeData?.dbId && label !== nodeData.label) {
      onUpdateNode(nodeData.dbId, { label });
    }
  };

  const handleConfigSave = useCallback((newConfig: Record<string, unknown>) => {
    setConfig(newConfig);
    if (nodeData?.dbId) {
      onUpdateNode(nodeData.dbId, { config: JSON.stringify(newConfig) });
    }
  }, [nodeData?.dbId, onUpdateNode]);

  const effectiveSchema = nodeData
    ? getEffectiveSchema(nodeData.configSchema, nodeData.kind, nodeData.primitiveType)
    : {};

  return (
    <div className="w-80 h-full bg-surface-dark border-l border-border-dark flex flex-col shrink-0">
      {/* Tabs */}
      <div className="flex border-b border-border-dark">
        <button
          onClick={() => setTab('node')}
          className={`flex-1 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors
            ${tab === 'node' ? 'text-primary border-b-2 border-primary' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          Node
        </button>
        <button
          onClick={() => setTab('workflow')}
          className={`flex-1 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors
            ${tab === 'workflow' ? 'text-primary border-b-2 border-primary' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          Workflow
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {tab === 'node' && selectedNode && nodeData ? (
          <div className="space-y-5">
            {/* Label */}
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">Label</label>
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                onBlur={handleLabelBlur}
                className="mt-1 w-full px-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
                  text-zinc-200 focus:outline-none focus:border-primary/50"
              />
            </div>

            {/* Kind */}
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">Kind</label>
              <p className="text-sm text-zinc-300 mt-1 capitalize">{nodeData.kind}</p>
            </div>

            {/* Primitive Type */}
            {nodeData.primitiveType && (
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider">Type</label>
                <p className="text-sm text-zinc-300 mt-1">{nodeData.primitiveType}</p>
              </div>
            )}

            {/* Config Form */}
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider mb-2 block">Configuration</label>
              <ConfigForm
                configSchema={effectiveSchema}
                config={config}
                onSave={handleConfigSave}
              />
            </div>

            {/* Error Handling */}
            {supportsErrorHandling(nodeData.kind, nodeData.primitiveType) && (
              <ErrorHandlingSection
                config={config}
                onSave={handleConfigSave}
                isOpen={errorHandlingOpen}
                onToggle={() => setErrorHandlingOpen((v) => !v)}
              />
            )}

            {/* View Logs placeholder */}
            <button className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-zinc-400
              border border-border-dark rounded-lg hover:bg-zinc-800 transition-colors">
              <span className="material-symbols-outlined text-[16px]">description</span>
              View Node Logs
            </button>
          </div>
        ) : tab === 'node' ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <span className="material-symbols-outlined text-3xl text-zinc-700">touch_app</span>
            <p className="text-zinc-500 text-sm mt-2">Select a node to inspect</p>
          </div>
        ) : (
          /* Workflow Tab */
          <div className="space-y-5">
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">Name</label>
              <p className="text-sm text-zinc-300 mt-1">{workflow.name}</p>
            </div>
            {workflow.description && (
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider">Description</label>
                <p className="text-sm text-zinc-300 mt-1">{workflow.description}</p>
              </div>
            )}
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">Entrypoint</label>
              <p className="text-sm text-zinc-300 font-mono mt-1">{workflow.entrypoint_symbol}</p>
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wider">Code Module</label>
              <p className="text-sm text-zinc-300 font-mono mt-1 break-all">{workflow.code_module_path}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
