"""Concierge module for intent classification and risk detection."""

from __future__ import annotations

from packages.core.concierge.classifier import (
    IntentClassifier,
    IntentPattern,
    RiskDetector,
    RiskPattern,
)
from packages.core.schemas.models import Intent, RiskSignals

# Module-level convenience functions
_default_classifier = IntentClassifier()
_default_detector = RiskDetector()


def classify_intent(text: str) -> Intent:
    """Classify intent from text using default classifier."""
    return _default_classifier.classify_intent(text)


def detect_risks(text: str) -> RiskSignals:
    """Detect risks from text using default detector."""
    return _default_detector.detect_risks(text)


__all__ = [
    "IntentClassifier",
    "IntentPattern",
    "RiskDetector",
    "RiskPattern",
    "classify_intent",
    "detect_risks",
]
