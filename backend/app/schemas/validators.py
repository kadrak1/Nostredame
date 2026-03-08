"""Shared Pydantic field validators."""


def validate_phone(v: str) -> str:
    """Validate and normalise a phone number (10–15 digits required)."""
    digits = "".join(c for c in v if c.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Номер телефона должен содержать 10–15 цифр")
    return v.strip()
