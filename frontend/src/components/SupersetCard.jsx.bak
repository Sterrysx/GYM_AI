import { useRef, useCallback } from 'react';
import LogButton from './LogButton';
import { SUPERSET_COLORS } from '../lib/constants';

/**
 * Interleaved superset card — renders 2+ exercises grouped by set number.
 *
 *   Set 1  →  Exercise A weight / reps
 *             Exercise B weight / reps
 *   Set 2  →  Exercise A weight / reps
 *             Exercise B weight / reps
 *   …
 *
 * Each exercise has its own Log button and collects reps independently.
 */
export default function SupersetCard({ exercises, week, day, onLog, onError }) {
  const group = exercises[0]?.superset_group ?? 'A';
  const groupColor = SUPERSET_COLORS[group] ?? SUPERSET_COLORS.A;
  const maxSets = Math.max(...exercises.map((ex) => ex.target_weights?.length ?? ex.sets ?? 0));

  // One ref array per exercise, keyed by exercise name
  const refsMap = useRef({});
  exercises.forEach((ex) => {
    if (!refsMap.current[ex.exercise]) {
      refsMap.current[ex.exercise] = [];
    }
  });

  const assignRef = useCallback(
    (exName, setIdx) => (el) => {
      if (!refsMap.current[exName]) refsMap.current[exName] = [];
      refsMap.current[exName][setIdx] = el;
    },
    [],
  );

  /** Build a handleLog for a specific exercise */
  const makeHandleLog = (ex) => async () => {
    const weights = ex.target_weights ?? [];
    const numSets = weights.length;
    const refs = refsMap.current[ex.exercise] ?? [];
    const actualReps = [];
    let valid = true;

    for (let i = 0; i < numSets; i++) {
      const input = refs[i];
      const val = input?.value?.trim() ?? '';
      if (val === '') {
        valid = false;
        if (input) input.style.borderColor = '#f55';
      } else {
        if (input) input.style.borderColor = '';
        actualReps.push(parseInt(val, 10));
      }
    }

    if (!valid) {
      onError(`Fill in all reps for ${ex.exercise}.`);
      throw new Error('validation');
    }

    await onLog({
      week_id: week,
      day,
      exercise: ex.exercise,
      actual_weight: weights,
      actual_reps: actualReps,
    });
  };

  // Short labels for each exercise within the group (A1, A2, …)
  const labels = exercises.map((_, i) => `${group}${i + 1}`);

  return (
    <div
      className={`mx-3 my-2 bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden border-l-4 ${groupColor.border}`}
    >
      {/* ── Header: all exercise names ── */}
      <div className="px-4 pt-3 pb-1 space-y-1">
        {exercises.map((ex, i) => (
          <div key={ex.exercise} className="flex items-center gap-2">
            <span
              className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide shrink-0 ${groupColor.badge}`}
            >
              {labels[i]}
            </span>
            <span className="text-sm font-bold leading-snug truncate">{ex.exercise}</span>
          </div>
        ))}
      </div>

      {/* ── Meta row ── */}
      <div className="flex gap-3 px-4 pb-2 text-xs text-zinc-500">
        <span>{maxSets} sets each</span>
        <span>
          {exercises.map((ex, i) => `${labels[i]}: ${ex.target_reps} reps`).join(' · ')}
        </span>
      </div>

      {/* ── Interleaved set grid ── */}
      <div className="px-2.5 pb-1">
        {Array.from({ length: maxSets }, (_, setIdx) => (
          <div key={setIdx} className="mb-2">
            {/* Set divider */}
            <div className="flex items-center gap-2 px-1 mb-1">
              <span className="text-[0.6rem] font-bold text-zinc-500 uppercase tracking-widest">
                Set {setIdx + 1}
              </span>
              <div className="flex-1 h-px bg-zinc-800" />
            </div>

            {/* One row per exercise */}
            {exercises.map((ex, exIdx) => {
              const weights = ex.target_weights ?? [];
              if (setIdx >= weights.length) return null;
              return (
                <div
                  key={ex.exercise}
                  className="grid grid-cols-[2.5rem_2rem_1fr_1fr] gap-1.5 items-center mb-1"
                >
                  {/* Exercise label */}
                  <span
                    className={`text-[0.6rem] font-bold text-center rounded px-1 py-0.5 ${groupColor.badge}`}
                  >
                    {labels[exIdx]}
                  </span>

                  {/* Set number */}
                  <span className="text-sm font-semibold text-zinc-500 text-center">
                    S{setIdx + 1}
                  </span>

                  {/* Target weight (read-only) */}
                  <div className="bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-sky-400">
                    {weights[setIdx]} kg
                  </div>

                  {/* Reps input */}
                  <input
                    ref={assignRef(ex.exercise, setIdx)}
                    type="number"
                    inputMode="numeric"
                    placeholder={ex.target_reps != null ? String(ex.target_reps) : 'reps'}
                    min={0}
                    max={99}
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-[0.95rem] text-zinc-200 placeholder-zinc-600 placeholder:text-xs focus:outline-none focus:border-sky-400 appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  />
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* ── Log buttons — one per exercise ── */}
      <div className="px-2.5 pb-2.5 space-y-1.5">
        {exercises.map((ex, i) => (
          <LogButton
            key={ex.exercise}
            exerciseName={`${labels[i]}: ${ex.exercise}`}
            onLog={makeHandleLog(ex)}
          />
        ))}
      </div>
    </div>
  );
}
