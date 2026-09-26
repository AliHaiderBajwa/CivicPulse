from typing import Protocol

from pydantic import BaseModel, Field

from app.domain import Category, Priority


class TriageResult(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)


class ProviderError(Exception):
    """Any failure of a triage provider (network, bad output, quota)."""


class TriageProvider(Protocol):
    name: str

    def triage(self, text: str, location: str) -> TriageResult: ...
