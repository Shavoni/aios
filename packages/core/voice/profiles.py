"""Voice/Communication Profiles - User-facing abstractions over providers.

Profiles are what users select. Providers are implementation details.
This separates product concerns from vendor concerns.
"""

from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from .registry import (
    Region,
    PIIHandlingMode,
    ProviderType,
    VoiceProvider,
    get_provider_registry,
)


class ProfilePriority(str, Enum):
    """What the profile optimizes for."""
    LATENCY = "latency"  # Fastest response time
    PRIVACY = "privacy"  # Maximum data protection
    COST = "cost"  # Lowest cost
    COMPLIANCE = "compliance"  # Maximum compliance certifications
    QUALITY = "quality"  # Best quality output
    ACCESSIBILITY = "accessibility"  # Best for accessibility needs


class VoiceProfile(BaseModel):
    """A communication profile that maps to allowed providers.

    Users select profiles, not providers. The system selects
    the best provider based on profile requirements.
    """

    id: str
    name: str
    description: str
    priority: ProfilePriority

    # What this profile optimizes for (shown to users)
    benefits: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)

    # Required capabilities (must have all of these)
    required_capabilities: dict[str, Any] = Field(default_factory=dict)

    # Preferred capabilities (nice to have, used for ranking)
    preferred_capabilities: dict[str, Any] = Field(default_factory=dict)

    # Forbidden capabilities (must NOT have these)
    forbidden_capabilities: dict[str, Any] = Field(default_factory=dict)

    # Region restrictions
    allowed_regions: list[Region] = Field(default_factory=list)

    # PII handling restrictions
    allowed_pii_modes: list[PIIHandlingMode] = Field(default_factory=list)

    # Cost limits
    max_cost_per_minute: float | None = None

    # Latency requirements
    max_latency_ms: float | None = None

    # Provider ordering preference (for tie-breaking)
    preferred_provider_order: list[str] = Field(default_factory=list)

    # Fallback behavior
    fallback_to_text: bool = True  # If no voice provider available
    allow_degraded_providers: bool = False

    # Metadata
    is_default: bool = False
    is_enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# =============================================================================
# Default Profile Definitions
# =============================================================================

