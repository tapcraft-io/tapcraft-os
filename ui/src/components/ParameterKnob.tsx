import { useMemo, useState } from 'react';
import clsx from 'clsx';

interface ParameterKnobProps {
  label: string;
  value: number;
  min?: number;
  max?: number;
  onChange?: (value: number) => void;
}

const ParameterKnob = ({ label, value, min = 0, max = 100, onChange }: ParameterKnobProps) => {
  const [internal, setInternal] = useState(value);
  const percent = useMemo(() => ((internal - min) / (max - min)) * 270 - 135, [internal, min, max]);

  return (
    <div className="flex flex-col items-center gap-3 text-xs uppercase tracking-[0.3em] text-slate-400">
      <div
        className={clsx(
          'relative h-16 w-16 rounded-full border border-slate-700/80 bg-black/60 shadow-inner shadow-black/50',
          'flex items-center justify-center'
        )}
        onWheel={(event) => {
          event.preventDefault();
          const delta = Math.sign(event.deltaY) * -1;
          const next = Math.min(max, Math.max(min, internal + delta));
          setInternal(next);
          onChange?.(next);
        }}
      >
        <div
          className="h-2 w-10 origin-center rounded-full bg-holo-blue"
          style={{ transform: `rotate(${percent}deg)` }}
        />
      </div>
      <span>{label}</span>
    </div>
  );
};

export default ParameterKnob;
