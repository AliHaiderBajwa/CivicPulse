import { useEffect, useState } from 'react';
import { api, type Stats } from '../api/client';

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
              <div className="stat-label">Total complaints</div>
              <div className="stat-value" data-testid="stats-total">
                {stats.total}
              </div>
            </div>
          </div>

          <h3>By category</h3>
          <div className="stat-grid">
            {Object.entries(stats.by_category).map(([key, value]) => (
              <div className="stat-card" key={key}>
                <div className="stat-label">{key}</div>
                <div
                  className="stat-value"
                  data-testid={`count-category-${key}`}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>

          <h3>By priority</h3>
          <div className="stat-grid">
            {Object.entries(stats.by_priority).map(([key, value]) => (
              <div className="stat-card" key={key}>
                <div className="stat-label">{key}</div>
                <div
                  className="stat-value"
                  data-testid={`count-priority-${key}`}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
