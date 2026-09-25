import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DashboardPage from '../src/pages/DashboardPage';
import { jsonResponse, makeComplaint } from './helpers';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

const singlePage = {
  items: [
    makeComplaint({
      id: '3f1a2b9c-0000-4000-8000-0000000000aa',
      status: 'resolved',
    }),
  ],
  total: 1,
  page: 1,
  page_size: 10,
};

describe('DashboardPage', () => {
  it("renders the server's 409 conflict detail verbatim on a rejected status change", async () => {
    const conflict =
      'invalid transition: resolved -> open is not allowed by the state machine';
    fetchMock.mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return Promise.resolve(jsonResponse(409, { detail: conflict }));
        }
        return Promise.resolve(jsonResponse(200, singlePage));
      },
    );
    render(<DashboardPage />);
    const select = await screen.findByLabelText(/status for/i);
    fireEvent.change(select, { target: { value: 'open' } });
    expect(await screen.findByRole('alert')).toHaveTextContent(conflict);
    expect(screen.getByRole('alert')).toHaveTextContent(conflict);
  });

  it('offers all four statuses and refreshes the list after a successful change', async () => {
    fetchMock.mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return Promise.resolve(
            jsonResponse(200, makeComplaint({ status: 'in_progress' })),
          );
        }
        return Promise.resolve(jsonResponse(200, singlePage));
      },
    );
    render(<DashboardPage />);
    const select = await screen.findByLabelText(/status for/i);
    const options = Array.from(select.querySelectorAll('option')).map(
      (o) => o.value,
    );
    expect(options).toEqual(['open', 'in_progress', 'resolved', 'rejected']);
    fireEvent.change(select, { target: { value: 'in_progress' } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/complaints/3f1a2b9c-0000-4000-8000-0000000000aa/status',
      expect.objectContaining({ method: 'PATCH' }),
    );
  });

  it('sends page, page_size and active filters as query parameters', async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(jsonResponse(200, singlePage)),
    );
    render(<DashboardPage />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText('Category'), {
      target: { value: 'water' },
    });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        '/api/complaints?page=1&page_size=10&category=water',
        expect.anything(),
      ),
    );
  });
});
