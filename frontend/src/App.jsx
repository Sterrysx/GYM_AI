import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import WorkoutFeed from './components/WorkoutFeed';
import StatsPage from './components/StatsPage';
import Dashboard from './components/Dashboard';
import PlanViewer from './components/PlanViewer';
import ProgressionPage from './components/ProgressionPage';
import Toast from './components/Toast';
import ChatBubble from './components/ChatBubble';
import { useWorkout } from './hooks/useWorkout';
import { useToast } from './hooks/useToast';
import { hasCompletedDays } from './api/client';

export default function App() {
  const [activeView, setActiveView] = useState('stats');
  const { week, weeks, day, exercises, loading, error, load } = useWorkout();
  const { toast, showToast } = useToast();
  const [strengthUnlocked, setStrengthUnlocked] = useState(false);

  // Check if strength tab should be unlocked
  useEffect(() => {
    hasCompletedDays().then(setStrengthUnlocked).catch(() => {});
  }, []);

  const checkStrengthUnlock = () => {
    hasCompletedDays().then(setStrengthUnlocked).catch(() => {});
  };

  const handleSelectDay = (dayId) => {
    setActiveView('workout');
    load(dayId, week);
  };

  const handleSelectWeek = (weekId) => {
    if (day) load(day, weekId);
  };

  const handleGenerated = () => {
    if (day) load(day, week);
  };

  return (
    <>
      <Layout
        week={week}
        weeks={weeks}
        activeDay={day}
        onSelectDay={handleSelectDay}
        onSelectWeek={handleSelectWeek}
        onGenerated={handleGenerated}
        showToast={showToast}
        activeView={activeView}
        onViewChange={setActiveView}
        strengthUnlocked={strengthUnlocked}
      >
        {activeView === 'stats' && <StatsPage />}
        {activeView === 'metrics' && <Dashboard />}
        {activeView === 'progression' && <ProgressionPage />}
        {activeView === 'plan' && <PlanViewer />}
        {activeView === 'workout' && (
          <WorkoutFeed
            exercises={exercises}
            week={week}
            day={day}
            loading={loading}
            error={error}
            onError={(msg) => showToast(msg, true)}
            showToast={showToast}
            onDayCompleted={() => { if (day) load(day, week); checkStrengthUnlock(); }}
          />
        )}
      </Layout>

      <Toast msg={toast.msg} isError={toast.isError} visible={toast.visible} />
      <ChatBubble />
    </>
  );
}
