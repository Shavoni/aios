"""Concierge module for intent classification, risk detection, and agent routing."""

from __future__ import annotations

from packages.core.concierge.classifier import (
    AgentRouter,
    DOMAIN_TO_AGENT_MAP,
    IntentClassifier,
    IntentPattern,
    RiskDetector,
    RiskPattern,
    RoutingResult,
)
from packages.core.schemas.models import Intent, RiskSignals

# Module-level convenience instances
_default_classifier = IntentClassifier()
_default_detector = RiskDetector()
_default_router: AgentRouter | None = None


def classify_intent(text: str) -> Intent:
    """Classify intent from text using default classifier."""
    return _default_classifier.classify_intent(text)


def detect_risks(text: str) -> RiskSignals:
    """Detect risks from text using default detector."""
    return _default_detector.detect_risks(text)


def get_agent_router() -> AgentRouter:
    """Get the default agent router singleton."""
    global _default_router
    if _default_router is None:
        _default_router = AgentRouter(classifier=_default_classifier)
    return _default_router


def route_to_agent(
    text: str, available_agents: list[str] | None = None
) -> RoutingResult:
    """Route a query to the appropriate agent.

    Args:
        text: The user's query
        available_agents: Optional list of available agent IDs

    Returns:
        RoutingResult with primary agent, alternatives, and confidence
    """
    return get_agent_router().route(text, available_agents)


__all__ = [
    "AgentRouter",
    "DOMAIN_TO_AGENT_MAP",
    "IntentClassifier",
    "IntentPattern",
    "RiskDetector",
    "RiskPattern",
    "RoutingResult",
    "classify_intent",
    "detect_risks",
    "get_agent_router",
    "route_to_agent",
]
