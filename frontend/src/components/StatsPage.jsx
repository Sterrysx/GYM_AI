import { Dumbbell, Calendar, TrendingUp, Loader2, RefreshCw } from 'lucide-react';
import { useStats } from '../hooks/useStats';

/** Cycle week progress dots */
function CycleProgress({ current }) {
  const labels = ['5×5', '4×4', '3×3', '2×2', 'Deload', 'PR'];
  return (
    <div className="flex items-center gap-1.5 mt-3">
      {labels.map((label, i) => {
        const week = i + 1;
        const isActive = week === current;
        const isDone = week < current;
        return (
          <div key={week} className="flex flex-col items-center gap-1 flex-1">
            <div
              className={`w-full h-1.5 rounded-full transition-all ${
                isActive
                  ? 'bg-sky-400'
                  : isDone
                  ? 'bg-emerald-500'
                  : 'bg-zinc-800'
              }`}
            />
            <span
              className={`text-[0.55rem] font-semibold uppercase tracking-wide ${
                isActive ? 'text-sky-400' : isDone ? 'text-emerald-500' : 'text-zinc-700'
              }`}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** Single day completion bar */
function DayBar({ day }) {
  const pct = day.planned > 0 ? Math.round((day.logged / day.planned) * 100) : 0;
  const done = day.logged >= day.planned && day.planned > 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-zinc-500 w-20 shrink-0">
        D{day.day} {day.name}
      </span>
      <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all ${done ? 'bg-emerald-400' : 'bg-sky-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-semibold w-14 text-right shrink-0 ${done ? 'text-emerald-400' : 'text-zinc-400'}`}>
        {day.logged}/{day.planned}
      </span>
    </div>
  );
}

export default function StatsPage() {
  const { stats, loading, error, refresh } = useStats();

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" />
        Loading stats…
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-24 text-red-400 text-sm px-6">{error}</div>
    );
  }

  // Safe defaults for every field so we never crash on undefined
  const currentWeek = stats.current_week ?? 1;
  const benchCycleWeek = stats.bench_cycle_week ?? 1;
  const benchRm = stats.bench_1rm ?? 90;
  const bench = stats.bench_session ?? {};
  const days = Array.isArray(stats.day_completion) ? stats.day_completion : [];

  const benchSets = bench.sets ?? '-';
  const benchReps = bench.reps ?? '-';
  const benchWeight = bench.weight ?? '-';
  const benchIntensity = bench.intensity_pct ?? '-';
  const benchLabel = bench.label ?? '-';

  const totalPlanned = days.reduce((a, d) => a + (d.planned ?? 0), 0);
  const totalLogged = days.reduce((a, d) => a + (d.logged ?? 0), 0);
  const weekPct = totalPlanned > 0 ? Math.round((totalLogged / totalPlanned) * 100) : 0;

  return (
    <div className="px-3 pt-4 pb-10 space-y-3">
      {/* ── Week hero ── */}
      <div className="flex items-center justify-between bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sky-400/10 flex items-center justify-center">
            <Calendar size={20} className="text-sky-400" />
          </div>
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-widest">Current Week</p>
            <p className="text-2xl font-black text-sky-400">Week {currentWeek}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-zinc-500">Week done</p>
          <p className={`text-xl font-black ${weekPct === 100 ? 'text-emerald-400' : 'text-zinc-300'}`}>
            {weekPct}%
          </p>
        </div>
      </div>

      {/* ── Bench Press Cycle ── */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 mb-1">
          <Dumbbell size={15} className="text-sky-400" />
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
            Bench Press Cycle
          </span>
        </div>

        {/* This session */}
        <div className="flex items-center gap-3 mt-2">
          <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5">
            <span className="text-xl font-black text-sky-400 leading-none">
              {benchSets}×{benchReps}
            </span>
            <span className="text-[0.55rem] text-zinc-500 uppercase tracking-widest mt-0.5">
              sets × reps
            </span>
          </div>
          <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5">
            <span className="text-xl font-black text-emerald-400 leading-none">
              {benchWeight} kg
            </span>
            <span className="text-[0.55rem] text-zinc-500 uppercase tracking-widest mt-0.5">
              {benchIntensity}% 1RM
            </span>
          </div>
          <div className="flex flex-col items-center bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5 flex-1">
            <span className="text-base font-black text-amber-400 leading-none">
              {benchLabel}
            </span>
            <span className="text-[0.55rem] text-zinc-500 uppercase tracking-widest mt-0.5">
              phase
            </span>
          </div>
        </div>

        <CycleProgress current={benchCycleWeek} />

        <p className="text-[0.65rem] text-zinc-600 mt-2">1RM baseline: {benchRm} kg</p>
      </div>

      {/* ── Weekly Completion ── */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp size={15} className="text-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
            Week {currentWeek} Completion
          </span>
        </div>
        <div className="space-y-2.5">
          {days.map((d) => (
            <DayBar key={d.day} day={d} />
          ))}
        </div>
        <div className="mt-3 pt-2.5 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
          <span>Total: {totalLogged}/{totalPlanned} exercises</span>
          <button
            onClick={refresh}
            className="flex items-center gap-1 text-sky-400 cursor-pointer active:opacity-60"
          >
            <RefreshCw size={11} />
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
