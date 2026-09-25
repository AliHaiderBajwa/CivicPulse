import { useEffect, useState } from 'react';
import {
  api,
  ApiError,
  type Category,
  type Priority,
  type Status,
} from '../api/client';
import type { ComplaintPage } from '../api/client';

const PAGE_SIZE = 10;

const CATEGORIES: readonly Category[] = [
  'water',
  'electricity',
  'sanitation',
  'roads',
  'streetlights',
  'other',
];
const PRIORITIES: readonly Priority[] = ['high', 'normal', 'low'];
const STATUSES: readonly Status[] = [
  'open',
  'in_progress',
  'resolved',
  'rejected',
];

type Filter<T extends string> = T | '';

export default function DashboardPage() {
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<Filter<Category>>('');
  const [priority, setPriority] = useState<Filter<Priority>>('');
  const [status, setStatus] = useState<Filter<Status>>('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api
      .listComplaints({
        page,
        page_size: PAGE_SIZE,
        category: category === '' ? undefined : category,
        priority: priority === '' ? undefined : priority,
        status: status === '' ? undefined : status,
      })
      .then(({ data: pageData }) => {
        if (active) setData(pageData);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load complaints');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [page, category, priority, status, refreshKey]);

  async function handleStatusChange(id: string, next: Status) {
    setBusyId(id);
    try {
      await api.updateComplaintStatus(id, next);
      setRowErrors((prev) => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      setRefreshKey((key) => key + 1);
    } catch (err) {
      let message: string;
      if (err instanceof ApiError) {
        message =
          typeof err.detail === 'string' ? err.detail : err.message;
      } else {
        message = err instanceof Error ? err.message : 'Status update failed';
      }
      setRowErrors((prev) => ({ ...prev, [id]: message }));
    } finally {
      setBusyId(null);
    }
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtersActive = category !== '' || priority !== '' || status !== '';

  return (
    <section aria-labelledby="dashboard-heading">
      <h2 id="dashboard-heading">Operations dashboard</h2>

      <div className="filters">
        <div className="field">
          <label htmlFor="filter-category">Category</label>
          <select
            id="filter-category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value as Filter<Category>);
              setPage(1);
            }}
          >
            <option value="">All</option>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="filter-priority">Priority</label>
          <select
            id="filter-priority"
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value as Filter<Priority>);
              setPage(1);
            }}
          >
            <option value="">All</option>
            {PRIORITIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="filter-status">Status</label>
          <select
            id="filter-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as Filter<Status>);
              setPage(1);
            }}
          >
            <option value="">All</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => {
            setCategory('');
            setPriority('');
            setStatus('');
            setPage(1);
          }}
          disabled={!filtersActive}
        >
          Clear filters
        </button>
      </div>

      {loading && (
        <p role="status" className="loading">
          Loading complaints…
        </p>
      )}
      {error && <p role="alert">{error}</p>}

      {!loading && !error && data && data.items.length === 0 && (
        <p>No complaints match the current filters.</p>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Location</th>
                <th scope="col">Category</th>
                <th scope="col">Priority</th>
                <th scope="col">Summary</th>
                <th scope="col">Provider</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((complaint) => (
                <tr key={complaint.id}>
                  <td>{complaint.location}</td>
                  <td>{complaint.category}</td>
                  <td>{complaint.priority}</td>
                  <td>{complaint.ai_summary ?? complaint.text}</td>
                  <td>{complaint.triaged_by}</td>
                  <td>
                    <label
                      className="visually-hidden"
                      htmlFor={`status-${complaint.id}`}
                    >
                      Status for complaint {complaint.id}
                    </label>
                    <select
                      id={`status-${complaint.id}`}
                      value={complaint.status}
                      disabled={busyId === complaint.id}
                      onChange={(e) =>
                        handleStatusChange(
                          complaint.id,
                          e.target.value as Status,
                        )
                      }
                    >
                      {STATUSES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                    {rowErrors[complaint.id] && (
                      <p role="alert" className="row-error">
                        {rowErrors[complaint.id]}
                      </p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination">
        <button
          type="button"
          onClick={() => setPage((current) => Math.max(1, current - 1))}
          disabled={loading || page <= 1}
        >
          Previous
        </button>
        <span>
          Page {page} of {totalPages} — {total} complaints
        </span>
        <button
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={loading || page >= totalPages}
        >
          Next
        </button>
      </div>
    </section>
  );
}
