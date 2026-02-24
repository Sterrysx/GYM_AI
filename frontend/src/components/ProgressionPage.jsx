/**
 * ProgressionPage — Strength progression tracking for every exercise.
 * Shows: total reps, total weight, avg weight/rep, per-session history.
 */
import { useState, useEffect } from 'react';
import { TrendingUp, ChevronDown, ChevronUp, Loader2, Dumbbell } from 'lucide-react';
import { fetchAllProgressions, fetchProgression } from '../api/client';

function StatBadge({ label, value, unit }) {
  return (
    <div className="flex flex-col items-center px-2">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-bold text-zinc-200">
        {value}
        {unit && <span className="text-xs font-normal text-zinc-500 ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

function ExerciseRow({ exercise }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const handleToggle = async () => {
    if (!expanded && !detail) {
      setLoadingDetail(true);
      try {
        const data = await fetchProgression(exercise.exercise_id);
        setDetail(data);
      } catch {
        /* ignore */
      } finally {
        setLoadingDetail(false);
      }
    }
    setExpanded(!expanded);
  };

  const weightDelta =
    exercise.latest_weight != null && exercise.first_weight != null
      ? exercise.latest_weight - exercise.first_weight
      : null;

  return (
    <div className="border border-zinc-800 rounded-xl overflow-hidden bg-zinc-950 mx-3 my-1.5">
      {/* Summary row */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-4 py-3 cursor-pointer active:bg-zinc-900 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Dumbbell size={14} className="text-zinc-500 shrink-0" />
          <span className="text-sm font-semibold truncate">{exercise.exercise_name}</span>
          {weightDelta != null && weightDelta !== 0 && (
            <span
              className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                weightDelta > 0
                  ? 'bg-emerald-900/40 text-emerald-400'
                  : 'bg-red-900/40 text-red-400'
              }`}
            >
              {weightDelta > 0 ? '+' : ''}
              {weightDelta}kg
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <StatBadge label="Sets" value={exercise.total_sets} />
          <StatBadge label="Reps" value={exercise.total_reps} />
          <StatBadge label="Avg" value={exercise.avg_weight} unit="kg" />
          {expanded ? (
            <ChevronUp size={14} className="text-zinc-500" />
          ) : (
            <ChevronDown size={14} className="text-zinc-500" />
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-zinc-800 px-4 py-3">
          {loadingDetail ? (
            <div className="flex items-center justify-center py-4 text-zinc-500">
              <Loader2 size={16} className="animate-spin mr-2" />
              Loading…
            </div>
          ) : detail?.history?.length > 0 ? (
            <div className="space-y-3">
              {/* Global summary */}
              {detail.summary && (
                <div className="flex gap-4 pb-2 border-b border-zinc-800 text-xs text-zinc-400">
                  <span>
                    Total Volume:{' '}
                    <span className="text-zinc-200 font-semibold">
                      {detail.summary.total_volume_kg.toLocaleString()}kg
                    </span>
                  </span>
                  <span>
                    Max:{' '}
                    <span className="text-zinc-200 font-semibold">
                      {detail.summary.max_weight}kg
                    </span>
                  </span>
                  <span>
                    Sessions:{' '}
                    <span className="text-zinc-200 font-semibold">
                      {detail.summary.total_sessions}
                    </span>
                  </span>
                </div>
              )}

              {/* Per-session rows */}
              {detail.history.map((session, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>
                      Week {session.week_id} · Day {session.day}
                    </span>
                    <span>
                      {session.total_reps} reps · {session.avg_weight_per_rep}kg avg
                    </span>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {session.sets.map((s, j) => (
                      <div
                        key={j}
                        className="flex flex-col items-center px-2 py-1 rounded bg-zinc-900 text-xs"
                      >
                        <span className="text-zinc-500 text-[0.6rem]">S{s.set_number}</span>
                        <span className="font-semibold">{s.actual_weight}kg</span>
                        <span className="text-zinc-400">{s.actual_reps} reps</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500 text-center py-2">
              No logged data yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProgressionPage() {
  const [progressions, setProgressions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchAllProgressions();
        setProgressions(data.progressions || []);
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" />
        Loading progressions…
      </div>
    );
  }

  if (progressions.length === 0) {
    return (
      <div className="text-center py-16 text-zinc-500 text-sm">
        <TrendingUp size={24} className="mx-auto mb-2 opacity-40" />
        No logged exercises yet. Start logging to see your progression!
      </div>
    );
  }

  return (
    <div className="pt-3 pb-24">
      <div className="px-4 pb-3 flex items-center gap-2">
        <TrendingUp size={16} className="text-sky-400" />
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Strength Progression
        </h2>
        <span className="text-xs text-zinc-600">({progressions.length} exercises)</span>
      </div>

      {progressions.map((ex) => (
        <ExerciseRow key={ex.exercise_id} exercise={ex} />
      ))}
    </div>
  );
}
