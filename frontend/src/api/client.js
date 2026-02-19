import axios from 'axios';

const api = axios.create({
  baseURL: '/',
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Fetch the workout plan for a given day.
 * @param {number} dayId — 1‑5
 * @returns {{ week: number, day: number, exercises: Array }}
 */
export async function fetchWorkout(dayId) {
  const { data } = await api.get(`/workout/${dayId}`);
  if (data.error) throw new Error(data.error);
  return data;
}

/**
 * Post a completed exercise log.
 * @param {{ week_id: number, day: number, exercise: string, actual_weight: number[], actual_reps: number[] }} payload
 */
export async function logExercise(payload) {
  const { data } = await api.post('/log', payload);
  return data;
}

/**
 * Tell the backend to archive the current week and generate the next one.
 */
export async function generateNextWeek() {
  const { data } = await api.post('/generate-next-week');
  return data;
}

/**
 * Fetch dashboard stats: bench cycle, week completion, etc.
 */
export async function fetchStats() {
  const { data } = await api.get('/stats');
  return data;
}

/**
 * Mark a day as complete and dump its data to the data lake.
 * @param {number} weekId
 * @param {number} day — 1‑5
 */
export async function completeDay(weekId, day) {
  const { data } = await api.post(`/complete-day?week_id=${weekId}&day=${day}`);
  return data;
}

/**
 * Fetch volume chart data from the data lake.
 * Returns { volume: [{ date, week, day, sets, reps, tonnage_kg }] }
 */
export async function fetchVolume() {
  const { data } = await api.get('/dashboard/volume');
  return data;
}

/**
 * Fetch body-composition metrics from the data lake CSV.
 * Returns { metrics: [{ date, weight_kg, bodyfat_pct, muscle_mass_kg }] }
 */
export async function fetchMetrics() {
  const { data } = await api.get('/dashboard/metrics');
  return data;
}
