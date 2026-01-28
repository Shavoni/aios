"""HAAIS Instruction Builder.

Generates comprehensive, HAAIS-compliant instructions in the authentic
7-8 section format with knowledge base file references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.onboarding.kb_generator.structures import KnowledgeBase, KBFile
from packages.onboarding.kb_generator.templates import get_domain_templates


@dataclass
class InstructionConfig:
    """Configuration for instruction generation."""

    # Agent identity
    agent_name: str
    agent_title: str
    domain: str
    description: str

    # Director information
    director_name: str
    director_title: str = "Director"

    # Escalation
    escalates_to: str = ""

    # Governance
    sensitivity: str = "medium"  # low, medium, high, critical

    # Character limits (for platform targeting)
    max_chars: int = 8000  # ChatGPT default

    # Knowledge base
    knowledge_base: KnowledgeBase | None = None

    # Custom overrides
    custom_capabilities: list[str] = field(default_factory=list)
    custom_guardrails: list[str] = field(default_factory=list)
    custom_protocols: dict[str, str] = field(default_factory=dict)


class InstructionBuilder:
    """Builds HAAIS-compliant instructions in authentic format."""

    # Section character targets (matching real HAAIS agents)
    SECTION_TARGETS = {
        "identity": 500,
        "governance": 1500,
        "prohibited": 800,
        "modes": 1200,
        "competencies": 2000,
        "hierarchy": 500,
        "protocols": 1000,
        "special": 500,
    }

    def __init__(self, config: InstructionConfig):
        """Initialize the builder.

        Args:
            config: Instruction configuration
        """
        self.config = config
        self.sections: dict[str, str] = {}

    def build(self) -> str:
        """Build complete instructions.

        Returns:
            Complete instruction text in HAAIS format
        """
        # Build all sections
        self._build_identity_section()
        self._build_governance_section()
        self._build_prohibited_section()
        self._build_modes_section()
        self._build_competencies_section()
        self._build_hierarchy_section()
        self._build_protocols_section()
        self._build_special_section()

        # Combine sections
        full_instructions = self._combine_sections()

        # Compress if needed
        if len(full_instructions) > self.config.max_chars:
            full_instructions = self._compress(full_instructions)

        return full_instructions

    def _build_identity_section(self) -> None:
        """Build Section 1: Identity & Purpose."""
        escalation = self.config.escalates_to or f"the {self.config.director_title}"

        self.sections["identity"] = f"""## [SECTION 1: IDENTITY & PURPOSE - {self.SECTION_TARGETS['identity']} chars]
You are the HAAIS-governed AI assistant to {self.config.director_name}, {self.config.director_title} of the {self.config.domain} department. Your purpose is to support the {self.config.director_title} and their team in {self.config.description.lower() if self.config.description else f'serving the department mission'}.

You are **{self.config.agent_name}**, serving as the **{self.config.agent_title}**."""

    def _build_governance_section(self) -> None:
        """Build Section 2: HAAIS Governance."""
        domain_config = get_domain_templates(self.config.domain)

        # Domain-specific governance note
        domain_note = ""
        if domain_config:
            special = domain_config.get("special_protocols", {})
            if special:
                key_protocol = list(special.keys())[0]
                domain_note = f"Particularly critical: {special[key_protocol]}"

        self.sections["governance"] = f"""## [SECTION 2: HAAIS GOVERNANCE - {self.SECTION_TARGETS['governance']} chars]
You are governed by the HAAIS (Human Assisted AI Services) framework. Your operations are bound by its three pillars:

1) **Human Governance, Not Replacement:** You assist the {self.config.director_title}; you do not make decisions that require human authority.

2) **Assistance, Not Automation:** You enhance the effectiveness of department professionals. You provide information, draft documents, and analyze data - but humans make decisions.

3) **Services, Not Tools:** You are a specialized asset within a coordinated suite of municipal AI services.

You must adhere to all Tier 1 (Constitutional), Tier 2 (Organizational), and Tier 3 (Departmental) governance rules. All high-risk activities require human review and approval (DRAFT mode) or direct human intervention (ESCALATE mode).

{domain_note}"""

    def _build_prohibited_section(self) -> None:
        """Build Section 3: Prohibited Actions."""
        domain_config = get_domain_templates(self.config.domain)

        # Get domain-specific prohibitions
        prohibitions = []
        if domain_config and domain_config.get("prohibited_actions"):
            prohibitions = domain_config["prohibited_actions"]
        elif self.config.custom_guardrails:
            prohibitions = self.config.custom_guardrails

        # Add universal prohibitions
        universal = [
            "impersonate a city official or make commitments on their behalf",
            "disclose personally identifiable information (PII) inappropriately",
            "provide legal advice or make legal determinations",
            "bypass established approval workflows",
        ]

        # Combine and format
        all_prohibitions = []
        for p in prohibitions[:6]:  # Limit domain-specific
            if not p.lower().startswith("you can never"):
                all_prohibitions.append(f"- You can NEVER {p.lower()}")
            else:
                all_prohibitions.append(f"- {p}")

        prohibitions_text = "\n".join(all_prohibitions)

        universal_text = "\n".join(f"- You can NEVER {u}" for u in universal)

        self.sections["prohibited"] = f"""## [SECTION 3: PROHIBITED ACTIONS - {self.SECTION_TARGETS['prohibited']} chars]
{prohibitions_text}

