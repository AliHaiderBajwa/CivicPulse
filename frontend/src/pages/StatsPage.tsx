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
      <h2 id="stats-heading">Aggregate statistics</h2>

      <div className="stats-meta">
        <span
          data-testid="cache-badge"
          className={`cache-badge ${(cache ?? 'unknown').toLowerCase()}`}
        >
          Cache: {cache ?? 'UNKNOWN'}
        </span>
        <button
          type="button"
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
          <p>
            Total complaints:{' '}
            <strong data-testid="stats-total">{stats.total}</strong>
          </p>

          <h3>By category</h3>
          <table>
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col">Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.by_category).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td data-testid={`count-category-${key}`}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>By priority</h3>
          <table>
            <thead>
              <tr>
                <th scope="col">Priority</th>
                <th scope="col">Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.by_priority).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td data-testid={`count-priority-${key}`}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