DEFAULT_PROFILES: dict[str, VoiceProfile] = {
    "compliance_locked": VoiceProfile(
        id="compliance_locked",
        name="Compliance Locked",
        description="Maximum compliance for government and regulated industries. FedRAMP certified providers, US data residency, full audit trails.",
        priority=ProfilePriority.COMPLIANCE,
        benefits=[
            "FedRAMP certified providers only",
            "US data residency guaranteed",
            "Full audit logging",
            "HIPAA compliant",
            "PII redaction enabled",
        ],
        tradeoffs=[
            "Higher latency than low-latency mode",
            "Higher cost than economy options",
            "Fewer provider options",
        ],
        required_capabilities={
            "audit_logging": True,
            "fedramp_certified": True,
            "data_residency_guaranteed": True,
            "pii_redaction": True,
        },
        preferred_capabilities={
            "hipaa_compliant": True,
            "soc2_compliant": True,
        },
        forbidden_capabilities={
            "voice_cloning": True,  # No voice cloning in compliance mode
        },
        allowed_regions=[Region.US_EAST, Region.US_WEST, Region.US_GOV],
        allowed_pii_modes=[PIIHandlingMode.NEVER_STORED, PIIHandlingMode.REDACTED_ONLY],
        preferred_provider_order=["azure_speech", "aws_transcribe", "aws_polly"],
        allow_degraded_providers=False,
        is_default=True,
    ),

    "low_latency": VoiceProfile(
        id="low_latency",
        name="Ultra-Low Latency",
        description="Optimized for fastest possible response time. Best for real-time conversations and executive communications.",
        priority=ProfilePriority.LATENCY,
        benefits=[
            "Fastest response times",
            "Real-time streaming",
            "Barge-in support (interrupt mid-speech)",
            "WebSocket connections",
        ],
        tradeoffs=[
            "May use non-FedRAMP providers",
            "Higher cost than economy",
            "Data may be processed outside US",
        ],
        required_capabilities={
            "streaming_stt": True,
            "streaming_tts": True,
            "low_latency_mode": True,
            "barge_in": True,
            "websocket_support": True,
        },
        preferred_capabilities={
            "interim_transcripts": True,
        },
        allowed_regions=[Region.US_EAST, Region.US_WEST, Region.EU_WEST],
        allowed_pii_modes=[
            PIIHandlingMode.NEVER_STORED,
            PIIHandlingMode.REDACTED_ONLY,
            PIIHandlingMode.ENCRYPTED_STORED,
        ],
        max_latency_ms=200.0,
        preferred_provider_order=["deepgram", "azure_speech", "google_speech"],
        allow_degraded_providers=False,
    ),

    "privacy_first": VoiceProfile(
        id="privacy_first",
        name="Privacy First",
        description="Maximum privacy protection. Prefers local processing, no cloud storage of audio or transcripts.",
        priority=ProfilePriority.PRIVACY,
        benefits=[
            "Data never leaves your infrastructure",
            "No cloud storage of audio",
            "No third-party data sharing",
            "Local processing available",
        ],
        tradeoffs=[
            "Slower than cloud options",
            "Limited to local infrastructure capacity",
            "No real-time streaming",
        ],
        required_capabilities={
            "audit_logging": True,
        },
        preferred_capabilities={
            "data_residency_guaranteed": True,
        },
        forbidden_capabilities={
            "voice_cloning": True,
        },
        allowed_regions=[Region.LOCAL, Region.US_GOV],
        allowed_pii_modes=[PIIHandlingMode.NEVER_STORED],
        preferred_provider_order=["whisper_local", "azure_speech", "aws_transcribe"],
        allow_degraded_providers=True,  # Accept slower local processing
    ),

    "cost_saver": VoiceProfile(
        id="cost_saver",
        name="Cost Saver",
        description="Optimized for lowest cost. Best for high-volume, non-urgent processing.",
        priority=ProfilePriority.COST,
        benefits=[
            "Lowest per-minute cost",
            "Good for batch processing",
            "High volume discounts",
        ],
        tradeoffs=[
            "Higher latency acceptable",
            "May not have real-time streaming",
            "Fewer advanced features",
        ],
        required_capabilities={
            "audit_logging": True,
        },
        preferred_capabilities={
            "punctuation": True,
        },
        allowed_regions=[Region.US_EAST, Region.US_WEST, Region.LOCAL],
        allowed_pii_modes=[
            PIIHandlingMode.NEVER_STORED,
            PIIHandlingMode.REDACTED_ONLY,
            PIIHandlingMode.ENCRYPTED_STORED,
        ],
        max_cost_per_minute=0.01,  # $0.01/min max
        preferred_provider_order=["whisper_local", "whisper_api", "deepgram"],
        allow_degraded_providers=True,
    ),

    "accessibility": VoiceProfile(
        id="accessibility",
        name="Accessibility Mode",
        description="Optimized for accessibility needs. Clearer speech, confirmations, slower pace options.",
        priority=ProfilePriority.ACCESSIBILITY,
        benefits=[
            "Clearer TTS output",
            "Speed control available",
            "SSML support for prosody",
            "Confirmation prompts",
            "Speaker diarization",
        ],
        tradeoffs=[
            "Slower overall pace",
            "Higher latency acceptable",
            "May cost more per interaction",
        ],
        required_capabilities={
            "speed_control": True,
            "ssml_support": True,
            "punctuation": True,
            "audit_logging": True,
        },
        preferred_capabilities={
            "speaker_diarization": True,
            "streaming_tts": True,
        },
        allowed_regions=[Region.US_EAST, Region.US_WEST, Region.US_GOV, Region.LOCAL],
        allowed_pii_modes=[
            PIIHandlingMode.NEVER_STORED,
            PIIHandlingMode.REDACTED_ONLY,
            PIIHandlingMode.ENCRYPTED_STORED,
        ],
        preferred_provider_order=["azure_speech", "aws_polly", "elevenlabs"],
        allow_degraded_providers=True,
    ),

    "executive": VoiceProfile(
        id="executive",
        name="Executive Quality",
        description="Premium quality for executive communications. Best voices, lowest latency, highest reliability.",
        priority=ProfilePriority.QUALITY,
        benefits=[
            "Premium voice quality",
            "Ultra-low latency",
            "Highest reliability",
            "Emotion control available",
            "Natural prosody",
        ],
        tradeoffs=[
            "Highest cost option",
            "May use advanced features",
        ],
        required_capabilities={
            "streaming_stt": True,
            "streaming_tts": True,
            "low_latency_mode": True,
            "barge_in": True,
            "audit_logging": True,
        },
        preferred_capabilities={
            "emotion_control": True,
            "ssml_support": True,
            "interim_transcripts": True,
        },
        forbidden_capabilities={
            "voice_cloning": True,  # No cloning even in executive mode
        },
        allowed_regions=[Region.US_EAST, Region.US_WEST],
        allowed_pii_modes=[
            PIIHandlingMode.NEVER_STORED,
            PIIHandlingMode.REDACTED_ONLY,
            PIIHandlingMode.ENCRYPTED_STORED,
        ],
        max_latency_ms=150.0,
        preferred_provider_order=["elevenlabs", "deepgram", "azure_speech"],
        allow_degraded_providers=False,
    ),
}


# =============================================================================
# Profile Manager
# =============================================================================

