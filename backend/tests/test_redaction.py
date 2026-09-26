from app.services.redaction import redact


def test_pii_is_replaced():
    out = redact("user@example.com 35202-1234567-1 0300-1234567")
    assert out == "[email] [id] [phone]"
    assert "user@example.com" not in out
    assert "35202-1234567-1" not in out
    assert "0300-1234567" not in out


def test_ordinary_text_is_untouched():
    text = "The park gate opens at nine in the morning"
    assert redact(text) == text


def test_email_with_subdomains_and_tags():
    out = redact("write to first.last+tag@sub.domain.co.uk please")
    assert "[email]" in out
    assert "@" not in out


def test_contact_line_is_fully_redacted():
    out = redact("reach me at a@b.co or 0300-1234567")
    assert out == "reach me at [email] or [phone]"


def test_hostile_at_less_input_is_returned_verbatim():
    hostile = "a" * 5000
    assert redact(hostile) == hostile
