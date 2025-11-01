interface DiffViewerProps {
  text: string;
}

const DiffViewer = ({ text }: DiffViewerProps) => {
  if (!text) {
    return <p className="mt-2 text-xs text-slate-500">No module generated yet.</p>;
  }

  return (
    <pre className="mt-3 max-h-64 overflow-auto rounded-2xl bg-black/60 p-4 text-[11px] text-holo-amber/80">
      {text}
    </pre>
  );
};

export default DiffViewer;