**Universal Prohibitions:**
{universal_text}"""

    def _build_modes_section(self) -> None:
        """Build Section 4: Mode Assignments with KB file references."""
        kb = self.config.knowledge_base

        # Build mode examples with KB references
        inform_examples = self._get_mode_examples("INFORM", kb)
        draft_examples = self._get_mode_examples("DRAFT", kb)
        execute_examples = self._get_mode_examples("EXECUTE", kb)
        escalate_examples = self._get_mode_examples("ESCALATE", kb)

        self.sections["modes"] = f"""## [SECTION 4: MODE ASSIGNMENTS - {self.SECTION_TARGETS['modes']} chars]
- **INFORM:** Retrieve and synthesize information from your knowledge base.
  Examples: {inform_examples}

- **DRAFT:** Create documents and analyses for human review.
  Examples: {draft_examples}

- **EXECUTE:** Perform low-risk, pre-authorized tasks.
  Examples: {execute_examples}

- **ESCALATE:** When a request falls outside your scope or involves high-risk matters.
  Examples: {escalate_examples}"""

    def _get_mode_examples(self, mode: str, kb: KnowledgeBase | None) -> str:
        """Generate mode examples with KB file references."""
        domain_config = get_domain_templates(self.config.domain)
        domain = self.config.domain

        # Default examples by mode and domain
        examples_map = {
            "INFORM": {
                "Public Health": [
                    ("Summarize the latest CDC guidance on flu vaccination", "CDC_GUIDELINES_QUICK_REFERENCE.md"),
                    ("What are the social determinants of health affecting our city?", "05_health_equity_social_determinants.md"),
                    ("List community partners working on lead abatement", "15_partnerships.md"),
                ],
                "Building & Housing": [
                    ("What are the building code requirements for a deck?", "OHIO_BUILDING_CODE_SUMMARY.md"),
                    ("Summarize the process for obtaining a demolition permit", "08_demolition.md"),
                    ("What are the standards for lead-safe certification?", "03_lead_safe.md"),
                ],
                "Public Utilities": [
                    ("What are the current water quality requirements?", "SAFE_DRINKING_WATER.md"),
                    ("Explain the NPDES permit requirements", "09_clean_water_act.md"),
                    ("What is the lead service line replacement program?", "11_lead_copper.md"),
                ],
                "default": [
                    ("What are the relevant policies for this request?", "policies.md"),
                    ("Summarize the procedures for this process", "procedures.md"),
                ],
            },
            "DRAFT": {
                "Public Health": [
                    ("Draft a community health needs assessment for [neighborhood]", "14_community_health_assessment.md"),
                    ("Write a grant proposal for a new mobile health clinic", "18_grant_management.md"),
                    ("Create a presentation on reducing infant mortality", "06_maternal_child_health.md"),
                ],
                "Building & Housing": [
                    ("Draft a notice of violation for property with high grass", "02_housing_code.md"),
                    ("Write a checklist for commercial kitchen inspection", "01_permits_inspections.md"),
                    ("Create a report analyzing common code violations", "10_housing_data.md"),
                ],
                "Public Utilities": [
                    ("Draft a consumer confidence report summary", "01_water_treatment.md"),
                    ("Write a community notification about infrastructure work", "17_community_engagement.md"),
                    ("Create a report on water affordability programs", "16_affordability.md"),
                ],
                "default": [
                    ("Draft a memo on this topic for review", "policies.md"),
                    ("Create a report analyzing this data", "data.md"),
                ],
            },
            "EXECUTE": {
                "Public Health": [
                    ("Analyze this de-identified dataset and create a geographic hotspot map", "04_vital_statistics.md"),
                ],
                "Building & Housing": [
                    ("Analyze this list of vacant properties and prioritize for inspection based on risk factors", "04_vacant_property.md"),
                ],
                "Public Utilities": [
                    ("Analyze water quality trends and flag any approaching action levels", "01_water_treatment.md"),
                ],
                "default": [
                    ("Analyze this data and summarize key findings", "data.md"),
                ],
            },
            "ESCALATE": {
                "Public Health": [
                    ("A hospital reports a suspected case of highly contagious disease", "01_disease_surveillance.md"),
                    ("A foodborne illness outbreak traced to a local restaurant", "03_environmental_health.md"),
                ],
                "Building & Housing": [
                    ("An inspector reports a building in imminent danger of collapse", "17_fire_safety.md"),
                    ("A contractor is attempting to bribe an inspector", "HAAIS_GOVERNANCE.md"),
                ],
                "Public Utilities": [
                    ("Water quality test shows contamination above action level", "SAFE_DRINKING_WATER.md"),
                    ("Major infrastructure failure affecting service", "06_emergency_response.md"),
                ],
                "default": [
                    ("Request involves legal matters or potential liability", "HAAIS_GOVERNANCE.md"),
                    ("User explicitly requests human assistance", "HAAIS_GOVERNANCE.md"),
                ],
            },
        }

        # Get examples for this mode and domain
        mode_examples = examples_map.get(mode, {})
        domain_examples = mode_examples.get(domain, mode_examples.get("default", []))

        # Format with KB references
        formatted = []
        for example, kb_file in domain_examples[:3]:
            # If we have actual KB, try to find matching file
            actual_file = kb_file
            if kb:
                for f in kb.get_all_files():
                    if kb_file.split("_")[0] in f.name or kb_file.lower() in f.name.lower():
                        actual_file = f.name
                        break

            formatted.append(f'"{example}" (from `{actual_file}`)')

        return ", ".join(formatted)

    def _build_competencies_section(self) -> None:
        """Build Section 5: Core Competencies & Knowledge Base."""
        kb = self.config.knowledge_base
        domain_config = get_domain_templates(self.config.domain)

        competencies = []

        if self.config.custom_capabilities:
            # Use custom capabilities
            for i, cap in enumerate(self.config.custom_capabilities[:7], 1):
                competencies.append(f"{i}. **{cap}**")
        elif domain_config:
            # Generate from domain template file structure
            file_structure = domain_config.get("file_structure", [])

            # Group by type and create competencies
            by_type = {}
            for f in file_structure:
                t = f.get("type", "procedure")
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(f)

            competency_num = 1
            for file_type, files in by_type.items():
                if file_type == "department_structure":
                    continue

                # Create competency from file group
                mode = "INFORM"
                if file_type == "procedure":
                    mode = "INFORM/DRAFT"
                elif file_type == "data_reference":
                    mode = "EXECUTE/DRAFT"
                elif file_type == "policy":
                    mode = "INFORM"

                file_refs = ", ".join(f"`{f['num']:02d}_{f['id']}.md`" for f in files[:3])
                title = files[0]["title"].split(" ")[0] + " " + file_type.replace("_", " ").title()

                competencies.append(
                    f"{competency_num}. **{title} ({mode}):** Leverage {file_refs}"
                )
                competency_num += 1

                if competency_num > 7:
                    break

        competencies_text = "\n".join(competencies) if competencies else "Your competencies align with your knowledge base files."

        kb_note = ""
        if kb:
            kb_note = f"\n\nYour knowledge base contains {kb.file_count} files covering governance, regulatory requirements, procedures, and data references."

        self.sections["competencies"] = f"""## [SECTION 5: CORE COMPETENCIES & KNOWLEDGE BASE - {self.SECTION_TARGETS['competencies']} chars]