class ProfileManager:
    """Manages communication profiles and provider selection."""

    def __init__(self):
        self._profiles: dict[str, VoiceProfile] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default profile definitions."""
        for profile_id, profile in DEFAULT_PROFILES.items():
            self._profiles[profile_id] = profile.model_copy(deep=True)

    def get_profile(self, profile_id: str) -> VoiceProfile | None:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    def get_default_profile(self) -> VoiceProfile:
        """Get the default profile."""
        for profile in self._profiles.values():
            if profile.is_default:
                return profile
        # Fallback to compliance_locked if no default set
        return self._profiles.get("compliance_locked", list(self._profiles.values())[0])

    def list_profiles(self, enabled_only: bool = True) -> list[VoiceProfile]:
        """List all profiles."""
        profiles = list(self._profiles.values())
        if enabled_only:
            profiles = [p for p in profiles if p.is_enabled]
        return profiles

    def get_eligible_providers(
        self,
        profile_id: str,
        provider_type: ProviderType | None = None,
    ) -> list[VoiceProvider]:
        """Get providers eligible for a profile, sorted by preference.

        Args:
            profile_id: The profile to match against
            provider_type: Filter by STT/TTS/BOTH

        Returns:
            List of eligible providers, sorted by profile preference
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return []

        registry = get_provider_registry()
        all_providers = registry.list_providers(provider_type=provider_type)

        eligible = []
        for provider in all_providers:
            if self._provider_matches_profile(provider, profile):
                eligible.append(provider)

        # Sort by profile preference
        def sort_key(p: VoiceProvider) -> tuple:
            # Preferred providers first
            try:
                pref_index = profile.preferred_provider_order.index(p.id)
            except ValueError:
                pref_index = 999

            # Then by health
            health_score = 0 if p.health.is_healthy else 1

            # Then by latency (if latency matters)
            latency = p.health.avg_latency_ms

            # Then by cost
            cost = p.cost.cost_per_unit

            return (pref_index, health_score, latency, cost)

        eligible.sort(key=sort_key)
        return eligible

    def _provider_matches_profile(
        self,
        provider: VoiceProvider,
        profile: VoiceProfile,
    ) -> bool:
        """Check if a provider matches profile requirements."""
        caps = provider.capabilities.model_dump()

        # Check required capabilities
        for cap_name, required_value in profile.required_capabilities.items():
            if cap_name not in caps:
                return False
            if isinstance(required_value, bool) and required_value:
                if not caps[cap_name]:
                    return False
            elif isinstance(required_value, list):
                if not any(v in caps.get(cap_name, []) for v in required_value):
                    return False

        # Check forbidden capabilities
        for cap_name, forbidden_value in profile.forbidden_capabilities.items():
            if cap_name in caps:
                if isinstance(forbidden_value, bool) and forbidden_value:
                    if caps[cap_name]:
                        return False

        # Check region restrictions
        if profile.allowed_regions:
            provider_regions = set(provider.capabilities.supported_regions)
            allowed_regions = set(profile.allowed_regions)
            if not provider_regions & allowed_regions:
                return False

        # Check PII handling
        if profile.allowed_pii_modes:
            if provider.capabilities.pii_handling not in profile.allowed_pii_modes:
                return False

        # Check cost limit
        if profile.max_cost_per_minute is not None:
            # Convert to per-minute cost for comparison
            if provider.cost.cost_model.value == "per_minute":
                if provider.cost.cost_per_unit > profile.max_cost_per_minute:
                    return False

        # Check latency requirement (if provider has health data)
        if profile.max_latency_ms is not None:
            if provider.health.avg_latency_ms > profile.max_latency_ms:
                if not profile.allow_degraded_providers:
                    return False

        # Check health (unless profile allows degraded)
        if not profile.allow_degraded_providers:
            if provider.health.circuit_open or not provider.health.is_healthy:
                return False

        return True

    def select_best_provider(
        self,
        profile_id: str,
        provider_type: ProviderType,
    ) -> VoiceProvider | None:
        """Select the best provider for a profile.

        Returns the top-ranked eligible provider, or None if none available.
        """
        eligible = self.get_eligible_providers(profile_id, provider_type)
        return eligible[0] if eligible else None

    def set_profile_enabled(self, profile_id: str, enabled: bool) -> bool:
        """Enable or disable a profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        profile.is_enabled = enabled
        return True

    def set_default_profile(self, profile_id: str) -> bool:
        """Set a profile as the default."""
        if profile_id not in self._profiles:
            return False

        for p in self._profiles.values():
            p.is_default = (p.id == profile_id)
        return True


# Singleton instance
_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """Get the profile manager singleton."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


__all__ = [
    "ProfilePriority",
    "VoiceProfile",
    "ProfileManager",
    "get_profile_manager",
    "DEFAULT_PROFILES",
]
