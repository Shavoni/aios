"""Voice Provider Registry - Capability-based provider definitions.

Providers are defined by capabilities, not by brand.
This enables deterministic routing based on requirements.
"""

from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Region(str, Enum):
    """Supported deployment regions."""
    US_EAST = "us-east"
    US_WEST = "us-west"
    US_GOV = "us-gov"
    EU_WEST = "eu-west"
    LOCAL = "local"  # On-premise/local deployment


class PIIHandlingMode(str, Enum):
    """How the provider handles PII data."""
    NEVER_STORED = "never_stored"  # Audio/transcripts never stored
    REDACTED_ONLY = "redacted_only"  # Stored only after PII redaction
    ENCRYPTED_STORED = "encrypted_stored"  # Stored with encryption
    FULL_RETENTION = "full_retention"  # Full retention (not for gov)


class CostModel(str, Enum):
    """Provider pricing model."""
    PER_MINUTE = "per_minute"
    PER_CHARACTER = "per_character"
    PER_REQUEST = "per_request"
    FLAT_RATE = "flat_rate"


class ProviderType(str, Enum):
    """Type of voice provider."""
    STT = "stt"  # Speech-to-Text
    TTS = "tts"  # Text-to-Speech
    BOTH = "both"  # Supports both


class ProviderCapabilities(BaseModel):
    """Capability matrix for a voice provider."""

    # STT Capabilities
    streaming_stt: bool = False
    interim_transcripts: bool = False
    endpointing_controls: bool = False
    speaker_diarization: bool = False
    punctuation: bool = True
    profanity_filter: bool = False
    custom_vocabulary: bool = False

    # TTS Capabilities
    streaming_tts: bool = False
    ssml_support: bool = False
    voice_cloning: bool = False
    emotion_control: bool = False
    speed_control: bool = True

    # Interaction Capabilities
    barge_in: bool = False  # Can interrupt/cancel mid-stream
    low_latency_mode: bool = False
    websocket_support: bool = False

    # Compliance Capabilities
    audit_logging: bool = True
    pii_redaction: bool = False
    hipaa_compliant: bool = False
    soc2_compliant: bool = False
    fedramp_certified: bool = False

    # Regions
    supported_regions: list[Region] = Field(default_factory=lambda: [Region.US_EAST])

    # Data Handling
    pii_handling: PIIHandlingMode = PIIHandlingMode.ENCRYPTED_STORED
    data_residency_guaranteed: bool = False


class ProviderHealth(BaseModel):
    """Real-time health status of a provider."""

    is_healthy: bool = True
    is_degraded: bool = False
    last_check: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0  # 0.0 to 1.0
    current_load: float = 0.0  # 0.0 to 1.0

    # Circuit breaker state
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_open_until: str | None = None


class ProviderCost(BaseModel):
    """Cost configuration for a provider."""

    cost_model: CostModel = CostModel.PER_MINUTE
    cost_per_unit: float = 0.0  # USD
    unit_description: str = "minute"
    minimum_charge: float = 0.0

    # Limits
    max_concurrent_sessions: int = 100
    rate_limit_per_minute: int = 60


class VoiceProvider(BaseModel):
    """A registered voice provider with full capability definition."""

    id: str
    name: str
    provider_type: ProviderType
    description: str = ""

    # Capabilities
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)

    # Cost
    cost: ProviderCost = Field(default_factory=ProviderCost)

    # Health (updated at runtime)
    health: ProviderHealth = Field(default_factory=ProviderHealth)

    # Configuration
    api_endpoint: str = ""
    requires_api_key: bool = True

    # Status
    is_enabled: bool = True
    is_approved: bool = False  # Requires governance approval

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# =============================================================================
# Default Provider Definitions
# =============================================================================

