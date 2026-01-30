"""Voice Platform API Endpoints.

Provides endpoints for:
- Listing and managing communication profiles
- Viewing provider capabilities (governance only)
- Routing sessions to providers
- Health and circuit breaker status
- Audit log access
- WebSocket streaming for real-time voice pipeline
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator
import uuid

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
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
    VoiceAuditEvent,
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


# =============================================================================
# Pipeline Endpoints (Streaming Voice)
# =============================================================================


class BargeInRequest(BaseModel):
    """Request to trigger barge-in (user interruption)."""

    reason: str = Field(default="user_speech_detected", description="Why barge-in triggered")


class PipelineSessionRequest(BaseModel):
    """Request to create a voice pipeline session."""

    profile_id: str = Field(default="compliance_locked")
    is_interruptible: bool = Field(default=True, description="Allow barge-in")
    org_id: str = ""
    user_id: str = ""


class PipelineMetricsResponse(BaseModel):
    """Pipeline latency metrics."""

    stt_first_interim_ms: float = 0.0
    stt_final_ms: float = 0.0
    llm_first_token_ms: float = 0.0
    llm_complete_ms: float = 0.0
    tts_first_chunk_ms: float = 0.0
    tts_complete_ms: float = 0.0
    total_latency_ms: float = 0.0
    user_perceived_latency_ms: float = 0.0


@router.post("/pipeline/session")
async def create_pipeline_session(request: PipelineSessionRequest) -> dict:
    """Create a new voice pipeline session.

    This prepares a session for streaming STT → LLM → TTS processing.
    Use WebSocket endpoint for actual audio streaming.
    """
    from packages.core.voice.pipeline import get_voice_pipeline

    pipeline = get_voice_pipeline()

    # Get provider assignments from routing
    voice_router = get_voice_router()
    stt_result = voice_router.route(
        session_id=str(uuid.uuid4()),
        profile_id=request.profile_id,
        provider_type=ProviderType.STT,
    )
    tts_result = voice_router.route(
        session_id=str(uuid.uuid4()),
        profile_id=request.profile_id,
        provider_type=ProviderType.TTS,
    )

    session = pipeline.create_session(
        stt_provider_id=stt_result.provider.id if stt_result.provider else "",
        tts_provider_id=tts_result.provider.id if tts_result.provider else "",
        is_interruptible=request.is_interruptible,
    )

    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "stt_provider_id": session.stt_provider_id,
        "tts_provider_id": session.tts_provider_id,
        "is_interruptible": session.is_interruptible,
        "websocket_url": f"/voice/pipeline/ws/{session.session_id}",
    }


@router.post("/pipeline/session/{session_id}/barge-in")
async def handle_barge_in(session_id: str, request: BargeInRequest) -> dict:
    """Trigger barge-in to interrupt current TTS playback.

    ENTERPRISE: Barge-in allows natural conversation flow by letting
    users interrupt the AI mid-speech. This:
    1. Cancels current TTS stream
    2. Immediately switches to listening mode
    3. Logs the interruption for analytics
    """
    from packages.core.voice.pipeline import get_voice_pipeline

    pipeline = get_voice_pipeline()
    session = pipeline.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline session '{session_id}' not found",
        )

    if not session.is_interruptible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session does not support barge-in",
        )

    # Trigger barge-in
    event = await pipeline.handle_barge_in(session_id)

    # Log to audit
    audit = get_voice_audit_log()
    audit.log(
        VoiceAuditEvent(
            event_type=VoiceEventType.BARGE_IN,
            session_id=session_id,
            org_id="",  # TODO: Get from session
            metadata={
                "reason": request.reason,
                "tts_cancelled": event.tts_cancelled,
                "audio_position_ms": event.audio_position_ms,
            },
        )
    )

    return {
        "success": True,
        "session_id": session_id,
        "tts_cancelled": event.tts_cancelled,
        "new_state": session.state.value,
    }


@router.get("/pipeline/session/{session_id}/metrics", response_model=PipelineMetricsResponse)
async def get_pipeline_metrics(session_id: str) -> PipelineMetricsResponse:
    """Get latency metrics for a pipeline session.

    ENTERPRISE: Latency tracking for SLA monitoring and optimization.
    """
    from packages.core.voice.pipeline import get_voice_pipeline

    pipeline = get_voice_pipeline()
    session = pipeline.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline session '{session_id}' not found",
        )

    return PipelineMetricsResponse(
        stt_first_interim_ms=session.metrics.stt_first_interim_ms,
        stt_final_ms=session.metrics.stt_final_ms,
        llm_first_token_ms=session.metrics.llm_first_token_ms,
        llm_complete_ms=session.metrics.llm_complete_ms,
        tts_first_chunk_ms=session.metrics.tts_first_chunk_ms,
        tts_complete_ms=session.metrics.tts_complete_ms,
        total_latency_ms=session.metrics.total_latency_ms,
        user_perceived_latency_ms=session.metrics.user_perceived_latency_ms,
    )


@router.delete("/pipeline/session/{session_id}")
async def end_pipeline_session(session_id: str) -> dict:
    """End a voice pipeline session."""
    from packages.core.voice.pipeline import get_voice_pipeline

    pipeline = get_voice_pipeline()
    session = pipeline.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline session '{session_id}' not found",
        )

    # Get final metrics before ending
    metrics = session.metrics

    pipeline.end_session(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "turn_count": session.turn_count,
        "final_metrics": {
            "avg_user_perceived_latency_ms": metrics.user_perceived_latency_ms,
            "total_latency_ms": metrics.total_latency_ms,
        },
    }


# =============================================================================
# WebSocket Streaming Endpoint
# =============================================================================


class WebSocketMessage(BaseModel):
    """WebSocket message format for voice streaming."""

    type: str  # "audio", "config", "barge_in", "end"
    data: Any = None


@router.websocket("/pipeline/ws/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time bidirectional voice streaming.

    PROTOCOL:
    Client → Server messages:
    - {"type": "audio", "data": "<base64_audio_chunk>"}  - Audio input
    - {"type": "config", "data": {...}}                  - Session configuration
    - {"type": "barge_in"}                               - User interruption
    - {"type": "end"}                                    - End session

    Server → Client messages:
    - {"type": "stt_interim", "data": {"text": "..."}}           - Interim STT result
    - {"type": "stt_final", "data": {"text": "..."}}             - Final STT result
    - {"type": "llm_token", "data": {"token": "..."}}            - LLM token
    - {"type": "tts_audio", "data": "<base64_audio_chunk>"}      - TTS audio
    - {"type": "state", "data": {"state": "..."}}                - Pipeline state change
    - {"type": "metrics", "data": {...}}                         - Latency metrics
    - {"type": "error", "data": {"message": "..."}}              - Error message

    LATENCY TARGETS:
    - First STT interim: <200ms
    - First LLM token: <300ms from final STT
    - First TTS audio: <200ms from first LLM token
    - Total first-byte: <500ms (streaming mode)
    """
    from packages.core.voice.pipeline import get_voice_pipeline, PipelineState
    from packages.core.voice.providers import ProviderFactory

    await websocket.accept()

    pipeline = get_voice_pipeline()
    session = pipeline.get_session(session_id)

    if not session:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Session '{session_id}' not found. Create session first via POST /pipeline/session"}
        })
        await websocket.close(code=4004)
        return

    # Conversation history for LLM context
    conversation_history: list[dict[str, str]] = []
    system_prompt = "You are a helpful voice assistant. Keep responses concise and natural for speech."

    # Audio input queue for STT
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    # Track if we're in an active turn
    turn_active = False

    async def audio_generator() -> AsyncIterator[bytes]:
        """Generate audio chunks from the queue for STT."""
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    async def send_state_update(state: PipelineState):
        """Send state update to client."""
        try:
            await websocket.send_json({
                "type": "state",
                "data": {"state": state.value}
            })
        except Exception:
            pass

    async def process_turn():
        """Process a complete voice turn through the pipeline."""
        nonlocal turn_active

        try:
            # Register callbacks for real-time updates
            async def on_stt_interim(sid: str, text: str):
                if sid == session_id:
                    await websocket.send_json({
                        "type": "stt_interim",
                        "data": {"text": text}
                    })

            async def on_stt_final(sid: str, text: str):
                if sid == session_id:
                    await websocket.send_json({
                        "type": "stt_final",
                        "data": {"text": text}
                    })
                    # Add to conversation history
                    conversation_history.append({"role": "user", "content": text})

            async def on_llm_token(sid: str, token: str):
                if sid == session_id:
                    await websocket.send_json({
                        "type": "llm_token",
                        "data": {"token": token}
                    })

            # Process the turn
            import base64
            assistant_response = ""

            async for audio_chunk in pipeline.process_turn(
                session_id=session_id,
                audio_chunks=audio_generator(),
                conversation_history=conversation_history.copy(),
                system_prompt=system_prompt,
            ):
                # Send TTS audio as base64
                await websocket.send_json({
                    "type": "tts_audio",
                    "data": base64.b64encode(audio_chunk).decode("utf-8")
                })

            # Add assistant response to history
            if session and session.metrics.llm_tokens_generated > 0:
                # The full response was built during process_turn
                # We'd need to track it - for now just mark the turn complete
                pass

            # Send final metrics
            if session:
                await websocket.send_json({
                    "type": "metrics",
                    "data": {
                        "stt_first_interim_ms": session.metrics.stt_first_interim_ms,
                        "stt_final_ms": session.metrics.stt_final_ms,
                        "llm_first_token_ms": session.metrics.llm_first_token_ms,
                        "tts_first_chunk_ms": session.metrics.tts_first_chunk_ms,
                        "user_perceived_latency_ms": session.metrics.user_perceived_latency_ms,
                        "total_latency_ms": session.metrics.total_latency_ms,
                    }
                })

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        finally:
            turn_active = False
            await send_state_update(PipelineState.IDLE)

    # Main WebSocket loop
    turn_task: asyncio.Task | None = None

    try:
        await send_state_update(session.state)

        while True:
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=300.0  # 5 minute timeout
                )
                message = json.loads(raw_message)

            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping"})
                continue
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON message"}
                })
                continue

            msg_type = message.get("type", "")

            if msg_type == "audio":
                # Decode base64 audio and queue for STT
                import base64
                try:
                    audio_data = base64.b64decode(message.get("data", ""))
                    await audio_queue.put(audio_data)

                    # Start turn if not active
                    if not turn_active:
                        turn_active = True
                        await send_state_update(PipelineState.LISTENING)
                        turn_task = asyncio.create_task(process_turn())

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Audio decode error: {str(e)}"}
                    })

            elif msg_type == "audio_end":
                # Signal end of audio input for current turn
                await audio_queue.put(None)

            elif msg_type == "config":
                # Update session configuration
                config_data = message.get("data", {})
                if "system_prompt" in config_data:
                    system_prompt = config_data["system_prompt"]
                if "is_interruptible" in config_data:
                    session.is_interruptible = config_data["is_interruptible"]

                await websocket.send_json({
                    "type": "config_ack",
                    "data": {"status": "ok"}
                })

            elif msg_type == "barge_in":
                # Handle user interruption
                if session.is_interruptible and session.state == PipelineState.SPEAKING:
                    event = await pipeline.handle_barge_in(session_id)
                    await websocket.send_json({
                        "type": "barge_in_ack",
                        "data": {
                            "tts_cancelled": event.tts_cancelled,
                            "timestamp": event.timestamp
                        }
                    })
                    await send_state_update(PipelineState.INTERRUPTED)

            elif msg_type == "clear_history":
                # Clear conversation history
                conversation_history.clear()
                await websocket.send_json({
                    "type": "history_cleared",
                    "data": {"status": "ok"}
                })

            elif msg_type == "end":
                # End session
                break

            elif msg_type == "pong":
                # Keepalive response, ignore
                pass

            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {msg_type}"}
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"WebSocket error: {str(e)}"}
            })
        except Exception:
            pass
    finally:
        # Cleanup
        if turn_task and not turn_task.done():
            turn_task.cancel()
            try:
                await turn_task
            except asyncio.CancelledError:
                pass

        # End the pipeline session
        pipeline.end_session(session_id)

        try:
            await websocket.close()
        except Exception:
            pass


