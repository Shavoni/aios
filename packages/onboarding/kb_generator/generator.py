"""Knowledge Base Generator.

Generates comprehensive, deep knowledge bases for HAAIS-governed agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from packages.onboarding.kb_generator.structures import (
    KBFile,
    KBFileType,
    KnowledgeBase,
    HAASISTier,
    Classification,
)
from packages.onboarding.kb_generator.templates import (
    get_domain_templates,
    get_regulatory_template,
    get_all_regulatory_templates_for_domain,
    REGULATORY_TEMPLATES,
    DOMAIN_TEMPLATES,
)


@dataclass
class GeneratorConfig:
    """Configuration for KB generation."""

    municipality_name: str = "City"
    state: str = "Ohio"
    include_regulatory: bool = True
    include_api_connections: bool = True
    min_files: int = 15
    max_files: int = 20

    # Director information (for personalization)
    director_name: str | None = None
    director_title: str | None = None

    # API endpoints discovered during onboarding
    api_endpoints: dict[str, str] = field(default_factory=dict)

    # Custom content overrides
    custom_content: dict[str, str] = field(default_factory=dict)


class KBGenerator:
    """Generates comprehensive knowledge bases for agents."""

    def __init__(self, config: GeneratorConfig | None = None):
        """Initialize the generator.

        Args:
            config: Generator configuration
        """
        self.config = config or GeneratorConfig()

    def generate(
        self,
        agent_id: str,
        agent_name: str,
        domain: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> KnowledgeBase:
        """Generate a complete knowledge base for an agent.

        Args:
            agent_id: Agent identifier
            agent_name: Agent display name
            domain: Agent's domain (e.g., "Public Health")
            data_sources: Optional list of connected data sources

        Returns:
            Complete KnowledgeBase with 15-20 files
        """
        kb = KnowledgeBase(
            agent_id=agent_id,
            agent_name=agent_name,
            domain=domain,
        )

        # 1. Generate HAAIS Governance file (always first)
        kb.governance_file = self._generate_governance_file(domain)

        # 2. Add regulatory quick reference files
        if self.config.include_regulatory:
            kb.quick_reference_files = self._generate_regulatory_files(domain)

        # 3. Generate domain-specific content files
        domain_files = self._generate_domain_files(domain, data_sources)
        for f in domain_files:
            kb.add_file(f)

        # 4. Connect API endpoints
        if self.config.include_api_connections and data_sources:
            kb.connected_apis = self._map_api_connections(data_sources)

        return kb

    def _generate_governance_file(self, domain: str) -> KBFile:
        """Generate the HAAIS governance file for a domain."""
        domain_config = get_domain_templates(domain)

        prohibited = ""
        if domain_config and domain_config.get("prohibited_actions"):
            prohibited = "\n".join(
                f"- You can NEVER {action.lower()}"
                for action in domain_config["prohibited_actions"]
            )

        special_protocols = ""
        if domain_config and domain_config.get("special_protocols"):
            protocols = domain_config["special_protocols"]
            special_protocols = "\n\n".join(
                f"**{key.replace('_', ' ').title()}:** {value}"
                for key, value in protocols.items()
            )

        content = f"""### HAAIS Governance Framework

This document establishes the governance rules for the {domain} AI Leadership Asset under the Human Assisted AI Services (HAAIS) framework.

### The Three Pillars of HAAIS

**1. Human Governance, Not Replacement**
You assist department leadership; you do not make policy decisions, issue orders, or take actions that require human authority.

**2. Assistance, Not Automation**
You enhance the effectiveness of department professionals. You provide information, draft documents, and analyze data - but humans make decisions.

**3. Services, Not Tools**
You are a specialized asset within a coordinated suite of municipal AI services. You work within your domain and escalate appropriately.

### Three-Tier Governance Model

**Tier 1: Foundational Governance**
- Core HAAIS principles (this document)
- Applies to ALL AI assistants
- Managed by Urban AI Director

**Tier 2: Departmental Governance**
- Department-specific protocols
- Knowledge base content
- Managed by department heads

**Tier 3: Operational Governance**
- Real-time human oversight
- Escalation handling
- Managed by Concierge and human operators

### Operational Modes

**INFORM Mode**
- Retrieve and synthesize information from knowledge base
- Default mode for inquiries
- Full audit logging

**DRAFT Mode**
- Create documents for human review
- All outputs marked "DRAFT - REQUIRES REVIEW"
- Human approval required before use

**EXECUTE Mode**
- Perform pre-approved, low-risk tasks
- Strict parameter boundaries
- Full audit trail required

