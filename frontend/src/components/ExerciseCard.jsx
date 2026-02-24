/**
 * ExerciseCard — single exercise with per-set logging.
 * Shows already-logged sets as completed, allows editing.
 */
import SetRow from './SetRow';
import { SUPERSET_COLORS } from '../lib/constants';
import { Check } from 'lucide-react';

export default function ExerciseCard({ exercise, week, day, onError, showToast }) {
  const {
    exercise_id: exerciseId,
    exercise: name,
    target_weights: weights,
    sets,
    target_reps: targetReps,
    superset_group,
    strategy,
    equipment,
    sets_data: setsData = [],
    all_logged: allLogged = false,
  } = exercise;

  const numSets = weights?.length ?? sets ?? 0;
  const supersetBorder = superset_group
    ? SUPERSET_COLORS[superset_group]?.border ?? ''
    : '';

  return (
    <div
      className={`mx-3 my-2 bg-zinc-950 rounded-xl border overflow-hidden ${
        allLogged
          ? 'border-emerald-800/50'
          : `border-zinc-800 ${superset_group ? `border-l-4 ${supersetBorder}` : ''}`
      }`}
    >
      <div className="flex items-start justify-between px-4 pt-3 pb-1 gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold leading-snug">{name}</span>
          {allLogged && <Check size={14} className="text-emerald-400" strokeWidth={3} />}
        </div>
        <div className="flex items-center gap-1.5">
          {equipment && (
            <span className="text-[0.6rem] font-medium px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 uppercase tracking-wide">
              {equipment.replace(/_/g, ' ')}
            </span>
          )}
          {superset_group && (
            <span
              className={`text-[0.65rem] font-bold px-2 py-0.5 rounded uppercase tracking-wide shrink-0 ${
                SUPERSET_COLORS[superset_group]?.badge ?? ''
              }`}
            >
              SS-{superset_group}
            </span>
          )}
        </div>
      </div>
      <div className="flex gap-3 px-4 pb-2 text-xs text-zinc-500">
        <span>{numSets} sets</span>
        <span>{targetReps} reps</span>
        {strategy && <span>{strategy}</span>}
      </div>
      <div className="px-2.5 pb-1">
        <div className="grid grid-cols-[3.2rem_1fr_1fr_2.5rem] gap-1.5 px-1.5 pb-1 text-[0.65rem] font-semibold text-zinc-500 uppercase tracking-wide">
          <span />
          <span>Weight</span>
          <span>Reps</span>
          <span />
        </div>
        {Array.from({ length: numSets }, (_, i) => (
          <SetRow
            key={i}
            index={i}
            weight={weights[i]}
            targetReps={targetReps}
            setData={setsData[i]}
            weekId={week}
            day={day}
            exerciseId={exerciseId}
            onSetLogged={() => showToast?.(`${name} S${i + 1} logged`)}
            onError={onError}
          />
        ))}
      </div>
    </div>
  );
}
