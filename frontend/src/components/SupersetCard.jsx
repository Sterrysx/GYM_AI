/**
 * SupersetCard — interleaved superset exercises with per-set logging.
 * Each set gets its own log button via SetRow.
 */
import { useState } from 'react';
import { Check, Loader2, Pencil } from 'lucide-react';
import { logSet, editSet } from '../api/client';
import { SUPERSET_COLORS } from '../lib/constants';

function SupersetSetRow({ exLabel, setIdx, weight, targetReps, setData, weekId, day, exerciseId, groupColor, onSetLogged, onError }) {
  const isLogged = setData?.logged ?? false;
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loggedReps, setLoggedReps] = useState(setData?.actual_reps);
  const [done, setDone] = useState(isLogged);
  let inputRef = null;

  const handleLog = async () => {
    const val = inputRef?.value?.trim();
    if (!val) { onError?.('Enter reps'); if (inputRef) inputRef.style.borderColor = '#f55'; return; }
    if (inputRef) inputRef.style.borderColor = '';
    setSaving(true);
    try {
      await logSet({ week_id: weekId, day, exercise_id: exerciseId, set_number: setIdx + 1, actual_weight: weight, actual_reps: parseInt(val, 10) });
      setLoggedReps(parseInt(val, 10));
      setDone(true);
      setEditing(false);
      onSetLogged?.();
    } catch (err) { onError?.(err.response?.data?.detail ?? err.message); }
    finally { setSaving(false); }
  };

  const handleEdit = async () => {
    const val = inputRef?.value?.trim();
    if (!val) return;
    setSaving(true);
    try {
      await editSet({ week_id: weekId, day, exercise_id: exerciseId, set_number: setIdx + 1, actual_weight: weight, actual_reps: parseInt(val, 10) });
      setLoggedReps(parseInt(val, 10));
      setDone(true);
      setEditing(false);
      onSetLogged?.();
    } catch (err) { onError?.(err.response?.data?.detail ?? err.message); }
    finally { setSaving(false); }
  };

  if (done && !editing) {
    return (
      <div className="grid grid-cols-[2.5rem_2rem_1fr_1fr_2rem] gap-1.5 items-center mb-1">
        <span className={`text-[0.6rem] font-bold text-center rounded px-1 py-0.5 ${groupColor.badge}`}>{exLabel}</span>
        <span className="text-sm font-semibold text-zinc-500 text-center">S{setIdx + 1}</span>
        <div className="bg-zinc-900 border border-emerald-800/50 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-emerald-400">{weight} kg</div>
        <div className="bg-zinc-900 border border-emerald-800/50 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-emerald-400">{loggedReps} reps</div>
        <button onClick={() => setEditing(true)} className="flex items-center justify-center text-zinc-600 active:text-zinc-300 cursor-pointer p-1"><Pencil size={12} /></button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[2.5rem_2rem_1fr_1fr_2rem] gap-1.5 items-center mb-1">
      <span className={`text-[0.6rem] font-bold text-center rounded px-1 py-0.5 ${groupColor.badge}`}>{exLabel}</span>
      <span className="text-sm font-semibold text-zinc-500 text-center">S{setIdx + 1}</span>
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-sky-400">{weight} kg</div>
      <input
        ref={(el) => { inputRef = el; }}
        type="number" inputMode="numeric"
        defaultValue={editing ? loggedReps : undefined}
        placeholder={targetReps != null ? String(targetReps) : 'reps'}
        min={0} max={99}
        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-[0.95rem] text-zinc-200 placeholder-zinc-600 placeholder:text-xs focus:outline-none focus:border-sky-400 appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      {saving ? (
        <div className="flex items-center justify-center"><Loader2 size={12} className="animate-spin text-zinc-500" /></div>
      ) : (
        <button onClick={editing ? handleEdit : handleLog} className="flex items-center justify-center rounded-lg bg-emerald-400 text-black cursor-pointer active:opacity-70 p-1"><Check size={12} strokeWidth={3} /></button>
      )}
    </div>
  );
}

export default function SupersetCard({ exercises, week, day, onError, showToast }) {
  const group = exercises[0]?.superset_group ?? 'A';
  const groupColor = SUPERSET_COLORS[group] ?? SUPERSET_COLORS.A;
  const maxSets = Math.max(...exercises.map((ex) => ex.target_weights?.length ?? ex.sets ?? 0));
  const allComplete = exercises.every((ex) => ex.all_logged);
  const labels = exercises.map((_, i) => `${group}${i + 1}`);

  return (
    <div className={`mx-3 my-2 bg-zinc-950 rounded-xl border overflow-hidden ${allComplete ? 'border-emerald-800/50' : `border-zinc-800 border-l-4 ${groupColor.border}`}`}>
      {/* Header */}
      <div className="px-4 pt-3 pb-1 space-y-1">
        {exercises.map((ex, i) => (
          <div key={ex.exercise_id ?? ex.exercise} className="flex items-center gap-2">
            <span className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide shrink-0 ${groupColor.badge}`}>{labels[i]}</span>
            <span className="text-sm font-bold leading-snug truncate">{ex.exercise}</span>
            {ex.all_logged && <Check size={12} className="text-emerald-400" strokeWidth={3} />}
          </div>
        ))}
      </div>

      {/* Meta */}
      <div className="flex gap-3 px-4 pb-2 text-xs text-zinc-500">
        <span>{maxSets} sets each</span>
        <span>{exercises.map((ex, i) => `${labels[i]}: ${ex.target_reps} reps`).join(' · ')}</span>
      </div>

      {/* Interleaved sets */}
      <div className="px-2.5 pb-2.5">
        {Array.from({ length: maxSets }, (_, setIdx) => (
          <div key={setIdx} className="mb-2">
            <div className="flex items-center gap-2 px-1 mb-1">
              <span className="text-[0.6rem] font-bold text-zinc-500 uppercase tracking-widest">Set {setIdx + 1}</span>
              <div className="flex-1 h-px bg-zinc-800" />
            </div>
            {exercises.map((ex, exIdx) => {
              const weights = ex.target_weights ?? [];
              if (setIdx >= weights.length) return null;
              const setsDataArr = ex.sets_data ?? [];
              return (
                <SupersetSetRow
                  key={ex.exercise_id ?? ex.exercise}
                  exLabel={labels[exIdx]}
                  setIdx={setIdx}
                  weight={weights[setIdx]}
                  targetReps={ex.target_reps}
                  setData={setsDataArr[setIdx]}
                  weekId={week}
                  day={day}
                  exerciseId={ex.exercise_id}
                  groupColor={groupColor}
                  onSetLogged={() => showToast?.(`${labels[exIdx]} S${setIdx + 1} logged`)}
                  onError={onError}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
