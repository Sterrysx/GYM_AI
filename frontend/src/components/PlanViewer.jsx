import { useState, useEffect, useCallback } from 'react';
import { Loader2, ChevronLeft, ChevronRight, Dumbbell } from 'lucide-react';
import { fetchPlan } from '../api/client';
import { SUPERSET_COLORS, DAY_NAMES } from '../lib/constants';

/**
 * Read-only plan viewer — browse any week's exercises, sets, weights.
 * Week switcher at the top; exercises grouped by day in accordions.
 */
export default function PlanViewer() {
  const [weeks, setWeeks]       = useState([]);
  const [weekId, setWeekId]     = useState(null);
  const [days, setDays]         = useState({});
  const [loading, setLoading]   = useState(true);
  const [openDay, setOpenDay]   = useState(null);  // which day accordion is open

  const load = useCallback(async (wk = null) => {
    setLoading(true);
    try {
      const res = await fetchPlan(wk);
      setWeeks(res.weeks);
      setWeekId(res.current_week);
      setDays(res.days);
      // Auto-open first day
      const firstDay = Object.keys(res.days).sort((a, b) => a - b)[0];
      setOpenDay(firstDay ? Number(firstDay) : null);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const goWeek = (dir) => {
    const idx = weeks.indexOf(weekId);
    const next = weeks[idx + dir];
    if (next != null) load(next);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" /> Loading plan…
      </div>
    );
  }

  if (weeks.length === 0) {
    return <div className="text-center py-24 text-zinc-500 text-sm">No plans found.</div>;
  }

  const sortedDays = Object.values(days).sort((a, b) => a.day - b.day);
  const weekIdx = weeks.indexOf(weekId);
  const canPrev = weekIdx > 0;
  const canNext = weekIdx < weeks.length - 1;

  return (
    <div className="px-3 pt-4 pb-16 space-y-3 overflow-x-hidden">
      {/* ── Week Switcher ── */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={() => goWeek(-1)}
          disabled={!canPrev}
          className="p-2 rounded-lg text-zinc-400 active:bg-zinc-800 cursor-pointer disabled:opacity-25 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={20} />
        </button>
        <span className="text-sm font-bold uppercase tracking-widest text-zinc-300">
          Week {weekId}
        </span>
        <button
          onClick={() => goWeek(1)}
          disabled={!canNext}
          className="p-2 rounded-lg text-zinc-400 active:bg-zinc-800 cursor-pointer disabled:opacity-25 disabled:cursor-not-allowed"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* week dots */}
      <div className="flex justify-center gap-1.5 pb-1">
        {weeks.map((w) => (
          <button
            key={w}
            onClick={() => load(w)}
            className={`w-2 h-2 rounded-full cursor-pointer transition-all ${
              w === weekId ? 'bg-sky-400 scale-125' : 'bg-zinc-700 active:bg-zinc-500'
            }`}
          />
        ))}
      </div>

      {/* ── Days ── */}
      {sortedDays.map(({ day, day_name, exercises }) => {
        const isOpen = openDay === day;
        const label = day_name || DAY_NAMES[day] || `Day ${day}`;
        return (
          <div key={day} className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
            {/* Day header — click to toggle */}
            <button
              onClick={() => setOpenDay(isOpen ? null : day)}
              className="w-full flex items-center justify-between px-4 py-3 cursor-pointer active:bg-zinc-900 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-sky-500/10 flex items-center justify-center">
                  <Dumbbell size={14} className="text-sky-400" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-bold text-zinc-200">Day {day} — {label}</p>
                  <p className="text-[0.6rem] text-zinc-500">{exercises.length} exercises</p>
                </div>
              </div>
              <ChevronRight
                size={16}
                className={`text-zinc-500 transition-transform ${isOpen ? 'rotate-90' : ''}`}
              />
            </button>

            {/* Exercise list */}
            {isOpen && (
              <div className="border-t border-zinc-800 divide-y divide-zinc-800/60">
                {exercises.map((ex, i) => {
                  const ss = ex.superset_group;
                  const ssColor = ss && SUPERSET_COLORS[ss];
                  return (
                    <div
                      key={`${ex.exercise}-${i}`}
                      className={`px-4 py-3 ${ss && ssColor ? `border-l-4 ${ssColor.border}` : ''}`}
                    >
                      {/* Name + meta */}
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-zinc-200 leading-snug">{ex.exercise}</p>
                          <div className="flex gap-2 mt-0.5 text-[0.6rem] text-zinc-500">
                            <span>{ex.sets} sets</span>
                            <span>{ex.target_reps} reps</span>
                            {ex.strategy && ex.strategy !== 'linear' && (
                              <span className="text-zinc-600">{ex.strategy}</span>
                            )}
                          </div>
                        </div>
                        {ss && ssColor && (
                          <span className={`text-[0.55rem] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide shrink-0 ${ssColor.badge}`}>
                            SS-{ss}
                          </span>
                        )}
                      </div>

                      {/* Set-by-set weight table */}
                      <div className="grid grid-cols-[2.5rem_1fr] gap-x-2 gap-y-1">
                        {ex.weights.map((w, si) => (
                          <div key={si} className="contents">
                            <span className="text-[0.65rem] font-semibold text-zinc-500 text-center leading-6">
                              S{si + 1}
                            </span>
                            <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm font-semibold text-sky-400">
                              {w} kg
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
