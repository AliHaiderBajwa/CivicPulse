import { useEffect, useState } from 'react';
import { api, type Stats } from '../api/client';

const ICONS: Record<string, string> = {
  water:
    'M12 3.5c3.2 4.6 6 8.2 6 11.7a6 6 0 1 1-12 0c0-3.5 2.8-7.1 6-11.7Z',
  electricity: 'M13 2.5 5.5 13.5H11l-1.2 8 7.7-11H12l1-8Z',
  sanitation:
    'M5 7h14M10 4.5h4M8.5 7l.8 13h5.4l.8-13M10.5 11v5M13.5 11v5',
  roads: 'M6 21.5v-17m0 1.5h11.5l-2.8 3.8 2.8 3.8H6',
  streetlights:
    'M12 3.5a4.5 4.5 0 0 1 2.6 8.1c-.8.6-1.1 1.2-1.1 2.1H10.4c0-.9-.3-1.5-1.1-2.1A4.5 4.5 0 0 1 12 3.5ZM10.5 17.5h3M11 20h2',
};

function CategoryIcon({ value }: { value: string }) {
  return (
    <span className="stat-icon" aria-hidden="true">
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        focusable="false"
      >
        {value === 'other' ? (
          <>
            <circle cx="6" cy="12" r="1.6" fill="currentColor" stroke="none" />
            <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
            <circle cx="18" cy="12" r="1.6" fill="currentColor" stroke="none" />
          </>
        ) : (
          <path d={ICONS[value] ?? ICONS.roads} />
        )}
      </svg>
    </span>
  );
}

function share(value: number, total: number): string {
  if (total <= 0) return '—';
  return `${((100 * value) / total).toFixed(1)}%`;
}

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [cache, setCache] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api
      .getStats()
      .then(({ data, headers }) => {
        if (active) {
          setStats(data);
          setCache(headers.get('X-Cache'));
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load stats');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refreshKey]);

  return (
    <section aria-labelledby="stats-heading">
      <p className="eyebrow">At a glance</p>
      <h2 id="stats-heading">Aggregate statistics</h2>
      <p className="page-lede">
        Live totals across every filed complaint. The badge shows whether
        this view came from the Redis cache or a fresh computation.
      </p>

      <div className="stats-meta">
        <span
          data-testid="cache-badge"
          className={`cache-badge ${(cache ?? 'unknown').toLowerCase()}`}
        >
          Cache: {cache ?? 'UNKNOWN'}
        </span>
        <button
          type="button"
          className="btn-quiet"
          onClick={() => setRefreshKey((key) => key + 1)}
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      {loading && (
        <p role="status" className="loading">
          Loading stats…
        </p>
      )}
      {error && <p role="alert">{error}</p>}

      {stats && !loading && !error && (
        <>
          <div className="stat-grid">
            <div className="stat-card hero">
              <div className="stat-top">
                <div className="stat-label">Total complaints</div>
              </div>
              <div className="stat-value" data-testid="stats-total">
                {stats.total}
              </div>
            </div>
          </div>

          <h3>By category</h3>
          <div className="stat-grid">
            {Object.entries(stats.by_category).map(([key, value]) => (
              <div className="stat-card" key={key}>
                <div className="stat-top">
                  <div className="stat-label">{key}</div>
                  <CategoryIcon value={key} />
                </div>
                <div
                  className="stat-value"
                  data-testid={`count-category-${key}`}
                >
                  {value}
                </div>
                <div className="stat-share">
                  {share(value, stats.total)} of intake
                </div>
              </div>
            ))}
          </div>

          <h3>By priority</h3>
          <div className="stat-grid">
            {Object.entries(stats.by_priority).map(([key, value]) => (
              <div className="stat-card" key={key}>
                <div className="stat-top">
                  <div className="stat-label">
                    <span
                      className={
                        key === 'high'
                          ? 'pill pill-red'
                          : key === 'normal'
                            ? 'pill pill-sky'
                            : 'pill pill-slate'
                      }
                    >
                      {key}
                    </span>
                  </div>
                </div>
                <div
                  className="stat-value"
                  data-testid={`count-priority-${key}`}
                >
                  {value}
                </div>
                <div className="stat-share">
                  {share(value, stats.total)} of intake
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
