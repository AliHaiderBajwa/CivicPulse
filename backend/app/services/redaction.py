import re

# Possessive quantifiers (`++`, `{1,5}+`): Python 3.11+ forbids backtracking
# into matched runs, so this is linear on hostile input while keeping the exact
# match set of the original nested-quantifier pattern (Sonar S8786).
_EMAIL = re.compile(r"[\w.+-]++@[\w-]++(?:\.[\w-]+){1,5}+")
_CNIC = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)")


def redact(text: str) -> str:
    # The email pattern requires '@'; without it no match is possible, so skip
    # the scan entirely (keeps hostile @-less input linear).
    if "@" in text:
        text = _EMAIL.sub("[email]", text)
    text = _CNIC.sub("[id]", text)         # before phone: a CNIC is 13 digits and would match the phone rule
    return _PHONE.sub("[phone]", text)
