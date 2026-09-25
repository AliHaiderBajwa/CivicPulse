import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import ErrorBoundary from '../src/components/ErrorBoundary';
import { jsonResponse } from './helpers';

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith('/api/stats')) {
        return Promise.resolve(
          jsonResponse(200, { total: 0, by_category: {}, by_priority: {} }, { 'X-Cache': 'HIT' }),
        );
      }
      return Promise.resolve(
        jsonResponse(200, { items: [], total: 0, page: 1, page_size: 10 }),
      );
    }),
  );
});

describe('App navigation', () => {
  it('switches between Submit, Dashboard and Stats views', async () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: 'Submit a complaint' }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dashboard' }));
    expect(
      await screen.findByRole('heading', { name: 'Operations dashboard' }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Stats' }));
    expect(await screen.findByTestId('stats-total')).toHaveTextContent('0');
    expect(screen.getByTestId('cache-badge')).toHaveTextContent('Cache: HIT');
  });
});

describe('ErrorBoundary', () => {
  it('renders the fallback UI when a child throws during render', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    function Boom(): ReactNode {
      throw new Error('render exploded');
    }

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('render exploded');
    expect(
      screen.getByRole('button', { name: 'Try again' }),
    ).toBeInTheDocument();
    consoleSpy.mockRestore();
  });
});
