import { useRef, useCallback } from 'react';
import SetRow from './SetRow';
import LogButton from './LogButton';
import { SUPERSET_COLORS } from '../lib/constants';

/**
 * Full exercise card — set rows with read-only weights + reps inputs + log button.
 * Uses uncontrolled refs for reps inputs to avoid re-renders on keystrokes.
 */
export default function ExerciseCard({ exercise, week, day, onLog, onError }) {
  const {
    exercise: name,
    target_weights: weights,
    sets,
    target_reps: targetReps,
    superset_group,
    strategy,
  } = exercise;

  const numSets = weights.length;
  const repsRefs = useRef([]);

  /** Collect refs for each SetRow input */
  const assignRef = useCallback(
    (i) => (el) => {
      repsRefs.current[i] = el;
    },
    [],
  );

  const supersetBorder = superset_group
    ? SUPERSET_COLORS[superset_group]?.border ?? ''
    : '';

  /** Validate & submit */
  const handleLog = async () => {
    const actualReps = [];
    let valid = true;

    for (let i = 0; i < numSets; i++) {
      const input = repsRefs.current[i];
      const val = input?.value?.trim() ?? '';

      if (val === '') {
        valid = false;
        input.style.borderColor = '#f55';
      } else {
        input.style.borderColor = '';
        actualReps.push(parseInt(val, 10));
      }
    }

    if (!valid) {
      onError('Fill in all reps.');
      throw new Error('validation');
    }

    await onLog({
      week_id: week,
      day,
      exercise: name,
      actual_weight: weights,
      actual_reps: actualReps,
    });
  };

  return (
    <div
      className={`mx-3 my-2 bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden ${
        superset_group ? `border-l-4 ${supersetBorder}` : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-3 pb-1 gap-2">
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

      {/* Meta */}
      <div className="flex gap-3 px-4 pb-2 text-xs text-zinc-500">
        <span>{numSets} sets</span>
        <span>{targetReps} reps</span>
        {strategy && <span>{strategy}</span>}
      </div>

      {/* Set grid */}
      <div className="px-2.5 pb-1">
        {/* Column headers */}
        <div className="grid grid-cols-[3.2rem_1fr_1fr] gap-1.5 px-1.5 pb-1 text-[0.65rem] font-semibold text-zinc-500 uppercase tracking-wide">
          <span />
          <span>Weight</span>
          <span>Reps</span>
        </div>

        {Array.from({ length: numSets }, (_, i) => (
          <SetRow key={i} index={i} weight={weights[i]} targetReps={targetReps} ref={assignRef(i)} />
        ))}
      </div>

      {/* Log button */}
      <div className="px-2.5 pb-2.5">
        <LogButton exerciseName={name} onLog={handleLog} />
      </div>
    </div>
  );
}
