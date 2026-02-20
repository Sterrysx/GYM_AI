import { useState } from 'react';
import Layout from './components/Layout';
import WorkoutFeed from './components/WorkoutFeed';
import StatsPage from './components/StatsPage';
import Dashboard from './components/Dashboard';
import PlanViewer from './components/PlanViewer';
import Toast from './components/Toast';
import ChatBubble from './components/ChatBubble';
import { useWorkout } from './hooks/useWorkout';
import { useToast } from './hooks/useToast';
import { logExercise } from './api/client';

export default function App() {
  const [activeView, setActiveView] = useState('stats'); // 'stats' | 'metrics' | 'workout'
  const { week, day, exercises, loading, error, load } = useWorkout();
  const { toast, showToast } = useToast();

  /** Switch to workout tab and load the day. */
  const handleSelectDay = (dayId) => {
    setActiveView('workout');
    load(dayId);
  };

  /** Called after "Generate Next Week" succeeds — reload the active day. */
  const handleGenerated = () => {
    if (day) load(day);
  };

  /** Called by ExerciseCard when user hits "Log". */
  const handleLog = async (payload) => {
    const result = await logExercise(payload);
    showToast(`${result.exercise} saved.`);
    return result;
  };

  return (
    <>
      <Layout
        week={week}
        activeDay={day}
        onSelectDay={handleSelectDay}
        onGenerated={handleGenerated}
        showToast={showToast}
        activeView={activeView}
        onViewChange={setActiveView}
      >
        {activeView === 'stats' && <StatsPage />}
        {activeView === 'metrics' && <Dashboard />}
        {activeView === 'plan' && <PlanViewer />}
        {activeView === 'workout' && (
          <WorkoutFeed
            exercises={exercises}
            week={week}
            day={day}
            loading={loading}
            error={error}
            onLog={handleLog}
            onError={(msg) => showToast(msg, true)}
            showToast={showToast}
          />
        )}
      </Layout>

      <Toast msg={toast.msg} isError={toast.isError} visible={toast.visible} />
      <ChatBubble />
    </>
  );
}
