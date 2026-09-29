import type { Complaint } from '../src/api/client';

export function jsonResponse(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

export function makeComplaint(overrides: Partial<Complaint> = {}): Complaint {
  return {
    id: '3f1a2b9c-0000-4000-8000-000000000001',
    text: 'Water pipe burst flooding the street',
    location: 'Karachi, Saddar',
    reporter_contact: null,
    category: 'water',
    priority: 'normal',
    status: 'open',
    ai_summary: 'Burst pipe flooding the street',
    triaged_by: 'llm:groq',
    triage_latency_ms: 420,
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  };
}
