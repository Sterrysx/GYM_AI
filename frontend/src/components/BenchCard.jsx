/**
 * BenchCard — periodized bench press card with per-set logging.
 * If already logged, shows completed state with edit option.
 */
import { useState } from 'react';
import { Dumbbell, Check, Loader2, Pencil } from 'lucide-react';
import { logSet, editSet } from '../api/client';

export default function BenchCard({ exercise, week, day, onLogged, onError }) {
  const {
    exercise_id: exerciseId,
    exercise: name,
    target_weights: weights,
    sets,
    target_reps: targetReps,
    sets_data: setsData = [],
    all_logged: initialAllLogged = false,
  } = exercise;

  const weight = weights?.[0] ?? 0;
  const allAlreadyLogged = initialAllLogged || setsData.every((s) => s?.logged);
  const [logState, setLogState] = useState(allAlreadyLogged ? 'logged' : 'idle');

  const handleLog = async () => {
    if (logState !== 'idle') return;
    setLogState('saving');
    const repsVal = parseInt(targetReps, 10);

    try {
      for (let i = 0; i < sets; i++) {
        await logSet({
          week_id: week,
          day,
          exercise_id: exerciseId,
          set_number: i + 1,
          actual_weight: weights[i] ?? weight,
          actual_reps: repsVal,
        });
      }
      setLogState('logged');
      onLogged?.(`${name} logged.`);
    } catch (err) {
      setLogState('idle');
      onError?.(err.response?.data?.detail ?? err.message);
    }
  };

  return (
    <div className="mx-3 my-2 bg-zinc-950 rounded-xl border border-sky-900 overflow-hidden">
      <div className="flex items-start justify-between px-4 pt-3 pb-1 gap-2">
        <div className="flex items-center gap-2">
          <Dumbbell size={16} className="text-sky-400 shrink-0" />
          <span className="text-base font-bold leading-snug">{name}</span>
          {logState === 'logged' && <Check size={14} className="text-emerald-400" strokeWidth={3} />}
        </div>
        <span className="text-[0.65rem] font-bold px-2 py-0.5 rounded uppercase tracking-wide shrink-0 bg-sky-900 text-sky-300">Cycle</span>
      </div>
      <div className="px-4 py-3 flex items-center gap-4">
        <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-5 py-3">
          <span className="text-2xl font-black text-sky-400 leading-none">{sets}×{targetReps}</span>
          <span className="text-[0.6rem] text-zinc-500 uppercase tracking-widest mt-0.5">sets × reps</span>
        </div>
        <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-5 py-3">
          <span className="text-2xl font-black text-emerald-400 leading-none">{weight}</span>
          <span className="text-[0.6rem] text-zinc-500 uppercase tracking-widest mt-0.5">kg / set</span>
        </div>
      </div>

      {/* Per-set summary when logged */}
      {logState === 'logged' && setsData.length > 0 && (
        <div className="px-4 pb-2">
          <div className="flex gap-1 flex-wrap">
            {setsData.map((s, i) => (
              <span key={i} className="text-xs bg-emerald-400/10 text-emerald-400 px-2 py-0.5 rounded-md font-semibold">
                S{i + 1}: {s.actual_reps ?? targetReps} reps
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="px-4 pb-2 text-xs text-zinc-600 italic">
        {logState === 'logged'
          ? 'Session complete. Reps recorded above.'
          : 'Reps are fixed by programme — just confirm you completed the session.'}
      </p>
      <div className="px-2.5 pb-2.5">
        {logState === 'logged' ? (
          <button disabled className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-zinc-900 text-emerald-400 border border-emerald-400">
            <Check size={16} strokeWidth={3} /> Session Logged
          </button>
        ) : logState === 'saving' ? (
          <button disabled className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-zinc-800 text-zinc-500 cursor-not-allowed">
            <Loader2 size={16} className="animate-spin" /> Saving…
          </button>
        ) : (
          <button onClick={handleLog} className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-[0.95rem] font-bold bg-sky-400 text-black cursor-pointer active:opacity-70">
            Confirm Session Complete
          </button>
        )}
      </div>
    </div>
  );
}
