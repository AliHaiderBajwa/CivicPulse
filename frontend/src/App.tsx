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

function BrandMark() {
  return (
    <svg
      width="26"
      height="26"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M12 2.5 20 6v6c0 5-3.4 8.3-8 9.5C7.4 20.3 4 17 4 12V6l8-3.5Z"
        fill="#0369A1"
      />
      <path
        d="m8.75 12.1 2.3 2.3 4.2-4.6"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function App() {
  const [tab, setTab] = useState<TabId>('submit');

  return (
    <ErrorBoundary>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="app-header">
        <h1 className="brand">
          <BrandMark />
          CivicPulse
        </h1>
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
      <main id="main">
        {tab === 'submit' && <SubmitPage />}
        {tab === 'dashboard' && <DashboardPage />}
        {tab === 'stats' && <StatsPage />}
      </main>
      <footer className="app-footer">
        CivicPulse · Municipal complaint intake, triage and operations.
        Contract: <code>docs/openapi.json</code>.
      </footer>
    </ErrorBoundary>
  );
}
