"""Municipal Onboarding System for aiOS.

Automates discovery, configuration, and deployment of HAAIS-governed
AI agents for any municipality.

Key components:
- Discovery: Auto-discover municipal organizational structure from websites
- Catalog: Extract and categorize open data from municipal data portals
- Config: Configuration management for onboarding workflow
- Manifest: Generate deployment manifests for AI agents
- Deploy: Orchestrate agent deployment with governance
- KB Generator: Create deep, comprehensive knowledge bases (15-20 files/agent)
- Instruction Builder: Generate HAAIS-compliant instructions with KB references
- Platforms: Multi-platform agent generation (Copilot, ChatGPT, Azure, N8N, Vertex)
"""

from packages.onboarding.discovery import (
    DiscoveryEngine,
    DiscoveryResult,
    Department,
    Executive,
    DataPortal,
    start_discovery,
    get_discovery_status,
)
from packages.onboarding.llm_discovery import (
    LLMDiscoveryEngine,
    LLMExtractionResult,
    EnhancedDepartment,
    EnhancedDiscoveryResult,
    get_llm_discovery_engine,
)
from packages.onboarding.catalog import (
    CatalogExtractor,
    DatasetCatalog,
    Dataset,
)
from packages.onboarding.config import (
    OnboardingConfig,
    ConfigSection,
    save_config,
    load_config,
    validate_config,
)
from packages.onboarding.manifest import (
    ManifestGenerator,
    DeploymentManifest,
    generate_manifest,
)
from packages.onboarding.deploy import (
    DeploymentOrchestrator,
    DeploymentStatus,
    start_deployment,
    get_deployment_status,
)
from packages.onboarding.kb_generator import (
    KBGenerator,
    GeneratorConfig,
    generate_knowledge_base,
    KBFile,
    KnowledgeBase,
    REGULATORY_TEMPLATES,
    DOMAIN_TEMPLATES,
)
from packages.onboarding.instruction_builder import (
    InstructionBuilder,
    InstructionConfig,
    build_instructions,
)
from packages.onboarding.platforms import (
    PlatformAdapter,
    PlatformConfig,
    PlatformType,
    AgentOutput,
    get_adapter,
    generate_for_platform,
    generate_for_all_platforms,
    get_available_platforms,
    compare_platforms,
)

__all__ = [
    # Discovery
    "DiscoveryEngine",
    "DiscoveryResult",
    "Department",
    "Executive",
    "DataPortal",
    "start_discovery",
    "get_discovery_status",
    # LLM-Enhanced Discovery
    "LLMDiscoveryEngine",
    "LLMExtractionResult",
    "EnhancedDepartment",
    "EnhancedDiscoveryResult",
    "get_llm_discovery_engine",
    # Catalog
    "CatalogExtractor",
    "DatasetCatalog",
    "Dataset",
    # Config
    "OnboardingConfig",
    "ConfigSection",
    "save_config",
    "load_config",
    "validate_config",
    # Manifest
    "ManifestGenerator",
    "DeploymentManifest",
    "generate_manifest",
    # Deploy
    "DeploymentOrchestrator",
    "DeploymentStatus",
    "start_deployment",
    "get_deployment_status",
    # KB Generator
    "KBGenerator",
    "GeneratorConfig",
    "generate_knowledge_base",
    "KBFile",
    "KnowledgeBase",
    "REGULATORY_TEMPLATES",
    "DOMAIN_TEMPLATES",
    # Instruction Builder
    "InstructionBuilder",
    "InstructionConfig",
    "build_instructions",
    # Platforms
    "PlatformAdapter",
    "PlatformConfig",
    "PlatformType",
    "AgentOutput",
    "get_adapter",
    "generate_for_platform",
    "generate_for_all_platforms",
    "get_available_platforms",
    "compare_platforms",
]

# Auto-Onboarding Wizard
from packages.onboarding.wizard import (
    OnboardingWizard,
    WizardState,
    WizardStep,
    ConfidenceLevel,
    ConfidenceScore,
    DetectedDepartment,
    TemplateMatch,
    DeploymentPreview,
    get_wizard,
)

# API Endpoints
from packages.onboarding.api import (
    router as onboarding_router,
    include_router as include_onboarding_router,
)

__all__ += [
    # Wizard
    "OnboardingWizard",
    "WizardState",
    "WizardStep",
    "ConfidenceLevel",
    "ConfidenceScore",
    "DetectedDepartment",
    "TemplateMatch",
    "DeploymentPreview",
    "get_wizard",
    # API
    "onboarding_router",
    "include_onboarding_router",
]

# Deployment Package components
from packages.onboarding.deployment import (
    DeploymentPackage,
    DeploymentPackageGenerator,
    DeploymentExecutor,
    ApprovalManager,
    ManifestChecksum,
)

__all__ += [
    "DeploymentPackage",
    "DeploymentPackageGenerator",
    "DeploymentExecutor",
    "ApprovalManager",
    "ManifestChecksum",
]
