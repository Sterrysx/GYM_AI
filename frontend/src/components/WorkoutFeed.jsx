/**
 * Renders the list of exercises for the selected day.
 * - periodized_bench  → BenchCard
 * - static            → grouped into AbsAccordion
 * - superset_group    → grouped via SupersetCard
 * - everything else   → ExerciseCard
 *
 * All cards now receive per-set logged data from the backend.
 */
import { useState } from 'react';
import ExerciseCard from './ExerciseCard';
import BenchCard from './BenchCard';
import AbsAccordion from './AbsAccordion';
import SupersetCard from './SupersetCard';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { completeDay } from '../api/client';

export default function WorkoutFeed({ exercises, week, day, loading, error, onError, showToast, onDayCompleted }) {
  const [completing, setCompleting] = useState(false);

  const allExercisesLogged = exercises
    .filter((ex) => ex.strategy !== 'static')
    .every((ex) => ex.all_logged);

  const handleCompleteDay = async () => {
    setCompleting(true);
    try {
      await completeDay(week, day);
      showToast(`Day ${day} completed!`);
      onDayCompleted?.();
    } catch (err) {
      showToast(err.response?.data?.detail ?? err.message, true);
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" />
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 text-red-400 text-sm px-4">{error}</div>
    );
  }

  if (!day) {
    return (
      <div className="text-center py-16 text-zinc-500 text-sm">
        Select a day to load your workout.
      </div>
    );
  }

  if (exercises.length === 0) {
    return (
      <div className="text-center py-16 text-zinc-500 text-sm">
        No exercises for this day.
      </div>
    );
  }

  const staticExercises = exercises.filter((ex) => ex.strategy === 'static');
  const mainExercises = exercises.filter((ex) => ex.strategy !== 'static');

  const rendered = [];
  const supersetSeen = new Set();

  mainExercises.forEach((ex, idx) => {
    // Bench press
    if (ex.strategy === 'periodized_bench') {
      rendered.push(
        <BenchCard
          key={`bench-${idx}`}
          exercise={ex}
          week={week}
          day={day}
          onLogged={(msg) => showToast(msg)}
          onError={(msg) => showToast(msg, true)}
          onReload={onDayCompleted}
        />,
      );
      return;
    }

    // Superset group
    const sg = ex.superset_group;
    if (sg && sg !== 'Abs' && !supersetSeen.has(sg)) {
      supersetSeen.add(sg);
      const groupExercises = mainExercises.filter((e) => e.superset_group === sg);
      if (groupExercises.length >= 2) {
        rendered.push(
          <SupersetCard
            key={`ss-${sg}`}
            exercises={groupExercises}
            week={week}
            day={day}
            onError={(msg) => showToast(msg, true)}
            showToast={showToast}
            onReload={onDayCompleted}
          />,
        );
        return;
      }
    }

    if (sg && sg !== 'Abs' && supersetSeen.has(sg)) return;

    // Normal exercise
    rendered.push(
      <ExerciseCard
        key={`${ex.exercise_id ?? ex.exercise}-${idx}`}
        exercise={ex}
        week={week}
        day={day}
        onError={(msg) => showToast(msg, true)}
        showToast={showToast}
        onReload={onDayCompleted}
      />,
    );
  });

  return (
    <div className="pt-3 pb-24 space-y-0">
      {rendered}
      {staticExercises.length > 0 && (
        <AbsAccordion
          exercises={staticExercises}
          week={week}
          day={day}
          showToast={showToast}
          onReload={onDayCompleted}
        />
      )}

      {/* ── Complete Day button ── */}
      {exercises.length > 0 && (
        <div className="px-3 pt-6 pb-4">
          <button
            onClick={handleCompleteDay}
            disabled={completing || allExercisesLogged}
            className={`w-full py-3.5 rounded-xl font-bold text-sm uppercase tracking-wide flex items-center justify-center gap-2 transition-all cursor-pointer disabled:cursor-not-allowed ${
              allExercisesLogged
                ? 'bg-emerald-900/30 border border-emerald-800/50 text-emerald-400'
                : 'bg-sky-500 text-black active:bg-sky-400 disabled:opacity-50'
            }`}
          >
            {completing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <CheckCircle2 size={16} />
            )}
            {allExercisesLogged
              ? `Day ${day} Complete ✓`
              : completing
                ? 'Completing…'
                : `Complete Day ${day}`}
          </button>
          {!allExercisesLogged && (
            <p className="text-center text-[0.6rem] text-zinc-600 mt-1.5">
              Unlogged sets will be marked as 0
            </p>
          )}
        </div>
      )}
    </div>
  );
}
