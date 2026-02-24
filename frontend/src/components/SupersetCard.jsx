/**
 * SupersetCard — interleaved superset exercises with per-set logging.
 * Each set group has a shared "Log Set X" button that logs all exercises at once.
 * Individual exercises can still be logged one at a time.
 */
import { useState, useRef, useCallback } from 'react';
import { Check, Loader2, Pencil, CheckCircle2 } from 'lucide-react';
import { logSet, editSet, completeExercise } from '../api/client';
import { SUPERSET_COLORS } from '../lib/constants';

/** Single exercise row within a superset set — exposes its input ref via registerRef */
function SupersetSetRow({ exLabel, setIdx, weight, targetReps, setData, weekId, day, exerciseId, groupColor, onSetLogged, onError, registerRef }) {
  const isLogged = setData?.logged ?? false;
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loggedReps, setLoggedReps] = useState(setData?.actual_reps);
  const [done, setDone] = useState(isLogged);
  const localRef = useRef(null);

  // Expose ref for parent "Log Set" button
  const refCb = useCallback((el) => {
    localRef.current = el;
    registerRef?.(el);
  }, [registerRef]);

  // Mark as done externally (called by parent batch-log)
  const markDone = (reps) => { setLoggedReps(reps); setDone(true); setEditing(false); };

  const handleLog = async () => {
    const val = localRef.current?.value?.trim();
    if (!val) { onError?.('Enter reps'); if (localRef.current) localRef.current.style.borderColor = '#f55'; return; }
    if (localRef.current) localRef.current.style.borderColor = '';
    setSaving(true);
    try {
      await logSet({ week_id: weekId, day, exercise_id: exerciseId, set_number: setIdx + 1, actual_weight: weight, actual_reps: parseInt(val, 10) });
      markDone(parseInt(val, 10));
      onSetLogged?.();
    } catch (err) { onError?.(err.response?.data?.detail ?? err.message); }
    finally { setSaving(false); }
  };

  const handleEdit = async () => {
    const val = localRef.current?.value?.trim();
    if (!val) return;
    setSaving(true);
    try {
      await editSet({ week_id: weekId, day, exercise_id: exerciseId, set_number: setIdx + 1, actual_weight: weight, actual_reps: parseInt(val, 10) });
      markDone(parseInt(val, 10));
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
        ref={refCb}
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

export default function SupersetCard({ exercises, week, day, onError, showToast, onReload }) {
  const group = exercises[0]?.superset_group ?? 'A';
  const groupColor = SUPERSET_COLORS[group] ?? SUPERSET_COLORS.A;
  const maxSets = Math.max(...exercises.map((ex) => ex.target_weights?.length ?? ex.sets ?? 0));
  const labels = exercises.map((_, i) => `${group}${i + 1}`);
  const [completing, setCompleting] = useState(false);

  // Track locally-logged sets so we don't reload after each individual log
  const [locallyLogged, setLocallyLogged] = useState(0);
  const initiallyLogged = exercises.reduce(
    (sum, ex) => sum + (ex.sets_data?.filter((s) => s?.logged).length ?? 0), 0,
  );
  const totalSets = exercises.reduce(
    (sum, ex) => sum + (ex.target_weights?.length ?? ex.sets ?? 0), 0,
  );
  const allComplete = exercises.every((ex) => ex.all_logged) || (initiallyLogged + locallyLogged) >= totalSets;
  const hasUnlogged = !allComplete;

  // Refs for all inputs: inputRefs[setIdx][exIdx] = DOM element
  const inputRefs = useRef({});
  const setRowRefs = useRef({});

  const registerRef = (setIdx, exIdx, el) => {
    if (!inputRefs.current[setIdx]) inputRefs.current[setIdx] = {};
    inputRefs.current[setIdx][exIdx] = el;
  };

  const registerRowRef = (setIdx, exIdx, el) => {
    if (!setRowRefs.current[setIdx]) setRowRefs.current[setIdx] = {};
    setRowRefs.current[setIdx][exIdx] = el;
  };

  // Track which sets have been batch-logged
  const [batchLogged, setBatchLogged] = useState(new Set());
  const [batchSaving, setBatchSaving] = useState(null);

  const handleBatchLog = async (setIdx) => {
    const refs = inputRefs.current[setIdx] ?? {};
    const entries = [];
    let hasError = false;

    // Collect values from all exercise inputs for this set
    exercises.forEach((ex, exIdx) => {
      const weights = ex.target_weights ?? [];
      if (setIdx >= weights.length) return;
      const sData = ex.sets_data?.[setIdx];
      if (sData?.logged) return; // Already logged from server

      const el = refs[exIdx];
      if (!el) return;
      const val = el.value?.trim();
      if (!val) {
        el.style.borderColor = '#f55';
        hasError = true;
        return;
      }
      el.style.borderColor = '';
      entries.push({ ex, exIdx, weight: weights[setIdx], reps: parseInt(val, 10) });
    });

    if (hasError) { onError?.('Enter reps for all exercises'); return; }
    if (entries.length === 0) return;

    setBatchSaving(setIdx);
    try {
      await Promise.all(entries.map(({ ex, weight, reps }) =>
        logSet({ week_id: week, day, exercise_id: ex.exercise_id, set_number: setIdx + 1, actual_weight: weight, actual_reps: reps })
      ));
      setLocallyLogged((n) => n + entries.length);
      setBatchLogged((prev) => new Set([...prev, setIdx]));
      showToast?.(`Set ${setIdx + 1} logged for all exercises`);
      // Refresh data so child rows switch to "done" state
      onReload?.();
    } catch (err) {
      onError?.(err.response?.data?.detail ?? err.message);
    } finally {
      setBatchSaving(null);
    }
  };

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const ids = exercises.map((ex) => ex.exercise_id);
      await completeExercise(week, day, ids);
      showToast?.(`Superset ${group} completed`);
      onReload?.();
    } catch (err) {
      onError?.(err.response?.data?.detail ?? err.message);
    } finally {
      setCompleting(false);
    }
  };

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
        {Array.from({ length: maxSets }, (_, setIdx) => {
          // Check if all exercises in this set are already logged
          const allInSetLogged = exercises.every((ex) => {
            const weights = ex.target_weights ?? [];
            if (setIdx >= weights.length) return true;
            return ex.sets_data?.[setIdx]?.logged;
          }) || batchLogged.has(setIdx);

          // Count how many exercises in this set still need logging
          const unloggedCount = exercises.filter((ex) => {
            const weights = ex.target_weights ?? [];
            if (setIdx >= weights.length) return false;
            return !ex.sets_data?.[setIdx]?.logged;
          }).length;

          return (
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
                    onSetLogged={() => {
                      setLocallyLogged((n) => n + 1);
                      showToast?.(`${labels[exIdx]} S${setIdx + 1} logged`);
                    }}
                    onError={onError}
                    registerRef={(el) => registerRef(setIdx, exIdx, el)}
                  />
                );
              })}

              {/* Batch log button for this set — logs all exercises at once */}
              {!allInSetLogged && unloggedCount >= 2 && (
                <button
                  onClick={() => handleBatchLog(setIdx)}
                  disabled={batchSaving === setIdx}
                  className="w-full mt-1 py-1.5 rounded-lg text-[0.65rem] font-semibold uppercase tracking-wide bg-sky-500/10 border border-sky-500/30 text-sky-400 active:bg-sky-500/20 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
                >
                  {batchSaving === setIdx ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <Check size={11} strokeWidth={3} />
                  )}
                  {batchSaving === setIdx ? 'Logging…' : `Log Set ${setIdx + 1} (all exercises)`}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Complete superset button */}
      {hasUnlogged && (
        <div className="px-3 pb-2.5">
          <button
            onClick={handleComplete}
            disabled={completing}
            className="w-full py-2 rounded-lg text-[0.7rem] font-semibold uppercase tracking-wide border border-zinc-700 text-zinc-400 active:bg-zinc-800 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
          >
            {completing ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
            {completing ? 'Completing…' : `Complete Superset ${group}`}
          </button>
        </div>
      )}

      {/* All done indicator */}
      {allComplete && (
        <div className="px-3 pb-2.5">
          <div className="w-full py-2 rounded-lg text-[0.7rem] font-semibold uppercase tracking-wide text-emerald-400 flex items-center justify-center gap-1.5">
            <CheckCircle2 size={12} /> Superset {group} Complete
          </div>
        </div>
      )}
    </div>
  );
}