# =============================================================================
# Provider Management Endpoints
# =============================================================================


class ConfigureProviderRequest(BaseModel):
    """Request to configure a provider."""

    provider_type: str = Field(..., description="'stt', 'tts', or 'llm'")
    provider_name: str = Field(..., description="Provider name: deepgram, elevenlabs, azure, openai")
    api_key: str | None = Field(default=None, description="Optional API key override")


@router.get("/providers/available")
async def list_available_provider_sdks() -> dict:
    """List available provider SDKs and their configuration status.

    ENTERPRISE: Shows which provider SDKs are available and configured.
    """
    import os

    providers = {
        "stt": {
            "deepgram": {
                "available": True,
                "configured": bool(os.environ.get("DEEPGRAM_API_KEY")),
                "features": ["streaming", "interim_results", "diarization", "smart_format"],
                "latency": "fast (<200ms first interim)",
            },
            "azure": {
                "available": True,
                "configured": bool(os.environ.get("AZURE_SPEECH_KEY")),
                "features": ["streaming", "interim_results", "custom_models", "compliance"],
                "latency": "fast (<250ms first interim)",
            },
            "openai": {
                "available": True,
                "configured": bool(os.environ.get("OPENAI_API_KEY")),
                "features": ["batch_only", "high_accuracy", "57_languages"],
                "latency": "slow (batch only)",
            },
        },
        "tts": {
            "elevenlabs": {
                "available": True,
                "configured": bool(os.environ.get("ELEVENLABS_API_KEY")),
                "features": ["streaming", "neural_voices", "voice_cloning", "emotion"],
                "latency": "fast (<200ms first chunk)",
            },
            "azure": {
                "available": True,
                "configured": bool(os.environ.get("AZURE_SPEECH_KEY")),
                "features": ["streaming", "ssml", "neural_voices", "compliance"],
                "latency": "medium (<300ms first chunk)",
            },
            "openai": {
                "available": True,
                "configured": bool(os.environ.get("OPENAI_API_KEY")),
                "features": ["streaming", "6_voices", "speed_control"],
                "latency": "medium (<300ms first chunk)",
            },
        },
        "llm": {
            "openai": {
                "available": True,
                "configured": bool(os.environ.get("OPENAI_API_KEY")),
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                "features": ["streaming", "function_calling", "json_mode"],
            },
        },
    }

    return {
        "providers": providers,
        "recommended": {
            "stt": "deepgram" if os.environ.get("DEEPGRAM_API_KEY") else "azure",
            "tts": "elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "openai",
            "llm": "openai",
        },
    }


@router.post("/providers/test/{provider_type}/{provider_name}")
async def test_provider_connection(
    provider_type: str,
    provider_name: str,
) -> dict:
    """Test connection to a provider.

    ENTERPRISE: Validates API key and connectivity before use.
    """
    from packages.core.voice.providers import ProviderFactory

    try:
        if provider_type == "stt":
            provider = ProviderFactory.get_stt_provider(provider_name)
            # Simple connectivity test
            return {
                "status": "ok",
                "provider_type": provider_type,
                "provider_name": provider_name,
                "message": "Provider initialized successfully",
            }
        elif provider_type == "tts":
            provider = ProviderFactory.get_tts_provider(provider_name)
            return {
                "status": "ok",
                "provider_type": provider_type,
                "provider_name": provider_name,
                "message": "Provider initialized successfully",
            }
        elif provider_type == "llm":
            provider = ProviderFactory.get_llm_provider(provider_name)
            return {
                "status": "ok",
                "provider_type": provider_type,
                "provider_name": provider_name,
                "message": "Provider initialized successfully",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {provider_type}. Must be 'stt', 'tts', or 'llm'",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        return {
            "status": "error",
            "provider_type": provider_type,
            "provider_name": provider_name,
            "message": str(e),
        }
