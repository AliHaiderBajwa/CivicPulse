import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../src/api/client';
import { jsonResponse } from './helpers';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
});

describe('api client', () => {
  it('uses only relative /api/ URLs', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { items: [], total: 0, page: 1, page_size: 10 }));
    vi.stubGlobal('fetch', fetchMock);
    await api.listComplaints({ page: 2, category: 'water' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/complaints?page=2&category=water',
      expect.anything(),
    );
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url.startsWith('/api/')).toBe(true);
  });

  it('throws a typed ApiError carrying the server detail verbatim', async () => {
    const conflict = 'open -> rejected is blocked by the state machine';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: conflict })),
    );
    const error = await api
      .updateComplaintStatus('3f1a2b9c-0000-4000-8000-000000000001', 'rejected')
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(409);
    expect(apiError.detail).toBe(conflict);
    expect(apiError.message).toBe(conflict);
  });

  it('parses field-level 400 validation errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(400, {
          detail: [{ field: 'text', message: 'String should have at least 10 characters' }],
        }),
      ),
    );
    const error = await api
      .createComplaint({ text: 'short', location: 'Karachi' })
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).fieldErrors).toEqual([
      { field: 'text', message: 'String should have at least 10 characters' },
    ]);
  });
});
