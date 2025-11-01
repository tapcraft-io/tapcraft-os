import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface ModuleNodeProps {
  id: string;
  title: string;
  description?: string;
  ports?: string[];
  tools?: string[];
  footer?: ReactNode;
  onSelect?: (id: string) => void;
}

const variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 }
};

const ModuleNode = ({ id, title, description, ports = [], tools = [], footer, onSelect }: ModuleNodeProps) => {
  return (
    <motion.div
      layoutId={id}
      variants={variants}
      initial="hidden"
      animate="show"
      className="glass-panel relative w-72 cursor-pointer p-4"
      data-workflow-ref={id}
      onClick={() => onSelect?.(id)}
    >
      <header className="mb-3">
        <h3 className="text-sm uppercase tracking-[0.35em] text-holo-blue">{title}</h3>
        {description && <p className="mt-2 text-xs text-slate-400">{description}</p>}
      </header>
      <div className="panel-divider mb-3" />
      <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.3em] text-slate-400">
        {ports.map((port) => (
          <span key={port} className="rounded-full border border-slate-600/60 px-2 py-1">
            {port}
          </span>
        ))}
        {ports.length === 0 && <span className="text-slate-500">No ports</span>}
      </div>
      <div className="panel-divider my-3" />
      <div className="text-xs text-slate-400">
        <p className="font-semibold uppercase tracking-[0.3em] text-holo-amber mb-2">Tools</p>
        <ul className="space-y-1">
          {tools.length > 0 ? (
            tools.map((tool) => (
              <li key={tool} className="truncate text-slate-300">
                {tool}
              </li>
            ))
          ) : (
            <li className="text-slate-500">No linked tools</li>
          )}
        </ul>
      </div>
      {footer && <div className="panel-divider my-3" />}
      {footer}
    </motion.div>
  );
};

export default ModuleNode;
