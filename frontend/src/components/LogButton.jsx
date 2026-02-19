import { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';

/**
 * Log button with three visual states: idle → saving → logged.
 */
export default function LogButton({ exerciseName, onLog }) {
  const [state, setState] = useState('idle'); // idle | saving | logged

  const handleClick = async () => {
    if (state !== 'idle') return;
    setState('saving');

    try {
      await onLog();
      setState('logged');
    } catch {
      setState('idle');
    }
  };

  const baseClasses =
    'w-full rounded-xl py-3 text-[0.95rem] font-bold transition-all cursor-pointer flex items-center justify-center gap-2';

  if (state === 'logged') {
    return (
      <button disabled className={`${baseClasses} bg-zinc-900 text-emerald-400 border border-emerald-400`}>
        <Check size={16} strokeWidth={3} />
        Logged
      </button>
    );
  }

  if (state === 'saving') {
    return (
      <button disabled className={`${baseClasses} bg-zinc-800 text-zinc-500 cursor-not-allowed`}>
        <Loader2 size={16} className="animate-spin" />
        Saving…
      </button>
    );
  }

  return (
    <button onClick={handleClick} className={`${baseClasses} bg-emerald-400 text-black active:opacity-70`}>
      Log {exerciseName}
    </button>
  );
}
