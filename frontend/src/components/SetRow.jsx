/**
 * Single set row — read-only weight display + reps input.
 * Uses uncontrolled ref for zero re-render keystrokes.
 */
import { forwardRef } from 'react';

const SetRow = forwardRef(function SetRow({ index, weight, targetReps }, ref) {
  return (
    <div className="grid grid-cols-[3.2rem_1fr_1fr] gap-1.5 items-center mb-1">
      {/* Set label */}
      <span className="text-sm font-semibold text-zinc-500 text-center">
        S{index + 1}
      </span>

      {/* Target weight (read-only) */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-sm font-semibold text-sky-400">
        {weight} kg
      </div>

      {/* Reps input */}
      <input
        ref={ref}
        type="number"
        inputMode="numeric"
        placeholder={targetReps != null ? String(targetReps) : 'reps'}
        min={0}
        max={99}
        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-2 text-center text-[0.95rem] text-zinc-200 placeholder-zinc-600 placeholder:text-xs focus:outline-none focus:border-sky-400 appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      />
    </div>
  );
});

export default SetRow;
