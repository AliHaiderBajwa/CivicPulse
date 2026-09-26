import pytest

from app.providers.triage.rules import RuleBasedTriage

triage = RuleBasedTriage()


@pytest.mark.parametrize(
    "text,category,priority",
    [
        ("burst water main flooding street 12", "water", "high"),
        ("load shedding every evening this week", "electricity", "normal"),
        ("sewage overflow near the school gate", "sanitation", "high"),
        ("deep pothole on the main road", "roads", "normal"),
        ("streetlight outside our house is dead", "streetlights", "normal"),
        ("community picnic cancelled by the society", "other", "normal"),
        ("minor pothole, purely cosmetic", "roads", "low"),
    ],
)
def test_rules_table(text, category, priority):
    result = triage.triage(text, "anywhere")
    assert result.category.value == category
    assert result.priority.value == priority


def test_rules_confidence_reflects_keyword_evidence():
    assert triage.triage("water pipe leak", "l").confidence == 0.4
    assert triage.triage("no keywords at all here", "l").confidence == 0.2


def test_rules_summary_is_single_line_and_bounded():
    result = triage.triage("water leak\nin\tthe pipe", "l")
    assert "\n" not in result.summary
    assert "\t" not in result.summary
    assert len(result.summary) <= 140

    long = triage.triage("x" * 300, "l")
    assert len(long.summary) <= 140
