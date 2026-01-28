"""Analytics API endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from packages.core.analytics import (
    AnalyticsSummary,
    QueryEvent,
    get_analytics_manager,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# =============================================================================
# Request/Response Models
# =============================================================================


class RecordQueryRequest(BaseModel):
    """Request to record a query event."""

    agent_id: str
    agent_name: str
    query_text: str
    response_text: str = ""
    user_id: str = "anonymous"
    department: str = "General"
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    hitl_mode: str = "INFORM"
    was_escalated: bool = False
    was_approved: bool = False
    guardrails_triggered: list[str] = Field(default_factory=list)
    sources_used: int = 0
    success: bool = True
    error_message: str | None = None
    session_id: str | None = None
    routed_from: str | None = None


class FeedbackRequest(BaseModel):
    """Request to add feedback to an event."""

    rating: int = Field(..., ge=1, le=5)
    text: str | None = None


class EventListResponse(BaseModel):
    """Response containing list of events."""

    events: list[QueryEvent]
    total: int
    limit: int
    offset: int


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
) -> AnalyticsSummary:
    """Get analytics summary for the dashboard."""
    manager = get_analytics_manager()
    return manager.get_summary(days=days)


@router.get("/agents/{agent_id}")
async def get_agent_analytics(
    agent_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Get analytics for a specific agent."""
    manager = get_analytics_manager()
    return manager.get_agent_metrics(agent_id, days=days)


@router.post("/events", response_model=QueryEvent, status_code=status.HTTP_201_CREATED)
async def record_query_event(request: RecordQueryRequest) -> QueryEvent:
    """Record a query event for analytics."""
    import uuid

    manager = get_analytics_manager()
    event = QueryEvent(
        id=str(uuid.uuid4()),
        **request.model_dump(),
    )
    manager.record_query(event)
    return event


