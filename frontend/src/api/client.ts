import type { components } from './schema';

export type Complaint = components['schemas']['Complaint'];
export type ComplaintCreate = components['schemas']['ComplaintCreate'];
export type ComplaintPage = components['schemas']['ComplaintPage'];
export type Category = components['schemas']['Category'];
export type Priority = components['schemas']['Priority'];
export type Status = components['schemas']['Status'];
export type Stats = components['schemas']['Stats'];
export type FieldError = components['schemas']['ValidationError']['detail'][number];

/** Typed error for any non-2xx response; `detail` is the server's JSON payload verbatim. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }

  get fieldErrors(): FieldError[] {
    return Array.isArray(this.detail)
      ? (this.detail.filter(
          (entry): entry is FieldError =>
            typeof entry === 'object' &&
            entry !== null &&
            'field' in entry &&
            'message' in entry,
        ) as FieldError[])
      : [];
  }
}

export interface ApiResponse<T> {
  data: T;
  headers: Headers;
}

export interface ListComplaintsParams {
  page?: number;
  page_size?: number;
  category?: Category;
  priority?: Priority;
  status?: Status;
}

const API_PREFIX = '/api/';

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResponse<T>> {
  if (!path.startsWith(API_PREFIX)) {
    throw new Error(`Refusing to call non-relative API path: ${path}`);
  }
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      body !== null && typeof body === 'object' && 'detail' in body
        ? (body as { detail: unknown }).detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, detail);
  }

  return { data: body as T, headers: response.headers };
}

export const api = {
  createComplaint(payload: ComplaintCreate): Promise<ApiResponse<Complaint>> {
    return request<Complaint>('/api/complaints', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listComplaints(params: ListComplaintsParams = {}): Promise<ApiResponse<ComplaintPage>> {
    const query = buildQuery({
      page: params.page,
      page_size: params.page_size,
      category: params.category,
      priority: params.priority,
      status: params.status,
    });
    return request<ComplaintPage>(`/api/complaints${query}`);
  },

  updateComplaintStatus(id: string, status: Status): Promise<ApiResponse<Complaint>> {
    return request<Complaint>(
      `/api/complaints/${encodeURIComponent(id)}/status`,
      { method: 'PATCH', body: JSON.stringify({ status }) },
    );
  },

  getStats(): Promise<ApiResponse<Stats>> {
    return request<Stats>('/api/stats');
  },
};
