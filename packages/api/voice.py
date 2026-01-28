"""Voice Platform API Endpoints.

Provides endpoints for:
- Listing and managing communication profiles
- Viewing provider capabilities (governance only)
- Routing sessions to providers
- Health and circuit breaker status
- Audit log access
"""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.core.voice import (
    # Registry
    ProviderType,
    VoiceProvider,
    get_provider_registry,

    # Profiles
    VoiceProfile,
    get_profile_manager,
    DEFAULT_PROFILES,

    # Router
    RouteResult,
    get_voice_router,

    # Audit
    VoiceEventType,
    get_voice_audit_log,
)

router = APIRouter(prefix="/voice", tags=["Voice Platform"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ProfileListResponse(BaseModel):
    """Response containing list of profiles."""
    profiles: list[VoiceProfile]
    total: int
    default_profile_id: str


class ProviderListResponse(BaseModel):
    """Response containing list of providers."""
    providers: list[VoiceProvider]
    total: int


class RouteSessionRequest(BaseModel):
    """Request to route a voice session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str = Field(default="compliance_locked")
    provider_type: str = Field(default="both")  # "stt", "tts", or "both"
    org_id: str = Field(default="default")
    department_id: str = Field(default="")
    user_id: str = Field(default="")


class FallbackRequest(BaseModel):
    """Request to trigger fallback for a session."""
    session_id: str
    reason: str = ""


class RecordEventRequest(BaseModel):
    """Request to record a provider success/failure."""
    session_id: str
    provider_id: str
    success: bool
    latency_ms: float = 0.0
    error_message: str = ""


class HealthResponse(BaseModel):
    """Response containing health status."""
    circuits: dict[str, dict]
    active_sessions: int
    routing_stats: dict[str, Any]


class AuditSummaryResponse(BaseModel):
    """Response containing audit summary."""
    total_events: int
    events_by_type: dict[str, int]
    providers_used: list[str]
    avg_latency_ms: float
    fallback_count: int
    error_count: int


# =============================================================================
# Profile Endpoints (User-Facing)
# =============================================================================


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles(
    enabled_only: bool = Query(default=True),
) -> ProfileListResponse:
    """List available communication profiles.

    Profiles are the user-facing abstraction over voice providers.
    Users select a profile, not a specific provider.
    """
    manager = get_profile_manager()
    profiles = manager.list_profiles(enabled_only=enabled_only)
    default_profile = manager.get_default_profile()

    return ProfileListResponse(
        profiles=profiles,
        total=len(profiles),
        default_profile_id=default_profile.id,
    )


@router.get("/profiles/{profile_id}", response_model=VoiceProfile)
async def get_profile(profile_id: str) -> VoiceProfile:
    """Get a specific profile by ID."""
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    return profile


@router.get("/profiles/{profile_id}/eligible-providers")
async def get_eligible_providers(
    profile_id: str,
    provider_type: str = Query(default="both"),
) -> dict:
    """Get providers eligible for a profile.

    This is primarily for debugging and governance review.
    Users should not need to see this.
    """
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    ptype = ProviderType(provider_type) if provider_type != "both" else None
    providers = manager.get_eligible_providers(profile_id, ptype)

    return {
        "profile_id": profile_id,
        "provider_type": provider_type,
        "eligible_providers": [
            {
                "id": p.id,
                "name": p.name,
                "is_healthy": p.health.is_healthy,
                "latency_ms": p.health.avg_latency_ms,
            }
            for p in providers
        ],
        "total": len(providers),
    }


@router.post("/profiles/{profile_id}/enable")
async def enable_profile(profile_id: str) -> dict:
    """Enable a profile (governance action)."""
    manager = get_profile_manager()
    if manager.set_profile_enabled(profile_id, True):
        return {"status": "ok", "message": f"Profile '{profile_id}' enabled"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Profile '{profile_id}' not found",
    )


@router.post("/profiles/{profile_id}/disable")
async def disable_profile(profile_id: str) -> dict:
    """Disable a profile (governance action)."""
    manager = get_profile_manager()
    if manager.set_profile_enabled(profile_id, False):
        return {"status": "ok", "message": f"Profile '{profile_id}' disabled"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Profile '{profile_id}' not found",
    )


@router.post("/profiles/{profile_id}/set-default")
async def set_default_profile(profile_id: str) -> dict:
    """Set a profile as the default (governance action)."""
    manager = get_profile_manager()
    if manager.set_default_profile(profile_id):
        return {"status": "ok", "message": f"Profile '{profile_id}' is now the default"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Profile '{profile_id}' not found",
    )


# =============================================================================
# Provider Endpoints (Governance Only)
# =============================================================================


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    provider_type: str | None = None,
    enabled_only: bool = Query(default=True),
    approved_only: bool = Query(default=True),
) -> ProviderListResponse:
    """List registered voice providers.

    This endpoint is for governance/admin use only.
    End users should not need to see provider details.
    """
    registry = get_provider_registry()

    ptype = ProviderType(provider_type) if provider_type else None
    providers = registry.list_providers(
        provider_type=ptype,
        enabled_only=enabled_only,
        approved_only=approved_only,
    )

    return ProviderListResponse(
        providers=providers,
        total=len(providers),
    )


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str) -> VoiceProvider:
    """Get a specific provider by ID."""
    registry = get_provider_registry()
    provider = registry.get_provider(provider_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found",
        )

    return provider


@router.post("/providers/{provider_id}/enable")
async def enable_provider(provider_id: str) -> dict:
    """Enable a provider (governance action)."""
    registry = get_provider_registry()
    if registry.set_provider_enabled(provider_id, True):
        return {"status": "ok", "message": f"Provider '{provider_id}' enabled"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


@router.post("/providers/{provider_id}/disable")
async def disable_provider(provider_id: str) -> dict:
    """Disable a provider (governance action)."""
    registry = get_provider_registry()
    if registry.set_provider_enabled(provider_id, False):
        return {"status": "ok", "message": f"Provider '{provider_id}' disabled"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


@router.post("/providers/{provider_id}/approve")
async def approve_provider(provider_id: str) -> dict:
    """Approve a provider for use (governance action)."""
    registry = get_provider_registry()
    if registry.set_provider_approved(provider_id, True):
        return {"status": "ok", "message": f"Provider '{provider_id}' approved"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


@router.post("/providers/{provider_id}/revoke")
async def revoke_provider(provider_id: str) -> dict:
    """Revoke approval for a provider (governance action)."""
    registry = get_provider_registry()
    if registry.set_provider_approved(provider_id, False):
        return {"status": "ok", "message": f"Provider '{provider_id}' approval revoked"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


# =============================================================================
# Routing Endpoints
# =============================================================================


@router.post("/route", response_model=RouteResult)
async def route_session(request: RouteSessionRequest) -> RouteResult:
    """Route a voice session to the best available provider.

    This is the main entry point for starting a voice session.
    The system will automatically select the best provider based on
    the profile and current health status.
    """
    voice_router = get_voice_router()
    audit = get_voice_audit_log()

    # Get governance policy info
    from packages.core.governance import get_governance_manager
    gov = get_governance_manager()
    policy_version = gov.get_current_version().version_number if gov.get_current_version() else 1
    policy_hash = gov._compute_policy_hash()[:16]

    # Map provider type
    ptype = ProviderType.BOTH
    if request.provider_type == "stt":
        ptype = ProviderType.STT
    elif request.provider_type == "tts":
        ptype = ProviderType.TTS

    # Route the session
    result = voice_router.route(
        session_id=request.session_id,
        profile_id=request.profile_id,
        provider_type=ptype,
    )

    # Log to audit
    if result.provider:
        audit.log_session_start(
            session_id=request.session_id,
            org_id=request.org_id,
            profile_id=request.profile_id,
            provider_id=result.provider.id,
            provider_name=result.provider.name,
            department_id=request.department_id,
            user_id=request.user_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
        )
        audit.log_provider_selected(
            session_id=request.session_id,
            org_id=request.org_id,
            provider_id=result.provider.id,
            provider_name=result.provider.name,
            profile_id=request.profile_id,
            reason=result.reason,
        )

    return result


@router.post("/fallback", response_model=RouteResult)
async def trigger_fallback(request: FallbackRequest) -> RouteResult:
    """Trigger fallback to the next provider in the chain.

    Called when the current provider fails mid-session.
    """
    voice_router = get_voice_router()
    audit = get_voice_audit_log()

    # Get current session for audit
    session = voice_router.get_session(request.session_id)
    old_provider_id = session.current_provider_id if session else ""

    # Trigger fallback
    result = voice_router.fallback(request.session_id)

    # Log to audit
    if result.provider and session:
        audit.log_fallback(
            session_id=request.session_id,
            org_id=session.profile_id,  # TODO: Need org_id in session
            old_provider_id=old_provider_id,
            new_provider_id=result.provider.id,
            new_provider_name=result.provider.name,
            reason=request.reason or result.reason,
            fallback_count=result.attempts,
        )

    return result


@router.post("/session/{session_id}/end")
async def end_session(session_id: str, success: bool = True) -> dict:
    """End a voice session."""
    voice_router = get_voice_router()
    session = voice_router.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    voice_router.end_session(session_id, success)

    return {
        "status": "ok",
        "session_id": session_id,
        "fallback_count": session.fallback_count,
    }


@router.post("/event")
async def record_event(request: RecordEventRequest) -> dict:
    """Record a provider success or failure event.

    This updates circuit breaker state and health metrics.
    """
    voice_router = get_voice_router()

    if request.success:
        voice_router.record_success(request.provider_id)
    else:
        voice_router.record_failure(request.provider_id, request.error_message)

    return {
        "status": "ok",
        "provider_id": request.provider_id,
        "circuit_state": voice_router.get_circuit_status(request.provider_id),
    }


# =============================================================================
# Health and Monitoring Endpoints
# =============================================================================


@router.get("/health", response_model=HealthResponse)
async def get_voice_health() -> HealthResponse:
    """Get voice platform health status.

    Includes circuit breaker states and routing statistics.
    """
    voice_router = get_voice_router()

    return HealthResponse(
        circuits=voice_router.get_all_circuits(),
        active_sessions=voice_router.get_active_sessions_count(),
        routing_stats=voice_router.get_routing_stats(),
    )


@router.get("/circuits")
async def get_circuits() -> dict:
    """Get all circuit breaker states."""
    voice_router = get_voice_router()
    return {
        "circuits": voice_router.get_all_circuits(),
    }


@router.get("/circuits/{provider_id}")
async def get_circuit(provider_id: str) -> dict:
    """Get circuit breaker state for a specific provider."""
    voice_router = get_voice_router()
    return voice_router.get_circuit_status(provider_id)


# =============================================================================
# Audit Endpoints
# =============================================================================


@router.get("/audit/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(org_id: str | None = None) -> AuditSummaryResponse:
    """Get voice audit summary."""
    audit = get_voice_audit_log()
    summary = audit.get_summary(org_id)
    return AuditSummaryResponse(**summary)


@router.get("/audit/session/{session_id}")
async def get_session_audit(session_id: str) -> dict:
    """Get audit events for a specific session."""
    audit = get_voice_audit_log()
    events = audit.get_session_events(session_id)

    return {
        "session_id": session_id,
        "events": [e.model_dump() for e in events],
        "total": len(events),
    }


@router.get("/audit/events")
async def list_audit_events(
    org_id: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=100, le=1000),
) -> dict:
    """List audit events with filtering."""
    audit = get_voice_audit_log()

    if event_type:
        try:
            etype = VoiceEventType(event_type)
            events = audit.get_events_by_type(etype, limit)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}",
            )
    elif org_id:
        events = audit.get_events_by_org(org_id, limit=limit)
    else:
        events = audit._events[-limit:]

    return {
        "events": [e.model_dump() for e in events],
        "total": len(events),
    }
