import time

from app.providers.triage.base import ProviderError, TriageResult
from app.providers.triage.rules import RuleBasedTriage

_RULES = RuleBasedTriage()


class SimulatedTriage:
    name = "simulated"

    def __init__(self, fail_mode: str = "none", delay_s: float = 0.0) -> None:
        self.fail_mode = fail_mode
        self.delay_s = delay_s

    def triage(self, text: str, location: str) -> TriageResult:
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.fail_mode == "raise":
            raise ProviderError("simulated provider failure")
        if self.fail_mode == "malformed":
            raise ProviderError("simulated malformed output")
        return _RULES.triage(text, location).model_copy(update={"confidence": 0.99})