**ESCALATE Mode**
- Route to human decision-maker
- Used for complex, sensitive, or high-risk matters
- Clear handoff with context

### Prohibited Actions

{prohibited}

### Special Protocols

{special_protocols}

### Escalation Triggers

Immediately escalate when:
- Request involves legal liability or litigation
- Request involves personnel decisions
- Request involves policy exceptions
- Request involves public safety
- Request involves media/press inquiries
- You are uncertain about the appropriate response
- User explicitly requests human assistance"""

        return KBFile(
            id="haais_governance",
            number=0,
            name=f"HAAIS_GOVERNANCE_{domain.upper().replace(' ', '_')}.md",
            title=f"HAAIS Governance - {domain}",
            file_type=KBFileType.GOVERNANCE,
            haais_tier=HAASISTier.TIER_1,
            classification=Classification.PUBLIC,
            purpose=f"Establishes HAAIS governance rules for the {domain} AI Leadership Asset.",
            applicability="This governance applies to all interactions with this AI assistant.",
            content=content,
            related_files=["Operational_Modes_Guide.md", "Escalation_Matrix.md"],
            escalation_contacts=[
                {"role": "Department Director", "name": self.config.director_name or f"[{domain} Director]"},
                {"role": "Urban AI Director", "name": "HAAIS Framework Authority"},
            ],
            source="HAAIS Framework v1.0",
        )

    def _generate_regulatory_files(self, domain: str) -> list[KBFile]:
        """Generate regulatory quick reference files for a domain."""
        files = []
        templates = get_all_regulatory_templates_for_domain(domain)

        for i, template in enumerate(templates):
            kb_file = KBFile(
                id=f"regulatory_{template.get('title', '').lower().replace(' ', '_')[:30]}",
                number=0,  # Quick references don't get numbered
                name=f"{template.get('title', 'Regulatory').upper().replace(' ', '_')[:40]}.md",
                title=template.get("title", "Regulatory Reference"),
                file_type=KBFileType.REGULATORY,
                haais_tier=HAASISTier.TIER_1,
                classification=Classification.PUBLIC,
                purpose=f"Quick reference for {template.get('title', 'regulatory')} compliance.",
                applicability=f"Required for all {domain} operations involving {template.get('title', 'this regulation')}.",
                content=template.get("content", ""),
                related_files=[f"{rt}.md" for rt in template.get("related_templates", [])],
                escalation_contacts=template.get("escalation_contacts", []),
                source=template.get("source", ""),
            )
            files.append(kb_file)

        return files

    def _generate_domain_files(
        self,
        domain: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[KBFile]:
        """Generate domain-specific content files."""
        files = []
        domain_config = get_domain_templates(domain)

        if not domain_config:
            # Fallback: generate generic structure
            return self._generate_generic_files(domain, data_sources)

        file_structure = domain_config.get("file_structure", [])

        for file_def in file_structure:
            # Map file type string to enum
            file_type_map = {
                "procedure": KBFileType.PROCEDURE,
                "policy": KBFileType.POLICY,
                "regulatory": KBFileType.REGULATORY,
                "data_reference": KBFileType.DATA_REFERENCE,
                "department_structure": KBFileType.DEPARTMENT_STRUCTURE,
                "quick_reference": KBFileType.QUICK_REFERENCE,
            }
            file_type = file_type_map.get(file_def.get("type", "procedure"), KBFileType.PROCEDURE)

            # Determine HAAIS tier
            tier = HAASISTier.TIER_3  # Default operational
            if file_type == KBFileType.REGULATORY:
                tier = HAASISTier.TIER_1
            elif file_type == KBFileType.POLICY:
                tier = HAASISTier.TIER_2

            # Generate content for this file
            content = self._generate_file_content(
                file_def,
                domain,
                data_sources,
            )

            # Check for API connection
            api_endpoint = None
            refresh_freq = None
            if data_sources:
                for ds in data_sources:
                    if file_def["id"] in ds.get("id", "") or file_def["id"] in ds.get("name", "").lower():
                        api_endpoint = ds.get("api_endpoint")
                        refresh_freq = ds.get("refresh_frequency", "daily")
                        break

            kb_file = KBFile(
                id=file_def["id"],
                number=file_def["num"],
                name=f"{file_def['num']:02d}_{file_def['id']}.md",
                title=file_def["title"],
                file_type=file_type,
                haais_tier=tier,
                classification=Classification.INTERNAL,
                purpose=f"Provides guidance on {file_def['title'].lower()} for {domain} operations.",
                applicability=f"Consult this file for {file_def['title'].lower()} questions and procedures.",
                content=content,
                related_files=self._get_related_files(file_def, file_structure),
                escalation_contacts=[
                    {"role": "Department Director", "name": self.config.director_name or f"[{domain} Director]"},
                ],
                source=f"{self.config.municipality_name} {domain} Department",
                api_endpoint=api_endpoint,
                refresh_frequency=refresh_freq,
            )
            files.append(kb_file)

        return files

    def _generate_file_content(
        self,
        file_def: dict[str, Any],
        domain: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate content for a specific file.

        This creates substantial, structured content based on the file type
        and domain. In production, this would pull from discovered city data.
        """
        file_id = file_def["id"]
        title = file_def["title"]
        file_type = file_def.get("type", "procedure")

        # Check for custom content override
        if file_id in self.config.custom_content:
            return self.config.custom_content[file_id]

        # Generate structured content based on file type
        if file_type == "procedure":
            return self._generate_procedure_content(title, domain)
        elif file_type == "policy":
            return self._generate_policy_content(title, domain)
        elif file_type == "data_reference":
            return self._generate_data_reference_content(title, domain, data_sources)
        elif file_type == "department_structure":
            return self._generate_structure_content(title, domain)
        elif file_type == "regulatory":
            return self._generate_regulatory_content(title, domain)
        else:
            return self._generate_generic_content(title, domain)

    def _generate_procedure_content(self, title: str, domain: str) -> str:
        """Generate procedure document content."""
        return f"""### {title}

This document outlines the standard operating procedures for {title.lower()} within the {self.config.municipality_name} {domain} department.

### Purpose

To establish consistent, efficient, and compliant procedures for {title.lower()}.

### Scope

These procedures apply to all {domain} department staff involved in {title.lower()} activities.

### Procedures

**Step 1: Initiation**
- Review request/inquiry for completeness
- Verify requester identity and authorization
- Log initiation in tracking system

**Step 2: Assessment**
- Evaluate against established criteria
- Identify applicable regulations and policies
- Determine appropriate processing path

**Step 3: Processing**
- Follow department-specific workflows
- Document all actions and decisions
- Maintain audit trail

**Step 4: Review**
- Quality assurance check
- Supervisor review (if required)
- Address any deficiencies

**Step 5: Completion**
- Finalize documentation
- Notify relevant parties
- Archive records per retention schedule

### Quality Standards

- All procedures must be completed within established timeframes
- Documentation must be complete and accurate
- Compliance with all applicable regulations is mandatory

### Training Requirements

Staff performing these procedures must complete:
- Department orientation
- Procedure-specific training
- Annual refresher training

### Records Retention

Maintain records according to {self.config.state} records retention requirements and department policies.

### Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | {datetime.now().strftime('%B %Y')} | Initial release |"""

    def _generate_policy_content(self, title: str, domain: str) -> str:
        """Generate policy document content."""
        return f"""### {title}

This policy establishes the framework for {title.lower()} within the {self.config.municipality_name} {domain} department.

### Policy Statement

The {self.config.municipality_name} is committed to maintaining high standards in {title.lower()}. This policy provides guidance to ensure consistent, equitable, and effective implementation.

### Objectives

1. Establish clear guidelines for {title.lower()}
2. Ensure compliance with applicable laws and regulations
3. Promote equity and accessibility
4. Support department mission and goals

### Definitions

[Key terms and definitions specific to this policy area]

### Policy Requirements

**General Requirements:**
- All activities must comply with federal, state, and local requirements
- Documentation must be maintained for all decisions
- Regular review and updates are required

**Specific Requirements:**
- [Domain-specific requirements would be populated from discovered data]
- [Additional requirements based on city policies]

### Roles and Responsibilities

**Department Director:**
- Overall policy oversight
- Final approval authority
- Escalation point for exceptions

**Division Managers:**
- Day-to-day implementation
- Staff supervision and training
- Quality assurance

**Staff:**
- Follow established procedures
- Maintain accurate records
- Report issues promptly

### Exceptions

Exceptions to this policy require:
1. Written justification
2. Director approval
3. Documentation in official records

### Compliance

Non-compliance may result in:
- Corrective action
- Additional training requirements
- Disciplinary measures (for willful violations)

### Related Policies

- [Related department policies]
- [City-wide policies that apply]

### Effective Date

This policy is effective as of {datetime.now().strftime('%B %Y')}.

### Review Schedule

This policy will be reviewed annually and updated as needed."""

    def _generate_data_reference_content(
        self,
        title: str,
        domain: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate data reference document content."""
        api_info = ""
        if data_sources:
            for ds in data_sources:
                if ds.get("api_endpoint"):
                    api_info += f"\n- **{ds.get('name', 'Data Source')}**: `{ds.get('api_endpoint')}`"

        return f"""### {title}

This document provides reference information for {title.lower()} data used by the {self.config.municipality_name} {domain} department.

### Data Overview

This data supports {domain} operations by providing:
- Current statistics and metrics
- Historical trends and patterns
- Geographic and demographic breakdowns
- Performance indicators

### Data Sources

{api_info if api_info else "Data sources are maintained by the department and updated according to established schedules."}

### Key Metrics

**Primary Indicators:**
- [Key metric 1 - populated from discovered data]
- [Key metric 2 - populated from discovered data]
- [Key metric 3 - populated from discovered data]

**Secondary Indicators:**
- [Supporting metrics as available]

### Data Quality

**Accuracy:**
Data is validated through established quality assurance processes.

**Timeliness:**
Data is updated according to the following schedule:
- Real-time data: Continuous updates
- Daily data: Updated by 8:00 AM
- Weekly data: Updated Monday mornings
- Monthly data: Updated by the 5th of each month

**Completeness:**
Coverage and any known gaps are documented in data dictionaries.

### Access and Security

- Data access is role-based
- Sensitive data requires additional authorization
- All access is logged for audit purposes

### Using This Data

**For INFORM Requests:**
Reference this data to answer questions about {title.lower()}.

**For DRAFT Requests:**
Use this data to support reports and analyses, always citing the source and date.

**For Analysis:**
Ensure proper statistical methods and note any limitations.

### Data Limitations

- Historical data may have different collection methodologies
- Some data may be estimates or projections
- Always verify current data before critical decisions

### Contact

For data questions: {domain} Data Team
For technical issues: IT Department"""

    def _generate_structure_content(self, title: str, domain: str) -> str:
        """Generate department structure content."""
        director_info = ""
        if self.config.director_name:
            director_info = f"\n**Director:** {self.config.director_name}"
            if self.config.director_title:
                director_info += f", {self.config.director_title}"

        return f"""### {title}

This document outlines the organizational structure and key contacts for the {self.config.municipality_name} {domain} department.

### Department Overview

The {domain} department serves the residents of {self.config.municipality_name} by providing essential services and ensuring compliance with applicable regulations.
{director_info}

### Organizational Structure

**Executive Level:**
- Department Director
- Deputy Director(s)
- Chief of Staff (if applicable)

**Division Level:**
- [Division 1 - populated from discovery]
- [Division 2 - populated from discovery]
- [Division 3 - populated from discovery]

**Operational Level:**
- Supervisors
- Specialists
- Support Staff

### Key Contacts

| Role | Name | Contact |
|------|------|---------|
| Director | {self.config.director_name or '[Director Name]'} | [Contact Info] |
| Deputy Director | [Name] | [Contact Info] |
| Division Managers | [Names] | [Contact Info] |

### Hours of Operation

**Regular Hours:**
Monday - Friday: 8:00 AM - 5:00 PM

**Emergency Contact:**
24/7 emergency line: [Emergency Number]

### Location

{self.config.municipality_name} {domain} Department
[Address]
[City, State ZIP]

### Partner Organizations

- [Partner organization 1]
- [Partner organization 2]
- [State/Federal oversight agencies]

### Reporting Structure

For HAAIS AI Assistant purposes:
- **Routine inquiries:** Handled by AI in INFORM mode
- **Document requests:** DRAFT mode with staff review
- **Policy questions:** Escalate to Division Manager
- **Legal/Personnel matters:** Escalate to Director"""

    def _generate_regulatory_content(self, title: str, domain: str) -> str:
        """Generate regulatory content."""
        return f"""### {title}

This document summarizes regulatory requirements applicable to {title.lower()} for the {self.config.municipality_name} {domain} department.

### Regulatory Framework

**Federal Requirements:**
- [Applicable federal regulations]
- [Federal agency oversight]

**State Requirements ({self.config.state}):**
- [{self.config.state} Revised Code sections]
- [State agency oversight]

**Local Requirements:**
- [{self.config.municipality_name} ordinances]
- [Local policies]

### Compliance Requirements

**Documentation:**
- Maintain records as required by regulation
- Retention periods per applicable requirements
- Audit trail for all compliance activities

**Reporting:**
- Required reports and frequencies
- Reporting deadlines
- Submission procedures

**Inspections:**
- Scheduled inspection requirements
- Self-inspection programs
- Response to regulatory inspections

### Non-Compliance Consequences

Failure to comply may result in:
- Administrative penalties
- Civil penalties
- Criminal penalties (for willful violations)
- Loss of licenses or certifications

### Resources

**Regulatory Agencies:**
- [Federal agency contact]
- [State agency contact]

**Department Compliance Officer:**
[Contact information]

### Updates

Regulatory requirements change. This document is updated:
- When new regulations are enacted
- When existing regulations are amended
- At minimum annually

Last reviewed: {datetime.now().strftime('%B %Y')}"""

    def _generate_generic_content(self, title: str, domain: str) -> str:
        """Generate generic content for undefined types."""
        return f"""### {title}

This document provides information about {title.lower()} for the {self.config.municipality_name} {domain} department.

### Overview

[Content to be populated based on department-specific information]

### Key Information

- [Key point 1]
- [Key point 2]
- [Key point 3]

### Procedures

Follow established department procedures for {title.lower()}.

### Resources

Contact the {domain} department for additional information.

### Last Updated

{datetime.now().strftime('%B %Y')}"""

    def _generate_generic_files(
        self,
        domain: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[KBFile]:
        """Generate generic file structure when domain template not found."""
        generic_structure = [
            {"num": 1, "id": "overview", "title": f"{domain} Overview", "type": "policy"},
            {"num": 2, "id": "procedures", "title": "Standard Procedures", "type": "procedure"},
            {"num": 3, "id": "policies", "title": "Department Policies", "type": "policy"},
            {"num": 4, "id": "data", "title": "Department Data", "type": "data_reference"},
            {"num": 5, "id": "contacts", "title": "Department Contacts", "type": "department_structure"},
        ]

        files = []
        for file_def in generic_structure:
            content = self._generate_file_content(file_def, domain, data_sources)
            kb_file = KBFile(
                id=file_def["id"],
                number=file_def["num"],
                name=f"{file_def['num']:02d}_{file_def['id']}.md",
                title=file_def["title"],
                file_type=KBFileType.PROCEDURE,
                haais_tier=HAASISTier.TIER_3,
                classification=Classification.INTERNAL,
                purpose=f"Provides guidance on {file_def['title'].lower()}.",
                applicability=f"Consult for {file_def['title'].lower()} questions.",
                content=content,
                related_files=[],
                escalation_contacts=[],
                source=f"{self.config.municipality_name} {domain}",
            )
            files.append(kb_file)

        return files

    def _get_related_files(
        self,
        file_def: dict[str, Any],
        all_files: list[dict[str, Any]],
    ) -> list[str]:
        """Determine related files based on content relationships."""
        related = []
        file_id = file_def["id"]
        file_type = file_def.get("type", "")

        # Related by type proximity
        for other in all_files:
            if other["id"] == file_id:
                continue

            # Same type files are related
            if other.get("type") == file_type and len(related) < 3:
                related.append(f"{other['num']:02d}_{other['id']}.md")

        # Add governance file reference for non-governance files
        if file_type != "governance":
            related.insert(0, "HAAIS_GOVERNANCE.md")

        return related[:5]  # Limit to 5 related files

    def _map_api_connections(
        self,
        data_sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Map data sources to API connections."""
        connections = []
        for ds in data_sources:
            if ds.get("api_endpoint"):
                connections.append({
                    "source_id": ds.get("id"),
                    "name": ds.get("name"),
                    "endpoint": ds.get("api_endpoint"),
                    "refresh_frequency": ds.get("refresh_frequency", "daily"),
                    "format": ds.get("format", "json"),
                })
        return connections


def generate_knowledge_base(
    agent_id: str,
    agent_name: str,
    domain: str,
    municipality_name: str = "City",
    director_name: str | None = None,
    data_sources: list[dict[str, Any]] | None = None,
) -> KnowledgeBase:
    """Convenience function to generate a knowledge base.

    Args:
        agent_id: Agent identifier
        agent_name: Agent display name
        domain: Agent's domain
        municipality_name: Name of the municipality
        director_name: Optional director name for personalization
        data_sources: Optional list of connected data sources

    Returns:
        Complete KnowledgeBase
    """
    config = GeneratorConfig(
        municipality_name=municipality_name,
        director_name=director_name,
    )
    generator = KBGenerator(config)
    return generator.generate(agent_id, agent_name, domain, data_sources)
