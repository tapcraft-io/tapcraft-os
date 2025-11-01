import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowPathIcon, CheckCircleIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import client from '../hooks/useApi';
import { AgentGeneration, PlanDoc, ValidationResult } from '../types';
import DiffViewer from './DiffViewer';

const AgentConsole = () => {
  const [task, setTask] = useState('');
  const [plan, setPlan] = useState<PlanDoc | null>(null);
  const [moduleText, setModuleText] = useState('');
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  const { data: capabilities } = useQuery({
    queryKey: ['capabilities'],
    queryFn: async () => {
      const { data } = await client.get('/config/capabilities');
      return data.capabilities ?? data;
    }
  });

  const planMutation = useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/agent/plan', {
        task_text: task,
        capabilities
      });
      return data as PlanDoc;
    },
    onSuccess: (next) => setPlan(next)
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/agent/generate', {
        task_text: task,
        plan,
        capabilities
      });
      return data as AgentGeneration;
    },
    onSuccess: (generation) => {
      setModuleText(generation.module_text);
    }
  });

  const validateMutation = useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/agent/validate', {
        module_text: moduleText
      });
      return data as ValidationResult;
    },
    onSuccess: (result) => setValidation(result)
  });

  const repairMutation = useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/agent/repair', {
        module_text: moduleText,
        issues: validation?.issues ?? []
      });
      return data;
    },
    onSuccess: (patched) => {
      if (patched?.patched_module_text) {
        setModuleText(patched.patched_module_text);
      }
    }
  });

  const testsMutation = useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/agent/tests', {
        module_text: moduleText
      });
      return data;
    }
  });

  return (
    <section className="glass-panel flex flex-col gap-6 p-8">
      <header className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold uppercase tracking-[0.35em] text-holo-blue">Agent Console</h2>
          <p className="mt-2 text-xs text-slate-400">
            Converse with the ship AI to plan, generate, validate, and repair workflows.
          </p>
        </div>
        <span className="rounded-full border border-holo-blue/40 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-holo-blue">
          {capabilities?.length ?? 0} tools
        </span>
      </header>

      <div className="grid grid-cols-2 gap-6">
        <div className="flex flex-col gap-4">
          <label className="text-xs uppercase tracking-[0.3em] text-slate-400">Mission brief</label>
          <textarea
            value={task}
            onChange={(event) => setTask(event.target.value)}
            className="min-h-[160px] rounded-3xl border border-slate-700/60 bg-black/50 px-4 py-3 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-holo-blue/70"
            placeholder="Chart a workflow to summarize analytics and post to Slack"
          />
          <div className="flex gap-3 text-xs uppercase tracking-[0.3em]">
            <button
              onClick={() => planMutation.mutate()}
              disabled={!task || planMutation.isPending}
              className="rounded-full border border-holo-blue/40 px-4 py-2 text-holo-blue hover:bg-holo-blue/10 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
            >
              {planMutation.isPending ? 'Planning…' : 'Plan'}
            </button>
            <button
              onClick={() => generateMutation.mutate()}
              disabled={!plan || generateMutation.isPending}
              className="rounded-full border border-holo-amber/40 px-4 py-2 text-holo-amber hover:bg-holo-amber/10 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
            >
              {generateMutation.isPending ? 'Generating…' : 'Generate'}
            </button>
            <button
              onClick={() => validateMutation.mutate()}
              disabled={!moduleText || validateMutation.isPending}
              className="rounded-full border border-emerald-400/40 px-4 py-2 text-emerald-400 hover:bg-emerald-400/10 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
            >
              {validateMutation.isPending ? 'Validating…' : 'Validate'}
            </button>
          </div>
          <div className="flex gap-3 text-xs uppercase tracking-[0.3em]">
            <button
              onClick={() => repairMutation.mutate()}
              disabled={!validation?.issues?.length}
              className="rounded-full border border-rose-400/40 px-4 py-2 text-rose-400 hover:bg-rose-400/10 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
            >
              Auto-repair
            </button>
            <button
              onClick={() => testsMutation.mutate()}
              disabled={!moduleText}
              className="rounded-full border border-holo-violet/40 px-4 py-2 text-holo-violet hover:bg-holo-violet/10 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
            >
              Generate tests
            </button>
          </div>
        </div>
        <div className="space-y-4">
          <div className="glass-panel border border-holo-blue/40 p-4">
            <h3 className="text-xs uppercase tracking-[0.3em] text-holo-blue">Plan</h3>
            {plan ? (
              <ul className="mt-3 space-y-2 text-xs text-slate-300">
                {plan.steps.map((step) => (
                  <li key={step.id} className="rounded-2xl border border-slate-700/60 bg-black/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="uppercase tracking-[0.3em] text-[10px] text-holo-amber">{step.id}</span>
                      <span className="text-[10px] text-slate-500">{step.tool_candidates.join(', ')}</span>
                    </div>
                    <p className="mt-2 text-slate-300">{step.goal}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-xs text-slate-500">Awaiting plan.</p>
            )}
          </div>
          <div className="glass-panel border border-holo-amber/40 p-4">
            <h3 className="text-xs uppercase tracking-[0.3em] text-holo-amber">Module Diff</h3>
            <DiffViewer text={moduleText} />
          </div>
          {validation && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel border border-emerald-400/40 p-4"
            >
              <div className="flex items-center gap-2 text-emerald-300">
                {validation.ok ? <CheckCircleIcon className="h-5 w-5" /> : <Cog6ToothIcon className="h-5 w-5" />}
                <h3 className="text-xs uppercase tracking-[0.3em]">Validation</h3>
              </div>
              <ul className="mt-3 space-y-2 text-xs text-slate-200">
                {validation.issues.length === 0 ? (
                  <li>All checks passed.</li>
                ) : (
                  validation.issues.map((issue) => (
                    <li key={`${issue.code}-${issue.message}`} className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3">
                      <p className="font-semibold text-rose-300">{issue.code}</p>
                      <p className="mt-1 text-rose-100/80">{issue.message}</p>
                    </li>
                  ))
                )}
              </ul>
            </motion.div>
          )}
        </div>
      </div>

      <footer className="flex items-center justify-end gap-3 text-xs uppercase tracking-[0.3em] text-slate-500">
        <ArrowPathIcon className="h-4 w-4 animate-spin" />
        Agent telemetry updates in real-time as you iterate.
      </footer>
    </section>
  );
};

export default AgentConsole;
