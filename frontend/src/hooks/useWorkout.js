import { useState, useCallback } from 'react';
import { fetchWorkout } from '../api/client';

/**
 * Encapsulates all workout-fetch state.
 * Returns { week, weeks, day, exercises, loading, error, load, setWeekId }.
 */
export function useWorkout() {
  const [week, setWeek] = useState(null);
  const [weeks, setWeeks] = useState([]);
  const [day, setDay] = useState(null);
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (dayId, weekId = null) => {
    setLoading(true);
    setError(null);
    setDay(dayId);

    try {
      const data = await fetchWorkout(dayId, weekId);
      setWeek(data.week);
      setWeeks(data.weeks || []);
      setExercises(data.exercises);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
      setExercises([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { week, weeks, day, exercises, loading, error, load };
}
