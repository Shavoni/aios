"""Router module for provider-agnostic LLM interface."""

from __future__ import annotations

from typing import Any, Protocol

from packages.core.router.claude import ClaudeClient
from packages.core.router.openai_client import OpenAIClient
from packages.core.router.config import RouterSettings
from packages.core.schemas.models import GovernanceDecision, Intent, ProviderConstraints


class LLMClient(Protocol):
    """Protocol for LLM clients."""

    def classify_intent(self, text: str) -> dict[str, Any]: ...
    def generate_response(
        self,
        request_text: str,
        intent_domain: str,
        hitl_mode: str,
        context: str | None = None,
    ) -> dict[str, Any]: ...


class Router:
    """Provider-agnostic router that respects governance constraints."""

    def __init__(self, settings: RouterSettings | None = None) -> None:
        self.settings = settings or RouterSettings()
        self._claude: ClaudeClient | None = None
        self._openai: OpenAIClient | None = None

    @property
    def claude(self) -> ClaudeClient:
        """Get Claude client (lazy loaded)."""
        if self._claude is None:
            self._claude = ClaudeClient(self.settings)
        return self._claude

    @property
    def openai(self) -> OpenAIClient:
        """Get OpenAI client (lazy loaded)."""
        if self._openai is None:
            self._openai = OpenAIClient(self.settings)
        return self._openai

    @property
    def llm(self) -> LLMClient:
        """Get the configured LLM client based on settings."""
        if self.settings.llm_provider == "openai":
            return self.openai
        return self.claude

    def can_use_external_provider(self, constraints: ProviderConstraints) -> bool:
        """Check if external providers can be used given constraints."""
        return not constraints.local_only

    def classify_intent_with_llm(
        self,
        text: str,
        constraints: ProviderConstraints | None = None,
    ) -> Intent:
        """Classify intent using LLM.

        Falls back to rule-based if constraints block external providers.
        """
        if constraints and constraints.local_only:
            # Fall back to rule-based classification
            from packages.core.concierge import classify_intent

            return classify_intent(text)

        if not self.settings.has_api_key:
            # No API key, fall back to rule-based
            from packages.core.concierge import classify_intent

            return classify_intent(text)

        # Use configured LLM for classification
        result = self.llm.classify_intent(text)

        return Intent(
            domain=result.get("domain", "General"),
            task=result.get("task", "unknown"),
            audience=result.get("audience", "internal"),
            impact=result.get("impact", "low"),
            confidence=result.get("confidence", 0.5),
        )

    def generate_response(
        self,
        request_text: str,
        intent: Intent,
        governance: GovernanceDecision,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Generate a response respecting governance constraints.

        Args:
            request_text: The user's request
            intent: Classified intent
            governance: Governance decision with constraints

        Returns:
            Response dict with text and metadata
        """
        # Check if we can use external providers
        if governance.provider_constraints.local_only:
            return {
                "text": "[Local-only mode: External AI providers blocked due to data sensitivity. "
                "Please use approved local resources or contact your administrator.]",
                "model": "none",
                "hitl_mode": governance.hitl_mode.value,
                "requires_approval": True,
                "blocked_reason": "local_only_constraint",
            }

        if not self.settings.has_api_key:
            return {
                "text": "[AI response unavailable: No API key configured]",
                "model": "none",
                "hitl_mode": governance.hitl_mode.value,
                "requires_approval": True,
                "blocked_reason": "no_api_key",
            }

        # Check HITL mode
        if governance.hitl_mode.value == "ESCALATE":
            return {
                "text": f"[ESCALATED] This request requires human review.\n"
                f"Reason: {governance.escalation_reason or 'Policy trigger'}\n"
                f"Domain: {intent.domain}\n"
                f"Please route to appropriate department for handling.",
                "model": "none",
                "hitl_mode": "ESCALATE",
                "requires_approval": True,
                "blocked_reason": "escalation_required",
            }

        # Generate response with configured LLM
        return self.llm.generate_response(
            request_text=request_text,
            intent_domain=intent.domain,
            hitl_mode=governance.hitl_mode.value,
            context=context,
        )


# Module-level convenience instance
_default_router: Router | None = None


def get_router() -> Router:
    """Get the default router instance."""
    global _default_router
    if _default_router is None:
        _default_router = Router()
    return _default_router


__all__ = [
    "ClaudeClient",
    "OpenAIClient",
    "Router",
    "RouterSettings",
    "get_router",
]
