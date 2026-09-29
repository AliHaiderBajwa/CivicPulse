from openai import OpenAI

from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def build_provider(s: Settings) -> TriageProvider:
    provider: TriageProvider
    if s.triage_provider == "rules":
        provider = RuleBasedTriage()
    elif s.triage_provider == "simulated":
        provider = SimulatedTriage(s.simulated_fail_mode, s.simulated_delay_s)
    elif s.triage_provider == "ollama":
        client = OpenAI(
            api_key="ollama", base_url=s.ollama_url, timeout=s.llm_timeout_s, max_retries=0
        )
        provider = OllamaTriage(client=client, model=s.ollama_model)
    else:
        client = OpenAI(
            api_key=s.llm_api_key.get_secret_value() or "missing",
            base_url=s.llm_base_url, timeout=s.llm_timeout_s, max_retries=0,
        )
        provider = LLMTriage(client=client, model=s.llm_model, name=s.llm_label)
    return provider
