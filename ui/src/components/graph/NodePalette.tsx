import { useState, type DragEvent } from 'react';
import { useActivities } from '../../hooks/useTapcraft';

export interface PaletteItem {
  kind: string;
  label: string;
  icon: string;
  primitiveType?: string;
  activityOperationId?: number;
  configSchema?: Record<string, unknown>;
  defaultConfig?: Record<string, unknown>;
}

// Built-in primitive node schemas
const PRIMITIVE_SCHEMAS: Record<string, { configSchema: Record<string, unknown>; defaultConfig: Record<string, unknown> }> = {
  http_request: {
    configSchema: {
      type: 'object',
      properties: {
        method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], description: 'HTTP method' },
        url: { type: 'string', description: 'Request URL' },
        headers: { type: 'object', description: 'Request headers (JSON)' },
        body: { type: 'string', description: 'Request body' },
      },
      required: ['method', 'url'],
    },
    defaultConfig: { method: 'GET', url: 'https://api.example.com/data' },
  },
  delay: {
    configSchema: {
      type: 'object',
      properties: {
        seconds: { type: 'integer', description: 'Seconds to wait' },
      },
      required: ['seconds'],
    },
    defaultConfig: { seconds: 60 },
  },
  log: {
    configSchema: {
      type: 'object',
      properties: {
        message: { type: 'string', description: 'Log message' },
        level: { type: 'string', enum: ['info', 'warning', 'error'], description: 'Log level' },
      },
      required: ['message'],
    },
    defaultConfig: { message: 'Step executed', level: 'info' },
  },
  browse: {
    configSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: 'URL to navigate to' },
        actions: { type: 'array', description: 'Browser actions (JSON array)' },
      },
      required: ['url', 'actions'],
    },
    defaultConfig: { url: 'https://example.com', actions: [] },
  },
};

const TRIGGER_SCHEMA = {
  configSchema: {
    type: 'object',
    properties: {
      trigger_type: { type: 'string', description: 'Trigger type' },
    },
  },
  defaultConfig: {},
};

const triggers: PaletteItem[] = [
  { kind: 'trigger', label: 'Manual Trigger', icon: 'touch_app', primitiveType: 'manual', ...TRIGGER_SCHEMA },
  { kind: 'trigger', label: 'Cron', icon: 'schedule', primitiveType: 'cron', ...TRIGGER_SCHEMA },
  { kind: 'trigger', label: 'Webhook', icon: 'webhook', primitiveType: 'webhook', ...TRIGGER_SCHEMA },
];

const primitives: PaletteItem[] = [
  { kind: 'primitive', label: 'HTTP Request', icon: 'http', primitiveType: 'http_request', ...PRIMITIVE_SCHEMAS.http_request },
  { kind: 'primitive', label: 'Delay', icon: 'schedule', primitiveType: 'delay', ...PRIMITIVE_SCHEMAS.delay },
  { kind: 'primitive', label: 'Log', icon: 'terminal', primitiveType: 'log', ...PRIMITIVE_SCHEMAS.log },
  { kind: 'primitive', label: 'Browse', icon: 'travel_explore', primitiveType: 'browse', ...PRIMITIVE_SCHEMAS.browse },
];

function PaletteSection({ title, items, defaultOpen = true }: { title: string; items: PaletteItem[]; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  const onDragStart = (e: DragEvent, item: PaletteItem) => {
    e.dataTransfer.setData('application/tapcraft-node', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        {title}
        <span className={`material-symbols-outlined text-[14px] transition-transform ${open ? '' : '-rotate-90'}`}>
          expand_more
        </span>
      </button>
      {open && (
        <div className="space-y-0.5 px-1.5 pb-2">
          {items.map((item, i) => (
            <div
              key={`${item.kind}-${item.label}-${i}`}
              draggable
              onDragStart={(e) => onDragStart(e, item)}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-grab active:cursor-grabbing
                hover:bg-zinc-800 transition-colors select-none"
            >
              <span className="material-symbols-outlined text-[16px] text-zinc-400">{item.icon}</span>
              <span className="text-sm text-zinc-300">{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function NodePalette() {
  const [search, setSearch] = useState('');
  const { data: activities } = useActivities(1);

  const activityItems: PaletteItem[] = (activities ?? []).flatMap((act) =>
    act.operations.map((op) => {
      let parsedSchema: Record<string, unknown> = {};
      try { parsedSchema = JSON.parse(op.config_schema); } catch { /* empty */ }
      return {
        kind: 'activity_operation',
        label: op.display_name,
        icon: 'apps',
        activityOperationId: op.id,
        configSchema: parsedSchema,
        defaultConfig: {},
      };
    })
  );

  const filterItems = (items: PaletteItem[]) =>
    search ? items.filter((i) => i.label.toLowerCase().includes(search.toLowerCase())) : items;

  const filteredTriggers = filterItems(triggers);
  const filteredPrimitives = filterItems(primitives);
  const filteredActivities = filterItems(activityItems);

  return (
    <div className="w-64 h-full bg-surface-dark border-r border-border-dark flex flex-col shrink-0">
      <div className="p-3 border-b border-border-dark">
        <div className="relative">
          <span className="material-symbols-outlined text-[16px] text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2">
            search
          </span>
          <input
            type="text"
            placeholder="Search nodes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm bg-zinc-800 border border-border-dark rounded-lg
              text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-primary/50"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {filteredTriggers.length > 0 && <PaletteSection title="Triggers" items={filteredTriggers} />}
        {filteredActivities.length > 0 && <PaletteSection title="Activity Operations" items={filteredActivities} defaultOpen={false} />}
        {filteredPrimitives.length > 0 && <PaletteSection title="Primitives" items={filteredPrimitives} />}
      </div>
    </div>
  );
}
