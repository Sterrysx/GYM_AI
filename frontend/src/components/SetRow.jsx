/**
 * SetRow — renders a single set with weight, reps input, and per-set log button.
 * Supports: log individual set, show already-logged state, edit logged values.
 */
import { useState, forwardRef, useImperativeHandle, useRef } from 'react';
import { Check, Loader2, Pencil } from 'lucide-react';
import { logSet, editSet } from '../api/client';

const SetRow = forwardRef(function SetRow(
  { index, weight, targetReps, setData, weekId, day, exerciseId, onSetLogged, onError },
  ref
) {
  const inputRef = useRef(null);
  const isLogged = setData?.logged ?? false;
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loggedReps, setLoggedReps] = useState(setData?.actual_reps);
  const [loggedWeight, setLoggedWeight] = useState(setData?.actual_weight);
  const [done, setDone] = useState(isLogged);

  useImperativeHandle(ref, () => inputRef.current);

  const handleLogSet = async () => {
    const val = inputRef.current?.value?.trim();
    if (!val || val === '') {
      if (onError) onError('Enter reps before logging.');
      if (inputRef.current) inputRef.current.style.borderColor = '#f55';
      return;
    }
    if (inputRef.current) inputRef.current.style.borderColor = '';
    setSaving(true);
    try {
      await logSet({
        week_id: weekId,
        day,
        exercise_id: exerciseId,
        set_number: index + 1,
        actual_weight: weight,
        actual_reps: parseInt(val, 10),
      });
      setLoggedReps(parseInt(val, 10));
      setLoggedWeight(weight);
      setDone(true);
      setEditing(false);
      onSetLogged?.();
    } catch (err) {
      onError?.(err.response?.data?.detail ?? err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async () => {
    const val = inputRef.current?.value?.trim();
    if (!val || val === '') return;
    setSaving(true);
    try {
      await editSet({
        week_id: weekId,
        day,
        exercise_id: exerciseId,
        set_number: index + 1,
        actual_weight: weight,
        actual_reps: parseInt(val, 10),
      });
      setLoggedReps(parseInt(val, 10));
      setDone(true);
      setEditing(false);
      onSetLogged?.();
    } catch (err) {
      onError?.(err.response?.data?.detail ?? err.message);
    } finally {
      setSaving(false);
    }
  };

  // Already logged and not editing — show completed state
  if (done && !editing) {
    return (
      <div className="grid grid-cols-[3.2rem_1fr_1fr_2.5rem] gap-1.5 items-center mb-1">
        <span className="text-sm font-semibold text-zinc-500 text-center">S{index + 1}</span>
        <div className="bg-zinc-900 border border-emerald-800/50 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-emerald-400">
          {loggedWeight ?? weight} kg
        </div>
        <div className="bg-zinc-900 border border-emerald-800/50 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-emerald-400">
          {loggedReps} reps
        </div>
        <button
          onClick={() => setEditing(true)}
          className="flex items-center justify-center text-zinc-600 active:text-zinc-300 cursor-pointer p-1"
          title="Edit this set"
        >
          <Pencil size={14} />
        </button>
      </div>
    );
  }

  // Input mode (not yet logged, or editing)
  return (
    <div className="grid grid-cols-[3.2rem_1fr_1fr_2.5rem] gap-1.5 items-center mb-1">
      <span className="text-sm font-semibold text-zinc-500 text-center">S{index + 1}</span>
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-sky-400">
        {weight} kg
      </div>
      <input
        ref={inputRef}
        type="number"
        inputMode="numeric"
        defaultValue={editing ? loggedReps : undefined}
        placeholder={targetReps != null ? String(targetReps) : 'reps'}
        min={0}
        max={99}
        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-[0.95rem] text-zinc-200 placeholder-zinc-600 placeholder:text-xs focus:outline-none focus:border-sky-400 appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      {saving ? (
        <div className="flex items-center justify-center">
          <Loader2 size={14} className="animate-spin text-zinc-500" />
        </div>
      ) : (
        <button
          onClick={editing ? handleEdit : handleLogSet}
          className="flex items-center justify-center rounded-lg bg-emerald-400 text-black cursor-pointer active:opacity-70 p-1.5"
          title={editing ? 'Save edit' : 'Log this set'}
        >
          <Check size={14} strokeWidth={3} />
        </button>
      )}
    </div>
  );
});

export default SetRow;
