"""Intent classification and risk detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from re import Pattern

from packages.core.schemas.models import Intent, RiskSignals


@dataclass
class IntentPattern:
    """Pattern for intent classification."""

    domain: str
    task: str
    audience: str = "internal"
    impact: str = "low"
    patterns: list[Pattern[str]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class RiskPattern:
    """Pattern for risk detection."""

    signal: str
    patterns: list[Pattern[str]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# Default intent patterns
DEFAULT_INTENT_PATTERNS: list[IntentPattern] = [
    IntentPattern(
        domain="Comms",
        task="draft_statement",
        audience="public",
        impact="high",
        patterns=[
            re.compile(r"public\s+statement", re.IGNORECASE),
            re.compile(r"press\s+release", re.IGNORECASE),
            re.compile(r"public\s+announcement", re.IGNORECASE),
        ],
        keywords=["public", "statement", "announcement", "press"],
    ),
    IntentPattern(
        domain="Legal",
        task="contract_review",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"review\s+.{0,20}contract", re.IGNORECASE),
            re.compile(r"contract\s+.{0,20}review", re.IGNORECASE),
            re.compile(r"(nda|agreement|legal)", re.IGNORECASE),
        ],
        keywords=["contract", "review", "legal", "nda", "agreement"],
    ),
    IntentPattern(
        domain="HR",
        task="lookup_employee",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"employee\s+.{0,20}(info|information|lookup|look\s*up)", re.IGNORECASE),
            re.compile(r"look\s*up\s+.{0,20}employee", re.IGNORECASE),
        ],
        keywords=["employee", "lookup", "information", "staff"],
    ),
    IntentPattern(
        domain="Finance",
        task="generate_report",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"financial\s+report", re.IGNORECASE),
            re.compile(r"(q[1-4]|quarterly)\s+.{0,20}report", re.IGNORECASE),
        ],
        keywords=["financial", "report", "quarterly", "budget"],
    ),
    IntentPattern(
        domain="General",
        task="answer_question",
        audience="internal",
        impact="low",
        patterns=[
            re.compile(r"what\s+is", re.IGNORECASE),
            re.compile(r"how\s+(do|does|can)", re.IGNORECASE),
        ],
        keywords=["what", "how", "why", "when", "where"],
    ),
]


# Default risk patterns
DEFAULT_RISK_PATTERNS: list[RiskPattern] = [
    RiskPattern(
        signal="PII",
        patterns=[
            re.compile(r"social\s+security", re.IGNORECASE),
            re.compile(r"(home\s+)?address", re.IGNORECASE),
            re.compile(r"salary", re.IGNORECASE),
            re.compile(r"personal\s+.{0,10}(info|information|data)", re.IGNORECASE),
        ],
        keywords=["ssn", "social security", "address", "salary", "personal"],
    ),
    RiskPattern(
        signal="LEGAL_CONTRACT",
        patterns=[
            re.compile(r"(nda|contract|agreement)", re.IGNORECASE),
            re.compile(r"legal\s+.{0,10}(review|document)", re.IGNORECASE),
        ],
        keywords=["contract", "nda", "agreement", "legal"],
    ),
    RiskPattern(
        signal="PUBLIC_STATEMENT",
        patterns=[
            re.compile(r"public\s+(statement|announcement)", re.IGNORECASE),
            re.compile(r"press\s+release", re.IGNORECASE),
        ],
        keywords=["public statement", "press release", "announcement"],
    ),
    RiskPattern(
        signal="FINANCIAL",
        patterns=[
            re.compile(r"wire\s+transfer", re.IGNORECASE),
            re.compile(r"payment", re.IGNORECASE),
            re.compile(r"invoice", re.IGNORECASE),
        ],
        keywords=["wire transfer", "payment", "invoice", "transaction"],
    ),
]


class IntentClassifier:
    """Classifies user requests into intents."""

    def __init__(self, patterns: list[IntentPattern] | None = None) -> None:
        self.patterns = patterns if patterns is not None else DEFAULT_INTENT_PATTERNS

    def classify_intent(self, text: str) -> Intent:
        """Classify the intent of a text input."""
        if not text or not text.strip():
            return Intent(domain="General", task="unknown", confidence=0.1)

        text_lower = text.lower()
        best_match: IntentPattern | None = None
        best_score = 0.0

        for pattern in self.patterns:
            score = self._score_pattern(text, text_lower, pattern)
            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match and best_score > 0.2:
            confidence = min(0.95, best_score)
            return Intent(
                domain=best_match.domain,
                task=best_match.task,
                audience=best_match.audience,
                impact=best_match.impact,
                confidence=confidence,
            )

        return Intent(domain="General", task="unknown", confidence=0.1)

    def _score_pattern(self, text: str, text_lower: str, pattern: IntentPattern) -> float:
        """Score how well a pattern matches the text."""
        score = 0.0

        # Check regex patterns (higher weight)
        for regex in pattern.patterns:
            if regex.search(text):
                score += 0.4

        # Check keywords (lower weight)
        for keyword in pattern.keywords:
            if keyword.lower() in text_lower:
                score += 0.15

        return min(1.0, score)


class RiskDetector:
    """Detects risk signals in user requests."""

    def __init__(self, patterns: list[RiskPattern] | None = None) -> None:
        self.patterns = patterns if patterns is not None else DEFAULT_RISK_PATTERNS

    def detect_risks(self, text: str) -> RiskSignals:
        """Detect risk signals in text."""
        if not text or not text.strip():
            return RiskSignals(signals=[])

        text_lower = text.lower()
        detected: list[str] = []

        for pattern in self.patterns:
            if self._matches_pattern(text, text_lower, pattern):
                detected.append(pattern.signal)

        return RiskSignals(signals=detected)

    def _matches_pattern(self, text: str, text_lower: str, pattern: RiskPattern) -> bool:
        """Check if pattern matches text."""
        # Check regex patterns
        for regex in pattern.patterns:
            if regex.search(text):
                return True

        # Check keywords
        return any(keyword.lower() in text_lower for keyword in pattern.keywords)
