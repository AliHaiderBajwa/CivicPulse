from typing import Any

from app.providers.triage.llm import LLMTriage


class OllamaTriage(LLMTriage):
    """Ollama exposes an OpenAI-compatible endpoint: same logic, other base_url."""

    def __init__(self, client: Any, model: str, **kwargs: Any) -> None:
        super().__init__(client=client, model=model, name="llm:ollama", **kwargs)
