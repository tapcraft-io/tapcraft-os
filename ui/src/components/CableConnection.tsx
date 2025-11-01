import { motion } from 'framer-motion';

interface CableConnectionProps {
  from: { x: number; y: number };
  to: { x: number; y: number };
  accent?: 'blue' | 'amber' | 'violet';
}

const accentMap = {
  blue: 'rgba(79, 209, 255, 0.85)',
  amber: 'rgba(255, 179, 71, 0.85)',
  violet: 'rgba(159, 122, 234, 0.85)'
};

const CableConnection = ({ from, to, accent = 'blue' }: CableConnectionProps) => {
  const path = `M ${from.x} ${from.y} C ${from.x + 120} ${from.y}, ${to.x - 120} ${to.y}, ${to.x} ${to.y}`;

  return (
    <motion.svg className="pointer-events-none absolute inset-0 h-full w-full">
      <motion.path
        d={path}
        fill="none"
        stroke={accentMap[accent]}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8, ease: 'easeInOut' }}
        className="drop-shadow-[0_0_12px_rgba(79,209,255,0.45)]"
      />
    </motion.svg>
  );
};

export default CableConnection;