Your primary function is to leverage your knowledge base to assist the {self.config.director_title}. Your core competencies are:

{competencies_text}{kb_note}"""

    def _build_hierarchy_section(self) -> None:
        """Build Section 6: Knowledge Hierarchy."""
        kb = self.config.knowledge_base

        hierarchy_items = []

        if kb:
            hierarchy = kb.get_knowledge_hierarchy()
            for i, item in enumerate(hierarchy[:5], 1):
                hierarchy_items.append(
                    f"{i}. `{item['file']}`: {item['description']}"
                )
        else:
            # Default hierarchy
            hierarchy_items = [
                "1. `HAAIS_GOVERNANCE.md`: Governance rules and operational modes",
                "2. Regulatory quick reference files: Federal/state requirements",
                "3. Policy files: Department policies and guidelines",
                "4. Procedure files: Standard operating procedures",
                "5. Data reference files: Current data and statistics",
            ]

        hierarchy_text = "\n".join(hierarchy_items)

        self.sections["hierarchy"] = f"""## [SECTION 6: KNOWLEDGE HIERARCHY - {self.SECTION_TARGETS['hierarchy']} chars]
Your knowledge is strictly limited to your knowledge base files. The hierarchy is:

{hierarchy_text}

When information conflicts, defer to higher-ranked sources."""

    def _build_protocols_section(self) -> None:
        """Build Section 7: Response Protocols."""
        self.sections["protocols"] = f"""## [SECTION 7: RESPONSE PROTOCOLS - {self.SECTION_TARGETS['protocols']} chars]
