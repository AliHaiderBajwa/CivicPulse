import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.deps import get_sessionmaker
from app.domain import Category, Priority, Status
from app.repositories.complaint_repository import ComplaintRepository
from app.seed_data import SEED_COMPLAINTS

SEED_NAMESPACE = uuid.UUID("6f1c0a2e-3b8d-4c57-9a41-0d2f5e7b8c19")   # fixed, so ids are stable forever


def _status_for(i: int) -> Status:
    return {3: Status.IN_PROGRESS, 6: Status.RESOLVED, 8: Status.REJECTED}.get(i % 9, Status.OPEN)


def _summary(text: str) -> str:
    s = " ".join(text.split())
    return s if len(s) <= 140 else s[:137].rstrip() + "..."


def run_seed(session: Session) -> tuple[int, int]:
    now = datetime.now(UTC)
    rows = []
    for i, (category, priority, location, text) in enumerate(SEED_COMPLAINTS):
        created = now - timedelta(hours=5 * (len(SEED_COMPLAINTS) - i))
        rows.append({
            "id": uuid.uuid5(SEED_NAMESPACE, text),          # same text -> same id -> no duplicate row
            "text": text, "location": location, "reporter_contact": None,
            "category": Category(category), "priority": Priority(priority),
            "status": _status_for(i), "ai_summary": _summary(text),
            "triaged_by": "rules", "triage_latency_ms": 0,   # the seed never calls an LLM
            "created_at": created, "updated_at": created,
        })
    repo = ComplaintRepository(session)
    before = repo.total()
    repo.insert_many_ignore(rows)
    repo.commit()
    # psycopg3 reports rowcount -1 for multi-row ON CONFLICT inserts, so count the delta instead.
    return repo.total() - before, len(rows)


def main() -> None:
    with get_sessionmaker()() as session:
        inserted, total = run_seed(session)
    print(f"seed: inserted {inserted}, skipped {total - inserted} (already present)")


if __name__ == "__main__":
    main()
