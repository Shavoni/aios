"""Data structures for Knowledge Base files."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime


class KBFileType(str, Enum):
    """Types of knowledge base files."""
    GOVERNANCE = "governance"  # HAAIS governance rules
    REGULATORY = "regulatory"  # Federal/state regulations
    POLICY = "policy"  # City/department policies
    PROCEDURE = "procedure"  # Operational procedures
    DATA_REFERENCE = "data_reference"  # Data source documentation
    DEPARTMENT_STRUCTURE = "department_structure"  # Org structure, contacts
    QUICK_REFERENCE = "quick_reference"  # Guidelines, checklists


class HAASISTier(str, Enum):
    """HAAIS classification tiers."""
    TIER_1 = "Tier 1"  # Constitutional/Foundational
    TIER_2 = "Tier 2"  # Organizational/Departmental
    TIER_3 = "Tier 3"  # Operational


class Classification(str, Enum):
    """Document classification levels."""
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"


@dataclass
class KBFile:
    """A single knowledge base file."""

    # Identification
    id: str  # e.g., "01_disease_surveillance"
    number: int  # File number for ordering
    name: str  # Full filename, e.g., "01_disease_surveillance_outbreak_response.md"
    title: str  # Human-readable title

    # Classification
    file_type: KBFileType
    haais_tier: HAASISTier
    classification: Classification

    # Content sections
    purpose: str
    applicability: str
    content: str  # Main content, can be substantial

    # Cross-references
    related_files: list[str] = field(default_factory=list)
    escalation_contacts: list[dict[str, str]] = field(default_factory=list)

    # Metadata
    version: str = "1.0"
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%B %Y"))
    source: str = ""

    # API connection (if this file is backed by live data)
    api_endpoint: str | None = None
    refresh_frequency: str | None = None  # e.g., "daily", "weekly"

    def to_markdown(self) -> str:
        """Generate the full markdown content."""
        lines = [
            f"# {self.title}",
            "",
            f"## Version: {self.version} | Last Updated: {self.last_updated} | Classification: {self.classification.value}",
            "",
            "---",
            "",
            "## PURPOSE",
            "",
            self.purpose,
            "",
            "## APPLICABILITY",
            "",
            self.applicability,
            "",
            "---",
            "",
            "## CONTENT",
            "",
            self.content,
            "",
            "---",
            "",
        ]

        # Related files
        if self.related_files:
            lines.append("## RELATED FILES")
            lines.append("")
            for rf in self.related_files:
                lines.append(f"- `{rf}`")
            lines.append("")

        # Escalation contacts
        if self.escalation_contacts:
            lines.append("## ESCALATION CONTACTS")
            lines.append("")
            for contact in self.escalation_contacts:
                role = contact.get("role", "Contact")
                name = contact.get("name", "")
                lines.append(f"- {role}: **{name}**")
            lines.append("")

        # API connection info
        if self.api_endpoint:
            lines.append("## DATA SOURCE")
            lines.append("")
            lines.append(f"- **API Endpoint**: `{self.api_endpoint}`")
            if self.refresh_frequency:
                lines.append(f"- **Refresh Frequency**: {self.refresh_frequency}")
            lines.append("")

        lines.append("---")
        lines.append("")
        if self.source:
            lines.append(f"*Source: {self.source}*")
        lines.append(f"*HAAIS Classification: {self.haais_tier.value}*")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "title": self.title,
            "file_type": self.file_type.value,
            "haais_tier": self.haais_tier.value,
            "classification": self.classification.value,
            "purpose": self.purpose,
            "applicability": self.applicability,
            "content": self.content,
            "related_files": self.related_files,
            "escalation_contacts": self.escalation_contacts,
            "version": self.version,
            "last_updated": self.last_updated,
            "source": self.source,
            "api_endpoint": self.api_endpoint,
            "refresh_frequency": self.refresh_frequency,
        }


@dataclass
class KnowledgeBase:
    """Complete knowledge base for an agent."""

    agent_id: str
    agent_name: str
    domain: str

    files: list[KBFile] = field(default_factory=list)

    # Governance file (always first)
    governance_file: KBFile | None = None

    # Quick reference files (regulatory summaries)
    quick_reference_files: list[KBFile] = field(default_factory=list)

    # API connections
    connected_apis: list[dict[str, Any]] = field(default_factory=list)

    def add_file(self, kb_file: KBFile) -> None:
        """Add a file to the knowledge base."""
        self.files.append(kb_file)
        self.files.sort(key=lambda f: f.number)

    def get_file_by_id(self, file_id: str) -> KBFile | None:
        """Get a file by its ID."""
        for f in self.files:
            if f.id == file_id:
                return f
        return None

    def get_files_by_type(self, file_type: KBFileType) -> list[KBFile]:
        """Get all files of a specific type."""
        return [f for f in self.files if f.file_type == file_type]

    @property
    def file_count(self) -> int:
        """Total number of files."""
        count = len(self.files)
        if self.governance_file:
            count += 1
        count += len(self.quick_reference_files)
        return count

    def get_all_files(self) -> list[KBFile]:
        """Get all files in order."""
        all_files = []
        if self.governance_file:
            all_files.append(self.governance_file)
        all_files.extend(self.quick_reference_files)
        all_files.extend(self.files)
        return sorted(all_files, key=lambda f: (f.number, f.name))

    def get_knowledge_hierarchy(self) -> list[dict[str, str]]:
        """Get the knowledge hierarchy for instructions."""
        hierarchy = []

        # Governance first
        if self.governance_file:
            hierarchy.append({
                "file": self.governance_file.name,
                "description": "HAAIS governance rules and operational modes",
                "priority": 1,
            })

        # Quick references (regulatory)
        for i, qr in enumerate(self.quick_reference_files):
            hierarchy.append({
                "file": qr.name,
                "description": qr.purpose[:100],
                "priority": 2 + i,
            })

        # Domain files by type priority
        type_priority = {
            KBFileType.REGULATORY: 10,
            KBFileType.POLICY: 20,
            KBFileType.PROCEDURE: 30,
            KBFileType.DATA_REFERENCE: 40,
            KBFileType.DEPARTMENT_STRUCTURE: 50,
        }

        for f in self.files:
            hierarchy.append({
                "file": f.name,
                "description": f.purpose[:100],
                "priority": type_priority.get(f.file_type, 99) + f.number,
            })

        hierarchy.sort(key=lambda x: x["priority"])
        return hierarchy

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "domain": self.domain,
            "file_count": self.file_count,
            "files": [f.to_dict() for f in self.get_all_files()],
            "connected_apis": self.connected_apis,
            "knowledge_hierarchy": self.get_knowledge_hierarchy(),
        }
