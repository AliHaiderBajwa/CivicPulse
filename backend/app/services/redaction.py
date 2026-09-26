import re

# {1,5} on the label chain: same behaviour for real domains (>=2 labels, <=6
# parts) without the nested unbounded quantifier Sonar flags as super-linear.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+){1,5}")
_CNIC = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)")


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _CNIC.sub("[id]", text)         # before phone: a CNIC is 13 digits and would match the phone rule
    return _PHONE.sub("[phone]", text)
