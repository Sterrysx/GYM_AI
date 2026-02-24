import { useState, useCallback } from 'react';
import { fetchWorkout } from '../api/client';

/**
 * Encapsulates all workout-fetch state.
 * Returns { week, day, exercises, loading, error, load }.
 */
export function useWorkout() {
  const [week, setWeek] = useState(null);
  const [day, setDay] = useState(null);
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (dayId) => {
    setLoading(true);
    setError(null);
    setDay(dayId);

    try {
      const data = await fetchWorkout(dayId);
      setWeek(data.week);
      setExercises(data.exercises);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
      setExercises([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { week, day, exercises, loading, error, load };
}
