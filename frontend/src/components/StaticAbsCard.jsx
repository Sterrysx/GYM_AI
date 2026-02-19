import { Timer } from 'lucide-react';
import { SUPERSET_COLORS } from '../lib/constants';

/**
 * Display-only card for "static" strategy exercises (Abs).
 * Shows exercise name + target duration. No inputs, no log button.
 */
export default function StaticAbsCard({ exercise }) {
  const { exercise: name, target_reps: duration, superset_group } = exercise;

  const supersetBorder = superset_group
    ? SUPERSET_COLORS[superset_group]?.border ?? ''
    : '';

  return (
    <div
      className={`mx-3 my-2 bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden ${
        superset_group ? `border-l-4 ${supersetBorder}` : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 gap-2">
        <span className="text-base font-bold leading-snug">{name}</span>
        {superset_group && (
          <span
            className={`text-[0.65rem] font-bold px-2 py-0.5 rounded uppercase tracking-wide shrink-0 ${
              SUPERSET_COLORS[superset_group]?.badge ?? ''
            }`}
          >
            SS-{superset_group}
          </span>
        )}
      </div>

      {/* Duration badge */}
      <div className="flex items-center gap-2 px-4 pb-3 text-sm text-zinc-500">
        <Timer size={14} />
        <span>{duration}</span>
      </div>
    </div>
  );
}
