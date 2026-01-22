"""Claude API client wrapper."""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from packages.core.router.config import RouterSettings


class ClaudeClient:
    """Wrapper for Claude API interactions."""

    def __init__(self, settings: RouterSettings | None = None) -> None:
        self.settings = settings or RouterSettings()
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            if not self.settings.has_anthropic_key:
                raise ValueError("Anthropic API key not configured")
            self._client = Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response from Claude.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            model: Model to use (defaults to settings)
            max_tokens: Max tokens (defaults to settings)
            temperature: Temperature (defaults to settings)

        Returns:
            The generated text response
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        kwargs: dict[str, Any] = {
            "model": model or self.settings.default_model,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if temperature is not None:
            kwargs["temperature"] = temperature
        elif self.settings.temperature is not None:
            kwargs["temperature"] = self.settings.temperature

        response = self.client.messages.create(**kwargs)

        # Extract text from response
        if response.content and len(response.content) > 0:
            content_block = response.content[0]
            if hasattr(content_block, "text"):
                return str(content_block.text)
        return ""

    def classify_intent(self, text: str) -> dict[str, Any]:
        """Use Claude to classify intent from text.

        Returns structured intent classification.
        """
        system = """You are an intent classifier for an enterprise AI system.
Analyze the user's request and classify it.

Respond ONLY with valid JSON in this exact format:
{
    "domain": "<Comms|Legal|HR|Finance|General>",
    "task": "<specific_task>",
    "audience": "<internal|public>",
    "impact": "<low|medium|high>",
    "confidence": <0.0-1.0>
}

Domain definitions:
- Comms: Public relations, announcements, press releases, external communications
- Legal: Contracts, NDAs, legal review, compliance questions
- HR: Employee information, policies, hiring, performance
- Finance: Budgets, reports, payments, financial data
- General: Everything else

Impact levels:
- high: External visibility, legal implications, employment decisions
- medium: Internal processes, moderate business impact
- low: Informational, no significant consequences"""

        prompt = f"Classify this request:\n\n{text}"

        response = self.generate(prompt, system=system, temperature=0.1)

        # Parse JSON response
        import json

        try:
            # Find JSON in response (handle markdown code blocks)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            parsed: dict[str, Any] = json.loads(json_str.strip())
            return parsed
        except (json.JSONDecodeError, IndexError):
            # Fallback to default
            return {
                "domain": "General",
                "task": "unknown",
                "audience": "internal",
                "impact": "low",
                "confidence": 0.5,
            }

    def generate_response(
        self,
        request_text: str,
        intent_domain: str,
        hitl_mode: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Generate an agent response with governance awareness.

        Args:
            request_text: The user's original request
            intent_domain: Classified domain (Comms, Legal, etc.)
            hitl_mode: Governance mode (INFORM, DRAFT, ESCALATE)
            context: Optional additional context

        Returns:
            Dict with response text and metadata
        """
        mode_instructions = {
            "INFORM": "Provide helpful information only. Do not draft content or take actions.",
            "DRAFT": "Create a draft response that will require human approval before use.",
            "ESCALATE": "This request requires human review. Explain why and what information would help.",
        }

        system = f"""You are an AI assistant operating under enterprise governance.

Domain: {intent_domain}
Mode: {hitl_mode}
Instructions: {mode_instructions.get(hitl_mode, mode_instructions['INFORM'])}

Guidelines:
- Be helpful but stay within governance boundaries
- If in DRAFT mode, clearly label your response as a draft
- If in ESCALATE mode, explain what human review is needed
- Always be professional and accurate
- Cite sources when making factual claims"""

        prompt = request_text
        if context:
            prompt = f"Context:\n{context}\n\nRequest:\n{request_text}"

        response_text = self.generate(prompt, system=system)

        return {
            "text": response_text,
            "model": self.settings.default_model,
            "hitl_mode": hitl_mode,
            "requires_approval": hitl_mode in ("DRAFT", "ESCALATE"),
        }
