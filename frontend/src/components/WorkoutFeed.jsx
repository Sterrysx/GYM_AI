/**
 * Renders the list of exercises for the selected day.
 * - periodized_bench  → BenchCard (no reps input, auto-log)
 * - static            → grouped into a single AbsAccordion
 * - everything else   → ExerciseCard
 */
import ExerciseCard from './ExerciseCard';
import BenchCard from './BenchCard';
import AbsAccordion from './AbsAccordion';
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

  return (
    <div className="pb-6">
      {mainExercises.map((ex, idx) =>
        ex.strategy === 'periodized_bench' ? (
          <BenchCard
            key={`bench-${idx}`}
            exercise={ex}
            week={week}
            day={day}
            onLogged={(msg) => showToast(msg)}
            onError={(msg) => showToast(msg, true)}
          />
        ) : (
          <ExerciseCard
            key={`${ex.exercise}-${idx}`}
            exercise={ex}
            week={week}
            day={day}
            onLog={onLog}
            onError={onError}
          />
        ),
      )}

      {staticExercises.length > 0 && (
        <AbsAccordion exercises={staticExercises} />
      )}
    </div>
  );
}
