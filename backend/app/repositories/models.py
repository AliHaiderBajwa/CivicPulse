import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain import Category, Priority, Status


class Base(DeclarativeBase):
    pass


def _enum(cls: type, name: str) -> SAEnum:
    # create_type=False: the migration owns the DDL, the app never creates types or tables.
    return SAEnum(cls, name=name, values_callable=lambda e: [m.value for m in e], create_type=False)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=func.gen_random_uuid())
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[Category] = mapped_column(
        _enum(Category, "complaint_category"), nullable=False)
    priority: Mapped[Priority] = mapped_column(
        _enum(Priority, "complaint_priority"), nullable=False)
    status: Mapped[Status] = mapped_column(_enum(Status, "complaint_status"), nullable=False,
                                           server_default="open")
    ai_summary: Mapped[str | None] = mapped_column(String(140))
    triaged_by: Mapped[str] = mapped_column(String(32), nullable=False)
    triage_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now())
