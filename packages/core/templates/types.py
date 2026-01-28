"""Template types and structures for agent generation.

Provides the foundational types for the template matching system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TemplateDomain(str, Enum):
    """Standard municipal/organizational domains."""

    # Core Government
    EXECUTIVE = "executive"
    LEGISLATIVE = "legislative"
    JUDICIAL = "judicial"

    # Public Services
    PUBLIC_SAFETY = "public_safety"
    PUBLIC_HEALTH = "public_health"
    PUBLIC_WORKS = "public_works"
    UTILITIES = "utilities"

    # Administrative
    FINANCE = "finance"
    HR = "human_resources"
    IT = "information_technology"
    LEGAL = "legal"

    # Community Services
    PARKS_RECREATION = "parks_recreation"
    COMMUNITY_DEVELOPMENT = "community_development"
    HOUSING = "housing"
    SOCIAL_SERVICES = "social_services"

    # Communications
    COMMUNICATIONS = "communications"
    PUBLIC_AFFAIRS = "public_affairs"

    # Planning
    PLANNING = "planning"
    ECONOMIC_DEVELOPMENT = "economic_development"

    # Special
    ROUTER = "router"
    STRATEGY = "strategy"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class TemplateComplexity(str, Enum):
    """Template complexity levels."""

    BASIC = "basic"  # Simple FAQ/information bot
    STANDARD = "standard"  # Department assistant
    ADVANCED = "advanced"  # Cross-functional capabilities
    ENTERPRISE = "enterprise"  # High-stakes, regulatory


class HITLRequirement(str, Enum):
    """Human-in-the-loop requirements."""

    INFORM = "inform"  # AI acts, logs for human review
    DRAFT = "draft"  # AI drafts, human approves
    ESCALATE = "escalate"  # AI identifies, human handles


@dataclass
class TemplateCapability:
    """A capability that a template provides."""

    name: str
    description: str
    requires_data_source: bool = False
    data_source_types: list[str] = field(default_factory=list)
    hitl_mode: HITLRequirement = HITLRequirement.INFORM


@dataclass
class TemplateGuardrail:
    """A guardrail for a template."""

    rule: str
    severity: str = "block"  # block, warn, log
    category: str = "general"  # general, legal, financial, operational


@dataclass
class AgentTemplate:
    """A pre-built template for generating AI agents.

    Templates capture common patterns for specific organizational
    domains and can be customized during agent generation.
    """

    # Identity
    template_id: str
    name: str
    description: str
    version: str = "1.0.0"

    # Classification
    domain: TemplateDomain = TemplateDomain.CUSTOM
    complexity: TemplateComplexity = TemplateComplexity.STANDARD
    tags: list[str] = field(default_factory=list)

    # Capabilities
    capabilities: list[TemplateCapability] = field(default_factory=list)
    capability_names: list[str] = field(default_factory=list)  # Simple string list

    # Governance
    guardrails: list[TemplateGuardrail] = field(default_factory=list)
    guardrail_rules: list[str] = field(default_factory=list)  # Simple string list
    default_hitl_mode: HITLRequirement = HITLRequirement.INFORM
    requires_approval_for: list[str] = field(default_factory=list)

    # Configuration
    system_prompt_template: str = ""
    required_context: list[str] = field(default_factory=list)
    optional_context: list[str] = field(default_factory=list)
    suggested_data_sources: list[str] = field(default_factory=list)

    # Escalation
    default_escalation_path: str = "Department Head"

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    author: str = "system"
    is_builtin: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "domain": self.domain.value if isinstance(self.domain, TemplateDomain) else self.domain,
            "complexity": self.complexity.value if isinstance(self.complexity, TemplateComplexity) else self.complexity,
            "tags": self.tags,
            "capabilities": self.capability_names or [c.name for c in self.capabilities],
            "guardrails": self.guardrail_rules or [g.rule for g in self.guardrails],
            "default_hitl_mode": self.default_hitl_mode.value if isinstance(self.default_hitl_mode, HITLRequirement) else self.default_hitl_mode,
            "requires_approval_for": self.requires_approval_for,
            "system_prompt_template": self.system_prompt_template,
            "default_escalation_path": self.default_escalation_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentTemplate:
        """Create from dictionary."""
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            domain=TemplateDomain(data.get("domain", "custom")),
            complexity=TemplateComplexity(data.get("complexity", "standard")),
            tags=data.get("tags", []),
            capability_names=data.get("capabilities", []),
            guardrail_rules=data.get("guardrails", []),
            default_hitl_mode=HITLRequirement(data.get("default_hitl_mode", "inform")),
            requires_approval_for=data.get("requires_approval_for", []),
            system_prompt_template=data.get("system_prompt_template", ""),
            default_escalation_path=data.get("default_escalation_path", "Department Head"),
            is_builtin=data.get("is_builtin", False),
        )


@dataclass
class MatchResult:
    """Result from template matching."""

    template: AgentTemplate
    confidence: float  # 0.0 to 1.0
    match_reasons: list[str]
    missing_requirements: list[str]
    customization_suggestions: list[str]
    domain_match: bool
    capability_coverage: float  # Percentage of requested capabilities covered

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template.template_id,
            "template_name": self.template.name,
            "confidence": round(self.confidence, 3),
            "match_reasons": self.match_reasons,
            "missing_requirements": self.missing_requirements,
            "customization_suggestions": self.customization_suggestions,
            "domain_match": self.domain_match,
            "capability_coverage": round(self.capability_coverage, 2),
        }


@dataclass
class MatchRequest:
    """Request for template matching."""

    # Required
    organization_name: str
    department_name: str

    # Optional hints
    domain_hint: str | None = None
    role_title: str | None = None
    role_description: str | None = None

    # Capabilities requested
    requested_capabilities: list[str] = field(default_factory=list)
    required_integrations: list[str] = field(default_factory=list)

    # Constraints
    hitl_preference: HITLRequirement | None = None
    complexity_preference: TemplateComplexity | None = None
    max_results: int = 5

    # Context
    existing_agents: list[str] = field(default_factory=list)
    organization_context: dict[str, Any] = field(default_factory=dict)
