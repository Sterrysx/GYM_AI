import { useState } from 'react';
import { Dumbbell, Check, Loader2 } from 'lucide-react';
import { logExercise } from '../api/client';

/**
 * Periodized Bench Press card.
 *
 * Reps are always fixed by the programme (e.g. 5×5, 4×4 …).
 * The user does NOT enter reps — the target is auto-submitted on log.
 */
export default function BenchCard({ exercise, week, day, onLogged, onError }) {
  const {
    exercise: name,
    target_weights: weights,
    sets,
    target_reps: targetReps,
  } = exercise;

  const [logState, setLogState] = useState('idle'); // idle | saving | logged

  const weight = weights[0]; // Uniform — every set is the same weight

  const handleLog = async () => {
    if (logState !== 'idle') return;
    setLogState('saving');

    // Auto-build reps array from the fixed target
    const repsVal = parseInt(targetReps, 10);
    const actualReps = Array.from({ length: sets }, () => repsVal);
    const actualWeights = Array.from({ length: sets }, () => weight);

    try {
      await logExercise({
        week_id: week,
        day,
        exercise: name,
        actual_weight: actualWeights,
        actual_reps: actualReps,
      });
      setLogState('logged');
      onLogged?.(`${name} logged.`);
    } catch (err) {
      setLogState('idle');
      onError?.(err.response?.data?.detail ?? err.message);
    }
  };

  return (
    <div className="mx-3 my-2 bg-zinc-950 rounded-xl border border-sky-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-3 pb-1 gap-2">
        <div className="flex items-center gap-2">
          <Dumbbell size={16} className="text-sky-400 shrink-0" />
          <span className="text-base font-bold leading-snug">{name}</span>
        </div>
        <span className="text-[0.65rem] font-bold px-2 py-0.5 rounded uppercase tracking-wide shrink-0 bg-sky-900 text-sky-300">
          Cycle
        </span>
      </div>

      {/* Programme display */}
      <div className="px-4 py-3 flex items-center gap-4">
        {/* Scheme chip */}
        <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-5 py-3">
          <span className="text-2xl font-black text-sky-400 leading-none">
            {sets}×{targetReps}
          </span>
          <span className="text-[0.6rem] text-zinc-500 uppercase tracking-widest mt-0.5">
            sets × reps
          </span>
        </div>

        {/* Weight chip */}
        <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-5 py-3">
          <span className="text-2xl font-black text-emerald-400 leading-none">
            {weight}
          </span>
          <span className="text-[0.6rem] text-zinc-500 uppercase tracking-widest mt-0.5">
            kg / set
          </span>
        </div>
      </div>

      <p className="px-4 pb-2 text-xs text-zinc-600 italic">
        Reps are fixed by programme — just confirm you completed the session.
      </p>

      {/* Log button */}
      <div className="px-2.5 pb-2.5">
        {logState === 'logged' ? (
          <button
            disabled
            className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-zinc-900 text-emerald-400 border border-emerald-400"
          >
            <Check size={16} strokeWidth={3} />
            Session Logged
          </button>
        ) : logState === 'saving' ? (
          <button
            disabled
            className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-zinc-800 text-zinc-500 cursor-not-allowed"
          >
            <Loader2 size={16} className="animate-spin" />
            Saving…
          </button>
        ) : (
          <button
            onClick={handleLog}
            className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-sky-400 text-black cursor-pointer active:opacity-70"
          >
            Confirm Session Complete
          </button>
        )}
      </div>
    </div>
  );
}
