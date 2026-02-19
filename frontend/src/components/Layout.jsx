import { useState } from 'react';
import { Sparkles, Loader2, BarChart2, Dumbbell } from 'lucide-react';
import DaySelector from './DaySelector';
import { generateNextWeek } from '../api/client';

/**
 * Sticky header with:
 * - Title + week badge
 * - Generate Next Week button
 * - Tab navigation: Dashboard | Workout
 * - Day selector (visible only on Workout tab)
 */
export default function Layout({ week, activeDay, onSelectDay, onGenerated, showToast, activeView, onViewChange, children }) {
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateNextWeek();
      showToast('Next week generated!');
      onGenerated();
    } catch (err) {
      showToast(err.response?.data?.detail ?? err.message, true);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-dvh bg-black text-zinc-200 font-sans">
      {/* ── Sticky Header ── */}
      <header className="sticky top-0 z-10 bg-black border-b border-zinc-800 px-4 py-3">
        {/* Title row */}
        <div className="flex items-center justify-between mb-2.5">
          <h1 className="text-sm font-semibold uppercase tracking-widest text-zinc-500">
            Zero-Idle Gym{' '}
            {week && (
              <span className="text-sky-400 font-normal text-xs">Week {week}</span>
            )}
          </h1>

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-sky-400 text-sky-400 text-xs font-bold uppercase tracking-wide transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed active:bg-sky-400 active:text-black"
          >
            {generating ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
            {generating ? 'Generating…' : 'Next Week'}
          </button>
        </div>

        {/* Tab navigation */}
        <div className="flex gap-1 mb-2.5">
          <button
            onClick={() => onViewChange('stats')}
            className={`flex items-center gap-1.5 flex-1 justify-center py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeView === 'stats'
                ? 'bg-zinc-800 text-zinc-200'
                : 'text-zinc-500 active:bg-zinc-900'
            }`}
          >
            <BarChart2 size={14} />
            Dashboard
          </button>
          <button
            onClick={() => onViewChange('workout')}
            className={`flex items-center gap-1.5 flex-1 justify-center py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeView === 'workout'
                ? 'bg-zinc-800 text-zinc-200'
                : 'text-zinc-500 active:bg-zinc-900'
            }`}
          >
            <Dumbbell size={14} />
            Workout
          </button>
        </div>

        {/* Day selector — only on Workout tab */}
        {activeView === 'workout' && (
          <DaySelector activeDay={activeDay} onSelect={onSelectDay} />
        )}
      </header>

      {/* ── Main Content ── */}
      <main>{children}</main>
    </div>
  );
}
