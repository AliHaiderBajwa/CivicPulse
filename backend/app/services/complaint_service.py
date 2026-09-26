import logging
import uuid

from app.domain import NotFound, Status, ensure_transition
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.models import Complaint
from app.schemas import ComplaintCreate
from app.services.stats_service import StatsService
from app.services.triage_orchestrator import TriageOrchestrator

log = logging.getLogger("app.complaints")


class ComplaintService:
    def __init__(self, repo: ComplaintRepository, triage: TriageOrchestrator, stats: StatsService) -> None:
        self._repo, self._triage, self._stats = repo, triage, stats

    def create(self, data: ComplaintCreate) -> Complaint:
        outcome = self._triage.run(data.text, data.location)
        complaint = self._repo.add(
            text=data.text, location=data.location, reporter_contact=data.reporter_contact,
            category=outcome.result.category, priority=outcome.result.priority,
            ai_summary=outcome.result.summary, triaged_by=outcome.triaged_by,
            triage_latency_ms=outcome.latency_ms,
        )
        self._repo.commit()
        self._stats.invalidate()                       # a new complaint must show in stats immediately
        if outcome.fallback:                           # exactly one WARNING per fallback
            log.warning("triage fallback", extra={
                "complaint_id": str(complaint.id),
                "provider": self._triage.primary_name,
                "error_class": outcome.error_class,
            })
        return complaint

    def get(self, complaint_id: uuid.UUID) -> Complaint:
        complaint = self._repo.get(complaint_id)
        if complaint is None:
            raise NotFound("Complaint", complaint_id)
        return complaint

    def list(self, **filters) -> tuple[list[Complaint], int]:  # type: ignore[no-untyped-def]
        return self._repo.list(**filters)

    def change_status(self, complaint_id: uuid.UUID, target: Status) -> Complaint:
        complaint = self._repo.get_for_update(complaint_id)
        if complaint is None:
            raise NotFound("Complaint", complaint_id)
        ensure_transition(complaint.status, target)    # raises InvalidTransition -> 409
        self._repo.set_status(complaint, target)
        self._repo.commit()
        self._stats.invalidate()
        return complaint
