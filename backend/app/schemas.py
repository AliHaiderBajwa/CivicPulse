from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain import Category, Priority, Status

TriagedBy = Literal["llm:groq", "llm:ollama", "rules", "rules:fallback", "simulated"]


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=10, max_length=2000, description="Free-text complaint")
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(
        default=None, max_length=200, description="Optional email or phone"
    )

    @field_validator("reporter_contact")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        return v or None


class Complaint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    location: str
    reporter_contact: str | None = None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None = Field(default=None, max_length=140)
    triaged_by: TriagedBy = Field(description="Which provider decided this triage")
    triage_latency_ms: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class ComplaintPage(BaseModel):
    items: list[Complaint]
    total: int
    page: int
    page_size: int


class StatusUpdate(BaseModel):
    status: Status


class Stats(BaseModel):
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]


class TriageOutcome(BaseModel):
    provider: str
    latency_ms: int
    fallback: bool
    complaint_id: UUID | None = None


class ProviderMeta(BaseModel):
    active_provider: str
    recent_triages: list[TriageOutcome] = Field(max_length=20)


class FieldError(BaseModel):
    field: str
    message: str


class ValidationError(BaseModel):
    detail: list[FieldError]


class Error(BaseModel):
    detail: str


class ReadyDependencies(BaseModel):
    postgres: bool
    redis: bool


class Ready(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: ReadyDependencies
