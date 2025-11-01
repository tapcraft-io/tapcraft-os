import { useQuery } from '@tanstack/react-query';
import { ArrowPathIcon, BoltIcon, ServerIcon } from '@heroicons/react/24/outline';
import dayjs from 'dayjs';
import client from '../hooks/useApi';
import { RunRecord } from '../types';

interface NextRunsResponse {
  runs: RunRecord[];
}

const CommandDeck = () => {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await client.get('/health');
      return data;
    }
  });

  const { data: runs } = useQuery<NextRunsResponse>({
    queryKey: ['runs', 10],
    queryFn: async () => {
      const { data } = await client.get('/runs', { params: { limit: 10 } });
      return { runs: data.runs ?? data };
    },
    refetchInterval: 10_000
  });

  return (
    <section className="grid grid-cols-3 gap-6">
      <div className="glass-panel p-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <ServerIcon className="h-6 w-6 text-holo-blue" />
          <h2 className="text-lg font-semibold tracking-wide">Temporal Link</h2>
        </div>
        <p className="text-sm text-slate-300">
          {health?.temporal?.connected ? 'Connected to' : 'Connecting to'} {health?.temporal?.namespace ?? 'default'} namespace.
        </p>
        <span className={`text-xs uppercase tracking-widest ${health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>
          {health?.status === 'ok' ? 'Systems nominal' : 'Attention required'}
        </span>
      </div>
      <div className="glass-panel p-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <BoltIcon className="h-6 w-6 text-holo-amber" />
          <h2 className="text-lg font-semibold tracking-wide">Next Runs</h2>
        </div>
        <ul className="space-y-2 text-sm text-slate-200">
          {runs?.runs?.map((run) => (
            <li key={run.id} className="flex items-center justify-between">
              <span>{run.workflow_ref}</span>
              <span className="text-xs text-slate-400">
                {dayjs(run.started_at).format('HH:mm:ss')}
              </span>
            </li>
          )) || <li className="text-slate-500">Awaiting schedule intel…</li>}
        </ul>
      </div>
      <div className="glass-panel p-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <ArrowPathIcon className="h-6 w-6 text-holo-violet" />
          <h2 className="text-lg font-semibold tracking-wide">Quick Command Terminal</h2>
        </div>
        <textarea
          className="min-h-[120px] w-full rounded-xl bg-black/40 border border-slate-700/70 px-4 py-3 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
          placeholder="> Summon autopilot run diagnostics"
        />
        <button className="self-end rounded-full border border-holo-blue/40 px-4 py-2 text-xs uppercase tracking-[0.3em] text-holo-blue hover:bg-holo-blue/10">
          Execute
        </button>
      </div>
    </section>
  );
};

export default CommandDeck;
