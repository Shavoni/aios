"""Voice Provider Router with Fallback Chain and Circuit Breaker.

Handles automatic provider selection, fallback on failure,
and circuit breaker protection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable
from pydantic import BaseModel, Field

from .registry import (
    ProviderType,
    VoiceProvider,
    get_provider_registry,
)
from .profiles import (
    VoiceProfile,
    get_profile_manager,
)


class RouteDecision(str, Enum):
    """Result of a routing decision."""
    SUCCESS = "success"  # Provider selected successfully
    FALLBACK = "fallback"  # Primary failed, using fallback
    DEGRADED = "degraded"  # Using degraded provider
    TEXT_ONLY = "text_only"  # No voice providers, fallback to text
    FAILED = "failed"  # No options available


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class ProviderCircuit(BaseModel):
    """Circuit breaker for a single provider."""

    provider_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: str | None = None
    last_success: str | None = None
    open_until: str | None = None

    # Configuration
    failure_threshold: int = 3
    success_threshold: int = 2  # Successes needed in half-open to close
    timeout_seconds: int = 60  # How long circuit stays open


class RouteResult(BaseModel):
    """Result of a routing operation."""

    decision: RouteDecision
    provider: VoiceProvider | None = None
    fallback_chain: list[str] = Field(default_factory=list)
    attempts: int = 0
    reason: str = ""
    latency_ms: float = 0.0

    # For audit
    profile_id: str = ""
    provider_type: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class SessionRoute(BaseModel):
    """Active routing state for a voice session."""

    session_id: str
    profile_id: str
    provider_type: ProviderType

    # Current provider
    current_provider_id: str | None = None
    current_provider_name: str | None = None

    # Fallback tracking
    fallback_chain: list[str] = Field(default_factory=list)
    fallback_index: int = 0
    fallback_count: int = 0
    max_fallbacks: int = 3

    # Status
    is_active: bool = True
    is_degraded: bool = False
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_activity: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# =============================================================================
# Voice Router
# =============================================================================

class VoiceRouter:
    """Routes voice sessions to providers with fallback and circuit breaking."""

    def __init__(self):
        self._circuits: dict[str, ProviderCircuit] = {}
        self._active_sessions: dict[str, SessionRoute] = {}
        self._on_fallback_callbacks: list[Callable[[str, str, str], None]] = []

    # -------------------------------------------------------------------------
    # Circuit Breaker Management
    # -------------------------------------------------------------------------

    def _get_circuit(self, provider_id: str) -> ProviderCircuit:
        """Get or create circuit for a provider."""
        if provider_id not in self._circuits:
            self._circuits[provider_id] = ProviderCircuit(provider_id=provider_id)
        return self._circuits[provider_id]

    def _check_circuit(self, provider_id: str) -> bool:
        """Check if circuit allows requests.

        Returns True if requests are allowed, False if blocked.
        """
        circuit = self._get_circuit(provider_id)

        if circuit.state == CircuitState.CLOSED:
            return True

        if circuit.state == CircuitState.OPEN:
            # Check if timeout has passed
            if circuit.open_until:
                open_until = datetime.fromisoformat(circuit.open_until)
                if datetime.now(UTC) > open_until:
                    # Transition to half-open
                    circuit.state = CircuitState.HALF_OPEN
                    circuit.success_count = 0
                    return True
            return False

        # Half-open: allow requests to test recovery
        return True

    def record_success(self, provider_id: str) -> None:
        """Record a successful request."""
        circuit = self._get_circuit(provider_id)
        circuit.last_success = datetime.now(UTC).isoformat()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1
            if circuit.success_count >= circuit.success_threshold:
                # Close the circuit (recovered)
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.success_count = 0
        else:
            circuit.failure_count = 0

        # Update provider health
        registry = get_provider_registry()
        registry.update_provider_health(provider_id, is_healthy=True)

    def record_failure(self, provider_id: str, error: str = "") -> None:
        """Record a failed request."""
        circuit = self._get_circuit(provider_id)
        circuit.failure_count += 1
        circuit.last_failure = datetime.now(UTC).isoformat()

        if circuit.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, open circuit again
            circuit.state = CircuitState.OPEN
            circuit.open_until = (
                datetime.now(UTC) + timedelta(seconds=circuit.timeout_seconds)
            ).isoformat()
        elif circuit.failure_count >= circuit.failure_threshold:
            # Open the circuit
            circuit.state = CircuitState.OPEN
            circuit.open_until = (
                datetime.now(UTC) + timedelta(seconds=circuit.timeout_seconds)
            ).isoformat()

        # Update provider health
        registry = get_provider_registry()
        registry.update_provider_health(
            provider_id,
            is_healthy=(circuit.state != CircuitState.OPEN),
        )

    def get_circuit_status(self, provider_id: str) -> dict[str, Any]:
        """Get circuit breaker status for a provider."""
        circuit = self._get_circuit(provider_id)
        return {
            "provider_id": provider_id,
            "state": circuit.state.value,
            "failure_count": circuit.failure_count,
            "last_failure": circuit.last_failure,
            "last_success": circuit.last_success,
            "open_until": circuit.open_until,
        }

    # -------------------------------------------------------------------------
    # Provider Selection
    # -------------------------------------------------------------------------

    def route(
        self,
        session_id: str,
        profile_id: str,
        provider_type: ProviderType,
    ) -> RouteResult:
        """Route a session to the best available provider.

        This is the main entry point for routing decisions.
        """
        manager = get_profile_manager()
        profile = manager.get_profile(profile_id)

        if not profile:
            profile = manager.get_default_profile()
            profile_id = profile.id

        # Get eligible providers sorted by preference
        eligible = manager.get_eligible_providers(profile_id, provider_type)

        # Filter out providers with open circuits
        available = [
            p for p in eligible
            if self._check_circuit(p.id)
        ]

        # Build fallback chain
        fallback_chain = [p.id for p in available]

        if not available:
            # No providers available
            if profile.fallback_to_text:
                return RouteResult(
                    decision=RouteDecision.TEXT_ONLY,
                    fallback_chain=fallback_chain,
                    reason="No voice providers available, falling back to text",
                    profile_id=profile_id,
                    provider_type=provider_type.value,
                )
            else:
                return RouteResult(
                    decision=RouteDecision.FAILED,
                    fallback_chain=fallback_chain,
                    reason="No voice providers available and text fallback disabled",
                    profile_id=profile_id,
                    provider_type=provider_type.value,
                )

        # Select best provider
        selected = available[0]
        is_degraded = selected.health.is_degraded

        # Create session route
        session_route = SessionRoute(
            session_id=session_id,
            profile_id=profile_id,
            provider_type=provider_type,
            current_provider_id=selected.id,
            current_provider_name=selected.name,
            fallback_chain=fallback_chain,
            is_degraded=is_degraded,
        )
        self._active_sessions[session_id] = session_route

        return RouteResult(
            decision=RouteDecision.DEGRADED if is_degraded else RouteDecision.SUCCESS,
            provider=selected,
            fallback_chain=fallback_chain,
            attempts=1,
            reason=f"Selected {selected.name}" + (" (degraded)" if is_degraded else ""),
            profile_id=profile_id,
            provider_type=provider_type.value,
        )

    def fallback(self, session_id: str) -> RouteResult:
        """Trigger fallback to next provider in chain.

        Called when the current provider fails mid-session.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return RouteResult(
                decision=RouteDecision.FAILED,
                reason=f"Session {session_id} not found",
            )

        if session.fallback_count >= session.max_fallbacks:
            return RouteResult(
                decision=RouteDecision.FAILED,
                reason="Maximum fallbacks exceeded",
                profile_id=session.profile_id,
                provider_type=session.provider_type.value,
            )

        # Record failure for current provider
        if session.current_provider_id:
            self.record_failure(session.current_provider_id)

        # Move to next in fallback chain
        session.fallback_index += 1
        session.fallback_count += 1

        # Find next available provider
        registry = get_provider_registry()
        for i in range(session.fallback_index, len(session.fallback_chain)):
            provider_id = session.fallback_chain[i]
            if self._check_circuit(provider_id):
                provider = registry.get_provider(provider_id)
                if provider:
                    session.current_provider_id = provider.id
                    session.current_provider_name = provider.name
                    session.fallback_index = i
                    session.last_activity = datetime.now(UTC).isoformat()

                    # Notify callbacks
                    for callback in self._on_fallback_callbacks:
                        try:
                            callback(session_id, provider.id, "fallback")
                        except Exception:
                            pass

                    return RouteResult(
                        decision=RouteDecision.FALLBACK,
                        provider=provider,
                        fallback_chain=session.fallback_chain,
                        attempts=session.fallback_count + 1,
                        reason=f"Fallback to {provider.name}",
                        profile_id=session.profile_id,
                        provider_type=session.provider_type.value,
                    )

        # No more providers - check text fallback
        manager = get_profile_manager()
        profile = manager.get_profile(session.profile_id)

        if profile and profile.fallback_to_text:
            session.is_active = False
            return RouteResult(
                decision=RouteDecision.TEXT_ONLY,
                fallback_chain=session.fallback_chain,
                attempts=session.fallback_count + 1,
                reason="All providers exhausted, falling back to text",
                profile_id=session.profile_id,
                provider_type=session.provider_type.value,
            )

        session.is_active = False
        return RouteResult(
            decision=RouteDecision.FAILED,
            fallback_chain=session.fallback_chain,
            attempts=session.fallback_count + 1,
            reason="All providers exhausted",
            profile_id=session.profile_id,
            provider_type=session.provider_type.value,
        )

    def end_session(self, session_id: str, success: bool = True) -> None:
        """End a voice session."""
        session = self._active_sessions.get(session_id)
        if session:
            session.is_active = False
            if success and session.current_provider_id:
                self.record_success(session.current_provider_id)

    def get_session(self, session_id: str) -> SessionRoute | None:
        """Get active session info."""
        return self._active_sessions.get(session_id)

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def on_fallback(self, callback: Callable[[str, str, str], None]) -> None:
        """Register a callback for fallback events.

        Callback signature: (session_id, new_provider_id, reason)
        """
        self._on_fallback_callbacks.append(callback)

    # -------------------------------------------------------------------------
    # Health Monitoring
    # -------------------------------------------------------------------------

    def get_all_circuits(self) -> dict[str, dict]:
        """Get status of all circuit breakers."""
        return {
            provider_id: self.get_circuit_status(provider_id)
            for provider_id in self._circuits
        }

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return sum(1 for s in self._active_sessions.values() if s.is_active)

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        active = [s for s in self._active_sessions.values() if s.is_active]
        total = len(self._active_sessions)

        # Count by provider
        by_provider: dict[str, int] = {}
        for session in active:
            if session.current_provider_id:
                by_provider[session.current_provider_id] = (
                    by_provider.get(session.current_provider_id, 0) + 1
                )

        # Count circuits by state
        circuits_by_state = {"closed": 0, "open": 0, "half_open": 0}
        for circuit in self._circuits.values():
            circuits_by_state[circuit.state.value] += 1

        return {
            "active_sessions": len(active),
            "total_sessions": total,
            "sessions_by_provider": by_provider,
            "circuits": circuits_by_state,
            "fallback_rate": sum(s.fallback_count for s in active) / max(len(active), 1),
        }


# Singleton instance
_router: VoiceRouter | None = None


def get_voice_router() -> VoiceRouter:
    """Get the voice router singleton."""
    global _router
    if _router is None:
        _router = VoiceRouter()
    return _router


__all__ = [
    "RouteDecision",
    "CircuitState",
    "ProviderCircuit",
    "RouteResult",
    "SessionRoute",
    "VoiceRouter",
    "get_voice_router",
]
