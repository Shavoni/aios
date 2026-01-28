"""Deterministic Trace System for Simulation Mode.

Provides comprehensive execution tracing with:
- Full step-by-step execution recording
- Deterministic replay capability
- Test fixture generation
- Performance profiling
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class TraceEventType(str, Enum):
    """Types of trace events."""

    REQUEST_START = "request_start"
    REQUEST_END = "request_end"
    INTENT_CLASSIFICATION = "intent_classification"
    RISK_DETECTION = "risk_detection"
    GOVERNANCE_CHECK = "governance_check"
    AGENT_SELECTION = "agent_selection"
    AGENT_ROUTING = "agent_routing"
    KB_QUERY = "kb_query"
    LLM_CALL = "llm_call"
    LLM_RESPONSE = "llm_response"
    HITL_CHECK = "hitl_check"
    HITL_ESCALATION = "hitl_escalation"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class TraceEvent:
    """A single event in an execution trace."""

    id: str
    trace_id: str
    event_type: TraceEventType
    timestamp: str
    duration_ms: float = 0.0

    # Event data
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Hierarchy
    parent_event_id: str | None = None
    depth: int = 0

    # Deterministic hash for replay verification
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute deterministic hash of event content."""
        content = json.dumps({
            "event_type": self.event_type.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "metadata": self.metadata,
            "parent_event_id": self.parent_event_id,
            "depth": self.depth,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceEvent:
        return cls(
            id=data["id"],
            trace_id=data["trace_id"],
            event_type=TraceEventType(data["event_type"]),
            timestamp=data["timestamp"],
            duration_ms=data.get("duration_ms", 0.0),
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            metadata=data.get("metadata", {}),
            parent_event_id=data.get("parent_event_id"),
            depth=data.get("depth", 0),
            content_hash=data.get("content_hash", ""),
        )


@dataclass
class ExecutionTrace:
    """Complete execution trace for a request."""

    id: str
    tenant_id: str
    user_id: str

    # Request info
    request_text: str
    request_timestamp: str

    # Events
    events: list[TraceEvent] = field(default_factory=list)

    # Results
    final_response: str = ""
    success: bool = True
    error_message: str = ""

    # Metrics
    total_duration_ms: float = 0.0
    llm_calls: int = 0
    llm_tokens_used: int = 0
    llm_cost_usd: float = 0.0

    # Deterministic verification
    trace_hash: str = ""

    # Simulation flag
    is_simulation: bool = True
    tools_executed: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.trace_hash:
            self.trace_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of entire trace for verification."""
        event_hashes = [e.content_hash for e in self.events]
        content = json.dumps({
            "request_text": self.request_text,
            "event_hashes": event_hashes,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def add_event(self, event: TraceEvent) -> None:
        """Add an event to the trace."""
        self.events.append(event)
        self.trace_hash = self._compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_text": self.request_text,
            "request_timestamp": self.request_timestamp,
            "events": [e.to_dict() for e in self.events],
            "final_response": self.final_response,
            "success": self.success,
            "error_message": self.error_message,
            "total_duration_ms": self.total_duration_ms,
            "llm_calls": self.llm_calls,
            "llm_tokens_used": self.llm_tokens_used,
            "llm_cost_usd": self.llm_cost_usd,
            "trace_hash": self.trace_hash,
            "is_simulation": self.is_simulation,
            "tools_executed": self.tools_executed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionTrace:
        trace = cls(
            id=data["id"],
            tenant_id=data["tenant_id"],
            user_id=data["user_id"],
            request_text=data["request_text"],
            request_timestamp=data["request_timestamp"],
            final_response=data.get("final_response", ""),
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            llm_calls=data.get("llm_calls", 0),
            llm_tokens_used=data.get("llm_tokens_used", 0),
            llm_cost_usd=data.get("llm_cost_usd", 0.0),
            trace_hash=data.get("trace_hash", ""),
            is_simulation=data.get("is_simulation", True),
            tools_executed=data.get("tools_executed", []),
        )
        trace.events = [TraceEvent.from_dict(e) for e in data.get("events", [])]
        return trace

    def to_report(self) -> str:
        """Generate human-readable trace report."""
        lines = [
            "=" * 80,
            f"EXECUTION TRACE REPORT",
            f"Trace ID: {self.id}",
            f"Hash: {self.trace_hash}",
            "=" * 80,
            "",
            f"Request: {self.request_text[:100]}...",
            f"Tenant: {self.tenant_id} | User: {self.user_id}",
            f"Timestamp: {self.request_timestamp}",
            f"Simulation Mode: {self.is_simulation}",
            "",
            "-" * 80,
            "EXECUTION TIMELINE",
            "-" * 80,
        ]

        for event in self.events:
            indent = "  " * event.depth
            lines.append(
                f"{indent}[{event.duration_ms:7.2f}ms] {event.event_type.value}"
            )
            if event.input_data:
                for k, v in event.input_data.items():
                    lines.append(f"{indent}  → {k}: {str(v)[:60]}")
            if event.output_data:
                for k, v in event.output_data.items():
                    lines.append(f"{indent}  ← {k}: {str(v)[:60]}")

        lines.extend([
            "",
            "-" * 80,
            "SUMMARY",
            "-" * 80,
            f"Total Duration: {self.total_duration_ms:.2f}ms",
            f"LLM Calls: {self.llm_calls}",
            f"Tokens Used: {self.llm_tokens_used}",
            f"Cost: ${self.llm_cost_usd:.4f}",
            f"Success: {self.success}",
            f"Tools Executed: {len(self.tools_executed)}",
            "",
        ])

        if self.error_message:
            lines.append(f"ERROR: {self.error_message}")

        if self.final_response:
            lines.extend([
                "-" * 80,
                "RESPONSE",
                "-" * 80,
                self.final_response[:500],
            ])

        lines.append("=" * 80)
        return "\n".join(lines)


class TraceContext:
    """Context manager for creating trace events."""

    def __init__(
        self,
        tracer: ExecutionTracer,
        event_type: TraceEventType,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.tracer = tracer
        self.event_type = event_type
        self.input_data = input_data or {}
        self.metadata = metadata or {}
        self.start_time: float = 0.0
        self.event: TraceEvent | None = None

    def __enter__(self) -> TraceContext:
        self.start_time = time.perf_counter()
        self.event = self.tracer._create_event(
            event_type=self.event_type,
            input_data=self.input_data,
            metadata=self.metadata,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.event:
            duration = (time.perf_counter() - self.start_time) * 1000
            self.event.duration_ms = duration

            if exc_type:
                self.event.output_data["error"] = str(exc_val)
                self.event.metadata["exception_type"] = exc_type.__name__

    def set_output(self, output_data: dict[str, Any]) -> None:
        """Set output data for this event."""
        if self.event:
            self.event.output_data = output_data
            self.event.content_hash = self.event._compute_hash()


class ExecutionTracer:
    """Tracer for recording execution traces."""

    def __init__(
        self,
        trace_id: str | None = None,
        tenant_id: str = "default",
        user_id: str = "anonymous",
        request_text: str = "",
        is_simulation: bool = True,
    ):
        self.trace = ExecutionTrace(
            id=trace_id or str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            request_text=request_text,
            request_timestamp=datetime.now(UTC).isoformat(),
            is_simulation=is_simulation,
        )
        self._start_time = time.perf_counter()
        self._event_stack: list[TraceEvent] = []

    def _create_event(
        self,
        event_type: TraceEventType,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        """Create and add an event to the trace."""
        parent_id = self._event_stack[-1].id if self._event_stack else None
        depth = len(self._event_stack)

        event = TraceEvent(
            id=str(uuid.uuid4()),
            trace_id=self.trace.id,
            event_type=event_type,
            timestamp=datetime.now(UTC).isoformat(),
            input_data=input_data or {},
            output_data=output_data or {},
            metadata=metadata or {},
            parent_event_id=parent_id,
            depth=depth,
        )

        self.trace.add_event(event)
        self._event_stack.append(event)

        return event

    def event(
        self,
        event_type: TraceEventType,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceContext:
        """Create a trace context for an event."""
        return TraceContext(self, event_type, input_data, metadata)

    def record(
        self,
        event_type: TraceEventType,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        """Record a single event immediately."""
        event = self._create_event(
            event_type=event_type,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
        )
        event.duration_ms = duration_ms

        # Pop from stack if it was added
        if self._event_stack and self._event_stack[-1].id == event.id:
            self._event_stack.pop()

        return event

    def record_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        tokens_used: int,
        cost_usd: float,
        duration_ms: float,
    ) -> None:
        """Record an LLM call with metrics."""
        self.record(
            event_type=TraceEventType.LLM_CALL,
            input_data={"model": model, "prompt": prompt[:200] + "..."},
            output_data={"response": response[:200] + "..."},
            duration_ms=duration_ms,
            metadata={"tokens": tokens_used, "cost_usd": cost_usd},
        )

        self.trace.llm_calls += 1
        self.trace.llm_tokens_used += tokens_used
        self.trace.llm_cost_usd += cost_usd

    def record_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        executed: bool = False,
    ) -> None:
        """Record a tool call."""
        self.record(
            event_type=TraceEventType.TOOL_CALL if not executed else TraceEventType.TOOL_RESULT,
            input_data={"tool": tool_name, "args": args},
            output_data={"result": str(result)[:500], "executed": executed},
        )

        if executed:
            self.trace.tools_executed.append(tool_name)

    def finish(
        self,
        response: str = "",
        success: bool = True,
        error: str = "",
    ) -> ExecutionTrace:
        """Finish the trace and return the complete record."""
        self.trace.final_response = response
        self.trace.success = success
        self.trace.error_message = error
        self.trace.total_duration_ms = (time.perf_counter() - self._start_time) * 1000
        self.trace.trace_hash = self.trace._compute_hash()

        return self.trace


class TraceStore:
    """Persistent storage for execution traces."""

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path("data/traces")
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, trace: ExecutionTrace) -> str:
        """Save a trace to storage."""
        trace_file = self._storage_path / f"{trace.id}.json"
        trace_file.write_text(json.dumps(trace.to_dict(), indent=2))
        return str(trace_file)

    def load(self, trace_id: str) -> ExecutionTrace | None:
        """Load a trace by ID."""
        trace_file = self._storage_path / f"{trace_id}.json"
        if trace_file.exists():
            data = json.loads(trace_file.read_text())
            return ExecutionTrace.from_dict(data)
        return None

    def list_traces(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List traces with optional filtering."""
        traces = []
        for trace_file in sorted(
            self._storage_path.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                data = json.loads(trace_file.read_text())
                if tenant_id and data.get("tenant_id") != tenant_id:
                    continue
                traces.append({
                    "id": data["id"],
                    "tenant_id": data["tenant_id"],
                    "request_text": data["request_text"][:100],
                    "timestamp": data["request_timestamp"],
                    "success": data["success"],
                    "duration_ms": data["total_duration_ms"],
                    "is_simulation": data["is_simulation"],
                })
            except Exception:
                continue
        return traces

    def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        trace_file = self._storage_path / f"{trace_id}.json"
        if trace_file.exists():
            trace_file.unlink()
            return True
        return False


# Singleton store
_trace_store: TraceStore | None = None


def get_trace_store() -> TraceStore:
    """Get the trace store singleton."""
    global _trace_store
    if _trace_store is None:
        _trace_store = TraceStore()
    return _trace_store


__all__ = [
    "TraceEventType",
    "TraceEvent",
    "ExecutionTrace",
    "TraceContext",
    "ExecutionTracer",
    "TraceStore",
    "get_trace_store",
]
