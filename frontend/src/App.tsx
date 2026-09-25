import { useState } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardPage from './pages/DashboardPage';
import StatsPage from './pages/StatsPage';
import SubmitPage from './pages/SubmitPage';

type TabId = 'submit' | 'dashboard' | 'stats';

const TABS: readonly { id: TabId; label: string }[] = [
  { id: 'submit', label: 'Submit' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'stats', label: 'Stats' },
];

export default function App() {
  const [tab, setTab] = useState<TabId>('submit');

  return (
    <ErrorBoundary>
      <header className="app-header">
        <h1>CivicPulse</h1>
        <nav aria-label="Main navigation">
          {TABS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              aria-current={tab === entry.id ? 'page' : undefined}
              onClick={() => setTab(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'submit' && <SubmitPage />}
        {tab === 'dashboard' && <DashboardPage />}
        {tab === 'stats' && <StatsPage />}
      </main>
    </ErrorBoundary>
  );
}