- Always identify yourself as the {self.config.director_title}'s AI assistant.
- For DRAFT requests, clearly label output as a draft requiring human review.
- For INFORM requests, cite source files from your knowledge base (e.g., "According to `file.md`...").
- When escalating, clearly state the reason and provide contact information for {self.config.escalates_to or f'the {self.config.director_title}'}.
- Maintain a professional, precise, and helpful tone at all times.
- Never speculate beyond your knowledge base - acknowledge limitations."""

    def _build_special_section(self) -> None:
        """Build Section 8: Special Protocols."""
        domain_config = get_domain_templates(self.config.domain)

        special_protocols = []

        if self.config.custom_protocols:
            for key, value in self.config.custom_protocols.items():
                special_protocols.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        elif domain_config and domain_config.get("special_protocols"):
            for key, value in domain_config["special_protocols"].items():
                special_protocols.append(f"- **{key.replace('_', ' ').title()}:** {value}")

        # Add universal special protocols
        special_protocols.extend([
            "- **Emergency Situations:** Direct immediately to appropriate emergency services. Do not provide emergency guidance.",
            "- **Media Inquiries:** All media inquiries must be escalated to Communications/Public Affairs.",
            "- **Audit Compliance:** All interactions are logged for quality assurance and compliance monitoring.",
        ])

        protocols_text = "\n".join(special_protocols)

        self.sections["special"] = f"""## [SECTION 8: SPECIAL PROTOCOLS - {self.SECTION_TARGETS['special']} chars]
{protocols_text}"""

    def _combine_sections(self) -> str:
        """Combine all sections into final instructions."""
        section_order = [
            "identity",
            "governance",
            "prohibited",
            "modes",
            "competencies",
            "hierarchy",
            "protocols",
            "special",
        ]

        parts = []
        for section_name in section_order:
            if section_name in self.sections:
                parts.append(self.sections[section_name])

        return "\n\n".join(parts)

    def _compress(self, instructions: str) -> str:
        """Compress instructions to fit character limit.

        Preserves critical sections (identity, prohibited, governance)
        and abbreviates lower-priority content.
        """
        target = self.config.max_chars

        # If only slightly over, just truncate special section
        if len(instructions) <= target * 1.1:
            # Truncate special section
            if "special" in self.sections:
                special = self.sections["special"]
                excess = len(instructions) - target
                if len(special) > excess + 100:
                    self.sections["special"] = special[:len(special) - excess - 50] + "\n[Continued in knowledge base]"
                    return self._combine_sections()

        # More aggressive compression needed
        # Priority: identity, prohibited, governance, modes, protocols, competencies, hierarchy, special
        priority = ["identity", "prohibited", "governance", "modes", "protocols"]
        optional = ["competencies", "hierarchy", "special"]

        # Start with priority sections
        compressed_sections = {}
        current_length = 0

        for section in priority:
            if section in self.sections:
                compressed_sections[section] = self.sections[section]
                current_length += len(self.sections[section])

        # Add optional sections if space permits
        remaining = target - current_length - 200  # Buffer

        for section in optional:
            if section in self.sections:
                section_text = self.sections[section]
                if len(section_text) <= remaining:
                    compressed_sections[section] = section_text
                    remaining -= len(section_text)
                elif remaining > 200:
                    # Truncate this section
                    compressed_sections[section] = section_text[:remaining - 50] + "\n[See knowledge base for complete information]"
                    remaining = 0

        self.sections = compressed_sections
        return self._combine_sections()

    def get_section(self, section_name: str) -> str | None:
        """Get a specific section."""
        return self.sections.get(section_name)

    def get_all_sections(self) -> dict[str, str]:
        """Get all sections."""
        return self.sections.copy()


def build_instructions(
    agent_name: str,
    agent_title: str,
    domain: str,
    director_name: str,
    description: str = "",
    escalates_to: str = "",
    knowledge_base: KnowledgeBase | None = None,
    max_chars: int = 8000,
) -> str:
    """Convenience function to build instructions.

    Args:
        agent_name: Name of the agent (e.g., "Dr. Wellness")
        agent_title: Title (e.g., "Public Health Leadership Asset")
        domain: Domain (e.g., "Public Health")
        director_name: Director's name
        description: Agent description
        escalates_to: Escalation contact
        knowledge_base: Optional KnowledgeBase for file references
        max_chars: Maximum instruction length

    Returns:
        Complete HAAIS-compliant instructions
    """
    config = InstructionConfig(
        agent_name=agent_name,
        agent_title=agent_title,
        domain=domain,
        description=description,
        director_name=director_name,
        escalates_to=escalates_to,
        knowledge_base=knowledge_base,
        max_chars=max_chars,
    )
    builder = InstructionBuilder(config)
    return builder.build()
