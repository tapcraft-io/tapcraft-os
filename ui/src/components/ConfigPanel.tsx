import { useQuery } from '@tanstack/react-query';
import ParameterKnob from './ParameterKnob';
import client from '../hooks/useApi';

const ConfigPanel = () => {
  const { data } = useQuery({
    queryKey: ['config'],
    queryFn: async () => {
      const { data } = await client.get('/config');
      return data;
    }
  });

  return (
    <section className="grid grid-cols-3 gap-6">
      <div className="glass-panel p-6">
        <h3 className="text-xs uppercase tracking-[0.3em] text-holo-blue">Git</h3>
        <p className="mt-2 text-xs text-slate-400">Configure git remotes and commit behavior.</p>
        <div className="mt-4 space-y-3 text-xs text-slate-300">
          <label className="block">
            Remote URL
            <input
              type="text"
              defaultValue={data?.git_remote ?? ''}
              className="mt-1 w-full rounded-xl border border-slate-700/60 bg-black/50 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
            />
          </label>
          <label className="block">
            Branch
            <input
              type="text"
              defaultValue={data?.git_branch ?? 'main'}
              className="mt-1 w-full rounded-xl border border-slate-700/60 bg-black/50 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
            />
          </label>
        </div>
      </div>
      <div className="glass-panel p-6">
        <h3 className="text-xs uppercase tracking-[0.3em] text-holo-amber">LLM Limits</h3>
        <p className="mt-2 text-xs text-slate-400">Dial in planner/generator token budgets.</p>
        <div className="mt-6 flex justify-around">
          <ParameterKnob label="Plan" value={data?.limits?.plan_tokens ?? 1500} min={200} max={8000} />
          <ParameterKnob label="Generate" value={data?.limits?.generate_tokens ?? 8000} min={2000} max={16000} />
          <ParameterKnob label="RPM" value={data?.limits?.rpm ?? 60} min={5} max={120} />
        </div>
      </div>
      <div className="glass-panel p-6">
        <h3 className="text-xs uppercase tracking-[0.3em] text-holo-violet">Temporal</h3>
        <p className="mt-2 text-xs text-slate-400">Adjust namespace and task queue.</p>
        <div className="mt-4 space-y-3 text-xs text-slate-300">
          <label className="block">
            Namespace
            <input
              type="text"
              defaultValue={data?.temporal?.namespace ?? 'default'}
              className="mt-1 w-full rounded-xl border border-slate-700/60 bg-black/50 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
            />
          </label>
          <label className="block">
            Task queue
            <input
              type="text"
              defaultValue={data?.task_queue ?? 'tapcraft-default'}
              className="mt-1 w-full rounded-xl border border-slate-700/60 bg-black/50 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
            />
          </label>
        </div>
      </div>
    </section>
  );
};

export default ConfigPanel;
