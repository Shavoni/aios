"""Analytics API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
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
    format: str = Query(default="json", pattern="^(json|csv)$"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Export analytics data for compliance/reporting."""
    manager = get_analytics_manager()
    summary = manager.get_summary(days=days)
    events = manager.get_events(limit=10000)

    if format == "csv":
        # Return CSV-ready structure
        return {
            "format": "csv",
            "headers": [
                "timestamp", "user_id", "department", "agent_id",
                "query", "latency_ms", "cost_usd", "success"
            ],
            "rows": [
                [
                    e.timestamp, e.user_id, e.department, e.agent_id,
                    e.query_text[:200], e.latency_ms, e.cost_usd, e.success
                ]
                for e in events
            ]
        }

    return {
        "format": "json",
        "summary": summary.model_dump(),
        "events_count": len(events),
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
