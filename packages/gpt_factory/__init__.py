"""
HAAIS GPT Factory

Enterprise pipeline for automated Custom GPT generation.
Transforms organizational discovery into deployment-ready agent configurations.

Pipeline:
    DISCOVER -> RESEARCH -> GENERATE -> VALIDATE -> PACKAGE

Features:
    - AIOS-native: No artificial limits on instructions or knowledge
    - Archetype-driven: Domain-specific templates accelerate creation
    - Human checkpoints: Quality gates at critical stages
    - Multi-target export: AIOS, OpenAI GPTs, Azure, local LLMs
"""

from .models import (
    Organization,
    OrganizationType,
    AgentCandidate,
    CandidateType,
    AgentBlueprint,
    KnowledgeSource,
    SourceType,
    AuthorityLevel,
    ValidationReport,
    ExportTarget,
)

from .factory import GPTFactory
from .archetypes import ArchetypeRegistry
from .templates import TemplateEngine
from .validation import AgentValidator
from .exporters import ExportManager

__all__ = [
    # Models
    "Organization",
    "OrganizationType",
    "AgentCandidate",
    "CandidateType",
    "AgentBlueprint",
    "KnowledgeSource",
    "SourceType",
    "AuthorityLevel",
    "ValidationReport",
    "ExportTarget",
    # Components
    "GPTFactory",
    "ArchetypeRegistry",
    "TemplateEngine",
    "AgentValidator",
    "ExportManager",
]

__version__ = "1.0.0"
