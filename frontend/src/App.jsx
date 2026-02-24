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

export default function App() {
  const [activeView, setActiveView] = useState('stats');
  const { week, day, exercises, loading, error, load } = useWorkout();
  const { toast, showToast } = useToast();

  const handleSelectDay = (dayId) => {
    setActiveView('workout');
    load(dayId);
  };

  const handleGenerated = () => {
    if (day) load(day);
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
