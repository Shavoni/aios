"""Prompt template framework for aiOS."""

from packages.core.llm.prompts.base import PromptTemplate, PromptEngine
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

__all__ = [
    "PromptTemplate",
    "PromptEngine",
    "DiscoveryExtractionPrompt",
    "DataSourceDetectionPrompt",
    "KBGenerationPrompt",
    "RegulatoryContentPrompt",
    "GovernanceJudgePrompt",
    "RiskAssessmentPrompt",
]
