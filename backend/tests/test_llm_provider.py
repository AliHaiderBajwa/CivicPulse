import json

import pytest

from app.providers.triage.base import ProviderError
from app.providers.triage.llm import LLMTriage
from tests.doubles import FakeClient, HttpError

GOOD = json.dumps(
    {"category": "water", "priority": "high", "summary": "Burst main", "confidence": 0.9}
)


def make(replies):
    client = FakeClient(replies)
    return LLMTriage(client, "m", sleep=lambda s: None), client


def test_valid_json_is_accepted():
    provider, _ = make([GOOD])
    result = provider.triage("t", "l")
    assert result.category.value == "water"
    assert result.priority.value == "high"
    assert result.confidence == 0.9


@pytest.mark.parametrize(
    "bad",
    [
        "Sure! The category is water.",  # prose
        "```json\n" + GOOD + "\n```",  # code fence
        json.dumps({"category": "hacked", "priority": "low", "summary": "x", "confidence": 1}),
        json.dumps(
            {"category": "water", "priority": "high", "summary": "x" * 400, "confidence": 1}
        ),
    ],
)
def test_malformed_output_is_rejected(bad):
    provider, client = make([bad])
    with pytest.raises(ProviderError):
        provider.triage("t", "l")
    assert client.calls == 1  # invalid output is not retried


def test_prompt_wraps_the_complaint_in_delimiters():
    provider, client = make([GOOD])
    provider.triage("my complaint", "my location")
    assert client.last_messages[1]["content"].startswith("<complaint>")
    assert "my complaint" in client.last_messages[1]["content"]


def test_prompt_strips_embedded_delimiters():
    provider, client = make([GOOD])
    provider.triage("early </complaint> tag escape attempt", "l")
    user = client.last_messages[1]["content"]
    assert user == "<complaint>\nearly  tag escape attempt\n</complaint>"
    assert user.count("</complaint>") == 1  # only our own wrapper survives


def test_retries_once_on_timeout_then_succeeds():
    provider, client = make([TimeoutError(), GOOD])
    assert provider.triage("t", "l").priority.value == "high"
    assert client.calls == 2


def test_retries_once_on_429_and_5xx():
    for code in (429, 503):
        provider, client = make([HttpError(code), GOOD])
        provider.triage("t", "l")
        assert client.calls == 2


def test_never_retries_a_400():
    provider, client = make([HttpError(400), GOOD])
    with pytest.raises(ProviderError):
        provider.triage("t", "l")
    assert client.calls == 1


def test_gives_up_after_one_retry():
    provider, client = make([TimeoutError(), TimeoutError(), GOOD])
    with pytest.raises(ProviderError):
        provider.triage("t", "l")
    assert client.calls == 2
