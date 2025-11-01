import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import client from '../hooks/useApi';
import { Capability, WorkflowSpec } from '../types';
import ModuleNode from './ModuleNode';
import CableConnection from './CableConnection';
import { usePatchBayState } from '../hooks/usePatchBayState';

interface PatchBayProps {
  onSelect?: (workflowRef: string) => void;
}

const PatchBay = ({ onSelect }: PatchBayProps) => {
  const { data: workflows } = useQuery<WorkflowSpec[]>({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data } = await client.get('/workflows');
      return data.workflows ?? data;
    }
  });

  const { data: capabilities } = useQuery<Capability[]>({
    queryKey: ['capabilities'],
    queryFn: async () => {
      const { data } = await client.get('/config/capabilities');
      return data.capabilities ?? data;
    }
  });

  const modules = useMemo(() => workflows ?? [], [workflows]);
  const { cables } = usePatchBayState();

  return (
    <section className="relative mt-8 min-h-[480px] rounded-3xl border border-slate-700/40 bg-gradient-to-br from-black/60 via-deck-panel/70 to-black/80 p-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold uppercase tracking-[0.35em] text-holo-blue">Patch Bay</h2>
          <p className="mt-2 text-xs text-slate-400">
            Drag workflows and connect them like synth modules. Connections sync with configuration.
          </p>
        </div>
        <button className="flex items-center gap-2 rounded-full border border-holo-blue/40 px-4 py-2 text-xs uppercase tracking-[0.3em] text-holo-blue hover:bg-holo-blue/10">
          Auto-arrange
        </button>
      </header>
      <div className="relative grid grid-cols-3 gap-6">
        {modules.map((module) => (
          <ModuleNode
            key={module.workflow_ref}
            id={module.workflow_ref}
            title={module.workflow_ref}
            description={module.config_schema ? 'Configurable via manifest schema.' : 'No config schema declared.'}
            ports={module.config_schema ? Object.keys(module.config_schema) : ['cfg']}
            tools={(capabilities ?? []).map((tool) => tool.id)}
            onSelect={onSelect}
          />
        ))}
        {modules.length === 0 && (
          <div className="col-span-3 flex h-64 items-center justify-center rounded-3xl border border-dashed border-slate-600/60 text-sm text-slate-500">
            Awaiting workflows — load one from the Agent Console to begin patching.
          </div>
        )}
        {cables.map((cable) => (
          <CableConnection key={cable.id} from={{ x: 0, y: 0 }} to={{ x: 280, y: 160 }} accent="violet" />
        ))}
      </div>
    </section>
  );
};

export default PatchBay;
