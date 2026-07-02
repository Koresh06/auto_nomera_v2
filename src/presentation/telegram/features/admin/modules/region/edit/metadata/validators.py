import re

URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}"
    r"(?:/[^\s]*)?$"
)


def validate_url(value: str) -> str:
    cleaned = value.strip()

    if cleaned == "-":
        return cleaned

    if not URL_PATTERN.match(cleaned):
        raise ValueError("Некорректная ссылка")

    return cleaned