DEFAULT_PROVIDERS: dict[str, VoiceProvider] = {
    "deepgram": VoiceProvider(
        id="deepgram",
        name="Deepgram",
        provider_type=ProviderType.BOTH,
        description="Enterprise-grade STT/TTS with low latency",
        capabilities=ProviderCapabilities(
            streaming_stt=True,
            interim_transcripts=True,
            endpointing_controls=True,
            speaker_diarization=True,
            punctuation=True,
            custom_vocabulary=True,
            streaming_tts=True,
            barge_in=True,
            low_latency_mode=True,
            websocket_support=True,
            audit_logging=True,
            pii_redaction=True,
            soc2_compliant=True,
            supported_regions=[Region.US_EAST, Region.US_WEST, Region.EU_WEST],
            pii_handling=PIIHandlingMode.REDACTED_ONLY,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_MINUTE,
            cost_per_unit=0.0043,
            unit_description="minute of audio",
            max_concurrent_sessions=500,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),

    "whisper_local": VoiceProvider(
        id="whisper_local",
        name="Whisper (Local)",
        provider_type=ProviderType.STT,
        description="OpenAI Whisper running locally - data never leaves premises",
        capabilities=ProviderCapabilities(
            streaming_stt=False,  # Whisper is batch-based
            interim_transcripts=False,
            punctuation=True,
            speaker_diarization=False,
            audit_logging=True,
            supported_regions=[Region.LOCAL],
            pii_handling=PIIHandlingMode.NEVER_STORED,
            data_residency_guaranteed=True,
        ),
        cost=ProviderCost(
            cost_model=CostModel.FLAT_RATE,
            cost_per_unit=0.0,
            unit_description="free (infrastructure cost only)",
            max_concurrent_sessions=10,  # Limited by local GPU
            rate_limit_per_minute=20,
        ),
        requires_api_key=False,
        is_approved=True,
    ),

    "whisper_api": VoiceProvider(
        id="whisper_api",
        name="OpenAI Whisper API",
        provider_type=ProviderType.STT,
        description="OpenAI's hosted Whisper API",
        capabilities=ProviderCapabilities(
            streaming_stt=False,
            punctuation=True,
            audit_logging=True,
            supported_regions=[Region.US_EAST],
            pii_handling=PIIHandlingMode.ENCRYPTED_STORED,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_MINUTE,
            cost_per_unit=0.006,
            unit_description="minute of audio",
            max_concurrent_sessions=100,
            rate_limit_per_minute=50,
        ),
        is_approved=True,
    ),

    "elevenlabs": VoiceProvider(
        id="elevenlabs",
        name="ElevenLabs",
        provider_type=ProviderType.TTS,
        description="High-quality neural TTS with voice cloning",
        capabilities=ProviderCapabilities(
            streaming_tts=True,
            ssml_support=True,
            voice_cloning=True,  # Note: may be restricted by governance
            emotion_control=True,
            speed_control=True,
            barge_in=True,
            low_latency_mode=True,
            websocket_support=True,
            audit_logging=True,
            supported_regions=[Region.US_EAST, Region.EU_WEST],
            pii_handling=PIIHandlingMode.ENCRYPTED_STORED,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_CHARACTER,
            cost_per_unit=0.00003,
            unit_description="character",
            max_concurrent_sessions=200,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),

    "azure_speech": VoiceProvider(
        id="azure_speech",
        name="Azure Speech Services",
        provider_type=ProviderType.BOTH,
        description="Microsoft Azure STT/TTS - FedRAMP certified",
        capabilities=ProviderCapabilities(
            streaming_stt=True,
            interim_transcripts=True,
            endpointing_controls=True,
            speaker_diarization=True,
            punctuation=True,
            profanity_filter=True,
            custom_vocabulary=True,
            streaming_tts=True,
            ssml_support=True,
            speed_control=True,
            barge_in=True,
            websocket_support=True,
            audit_logging=True,
            pii_redaction=True,
            hipaa_compliant=True,
            soc2_compliant=True,
            fedramp_certified=True,
            supported_regions=[Region.US_EAST, Region.US_WEST, Region.US_GOV, Region.EU_WEST],
            pii_handling=PIIHandlingMode.REDACTED_ONLY,
            data_residency_guaranteed=True,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_MINUTE,
            cost_per_unit=0.016,
            unit_description="minute (STT) / per million chars (TTS)",
            max_concurrent_sessions=1000,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),

    "google_speech": VoiceProvider(
        id="google_speech",
        name="Google Cloud Speech",
        provider_type=ProviderType.BOTH,
        description="Google Cloud STT/TTS",
        capabilities=ProviderCapabilities(
            streaming_stt=True,
            interim_transcripts=True,
            endpointing_controls=True,
            speaker_diarization=True,
            punctuation=True,
            profanity_filter=True,
            streaming_tts=True,
            ssml_support=True,
            speed_control=True,
            websocket_support=True,
            audit_logging=True,
            soc2_compliant=True,
            supported_regions=[Region.US_EAST, Region.US_WEST, Region.EU_WEST],
            pii_handling=PIIHandlingMode.ENCRYPTED_STORED,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_MINUTE,
            cost_per_unit=0.016,
            unit_description="minute",
            max_concurrent_sessions=500,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),

    "aws_transcribe": VoiceProvider(
        id="aws_transcribe",
        name="AWS Transcribe",
        provider_type=ProviderType.STT,
        description="Amazon Transcribe - GovCloud available",
        capabilities=ProviderCapabilities(
            streaming_stt=True,
            interim_transcripts=True,
            speaker_diarization=True,
            punctuation=True,
            profanity_filter=True,
            custom_vocabulary=True,
            audit_logging=True,
            pii_redaction=True,
            hipaa_compliant=True,
            soc2_compliant=True,
            fedramp_certified=True,
            supported_regions=[Region.US_EAST, Region.US_WEST, Region.US_GOV],
            pii_handling=PIIHandlingMode.REDACTED_ONLY,
            data_residency_guaranteed=True,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_MINUTE,
            cost_per_unit=0.024,
            unit_description="minute",
            max_concurrent_sessions=500,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),

    "aws_polly": VoiceProvider(
        id="aws_polly",
        name="AWS Polly",
        provider_type=ProviderType.TTS,
        description="Amazon Polly TTS - GovCloud available",
        capabilities=ProviderCapabilities(
            streaming_tts=True,
            ssml_support=True,
            speed_control=True,
            audit_logging=True,
            hipaa_compliant=True,
            soc2_compliant=True,
            fedramp_certified=True,
            supported_regions=[Region.US_EAST, Region.US_WEST, Region.US_GOV],
            pii_handling=PIIHandlingMode.NEVER_STORED,
            data_residency_guaranteed=True,
        ),
        cost=ProviderCost(
            cost_model=CostModel.PER_CHARACTER,
            cost_per_unit=0.000004,
            unit_description="character",
            max_concurrent_sessions=500,
            rate_limit_per_minute=100,
        ),
        is_approved=True,
    ),
}


# =============================================================================
# Provider Registry Manager
# =============================================================================

class ProviderRegistry:
    """Manages the registry of voice providers."""

    def __init__(self):
        self._providers: dict[str, VoiceProvider] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default provider definitions."""
        for provider_id, provider in DEFAULT_PROVIDERS.items():
            self._providers[provider_id] = provider.model_copy(deep=True)

    def get_provider(self, provider_id: str) -> VoiceProvider | None:
        """Get a provider by ID."""
        return self._providers.get(provider_id)

    def list_providers(
        self,
        provider_type: ProviderType | None = None,
        enabled_only: bool = True,
        approved_only: bool = True,
    ) -> list[VoiceProvider]:
        """List providers with optional filtering."""
        providers = list(self._providers.values())

        if provider_type:
            providers = [
                p for p in providers
                if p.provider_type == provider_type or p.provider_type == ProviderType.BOTH
            ]

        if enabled_only:
            providers = [p for p in providers if p.is_enabled]

        if approved_only:
            providers = [p for p in providers if p.is_approved]

        return providers

    def find_providers_by_capability(
        self,
        required_capabilities: dict[str, Any],
        provider_type: ProviderType | None = None,
    ) -> list[VoiceProvider]:
        """Find providers that match required capabilities.

        Args:
            required_capabilities: Dict of capability_name -> required_value
            provider_type: Filter by STT/TTS/BOTH

        Returns:
            List of providers matching all requirements
        """
        matching = []

        for provider in self.list_providers(provider_type=provider_type):
            caps = provider.capabilities.model_dump()

            matches = True
            for cap_name, required_value in required_capabilities.items():
                if cap_name not in caps:
                    matches = False
                    break

                actual_value = caps[cap_name]

                # Handle different comparison types
                if isinstance(required_value, bool):
                    if required_value and not actual_value:
                        matches = False
                        break
                elif isinstance(required_value, list):
                    # Check if any required value is in actual list
                    if not any(v in actual_value for v in required_value):
                        matches = False
                        break
                elif actual_value != required_value:
                    matches = False
                    break

            if matches:
                matching.append(provider)

        return matching

    def update_provider_health(
        self,
        provider_id: str,
        is_healthy: bool,
        latency_ms: float | None = None,
        error_rate: float | None = None,
    ) -> bool:
        """Update a provider's health status."""
        provider = self._providers.get(provider_id)
        if not provider:
            return False

        provider.health.is_healthy = is_healthy
        provider.health.last_check = datetime.now(UTC).isoformat()

        if latency_ms is not None:
            provider.health.avg_latency_ms = latency_ms

        if error_rate is not None:
            provider.health.error_rate = error_rate
            provider.health.is_degraded = error_rate > 0.1  # >10% error rate = degraded

        # Update circuit breaker
        if not is_healthy:
            provider.health.consecutive_failures += 1
            if provider.health.consecutive_failures >= 3:
                provider.health.circuit_open = True
        else:
            provider.health.consecutive_failures = 0
            provider.health.circuit_open = False

        return True

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        """Enable or disable a provider."""
        provider = self._providers.get(provider_id)
        if not provider:
            return False
        provider.is_enabled = enabled
        provider.updated_at = datetime.now(UTC).isoformat()
        return True

    def set_provider_approved(self, provider_id: str, approved: bool) -> bool:
        """Set governance approval status for a provider."""
        provider = self._providers.get(provider_id)
        if not provider:
            return False
        provider.is_approved = approved
        provider.updated_at = datetime.now(UTC).isoformat()
        return True

    def get_healthy_providers(
        self,
        provider_type: ProviderType | None = None,
    ) -> list[VoiceProvider]:
        """Get all healthy, enabled, approved providers."""
        providers = self.list_providers(provider_type=provider_type)
        return [
            p for p in providers
            if p.health.is_healthy and not p.health.circuit_open
        ]


# Singleton instance
_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get the provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


__all__ = [
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
]
