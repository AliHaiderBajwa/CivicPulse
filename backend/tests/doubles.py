from types import SimpleNamespace


class AlwaysRaises:
    name = "llm:groq"

    def triage(self, text, location):
        raise TimeoutError("provider down")


class FakeClient:
    """Stands in for the OpenAI client. `replies` are returned (or raised) one per call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.last_messages = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        self.last_messages = kwargs["messages"]
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])


class HttpError(Exception):
    def __init__(self, status_code):
        super().__init__(f"http {status_code}")
        self.status_code = status_code


class CountingProvider:
    """Counts triage calls; must carry a TriagedBy-legal name for response validation."""

    name = "simulated"

    def __init__(self):
        self.calls = 0

    def triage(self, text, location):
        self.calls += 1
        from app.providers.triage.rules import RuleBasedTriage

        return RuleBasedTriage().triage(text, location)


class FlakyProvider:
    """Fails the first call, then succeeds — proves a fallback result is never cached."""

    name = "simulated"

    def __init__(self):
        self.calls = 0

    def triage(self, text, location):
        self.calls += 1
        from app.providers.triage.rules import RuleBasedTriage

        if self.calls == 1:
            raise TimeoutError("first call dies")
        return RuleBasedTriage().triage(text, location)
