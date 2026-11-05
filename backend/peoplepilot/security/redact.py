"""PII redaction for logs and stored message text.

Order matters: Aadhaar (12 digits) and UAN (12 digits) are matched before generic phones.
This is a regex baseline; for Phase 2 free-text HR data, add Microsoft Presidio on top.
"""
from __future__ import annotations

import logging
import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[PAN]"),  # PAN is 10 chars
    (re.compile(r"\b(?:UAN|uan)[\s:#-]*\d{12}\b"), "[UAN]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), "[IFSC]"),
    (re.compile(r"(?:\+?91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"), "[PHONE]"),
    (re.compile(r"\+\d{1,3}[\s-]?\d{6,12}\b"), "[PHONE]"),
    (re.compile(r"\b\d{9,18}\b"), "[NUMBER]"),  # long numbers: bank accounts etc.
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def mask_phone(last4: str) -> str:
    return f"+91 ••••••{last4}"


class RedactingFilter(logging.Filter):
    """Attach to every handler so no log line can carry raw PII."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # pragma: no cover - malformed log call
            return True
        record.msg = redact(msg)
        record.args = ()
        return True


def install_log_redaction() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for handler in root.handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter())
