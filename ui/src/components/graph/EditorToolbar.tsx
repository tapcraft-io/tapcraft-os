import { useExecuteWorkflow } from '../../hooks/useTapcraft';

interface EditorToolbarProps {
  workflowId: number;
  codeStatus: 'idle' | 'pending' | 'success' | 'error';
  showCode?: boolean;
  onToggleCode?: () => void;
}

export default function EditorToolbar({ workflowId, codeStatus, showCode, onToggleCode }: EditorToolbarProps) {
  const executeWorkflow = useExecuteWorkflow();

  const handleRunOnce = () => {
    executeWorkflow.mutate({
      workflowId,
      request: { workflow_id: workflowId, input_config: {} },
    });
  };

  return (
    <div className="h-12 bg-surface-dark border-t border-border-dark flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-2">
        <button
          onClick={handleRunOnce}
          disabled={executeWorkflow.isPending}
          className="flex items-center gap-1.5 h-8 px-3 bg-primary text-zinc-950 text-sm font-bold rounded-lg
            hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[16px]">play_arrow</span>
          {executeWorkflow.isPending ? 'Starting...' : 'Run Once'}
        </button>
        {executeWorkflow.isSuccess && (
          <span className="text-xs text-emerald-400">Started run #{executeWorkflow.data.run_id}</span>
        )}
        {executeWorkflow.isError && (
          <span className="text-xs text-red-400">Failed to start</span>
        )}
        <button className="flex items-center gap-1.5 h-8 px-3 text-sm text-zinc-400 border border-border-dark
          rounded-lg hover:bg-zinc-800 transition-colors">
          <span className="material-symbols-outlined text-[16px]">check_circle</span>
          Validate
        </button>
      </div>
      <div className="flex items-center gap-3">
        {onToggleCode && (
          <button
            onClick={onToggleCode}
            className={`flex items-center gap-1.5 h-8 px-3 text-sm font-medium border rounded-lg transition-colors ${
              showCode
                ? 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'
                : 'text-zinc-400 border-border-dark hover:bg-zinc-800'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">code</span>
            {showCode ? 'Hide Code' : 'View Code'}
          </button>
        )}
        <div className="flex items-center gap-1.5 text-xs text-zinc-500">
          {codeStatus === 'pending' ? (
            <>
              <span className="material-symbols-outlined text-[14px] text-amber-400 animate-spin">progress_activity</span>
              <span className="text-amber-400">Generating code...</span>
            </>
          ) : codeStatus === 'error' ? (
            <>
              <span className="material-symbols-outlined text-[14px] text-red-400">error</span>
              <span className="text-red-400">Code gen failed</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[14px] text-emerald-500">cloud_done</span>
              Saved
            </>
          )}
        </div>
      </div>
    </div>
  );
}
