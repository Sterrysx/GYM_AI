import axios from 'axios';

const api = axios.create({
  baseURL: '/',
  timeout: 100_000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Fetch the workout plan for a given day, including already-logged data.
 * Each exercise includes `sets_data` with per-set logged state.
 */
export async function fetchWorkout(dayId, weekId = null) {
  const params = weekId ? { week_id: weekId } : {};
  const { data } = await api.get(`/workout/${dayId}`, { params });
  if (data.error) throw new Error(data.error);
  return data;
}

/**
 * Log a single set of an exercise.
 */
export async function logSet(payload) {
  const { data } = await api.post('/log/set', payload);
  return data;
}

/**
 * Log all sets of an exercise at once.
 */
export async function logExercise(payload) {
  const { data } = await api.post('/log', payload);
  return data;
}

/**
 * Edit an already-logged set (fix typos).
 */
export async function editSet(payload) {
  const { data } = await api.put('/log/edit', payload);
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
 * Zero-fills any unlogged sets.
 */
export async function completeDay(weekId, day) {
  const { data } = await api.post(`/complete-day?week_id=${weekId}&day=${day}`);
  return data;
}

/**
 * Complete specific exercise(s) — zero-fills unlogged sets.
 * Pass an array of exercise_ids (works for single or superset).
 */
export async function completeExercise(weekId, day, exerciseIds) {
  const { data } = await api.post(
    `/complete-exercise?week_id=${weekId}&day=${day}`,
    exerciseIds,
  );
  return data;
}

/**
 * Check if user has completed at least one workout day.
 */
export async function hasCompletedDays() {
  const { data } = await api.get('/has-completed-days');
  return data.has_completed;
}

/**
 * Fetch volume chart data from the data lake.
 */
export async function fetchVolume() {
  const { data } = await api.get('/dashboard/volume');
  return data;
}

/**
 * Fetch body-composition metrics.
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
 */
export async function updateTargets(targets) {
  const { data } = await api.put('/targets', targets);
  return data;
}

/**
 * Send a chat message to the AI coach.
 */
export async function sendChatMessage(message, conversationId = null) {
  const { data } = await api.post('/chat', {
    message,
    conversation_id: conversationId,
  });
  return data;
}

/**
 * Stream a chat message from the AI coach (SSE).
 * Calls onToken(string) for each incremental token.
 * Returns { conversation_id, full_reply } when done.
 */
export async function streamChatMessage(message, conversationId, onToken) {
  const response = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullReply = '';
  let convId = conversationId;
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE lines from buffer
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete line in buffer

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.done) {
          convId = data.conversation_id;
        } else if (data.token) {
          fullReply += data.token;
          onToken(data.token);
        }
      } catch { /* partial JSON, skip */ }
    }
  }

  return { conversation_id: convId, full_reply: fullReply };
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
 * Update target weights for an exercise in the plan.
 */
export async function updatePlanWeight(weekId, day, exerciseId, weights) {
  const { data } = await api.put('/plan/weight', {
    week_id: weekId,
    day,
    exercise_id: exerciseId,
    weights,
  });
  return data;
}

/**
 * Fetch the workout plan for any week.
 */
export async function fetchPlan(weekId = null) {
  const params = weekId ? { week_id: weekId } : {};
  const { data } = await api.get('/plan', { params });
  return data;
}

/**
 * Fetch strength progression history for a single exercise.
 */
export async function fetchProgression(exerciseId) {
  const { data } = await api.get(`/progression/${exerciseId}`);
  return data;
}

/**
 * Fetch compact progression summary for ALL exercises.
 */
export async function fetchAllProgressions() {
  const { data } = await api.get('/progression');
  return data;
}

/**
 * Fetch RPG-style muscle levels for the muscle map.
 */
export async function fetchMuscleLevels() {
  const { data } = await api.get('/muscle-levels');
  return data;
}

/**
 * Fetch abs routine incomplete-seconds history across weeks.
 */
export async function fetchAbsHistory() {
  const { data } = await api.get('/abs/history');
  return data;
}
