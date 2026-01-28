"""Knowledge Base Generator for HAAIS-governed agents.

Generates deep, comprehensive knowledge bases with:
- 15-20 structured files per agent
- Regulatory templates (HIPAA, EPA, HUD, etc.)
- City-specific content from discovered data
- Proper HAAIS classification and cross-references
"""

from packages.onboarding.kb_generator.templates import (
    REGULATORY_TEMPLATES,
    DOMAIN_TEMPLATES,
    get_domain_templates,
    get_regulatory_template,
    get_all_regulatory_templates_for_domain,
)
from packages.onboarding.kb_generator.generator import (
    KBGenerator,
    GeneratorConfig,
    generate_knowledge_base,
)
from packages.onboarding.kb_generator.structures import (
    KBFile,
    KBFileType,
    KnowledgeBase,
    HAASISTier,
    Classification,
)

__all__ = [
    # Templates
    "REGULATORY_TEMPLATES",
    "DOMAIN_TEMPLATES",
    "get_domain_templates",
    "get_regulatory_template",
    "get_all_regulatory_templates_for_domain",
    # Generator
    "KBGenerator",
    "GeneratorConfig",
    "generate_knowledge_base",
    # Structures
    "KBFile",
    "KBFileType",
    "KnowledgeBase",
    "HAASISTier",
    "Classification",
]
