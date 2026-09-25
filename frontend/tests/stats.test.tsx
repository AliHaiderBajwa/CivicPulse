import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import StatsPage from '../src/pages/StatsPage';
import { jsonResponse } from './helpers';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

describe('StatsPage', () => {
  it('renders total, counts by category and by priority, plus the X-Cache badge', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        200,
        {
          total: 42,
          by_category: { water: 30, roads: 12 },
          by_priority: { high: 7, normal: 25, low: 10 },
        },
        { 'X-Cache': 'HIT' },
      ),
    );
    render(<StatsPage />);
    expect(await screen.findByTestId('stats-total')).toHaveTextContent('42');
    expect(screen.getByTestId('count-category-water')).toHaveTextContent('30');
    expect(screen.getByTestId('count-category-roads')).toHaveTextContent('12');
    expect(screen.getByTestId('count-priority-high')).toHaveTextContent('7');
    expect(screen.getByTestId('count-priority-low')).toHaveTextContent('10');
    expect(screen.getByTestId('cache-badge')).toHaveTextContent('Cache: HIT');
    expect(fetchMock).toHaveBeenCalledWith('/api/stats', expect.anything());
  });

  it('shows Cache: MISS when the X-Cache header says MISS', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        200,
        { total: 0, by_category: {}, by_priority: {} },
        { 'X-Cache': 'MISS' },
      ),
    );
    render(<StatsPage />);
    expect(await screen.findByTestId('cache-badge')).toHaveTextContent(
      'Cache: MISS',
    );
  });

  it('surfaces a load error when the stats request fails', async () => {
    fetchMock.mockRejectedValue(new Error('backend unreachable'));
    render(<StatsPage />);
    expect(
      await screen.findByText(/backend unreachable/i),
    ).toBeInTheDocument();
  });
});
