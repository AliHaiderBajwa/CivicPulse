import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SubmitPage from '../src/pages/SubmitPage';
import { jsonResponse, makeComplaint } from './helpers';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

function fillForm(text: string, location: string) {
  fireEvent.change(screen.getByLabelText('Complaint text'), {
    target: { value: text },
  });
  fireEvent.change(screen.getByLabelText('Location'), {
    target: { value: location },
  });
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: /submit/i }));
}

describe('SubmitPage', () => {
  it('blocks submission when complaint text is shorter than 10 characters', async () => {
    render(<SubmitPage />);
    fillForm('too short', 'Karachi, Saddar');
    submit();
    expect(await screen.findByText(/at least 10 characters/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows an honest loading state while the triage request is pending', async () => {
    let settle!: (response: Response) => void;
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          settle = resolve;
        }),
    );
    render(<SubmitPage />);
    fillForm('Water pipe burst flooding the street', 'Karachi, Saddar');
    submit();
    expect(await screen.findByText(/triage in progress/i)).toBeInTheDocument();
    settle(jsonResponse(201, makeComplaint()));
    expect(await screen.findByTestId('result-category')).toHaveTextContent(
      'water',
    );
  });

  it('renders category, priority, summary and provider after a 201 response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        201,
        makeComplaint({
          category: 'roads',
          priority: 'high',
          ai_summary: 'Deep pothole blocking the lane',
          triaged_by: 'llm:ollama',
        }),
      ),
    );
    render(<SubmitPage />);
    fillForm('Deep pothole blocking the lane near the market', 'Lahore, Gulberg');
    submit();
    expect(await screen.findByTestId('result-category')).toHaveTextContent(
      'roads',
    );
    expect(screen.getByTestId('result-priority')).toHaveTextContent('high');
    expect(screen.getByTestId('result-summary')).toHaveTextContent(
      'Deep pothole blocking the lane',
    );
    expect(screen.getByTestId('result-provider')).toHaveTextContent(
      'llm:ollama',
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/complaints',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('renders server field-level 400 errors alongside client validation', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(400, {
        detail: [{ field: 'location', message: 'Unknown municipality' }],
      }),
    );
    render(<SubmitPage />);
    fillForm('Valid complaint text here', 'Karachi, Saddar');
    submit();
    expect(
      await screen.findByText('location: Unknown municipality'),
    ).toBeInTheDocument();
  });
});
