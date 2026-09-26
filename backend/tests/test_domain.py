import pytest

from app.domain import InvalidTransition, Status, ensure_transition

VALID_PAIRS = [
    (Status.OPEN, Status.IN_PROGRESS),
    (Status.OPEN, Status.REJECTED),
    (Status.IN_PROGRESS, Status.RESOLVED),
    (Status.IN_PROGRESS, Status.REJECTED),
]


@pytest.mark.parametrize("current,target", VALID_PAIRS)
def test_valid_transitions(current, target):
    ensure_transition(current, target)


@pytest.mark.parametrize("current", list(Status))
@pytest.mark.parametrize("target", list(Status))
def test_everything_else_is_invalid(current, target):
    if (current, target) in VALID_PAIRS:
        return
    with pytest.raises(InvalidTransition):
        ensure_transition(current, target)


def test_invalid_transition_message_names_both_statuses():
    with pytest.raises(InvalidTransition) as exc:
        ensure_transition(Status.OPEN, Status.RESOLVED)
    assert "open -> resolved" in str(exc.value)
