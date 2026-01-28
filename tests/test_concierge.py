"""Unit tests for the Concierge module."""

import pytest

from packages.core.concierge import (
    IntentClassifier,
    RiskDetector,
    classify_intent,
    detect_risks,
)
from packages.core.schemas.models import Intent, RiskSignals


# ============================================================================
# Test: classify_intent
# ============================================================================

class TestClassifyIntent:
    """Test intent classification."""

    def test_public_statement_classifies_as_comms(self):
        """Public statement should classify as Comms domain with public audience."""
        text = "Draft a public statement about a partnership."

        intent = classify_intent(text)

        assert intent.domain == "Comms"
        assert intent.task == "draft_statement"
        assert intent.audience == "public"
        assert intent.impact == "high"
        assert intent.confidence >= 0.5

    def test_contract_review_classifies_as_legal(self):
        """Contract review should classify as Legal domain."""
        text = "Please review this contract for the vendor agreement."

        intent = classify_intent(text)

        assert intent.domain == "Legal"
        assert intent.task == "contract_review"
        assert intent.audience == "internal"
        assert intent.impact == "high"

    def test_employee_lookup_classifies_as_hr(self):
        """Employee lookup should classify as HR domain."""
        text = "Look up employee information for John Smith."

        intent = classify_intent(text)

        assert intent.domain == "HR"
        assert intent.task == "lookup_employee"
        assert intent.audience == "internal"

    def test_financial_report_classifies_as_finance(self):
        """Financial report should classify as Finance domain."""
        text = "Generate a financial report for Q3."

        intent = classify_intent(text)

        assert intent.domain == "Finance"
        assert intent.task == "generate_report"

    def test_general_question_classifies_as_general(self):
        """General question should classify as General domain."""
        text = "What is the weather like today?"

        intent = classify_intent(text)

        assert intent.domain == "General"
        assert intent.task == "answer_question"
        assert intent.audience == "internal"
        assert intent.impact == "low"

    def test_unknown_text_returns_low_confidence(self):
        """Unknown text should return low confidence."""
        text = "Xyz abc 123"

        intent = classify_intent(text)

        assert intent.confidence < 0.3
        assert intent.domain == "General"
        assert intent.task == "unknown"


# ============================================================================
# Test: detect_risks
# ============================================================================

class TestDetectRisks:
    """Test risk signal detection."""

    def test_detects_pii_signals(self):
        """Should detect PII risk signals."""
        text = "Please look up the employee's social security number and home address."

        risk = detect_risks(text)

        assert "PII" in risk.signals

    def test_detects_legal_contract_signals(self):
        """Should detect legal contract risk signals."""
        text = "Review this NDA agreement before signing the contract."

        risk = detect_risks(text)

        assert "LEGAL_CONTRACT" in risk.signals

    def test_detects_public_statement_signals(self):
        """Should detect public statement risk signals."""
        text = "Draft a public statement for the press release."

        risk = detect_risks(text)

        assert "PUBLIC_STATEMENT" in risk.signals

    def test_detects_financial_signals(self):
        """Should detect financial risk signals."""
        text = "Process this wire transfer payment for the invoice."

        risk = detect_risks(text)

        assert "FINANCIAL" in risk.signals

    def test_detects_multiple_risk_signals(self):
        """Should detect multiple risk signals."""
        text = "Draft a public statement about the employee's salary information."

        risk = detect_risks(text)

        assert "PUBLIC_STATEMENT" in risk.signals
        assert "PII" in risk.signals

    def test_no_risk_signals_for_safe_text(self):
        """Safe text should have no risk signals."""
        text = "What is the capital of France?"

        risk = detect_risks(text)

        assert len(risk.signals) == 0


# ============================================================================
# Test: IntentClassifier class
# ============================================================================

class TestIntentClassifierClass:
    """Test IntentClassifier class directly."""

    def test_classifier_instance(self):
        """Should be able to create classifier instance."""
        classifier = IntentClassifier()
        assert classifier is not None
        assert len(classifier.patterns) > 0

    def test_custom_patterns(self):
        """Should support custom patterns."""
        from packages.core.concierge.classifier import IntentPattern
        import re

        custom_patterns = [
            IntentPattern(
                domain="Custom",
                task="custom_task",
                audience="internal",
                impact="low",
                patterns=[re.compile(r"custom\s+keyword", re.IGNORECASE)],
                keywords=["custom", "keyword"],
            )
        ]

        classifier = IntentClassifier(patterns=custom_patterns)
        intent = classifier.classify_intent("This has custom keyword in it.")

        assert intent.domain == "Custom"
        assert intent.task == "custom_task"


# ============================================================================
# Test: RiskDetector class
# ============================================================================

class TestRiskDetectorClass:
    """Test RiskDetector class directly."""

    def test_detector_instance(self):
        """Should be able to create detector instance."""
        detector = RiskDetector()
        assert detector is not None
        assert len(detector.patterns) > 0

    def test_risk_signals_contains_method(self):
        """RiskSignals.contains() should work correctly."""
        risk = RiskSignals(signals=["PII", "LEGAL_CONTRACT"])

        assert risk.contains("PII") is True
        assert risk.contains("LEGAL_CONTRACT") is True
        assert risk.contains("FINANCIAL") is False


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_input(self):
        """Empty string should return low confidence default."""
        intent = classify_intent("")
        risk = detect_risks("")

        assert intent.confidence < 0.3
        assert len(risk.signals) == 0

    def test_case_insensitivity(self):
        """Classification should be case insensitive."""
        intent1 = classify_intent("PUBLIC STATEMENT")
        intent2 = classify_intent("public statement")
        intent3 = classify_intent("Public Statement")

        assert intent1.domain == intent2.domain == intent3.domain == "Comms"

    def test_partial_matches(self):
        """Partial keyword matches should still work."""
        text = "We need to draft a public announcement about the partnership."

        intent = classify_intent(text)

        assert intent.domain == "Comms"
        assert intent.audience == "public"

    def test_multiple_domain_signals(self):
        """When multiple domains match, highest scoring should win."""
        # This text has both Comms and Legal signals
        text = "Draft a public statement about the legal contract agreement."

        intent = classify_intent(text)

        # Should pick one domain (highest scoring)
        assert intent.domain in ["Comms", "Legal"]
        assert intent.confidence > 0.3
