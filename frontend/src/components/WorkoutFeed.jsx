/**
 * Renders the list of exercises for the selected day.
 * - periodized_bench  → BenchCard (no reps input, auto-log)
 * - static            → grouped into a single AbsAccordion
 * - superset_group    → grouped & interleaved via SupersetCard
 * - everything else   → ExerciseCard
 */
import ExerciseCard from './ExerciseCard';
import BenchCard from './BenchCard';
import AbsAccordion from './AbsAccordion';
import SupersetCard from './SupersetCard';
import { Loader2 } from 'lucide-react';

export default function WorkoutFeed({ exercises, week, day, loading, error, onLog, onError, showToast }) {
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
  const mainExercises   = exercises.filter((ex) => ex.strategy !== 'static');

  // ── Group superset exercises together, preserve order ──
  const rendered = [];
  const supersetSeen = new Set();

  mainExercises.forEach((ex, idx) => {
    // Bench press — always standalone
    if (ex.strategy === 'periodized_bench') {
      rendered.push(
        <BenchCard
          key={`bench-${idx}`}
          exercise={ex}
          week={week}
          day={day}
          onLogged={(msg) => showToast(msg)}
          onError={(msg) => showToast(msg, true)}
        />,
      );
      return;
    }

    // Superset group — render all exercises in the group at once
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
            onLog={onLog}
            onError={onError}
          />,
        );
        return;
      }
      // Single exercise with a superset_group — just render normally
    }

    // Already rendered as part of a superset group
    if (sg && sg !== 'Abs' && supersetSeen.has(sg)) return;

    // Normal exercise
    rendered.push(
      <ExerciseCard
        key={`${ex.exercise}-${idx}`}
        exercise={ex}
        week={week}
        day={day}
        onLog={onLog}
        onError={onError}
      />,
    );
  });

  return (
    <div className="pb-6">
      {rendered}

      {staticExercises.length > 0 && (
        <AbsAccordion exercises={staticExercises} />
      )}
    </div>
  );
}
