"""
GPT Factory Data Models

AIOS-native models with no artificial limits.
Export adapters handle platform-specific constraints.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class OrganizationType(str, Enum):
    """Type of organization being processed."""
    MUNICIPAL = "municipal"          # City/county government
    STATE = "state"                  # State government
    FEDERAL = "federal"              # Federal agency
    EDUCATION_K12 = "education_k12"  # K-12 school district
    EDUCATION_HIGHER = "education_higher"  # University/college
    HEALTHCARE = "healthcare"        # Hospital/health system
    ENTERPRISE = "enterprise"        # Corporate/business
    NONPROFIT = "nonprofit"          # Non-profit organization


class CandidateType(str, Enum):
    """Type of agent candidate discovered."""
    # Leadership
    EXECUTIVE = "executive"          # Mayor, CEO, President
    CABINET = "cabinet"              # Cabinet-level officials
    DIRECTOR = "director"            # Department directors
    DEPUTY = "deputy"                # Deputy directors

    # Departments - Municipal
    PUBLIC_SAFETY = "public_safety"
    PUBLIC_WORKS = "public_works"
    PUBLIC_HEALTH = "public_health"
    PUBLIC_UTILITIES = "public_utilities"
    FINANCE = "finance"
    HUMAN_RESOURCES = "human_resources"
    LEGAL = "legal"
    PLANNING = "planning"
    BUILDING_HOUSING = "building_housing"
    PARKS_RECREATION = "parks_recreation"
    COMMUNICATIONS = "communications"
    INFORMATION_TECHNOLOGY = "information_technology"

    # Departments - Education
    ADMISSIONS = "admissions"
    REGISTRAR = "registrar"
    FINANCIAL_AID = "financial_aid"
    STUDENT_SERVICES = "student_services"
    ACADEMIC_AFFAIRS = "academic_affairs"

    # Departments - Enterprise
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    IT_SUPPORT = "it_support"

    # Services
    SERVICE_PORTAL = "service_portal"   # 311, help desk
    DATA_PORTAL = "data_portal"         # Open data
    BOARD_COMMISSION = "board_commission"

    # Special
    CONCIERGE = "concierge"            # Router/triage agent
    GENERAL = "general"                # Generic fallback


class SourceType(str, Enum):
    """Type of knowledge source."""
    POLICY = "policy"                # Internal policy document
    ORDINANCE = "ordinance"          # Legal ordinance/statute
    REGULATION = "regulation"        # Regulatory requirement
    PROCEDURE = "procedure"          # Standard operating procedure
    FAQ = "faq"                      # Frequently asked questions
    FORM = "form"                    # Official form/application
    GUIDE = "guide"                  # User guide/manual
    WEB_CONTENT = "web_content"      # Scraped web page
    API_DATA = "api_data"            # Data from API
    HUMAN_INPUT = "human_input"      # Human-provided content


class AuthorityLevel(str, Enum):
    """Authority level of a source (highest to lowest)."""
    CONSTITUTIONAL = "constitutional"  # Charter, constitution
    STATUTORY = "statutory"            # Law, ordinance
    REGULATORY = "regulatory"          # Regulation, rule
    ORGANIZATIONAL = "organizational"  # Organization-wide policy
    DEPARTMENTAL = "departmental"      # Department policy
    OPERATIONAL = "operational"        # Procedure, guideline


class HITLMode(str, Enum):
    """Human-in-the-loop modes."""
    INFORM = "inform"        # Respond immediately
    DRAFT = "draft"          # Queue for review
    EXECUTE = "execute"      # Require approval
    ESCALATE = "escalate"    # Human takeover


class ExportTarget(str, Enum):
    """Export target platforms."""
    AIOS_NATIVE = "aios_native"      # HAAIS AIOS (full fidelity)
    OPENAI_GPT = "openai_gpt"        # OpenAI Custom GPTs
    AZURE_OPENAI = "azure_openai"    # Azure OpenAI Service
    ANTHROPIC = "anthropic"          # Claude/Anthropic
    LOCAL_LLM = "local_llm"          # Local deployment


class ValidationStatus(str, Enum):
    """Validation result status."""
    PASSED = "passed"
    WARNINGS = "warnings"
    FAILED = "failed"


# =============================================================================
# ORGANIZATION MODELS
# =============================================================================

class ContactInfo(BaseModel):
    """Contact information for a person or department."""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class OrganizationUnit(BaseModel):
    """A unit within an organization (department, division, etc.)."""
    id: str
    name: str
    type: CandidateType
    description: Optional[str] = None
    url: Optional[str] = None
    parent_id: Optional[str] = None
    contact: Optional[ContactInfo] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Organization(BaseModel):
    """Discovered organization structure."""
    id: str
    name: str
    type: OrganizationType
    url: str
    description: Optional[str] = None

    # Leadership
    executive: Optional[ContactInfo] = None
    leadership: list[ContactInfo] = Field(default_factory=list)

    # Structure
    units: list[OrganizationUnit] = Field(default_factory=list)

    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovery_depth: int = 0
    pages_crawled: int = 0

    # Source URLs
    source_urls: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# =============================================================================
# CANDIDATE MODELS
# =============================================================================

class AgentCandidate(BaseModel):
    """A candidate for agent creation."""
    id: str
    organization_id: str

    # Identity
    name: str
    suggested_agent_name: str
    type: CandidateType

    # Discovery info
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1 confidence score
    source_urls: list[str] = Field(default_factory=list)

    # Extracted info
    description: Optional[str] = None
    contact: Optional[ContactInfo] = None

    # Selection state
    selected: bool = False
    archetype_id: Optional[str] = None  # Matched archetype

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# KNOWLEDGE MODELS
# =============================================================================

class KnowledgeSource(BaseModel):
    """A knowledge source for an agent."""
    id: str
    agent_id: str

    # Source info
    name: str
    source_type: SourceType
    authority_level: AuthorityLevel

    # Content
    content: Optional[str] = None  # Raw content (no size limit in AIOS)
    url: Optional[str] = None
    file_path: Optional[str] = None

    # Metadata
    section_reference: Optional[str] = None  # e.g., "Policy 4.2"
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

    # Processing state
    processed: bool = False
    chunk_count: int = 0
    embedding_model: Optional[str] = None

    # Verification
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# AGENT BLUEPRINT MODELS
# =============================================================================

class GovernanceConfig(BaseModel):
    """Governance configuration for an agent."""
    default_hitl_mode: HITLMode = HITLMode.INFORM

    # Risk triggers -> HITL mode escalation
    risk_escalations: dict[str, HITLMode] = Field(default_factory=lambda: {
        "PII": HITLMode.ESCALATE,
        "LEGAL": HITLMode.DRAFT,
        "FINANCIAL": HITLMode.DRAFT,
        "PERSONNEL": HITLMode.EXECUTE,
    })

    # Prohibited topics (always escalate)
    prohibited_topics: list[str] = Field(default_factory=list)

    # Grounding requirements
    require_grounding: bool = True
    min_grounding_score: float = 0.5
    require_verified_sources: bool = False


class Capability(BaseModel):
    """A capability the agent has."""
    name: str
    description: str
    examples: list[str] = Field(default_factory=list)


class Guardrail(BaseModel):
    """A guardrail/constraint on agent behavior."""
    name: str
    description: str
    severity: str = "hard"  # hard (block) or soft (warn)
    examples: list[str] = Field(default_factory=list)


class AgentBlueprint(BaseModel):
    """
    Complete agent configuration blueprint.

    AIOS-native: No artificial limits on content size.
    Export adapters handle platform-specific constraints.
    """
    id: str
    organization_id: str
    archetype_id: Optional[str] = None

    # Identity
    name: str                    # Display name (e.g., "Dr. David Margolius")
    title: str                   # Role title (e.g., "Director of Public Health")
    domain: str                  # Domain category (e.g., "PublicHealth")
    avatar_url: Optional[str] = None

    # Description (AIOS: unlimited, OpenAI: 300 chars)
    description_short: str       # Elevator pitch (fits OpenAI limit)
    description_full: str        # Complete description (AIOS native)

    # Instructions (AIOS: unlimited, OpenAI: 8000 chars)
    instructions: str            # Full system prompt (can be 50K+ chars)
    instructions_summary: Optional[str] = None  # Condensed for export

    # Capabilities & Constraints
    capabilities: list[Capability] = Field(default_factory=list)
    guardrails: list[Guardrail] = Field(default_factory=list)

    # Knowledge (AIOS: unlimited, OpenAI: 20 files/512MB)
    knowledge_sources: list[KnowledgeSource] = Field(default_factory=list)

    # Governance
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)

    # Relationships
    escalates_to: Optional[str] = None
    collaborates_with: list[str] = Field(default_factory=list)
    is_router: bool = False

    # Conversation starters
    conversation_starters: list[str] = Field(default_factory=list)

    # Status
    status: str = "draft"  # draft, validated, deployed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# =============================================================================
# VALIDATION MODELS
# =============================================================================

class ValidationIssue(BaseModel):
    """A validation issue found during agent validation."""
    severity: str  # error, warning, info
    category: str  # instructions, knowledge, governance, etc.
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class TestScenario(BaseModel):
    """A test scenario for agent validation."""
    id: str
    name: str
    query: str
    expected_behavior: str
    expected_sources: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Result of running a test scenario."""
    scenario_id: str
    passed: bool
    response: Optional[str] = None
    actual_behavior: Optional[str] = None
    issues: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Complete validation report for an agent."""
    agent_id: str
    status: ValidationStatus

    # Issues found
    issues: list[ValidationIssue] = Field(default_factory=list)

    # Test results
    test_results: list[TestResult] = Field(default_factory=list)

    # Scores
    overall_score: float = Field(ge=0.0, le=1.0)
    instruction_score: float = Field(ge=0.0, le=1.0)
    knowledge_score: float = Field(ge=0.0, le=1.0)
    governance_score: float = Field(ge=0.0, le=1.0)

    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validator_version: str = "1.0.0"

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# =============================================================================
# EXPORT MODELS
# =============================================================================

class ExportResult(BaseModel):
    """Result of exporting an agent to a target platform."""
    agent_id: str
    target: ExportTarget
    success: bool

    # Output
    output_path: Optional[str] = None
    output_data: Optional[dict[str, Any]] = None

    # Transformations applied
    transformations: list[str] = Field(default_factory=list)

    # Warnings (e.g., content truncated)
    warnings: list[str] = Field(default_factory=list)

    exported_at: datetime = Field(default_factory=datetime.utcnow)
