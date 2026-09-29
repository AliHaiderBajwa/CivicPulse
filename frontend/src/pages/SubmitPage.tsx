import { useState, type FormEvent } from 'react';
import { api, ApiError, type Complaint, type FieldError } from '../api/client';

const MIN_TEXT = 10;
const MAX_TEXT = 2000;
const MIN_LOCATION = 3;
const MAX_LOCATION = 200;
const MAX_CONTACT = 200;

interface ClientErrors {
  text?: string;
  location?: string;
  contact?: string;
}

function validate(text: string, location: string, contact: string): ClientErrors {
  const errors: ClientErrors = {};
  if (text.length < MIN_TEXT) {
    errors.text = `Complaint text must be at least ${MIN_TEXT} characters.`;
  } else if (text.length > MAX_TEXT) {
    errors.text = `Complaint text must be at most ${MAX_TEXT} characters.`;
  }
  if (location.length < MIN_LOCATION) {
    errors.location = `Location must be at least ${MIN_LOCATION} characters.`;
  } else if (location.length > MAX_LOCATION) {
    errors.location = `Location must be at most ${MAX_LOCATION} characters.`;
  }
  if (contact.length > MAX_CONTACT) {
    errors.contact = `Contact must be at most ${MAX_CONTACT} characters.`;
  }
  return errors;
}

export default function SubmitPage() {
  const [text, setText] = useState('');
  const [location, setLocation] = useState('');
  const [contact, setContact] = useState('');
  const [clientErrors, setClientErrors] = useState<ClientErrors>({});
  const [serverErrors, setServerErrors] = useState<FieldError[]>([]);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validate(text, location, contact);
    setClientErrors(errors);
    setServerErrors([]);
    setRequestError(null);
    if (errors.text || errors.location || errors.contact) {
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.createComplaint({
        text,
        location,
        reporter_contact: contact.trim() === '' ? null : contact.trim(),
      });
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        const fields = err.fieldErrors;
        if (fields.length > 0) {
          setServerErrors(fields);
        } else {
          setRequestError(err.message);
        }
      } else {
        setRequestError(err instanceof Error ? err.message : 'Network error');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="submit-heading">
      <p className="eyebrow">Citizen intake</p>
      <h2 id="submit-heading">Submit a complaint</h2>
      <p className="page-lede">
        Describe the problem and where it is. CivicPulse validates it,
        triages it with AI, and files it with the municipality.
      </p>
      <div className="submit-grid">
      <form onSubmit={handleSubmit} noValidate className="card">
        <div className="field">
          <label htmlFor="complaint-text">Complaint text</label>
          <textarea
            id="complaint-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-describedby={clientErrors.text ? 'complaint-text-error' : undefined}
            rows={6}
          />
          <p className="hint" aria-hidden="true">
            {text.length} / {MAX_TEXT} characters
          </p>
          {clientErrors.text && (
            <p id="complaint-text-error" role="alert" className="field-error">
              {clientErrors.text}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="complaint-location">Location</label>
          <input
            id="complaint-location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            aria-describedby={
              clientErrors.location ? 'complaint-location-error' : undefined
            }
          />
          {clientErrors.location && (
            <p
              id="complaint-location-error"
              role="alert"
              className="field-error"
            >
              {clientErrors.location}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="complaint-contact">Contact (optional)</label>
          <input
            id="complaint-contact"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            aria-describedby={
              clientErrors.contact ? 'complaint-contact-error' : undefined
            }
          />
          {clientErrors.contact && (
            <p id="complaint-contact-error" role="alert" className="field-error">
              {clientErrors.contact}
            </p>
          )}
        </div>

        <button type="submit" disabled={loading} className="btn-accent">
          {loading ? 'Submitting…' : 'Submit complaint'}
        </button>
      </form>

      {loading && (
        <p role="status" className="loading">
          Triage in progress — AI calls take seconds…
        </p>
      )}

      {requestError && (
        <p role="alert" className="field-error">
          {requestError}
        </p>
      )}

      {serverErrors.length > 0 && (
        <div role="alert" className="form-errors">
          <p>The server rejected this submission:</p>
          <ul>
            {serverErrors.map((fieldError) => (
              <li key={`${fieldError.field}:${fieldError.message}`}>
                {fieldError.field}: {fieldError.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <section aria-label="Triage result" className="result-card">
          <h3>Triage result</h3>
          <dl>
            <dt>Category</dt>
            <dd>
              <span className="pill pill-sky" data-testid="result-category">
                {result.category}
              </span>
            </dd>
            <dt>Priority</dt>
            <dd>
              <span
                className={
                  result.priority === 'high'
                    ? 'pill pill-red'
                    : result.priority === 'normal'
                      ? 'pill pill-sky'
                      : 'pill pill-slate'
                }
                data-testid="result-priority"
              >
                {result.priority}
              </span>
            </dd>
            <dt>AI summary</dt>
            <dd data-testid="result-summary">{result.ai_summary ?? '—'}</dd>
            <dt>Provider (triaged_by)</dt>
            <dd>
              <span className="pill pill-mono" data-testid="result-provider">
                {result.triaged_by}
              </span>
            </dd>
          </dl>
          <div className="result-meta">
            <div className="meta-cell">
              <span className="meta-label">Latency</span>
              <span className="meta-value">
                {result.triage_latency_ms} ms
              </span>
            </div>
            <div className="meta-cell">
              <span className="meta-label">Filed</span>
              <span className="meta-value">
                {new Date(result.created_at).toLocaleString()}
              </span>
            </div>
            <div className="meta-cell">
              <span className="meta-label">Reference</span>
              <span className="meta-value">{result.id.slice(0, 8)}</span>
            </div>
          </div>
        </section>
      )}
      </div>
    </section>
  );
}
