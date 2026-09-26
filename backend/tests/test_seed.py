from app.deps import get_sessionmaker
from app.repositories.complaint_repository import ComplaintRepository
from app.seed import run_seed


def test_seed_is_idempotent():
    with get_sessionmaker()() as session:
        first, expected = run_seed(session)
        after_first = ComplaintRepository(session).total()
    with get_sessionmaker()() as session:
        second, _ = run_seed(session)
        after_second = ComplaintRepository(session).total()

    assert first == expected > 0
    assert second == 0
    assert after_second == after_first
