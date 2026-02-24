import axios from 'axios';

const api = axios.create({
  baseURL: '/',
  timeout: 100_000,
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
 * Returns { body_comp: [...], apple_health: [...], targets: {...} }
 * @param {string} range — 'lifetime' | 'day' | 'week' | 'month' (optional)
 */
export async function fetchMetrics(range) {
  const params = range && range !== 'lifetime' ? { range } : {};
  const { data } = await api.get('/dashboard/metrics', { params });
  return data;
}

/**
 * Get current targets { weight_kg, bodyfat_pct, muscle_kg }
 */
export async function fetchTargets() {
  const { data } = await api.get('/targets');
  return data;
}

/**
 * Update targets
 * @param {{ weight_kg: number, bodyfat_pct: number, muscle_kg: number }} targets
 */
export async function updateTargets(targets) {
  const { data } = await api.put('/targets', targets);
  return data;
}

/**
 * Send a chat message to the AI coach.
 * @param {string} message
 * @param {string|null} conversationId — omit to start a new conversation
 * @returns {{ conversation_id: string, reply: string }}
 */
export async function sendChatMessage(message, conversationId = null) {
  const { data } = await api.post('/chat', {
    message,
    conversation_id: conversationId,
  });
  return data;
}

/**
 * List all past conversations (summaries).
 */
export async function fetchChatHistory() {
  const { data } = await api.get('/chat/history');
  return data.conversations;
}

/**
 * Load a full conversation by ID.
 */
export async function fetchConversation(conversationId) {
  const { data } = await api.get(`/chat/${conversationId}`);
  return data;
}

/**
 * Fetch the workout plan for any week.
 * @param {number|null} weekId — omit for current week
 * @returns {{ weeks: number[], current_week: number, days: Object }}
 */
export async function fetchPlan(weekId = null) {
  const params = weekId ? { week_id: weekId } : {};
  const { data } = await api.get('/plan', { params });
  return data;
}
