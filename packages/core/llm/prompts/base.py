"""Base prompt template classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core.llm.adapters.base import ModelAdapter


@dataclass
class PromptTemplate(ABC):
    """Base class for aiOS prompt templates.

    Templates are model-agnostic - they define WHAT the model should do,
    not HOW (which varies by model architecture).

    Subclasses should:
    1. Define a TEMPLATE class variable with the prompt template
    2. Implement required_context listing required context keys
    3. Optionally override quality_criteria for validation
    """

    template_id: str
    purpose: str
    output_format: str = "text"  # text, json, markdown
    max_tokens: int = 4000
    temperature: float = 0.7
    required_context: list[str] = field(default_factory=list)
    quality_criteria: list[str] = field(default_factory=list)

    # Subclasses should override this
    TEMPLATE: str = ""

    def render(
        self,
        context: dict[str, Any],
        adapter: "ModelAdapter | None" = None,
    ) -> str:
        """Render the prompt with context values.

        Args:
            context: Dict of context values to inject
            adapter: Optional adapter for model-specific optimization

        Returns:
            Rendered prompt string
        """
        # Validate required context
        missing = [k for k in self.required_context if k not in context]
        if missing:
            raise ValueError(f"Missing required context keys: {missing}")

        # Render template
        prompt = self.TEMPLATE.format(**context)

        # Apply model-specific optimization if adapter provided
        if adapter:
            prompt = adapter.optimize_prompt(prompt, self)

        return prompt

    def get_system_prompt(self) -> str | None:
        """Get optional system prompt for this template.

        Override in subclasses to provide a system prompt.
        """
        return None


class PromptEngine:
    """Engine for managing and rendering prompt templates.

    Provides template registration, retrieval, and rendering
    with caching and validation.
    """

    _instance: PromptEngine | None = None

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}
        self._register_defaults()

    @classmethod
    def get_instance(cls) -> PromptEngine:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_defaults(self) -> None:
        """Register default prompt templates."""
        # Import here to avoid circular imports
        from packages.core.llm.prompts.discovery import (
            DiscoveryExtractionPrompt,
            DataSourceDetectionPrompt,
        )
        from packages.core.llm.prompts.kb_generation import (
            KBGenerationPrompt,
            RegulatoryContentPrompt,
        )
        from packages.core.llm.prompts.governance import (
            GovernanceJudgePrompt,
            RiskAssessmentPrompt,
        )

        default_templates = [
            DiscoveryExtractionPrompt(),
            DataSourceDetectionPrompt(),
            KBGenerationPrompt(),
            RegulatoryContentPrompt(),
            GovernanceJudgePrompt(),
            RiskAssessmentPrompt(),
        ]

        for template in default_templates:
            self.register(template)

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> PromptTemplate:
        """Get a template by ID."""
        if template_id not in self._templates:
            raise KeyError(f"Template not found: {template_id}")
        return self._templates[template_id]

    def render(
        self,
        template_id: str,
        context: dict[str, Any],
        adapter: "ModelAdapter | None" = None,
    ) -> str:
        """Render a template with context.

        Args:
            template_id: ID of template to render
            context: Context values
            adapter: Optional model adapter for optimization

        Returns:
            Rendered prompt string
        """
        template = self.get(template_id)
        return template.render(context, adapter)

    def list_templates(self) -> list[str]:
        """List all registered template IDs."""
        return list(self._templates.keys())

    def get_template_info(self, template_id: str) -> dict[str, Any]:
        """Get information about a template."""
        template = self.get(template_id)
        return {
            "id": template.template_id,
            "purpose": template.purpose,
            "output_format": template.output_format,
            "required_context": template.required_context,
            "quality_criteria": template.quality_criteria,
        }


def get_prompt_engine() -> PromptEngine:
    """Get the singleton prompt engine."""
    return PromptEngine.get_instance()
