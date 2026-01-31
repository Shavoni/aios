"""
Archetype Registry

Archetypes are domain-specific templates that accelerate agent creation.
Each archetype defines:
- Default capabilities and guardrails
- Instruction templates
- Knowledge source recommendations
- Governance configurations
- Conversation starters
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field

from ..models import (
    CandidateType,
    OrganizationType,
    HITLMode,
    Capability,
    Guardrail,
    GovernanceConfig,
)


class Archetype(BaseModel):
    """
    An archetype defines the template for a type of agent.

    Archetypes accelerate agent creation by providing sensible defaults
    for capabilities, guardrails, instructions, and governance.
    """
    id: str
    name: str
    description: str

    # Matching
    organization_types: list[OrganizationType]  # Which org types this applies to
    candidate_types: list[CandidateType]        # Which candidate types this matches

    # Domain
    domain: str                                  # e.g., "PublicHealth"
    subdomain: Optional[str] = None             # e.g., "Epidemiology"

    # Identity template
    title_template: str                         # e.g., "Director of {department}"
    description_template: str                   # Template for description

    # Capabilities (defaults)
    default_capabilities: list[Capability] = Field(default_factory=list)

    # Guardrails (defaults)
    default_guardrails: list[Guardrail] = Field(default_factory=list)

    # Instruction template
    instruction_template: str                   # Full instruction template

    # Knowledge recommendations
    recommended_knowledge: list[str] = Field(default_factory=list)
    required_knowledge: list[str] = Field(default_factory=list)

    # Governance
    default_governance: GovernanceConfig = Field(default_factory=GovernanceConfig)

    # Conversation starters
    default_conversation_starters: list[str] = Field(default_factory=list)

    # Relationships
    typical_escalation: Optional[str] = None    # Who this typically escalates to
    typical_collaborators: list[str] = Field(default_factory=list)

    # Metadata
    version: str = "1.0.0"
    author: str = "HAAIS"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchetypeRegistry:
    """
    Registry for managing and matching archetypes.

    Loads archetypes from JSON files and matches them to candidates.
    """

    def __init__(self):
        self._archetypes: dict[str, Archetype] = {}
        self._loaded = False

    def load_archetypes(self, archetypes_dir: Optional[Path] = None) -> None:
        """Load all archetypes from the archetypes directory."""
        if archetypes_dir is None:
            archetypes_dir = Path(__file__).parent

        for json_file in archetypes_dir.rglob("*.archetype.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    archetype = Archetype(**data)
                    self._archetypes[archetype.id] = archetype
            except Exception as e:
                print(f"Warning: Failed to load archetype {json_file}: {e}")

        self._loaded = True

    def get(self, archetype_id: str) -> Optional[Archetype]:
        """Get an archetype by ID."""
        if not self._loaded:
            self.load_archetypes()
        return self._archetypes.get(archetype_id)

    def list_all(self) -> list[Archetype]:
        """List all registered archetypes."""
        if not self._loaded:
            self.load_archetypes()
        return list(self._archetypes.values())

    def find_matching(
        self,
        organization_type: OrganizationType,
        candidate_type: CandidateType,
    ) -> list[Archetype]:
        """Find archetypes that match the given organization and candidate types."""
        if not self._loaded:
            self.load_archetypes()

        matches = []
        for archetype in self._archetypes.values():
            if (
                organization_type in archetype.organization_types
                and candidate_type in archetype.candidate_types
            ):
                matches.append(archetype)

        return matches

    def best_match(
        self,
        organization_type: OrganizationType,
        candidate_type: CandidateType,
    ) -> Optional[Archetype]:
        """Get the best matching archetype for the given types."""
        matches = self.find_matching(organization_type, candidate_type)
        if not matches:
            return None
        # Return first match (could add scoring logic later)
        return matches[0]

    def register(self, archetype: Archetype) -> None:
        """Register an archetype programmatically."""
        self._archetypes[archetype.id] = archetype

    def for_organization_type(self, org_type: OrganizationType) -> list[Archetype]:
        """Get all archetypes applicable to an organization type."""
        if not self._loaded:
            self.load_archetypes()

        return [
            a for a in self._archetypes.values()
            if org_type in a.organization_types
        ]


# Global registry instance
registry = ArchetypeRegistry()


def get_archetype(archetype_id: str) -> Optional[Archetype]:
    """Get an archetype by ID from the global registry."""
    return registry.get(archetype_id)


def find_archetype(
    organization_type: OrganizationType,
    candidate_type: CandidateType,
) -> Optional[Archetype]:
    """Find the best matching archetype from the global registry."""
    return registry.best_match(organization_type, candidate_type)
