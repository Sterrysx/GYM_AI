import { useState } from 'react';
import { ChevronDown, ChevronRight, Timer } from 'lucide-react';

/**
 * Collapsible "Abs Routine" accordion card.
 * Receives the full list of static exercises for the day
 * and renders them as a single expandable section.
 */
export default function AbsAccordion({ exercises }) {
  const [open, setOpen] = useState(false);

  const totalExercises = exercises.length;
  const totalSeconds = exercises.reduce((acc, ex) => {
    const match = String(ex.target_reps).match(/(\d+)/);
    return acc + (match ? parseInt(match[1], 10) : 0);
  }, 0);
  const totalMin = Math.floor(totalSeconds / 60);
  const totalSec = totalSeconds % 60;
  const durationStr = totalMin > 0
    ? `${totalMin}m ${totalSec > 0 ? totalSec + 's' : ''}`.trim()
    : `${totalSec}s`;

  return (
    <div className="mx-3 my-2 bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden">
      {/* Accordion toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-800">
            <Timer size={16} className="text-amber-400" />
          </div>
          <div>
            <p className="text-sm font-bold text-zinc-200">Abs Routine</p>
            <p className="text-xs text-zinc-500">
              {totalExercises} exercises · ~{durationStr} total
            </p>
          </div>
        </div>

        <div className="text-zinc-500">
          {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </div>
      </button>

      {/* Expandable list */}
      {open && (
        <div className="border-t border-zinc-800 divide-y divide-zinc-800/60">
          {exercises.map((ex, idx) => (
            <div key={idx} className="flex items-center justify-between px-4 py-2.5 gap-3">
              <span className="text-sm text-zinc-300 leading-snug">{ex.exercise}</span>
              <span className="flex items-center gap-1 text-xs font-semibold text-amber-400 shrink-0 bg-amber-400/10 px-2 py-0.5 rounded-md">
                <Timer size={11} />
                {ex.target_reps}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
