from enum import Enum


class Category(str, Enum):
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    ROADS = "roads"
    STREETLIGHTS = "streetlights"
    OTHER = "other"


class Priority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Status(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


# The state machine is DATA, not a chain of ifs. Anything not listed is illegal.
TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.OPEN: frozenset({Status.IN_PROGRESS, Status.REJECTED}),
    Status.IN_PROGRESS: frozenset({Status.RESOLVED, Status.REJECTED}),
    Status.RESOLVED: frozenset(),  # terminal
    Status.REJECTED: frozenset(),  # terminal
}


class DomainError(Exception):
    pass


class NotFound(DomainError):
    def __init__(self, entity: str, entity_id: object) -> None:
        self.entity, self.entity_id = entity, entity_id
        super().__init__(f"{entity} not found: {entity_id}")


class InvalidTransition(DomainError):
    def __init__(self, current: Status, target: Status) -> None:
        self.current, self.target = current, target
        super().__init__(f"Invalid status transition: {current.value} -> {target.value}")


def ensure_transition(current: Status, target: Status) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(current, target)