@router.get("/events", response_model=EventListResponse)
async def list_events(
    agent_id: str | None = None,
    user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    """List query events with filtering."""
    manager = get_analytics_manager()
    events = manager.get_events(
        agent_id=agent_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(
        events=events,
        total=len(events),
        limit=limit,
        offset=offset,
    )


@router.post("/events/{event_id}/feedback")
async def add_event_feedback(event_id: str, request: FeedbackRequest) -> dict[str, str]:
    """Add feedback to an existing event."""
    manager = get_analytics_manager()
    if manager.add_feedback(event_id, request.rating, request.text):
        return {"status": "ok", "message": "Feedback recorded"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Event '{event_id}' not found",
    )


@router.get("/export")
async def export_analytics(
    format: str = Query(default="json", pattern="^(json|csv|siem_cef|siem_json)$"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Export analytics data for compliance/reporting.

    Supported formats:
    - json: Standard JSON export
    - csv: CSV-formatted data with headers
    - siem_cef: CEF (Common Event Format) for SIEM integration
    - siem_json: JSON optimized for SIEM/ELK ingestion
    """
    from datetime import datetime, UTC

    manager = get_analytics_manager()
    summary = manager.get_summary(days=days)
    events = manager.get_events(limit=10000)

    if format == "csv":
        # Comprehensive CSV export
        return {
            "format": "csv",
            "headers": [
                "event_id", "timestamp", "user_id", "department", "agent_id",
                "agent_name", "query_text", "response_length", "latency_ms",
                "tokens_in", "tokens_out", "cost_usd", "hitl_mode",
                "was_escalated", "was_approved", "guardrails_triggered",
                "sources_used", "success", "error_message", "session_id"
            ],
            "rows": [
                [
                    e.id, e.timestamp, e.user_id, e.department, e.agent_id,
                    e.agent_name, e.query_text[:500], len(e.response_text),
                    e.latency_ms, e.tokens_in, e.tokens_out, e.cost_usd,
                    e.hitl_mode, e.was_escalated, e.was_approved,
                    ";".join(e.guardrails_triggered), e.sources_used,
                    e.success, e.error_message or "", e.session_id or ""
                ]
                for e in events
            ],
            "generated_at": datetime.now(UTC).isoformat(),
            "total_records": len(events),
        }

    elif format == "siem_cef":
        # CEF format for traditional SIEM systems (Splunk, ArcSight, etc.)
        cef_lines = []
        for e in events:
            # CEF severity based on escalation and errors
            severity = 3  # Default info
            if not e.success:
                severity = 7
            elif e.was_escalated:
                severity = 5
            elif e.guardrails_triggered:
                severity = 4

            cef_line = (
                f"CEF:0|HAAIS|AIOS|1.0|"
                f"{e.id}|"
                f"AI Query Event|"
                f"{severity}|"
                f"rt={e.timestamp} "
                f"src={e.user_id} "
                f"suser={e.user_id} "
                f"duser={e.agent_id} "
                f"msg={e.query_text[:200].replace('=', '\\=').replace('|', '\\|')} "
                f"outcome={'Success' if e.success else 'Failure'} "
                f"cs1={e.department} cs1Label=Department "
                f"cs2={e.hitl_mode} cs2Label=HITLMode "
                f"cn1={e.latency_ms} cn1Label=LatencyMs "
                f"cfp1={e.cost_usd} cfp1Label=CostUSD"
            )
            cef_lines.append(cef_line)

        return {
            "format": "siem_cef",
            "content_type": "text/plain",
            "lines": cef_lines,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_records": len(events),
        }

    elif format == "siem_json":
        # JSON format optimized for ELK/SIEM ingestion
        siem_events = []
        for e in events:
            siem_events.append({
                "@timestamp": e.timestamp,
                "event.kind": "event",
                "event.category": ["process"],
                "event.type": ["info"],
                "event.outcome": "success" if e.success else "failure",
                "event.id": e.id,

                "observer.vendor": "HAAIS",
                "observer.product": "AIOS",
                "observer.version": "1.0.0",

                "user.id": e.user_id,
                "user.group.name": e.department,

                "aios.agent.id": e.agent_id,
                "aios.agent.name": e.agent_name,
                "aios.query.text": e.query_text[:1000],
                "aios.response.length": len(e.response_text),
                "aios.latency_ms": e.latency_ms,
                "aios.tokens.input": e.tokens_in,
                "aios.tokens.output": e.tokens_out,
                "aios.cost_usd": e.cost_usd,
                "aios.hitl_mode": e.hitl_mode,
                "aios.was_escalated": e.was_escalated,
                "aios.was_approved": e.was_approved,
                "aios.guardrails_triggered": e.guardrails_triggered,
                "aios.sources_used": e.sources_used,
                "aios.session_id": e.session_id,

                "error.message": e.error_message if not e.success else None,
            })

        return {
            "format": "siem_json",
            "content_type": "application/x-ndjson",
            "events": siem_events,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_records": len(events),
        }

    # Default JSON format
    return {
        "format": "json",
        "summary": summary.model_dump(),
        "events": [e.model_dump() for e in events[:100]],  # Limit for JSON response
        "events_count": len(events),
        "generated_at": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# File Download Endpoints
# =============================================================================


@router.get("/export/download/csv")
async def download_csv(
    days: int = Query(default=30, ge=1, le=365),
) -> StreamingResponse:
    """Download analytics data as a CSV file.

    Returns a downloadable CSV file with all event data.
    """
    manager = get_analytics_manager()
    events = manager.get_events(limit=10000)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    headers = [
        "event_id", "timestamp", "user_id", "department", "agent_id",
        "agent_name", "query_text", "response_length", "latency_ms",
        "tokens_in", "tokens_out", "cost_usd", "hitl_mode",
        "was_escalated", "was_approved", "guardrails_triggered",
        "sources_used", "success", "error_message", "session_id"
    ]
    writer.writerow(headers)

    # Write data rows
    for e in events:
        writer.writerow([
            e.id, e.timestamp, e.user_id, e.department, e.agent_id,
            e.agent_name, e.query_text[:500], len(e.response_text),
            e.latency_ms, e.tokens_in, e.tokens_out, e.cost_usd,
            e.hitl_mode, e.was_escalated, e.was_approved,
            ";".join(e.guardrails_triggered), e.sources_used,
            e.success, e.error_message or "", e.session_id or ""
        ])

    # Generate filename with timestamp
    filename = f"aios_analytics_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/download/siem-cef")
async def download_siem_cef(
    days: int = Query(default=30, ge=1, le=365),
) -> StreamingResponse:
    """Download analytics data in CEF (Common Event Format) for SIEM.

    Returns a downloadable text file with CEF-formatted events.
    Compatible with Splunk, ArcSight, QRadar, and other SIEM systems.
    """
    manager = get_analytics_manager()
    events = manager.get_events(limit=10000)

    # Create CEF content
    lines = []
    for e in events:
        # CEF severity based on escalation and errors
        severity = 3  # Default info
        if not e.success:
            severity = 7
        elif e.was_escalated:
            severity = 5
        elif e.guardrails_triggered:
            severity = 4

        cef_line = (
            f"CEF:0|HAAIS|AIOS|1.0|"
            f"{e.id}|"
            f"AI Query Event|"
            f"{severity}|"
            f"rt={e.timestamp} "
            f"src={e.user_id} "
            f"suser={e.user_id} "
            f"duser={e.agent_id} "
            f"msg={e.query_text[:200].replace('=', '\\=').replace('|', '\\|').replace(chr(10), ' ')} "
            f"outcome={'Success' if e.success else 'Failure'} "
            f"cs1={e.department} cs1Label=Department "
            f"cs2={e.hitl_mode} cs2Label=HITLMode "
            f"cn1={e.latency_ms} cn1Label=LatencyMs "
            f"cfp1={e.cost_usd} cfp1Label=CostUSD"
        )
        lines.append(cef_line)

    content = "\n".join(lines)
    filename = f"aios_siem_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.cef"

    return StreamingResponse(
        iter([content]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/download/siem-json")
async def download_siem_json(
    days: int = Query(default=30, ge=1, le=365),
) -> StreamingResponse:
    """Download analytics data in NDJSON format for SIEM/ELK.

    Returns a downloadable NDJSON file optimized for Elasticsearch/ELK ingestion.
    Each line is a valid JSON object (Newline Delimited JSON).
    """
    import json

    manager = get_analytics_manager()
    events = manager.get_events(limit=10000)

    # Create NDJSON content (one JSON object per line)
    lines = []
    for e in events:
        siem_event = {
            "@timestamp": e.timestamp,
            "event.kind": "event",
            "event.category": ["process"],
            "event.type": ["info"],
            "event.outcome": "success" if e.success else "failure",
            "event.id": e.id,

            "observer.vendor": "HAAIS",
            "observer.product": "AIOS",
            "observer.version": "1.0.0",

            "user.id": e.user_id,
            "user.group.name": e.department,

            "aios.agent.id": e.agent_id,
            "aios.agent.name": e.agent_name,
            "aios.query.text": e.query_text[:1000],
            "aios.response.length": len(e.response_text),
            "aios.latency_ms": e.latency_ms,
            "aios.tokens.input": e.tokens_in,
            "aios.tokens.output": e.tokens_out,
            "aios.cost_usd": e.cost_usd,
            "aios.hitl_mode": e.hitl_mode,
            "aios.was_escalated": e.was_escalated,
            "aios.was_approved": e.was_approved,
            "aios.guardrails_triggered": e.guardrails_triggered,
            "aios.sources_used": e.sources_used,
            "aios.session_id": e.session_id,

            "error.message": e.error_message if not e.success else None,
        }
        lines.append(json.dumps(siem_event))

    content = "\n".join(lines)
    filename = f"aios_elk_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.ndjson"

    return StreamingResponse(
        iter([content]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
