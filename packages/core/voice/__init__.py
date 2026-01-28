"""Voice Platform Module - Enterprise voice/speech capabilities.

This module provides a 3-layer architecture for voice services:

Layer A - Governance Policy (immutable):
    Defines allowed providers, regions, data handling rules, and "no-go" rules.
    Managed by organization admins, requires approval to change.

Layer B - Department Profiles (selectable):
    Pre-configured profiles optimized for different use cases.
    Departments choose a profile, not individual providers.

Layer C - Runtime Routing (automatic):
    System automatically selects the best provider based on:
    - Profile requirements
    - Real-time health and latency
    - Circuit breaker state
    - Cost optimization

Key principle: "Vendors are implementation details. Profiles are product."
"""

from .registry import (
    Region,
    PIIHandlingMode,
    CostModel,
    ProviderType,
    ProviderCapabilities,
    ProviderHealth,
    ProviderCost,
    VoiceProvider,
    ProviderRegistry,
    get_provider_registry,
    DEFAULT_PROVIDERS,
)

from .profiles import (
    ProfilePriority,
    VoiceProfile,
    ProfileManager,
    get_profile_manager,
    DEFAULT_PROFILES,
)

from .router import (
    RouteDecision,
    CircuitState,
    ProviderCircuit,
    RouteResult,
    SessionRoute,
    VoiceRouter,
    get_voice_router,
)

from .audit import (
    VoiceEventType,
    VoiceAuditEvent,
    VoiceAuditLog,
    get_voice_audit_log,
)


__all__ = [
    # Registry
    "Region",
    "PIIHandlingMode",
    "CostModel",
    "ProviderType",
    "ProviderCapabilities",
    "ProviderHealth",
    "ProviderCost",
    "VoiceProvider",
    "ProviderRegistry",
    "get_provider_registry",
    "DEFAULT_PROVIDERS",

    # Profiles
    "ProfilePriority",
    "VoiceProfile",
    "ProfileManager",
    "get_profile_manager",
    "DEFAULT_PROFILES",

    # Router
    "RouteDecision",
    "CircuitState",
    "ProviderCircuit",
    "RouteResult",
    "SessionRoute",
    "VoiceRouter",
    "get_voice_router",

    # Audit
    "VoiceEventType",
    "VoiceAuditEvent",
    "VoiceAuditLog",
    "get_voice_audit_log",
]
