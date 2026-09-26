import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain import Category, Priority, Status
from app.repositories.models import Complaint


class ComplaintRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, **fields: Any) -> Complaint:
        obj = Complaint(**fields)
        self._s.add(obj)
        self._s.flush()                      # server defaults (id, timestamps) come back via RETURNING
        return obj

    def get(self, complaint_id: uuid.UUID) -> Complaint | None:
        return self._s.get(Complaint, complaint_id)

    def get_for_update(self, complaint_id: uuid.UUID) -> Complaint | None:
        # Row lock: two operators changing the same complaint are serialised, no lost update.
        stmt = select(Complaint).where(Complaint.id == complaint_id).with_for_update()
        return self._s.scalars(stmt).first()

    def list(self, *, category: Category | None, priority: Priority | None,
             status: Status | None, page: int, page_size: int) -> tuple[list[Complaint], int]:
        stmt = select(Complaint)
        count = select(func.count()).select_from(Complaint)
        for column, value in ((Complaint.category, category), (Complaint.priority, priority),
                              (Complaint.status, status)):
            if value is not None:
                stmt = stmt.where(column == value)
                count = count.where(column == value)
        total = self._s.scalar(count) or 0
        rows = self._s.scalars(
            stmt.order_by(Complaint.created_at.desc(), Complaint.id)
            .offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(rows), total

    def set_status(self, complaint: Complaint, status: Status) -> None:
        complaint.status = status
        complaint.updated_at = func.now()    # type: ignore[assignment]
        self._s.flush()
        self._s.refresh(complaint)

    def counts(self, column: Any) -> dict[str, int]:
        rows = self._s.execute(select(column, func.count()).group_by(column)).all()
        return {(k.value if hasattr(k, "value") else str(k)): int(v) for k, v in rows}

    def total(self) -> int:
        return self._s.scalar(select(func.count()).select_from(Complaint)) or 0

    def insert_many_ignore(self, rows: Sequence[dict[str, Any]]) -> int:
        stmt = pg_insert(Complaint).values(rows).on_conflict_do_nothing(index_elements=["id"])
        return self._s.execute(stmt).rowcount or 0  # type: ignore[attr-defined]

    def ping(self) -> None:
        self._s.execute(select(1))

    def commit(self) -> None:
        self._s.commit()
