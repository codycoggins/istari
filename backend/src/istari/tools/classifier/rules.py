"""Rule-based heuristics for content classification (Phase 1 implementation)."""

import re
from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    is_sensitive: bool
    flags: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    confidence: float = 0.0


# --- PII patterns ---
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_NAMED_PERSON_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+"
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Ave|Blvd|Dr|Ln|Rd|Way|Ct|Pl)\b"
)

# --- Financial patterns ---
_CC_RE = re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
_LARGE_DOLLAR_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+(?:\.\d{2})?")
_BANK_KEYWORDS_RE = re.compile(
    r"\b(?:routing\s*number|account\s*number|bank\s*account|wire\s*transfer|SWIFT|IBAN)\b",
    re.IGNORECASE,
)
_ROUTING_NUMBER_RE = re.compile(r"\b\d{9}\b")

# --- Email content patterns ---
_EMAIL_HEADER_RE = re.compile(r"^(?:From|To|Subject|Cc|Bcc):\s+", re.MULTILINE)
_FORWARDED_RE = re.compile(
    r"(?:------\s*Forwarded\s*message|Begin\s*forwarded\s*message)", re.IGNORECASE
)

# --- File/code content patterns ---
_FILE_PATH_RE = re.compile(r"(?:/Users/[^\s]+|/home/[^\s]+|[A-Z]:\\[^\s]+)")
_CODE_PATTERN_RE = re.compile(
    r"(?:^|\s)(?:def\s+\w+|import\s+\w+|from\s+\w+\s+import|function\s+\w+|class\s+\w+)",
    re.MULTILINE,
)

_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    # (flag, rule_name, pattern)
    ("pii", "email_address", _EMAIL_RE),
    ("pii", "phone_number", _PHONE_RE),
    ("pii", "ssn", _SSN_RE),
    ("pii", "named_person", _NAMED_PERSON_RE),
    ("pii", "street_address", _ADDRESS_RE),
    ("financial", "credit_card", _CC_RE),
    ("financial", "large_dollar_amount", _LARGE_DOLLAR_RE),
    ("financial", "bank_keyword", _BANK_KEYWORDS_RE),
    ("financial", "routing_number", _ROUTING_NUMBER_RE),
    ("email_content", "email_header", _EMAIL_HEADER_RE),
    ("email_content", "forwarded_message", _FORWARDED_RE),
    ("file_content", "file_path", _FILE_PATH_RE),
    ("file_content", "code_pattern", _CODE_PATTERN_RE),
]


def classify(text: str) -> ClassificationResult:
    """Classify text for sensitivity using rule-based heuristics.

    Returns a ClassificationResult with matched flags and rules.
    """
    flags: set[str] = set()
    matched_rules: list[str] = []

    for flag, rule_name, pattern in _RULES:
        if pattern.search(text):
            flags.add(flag)
            matched_rules.append(rule_name)

    is_sensitive = len(flags) > 0
    confidence = min(1.0, len(matched_rules) * 0.25) if is_sensitive else 0.0

    return ClassificationResult(
        is_sensitive=is_sensitive,
        flags=sorted(flags),
        matched_rules=matched_rules,
        confidence=confidence,
    )
