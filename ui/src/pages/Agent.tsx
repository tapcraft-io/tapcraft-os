import { useState } from 'react';
import { SparklesIcon, PlusIcon, BoltIcon } from '@heroicons/react/24/outline';
import { useNavigate } from 'react-router-dom';
import { useCreateWorkflow, useApps } from '../hooks/useTapcraft';

const WORKSPACE_ID = 1; // TODO: Get from context

const Agent = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const { data: apps } = useApps(WORKSPACE_ID);
  const createWorkflow = useCreateWorkflow(WORKSPACE_ID);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    try {
      const result = await createWorkflow.mutateAsync({
        user_prompt: prompt,
      });

      // Navigate to workflows page after creation
      navigate('/workflows');
    } catch (error) {
      console.error('Failed to create workflow:', error);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <SparklesIcon className="h-10 w-10 text-purple-500" />
          <h1 className="text-3xl font-semibold">Tapcraft Agent</h1>
        </div>
        <p className="text-slate-400">
          Describe your automation in natural language, and I'll create a working workflow
        </p>
      </div>

      {/* Creation Form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
          <label className="block text-sm font-medium text-slate-300 mb-3">
            What would you like to automate?
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Example: Fetch my unread emails every morning and send a summary to Slack..."
            className="w-full h-32 px-4 py-3 bg-slate-950 border border-slate-700 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
            disabled={createWorkflow.isPending}
          />

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              {apps && apps.length > 0 ? (
                <span>{apps.length} apps available with {apps.reduce((sum, app) => sum + app.operations.length, 0)} operations</span>
              ) : (
                <span>No apps available yet</span>
              )}
            </div>
            <button
              type="submit"
              disabled={!prompt.trim() || createWorkflow.isPending}
              className="flex items-center gap-2 px-6 py-2.5 bg-purple-500 hover:bg-purple-600 disabled:bg-slate-700 disabled:text-slate-500 rounded-md font-medium transition-colors"
            >
              {createWorkflow.isPending ? (
                <>
                  <div className="h-4 w-4 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <BoltIcon className="h-4 w-4" />
                  Create Workflow
                </>
              )}
            </button>
          </div>
        </div>

        {createWorkflow.isError && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            Error: {createWorkflow.error.message}
          </div>
        )}
      </form>

      {/* Examples */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-slate-300">Example Prompts</h2>
        <div className="grid gap-3">
          {[
            "Every morning, fetch my unread emails and send a count to Slack #general",
            "Get unread emails, create a Notion page for each one, then mark them as read",
            "Fetch weather data via HTTP and log it every hour",
            "Send me a daily Slack message with system status",
          ].map((example, i) => (
            <button
              key={i}
              onClick={() => setPrompt(example)}
              className="text-left p-4 bg-slate-900/30 hover:bg-slate-900/50 border border-slate-800 hover:border-slate-700 rounded-lg transition-colors"
              disabled={createWorkflow.isPending}
            >
              <div className="flex items-start gap-3">
                <SparklesIcon className="h-5 w-5 text-purple-400 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-slate-300">{example}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Info */}
      <div className="mt-8 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
        <h3 className="text-sm font-medium text-blue-300 mb-2">How it works</h3>
        <ul className="text-sm text-blue-200/80 space-y-1">
          <li>• Analyzes your prompt using GPT-4</li>
          <li>• Selects relevant app operations and primitives</li>
          <li>• Generates a workflow graph (nodes + edges)</li>
          <li>• Creates production-ready Temporal code</li>
          <li>• Commits to Git with reasoning</li>
        </ul>
      </div>
    </div>
  );
};

export default Agent;
