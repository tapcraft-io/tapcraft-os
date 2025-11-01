import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import client from '../hooks/useApi';
import { RunRecord } from '../types';

const ChronoScope = () => {
  const { data } = useQuery<{ runs: RunRecord[] }>({
    queryKey: ['runs', 'chronoscope'],
    queryFn: async () => {
      const { data } = await client.get('/runs', { params: { limit: 10 } });
      return { runs: data.runs ?? data };
    },
    refetchInterval: 10_000
  });

  return (
    <section className="glass-panel relative overflow-hidden rounded-3xl border border-holo-blue/20 px-8 py-6">
      <header className="flex items-center justify-between">
        <h3 className="text-xs uppercase tracking-[0.3em] text-holo-blue">Chrono-Scope</h3>
        <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Temporal waveforms</span>
      </header>
      <div className="mt-4 flex h-24 items-end gap-3">
        {data?.runs.map((run) => {
          const success = run.status === 'succeeded';
          const duration = run.duration_ms ?? 1_000;
          const height = Math.min(100, Math.max(20, duration / 50));
          return (
            <motion.div
              key={run.id}
              className="flex-1 rounded-full"
              style={{
                height,
                background: success
                  ? 'linear-gradient(180deg, rgba(79,209,255,0.75) 0%, rgba(15,20,36,0.4) 100%)'
                  : 'linear-gradient(180deg, rgba(248,113,113,0.75) 0%, rgba(15,20,36,0.4) 100%)'
              }}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              title={`${run.workflow_ref} (${run.status})`}
            />
          );
        })}
        {(!data || data.runs.length === 0) && (
          <p className="text-xs text-slate-500">Awaiting run history…</p>
        )}
      </div>
    </section>
  );
};

export default ChronoScope;
