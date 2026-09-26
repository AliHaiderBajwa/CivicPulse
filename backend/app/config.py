from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Required, no defaults: a missing value fails loudly and no "localhost" sneaks in.
    database_url: str
    redis_url: str

    triage_provider: Literal["llm", "ollama", "rules", "simulated"] = "rules"
    llm_api_key: SecretStr = SecretStr("")  # SecretStr: never appears in repr or logs
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.1-8b-instant"
    llm_label: str = "llm:groq"  # value stored in triaged_by for the hosted provider
    ollama_url: str = "http://ollama:11434/v1"
    ollama_model: str = "llama3.2:1b"
    llm_timeout_s: float = 10.0
    rate_limit_per_min: int = 10
    stats_ttl_s: int = 30
    triage_cache_ttl_s: int = 86400  # 24 h
    simulated_fail_mode: Literal["none", "raise", "malformed"] = "none"
    simulated_delay_s: float = 0.0  # lets you demo SIGTERM draining
    log_level: str = "INFO"
