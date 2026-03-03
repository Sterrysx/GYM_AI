/**
 * ExerciseCard — single exercise with per-set logging.
 * Shows already-logged sets as completed, allows editing.
 */
import { useState } from 'react';
import SetRow from './SetRow';
import { SUPERSET_COLORS } from '../lib/constants';
import { Check, Loader2, CheckCircle2 } from 'lucide-react';
import { completeExercise } from '../api/client';

export default function ExerciseCard({ exercise, week, day, onError, showToast, onReload }) {
  const {
    exercise_id: exerciseId,
    exercise: name,
    target_weights: weights,
    sets,
    target_reps: targetReps,
    superset_group,
    strategy,
    equipment,
    sets_data: setsData = [],
    all_logged: allLogged = false,
  } = exercise;

  const numSets = weights?.length ?? sets ?? 0;
  const supersetBorder = superset_group
    ? SUPERSET_COLORS[superset_group]?.border ?? ''
    : '';

  // Build rep range label from per-set data when reps differ across sets
  const numericSetReps = setsData
    .map((s) => s?.target_reps)
    .filter((r) => r != null && !isNaN(Number(r)))
    .map(Number);
  const hasNonNumeric = setsData.some(
    (s) => s?.target_reps != null && isNaN(Number(s.target_reps))
  );
  const repsLabel = (() => {
    if (numericSetReps.length === 0) {
      return hasNonNumeric ? null : targetReps != null ? `${targetReps} reps` : null;
    }
    const minR = Math.min(...numericSetReps);
    const maxR = Math.max(...numericSetReps);
    return minR === maxR ? `${minR} reps` : `${minR}–${maxR} reps`;
  })();

  const [completing, setCompleting] = useState(false);

  // Track locally-logged sets so we don't reload after each individual log
  const [locallyLogged, setLocallyLogged] = useState(0);
  const initiallyLogged = setsData.filter((s) => s?.logged).length;
  const localAllLogged = allLogged || (initiallyLogged + locallyLogged) >= numSets;
  const hasUnlogged = !localAllLogged;

  const handleSetLogged = (setIndex) => {
    setLocallyLogged((n) => n + 1);
    showToast?.(`${name} S${setIndex + 1} logged`);
  };

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await completeExercise(week, day, [exerciseId]);
      showToast?.(`${name} completed`);
      onReload?.();
    } catch (err) {
      onError?.(err.response?.data?.detail ?? err.message);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div
      className={`mx-3 my-2 bg-zinc-950 rounded-xl border overflow-hidden ${
        localAllLogged
          ? 'border-emerald-800/50'
          : `border-zinc-800 ${superset_group ? `border-l-4 ${supersetBorder}` : ''}`
      }`}
    >
      <div className="flex items-start justify-between px-4 pt-3 pb-1 gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold leading-snug">{name}</span>
          {localAllLogged && <Check size={14} className="text-emerald-400" strokeWidth={3} />}
        </div>
        <div className="flex items-center gap-1.5">
          {equipment && (
            <span className="text-[0.6rem] font-medium px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 uppercase tracking-wide">
              {equipment.replace(/_/g, ' ')}
            </span>
          )}
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
      </div>
      <div className="flex gap-3 px-4 pb-2 text-xs text-zinc-500">
        <span>{numSets} sets</span>
        {repsLabel && <span>{repsLabel}</span>}
        {strategy && <span>{strategy}</span>}
      </div>
      <div className="px-2.5 pb-1">
        <div className="grid grid-cols-[3.2rem_1fr_1fr_2.5rem] gap-1.5 px-1.5 pb-1 text-[0.65rem] font-semibold text-zinc-500 uppercase tracking-wide">
          <span />
          <span>Weight</span>
          <span>Reps</span>
          <span />
        </div>
        {Array.from({ length: numSets }, (_, i) => (
          <SetRow
            key={i}
            index={i}
            weight={weights[i]}
            targetReps={setsData[i]?.target_reps ?? targetReps}
            setData={setsData[i]}
            weekId={week}
            day={day}
            exerciseId={exerciseId}
            onSetLogged={() => handleSetLogged(i)}
            onError={onError}
          />
        ))}
      </div>

      {/* Complete exercise button */}
      {hasUnlogged && !localAllLogged && (
        <div className="px-3 pb-2.5">
          <button
            onClick={handleComplete}
            disabled={completing}
            className="w-full py-2 rounded-lg text-[0.7rem] font-semibold uppercase tracking-wide border border-zinc-700 text-zinc-400 active:bg-zinc-800 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
          >
            {completing ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
            {completing ? 'Completing…' : 'Complete Exercise'}
          </button>
        </div>
      )}
    </div>
  );
}
