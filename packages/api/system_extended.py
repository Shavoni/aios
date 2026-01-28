"""Extended system API endpoints for cache, rate limits, templates, and audit."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

# Cache
from packages.core.cache import CacheStats, get_cache_manager

# Rate limiting
from packages.core.ratelimit import (
    QuotaUsageReport,
    RateLimitConfig,
    RateLimitResult,
    get_rate_limit_manager,
)

# Templates
from packages.core.templates import (
    AgentTemplate,
    get_template,
    list_categories,
    list_templates,
    search_templates,
)

# Audit
from packages.core.audit import (
    AuditEvent,
    AuditEventType,
    AuditSummary,
    ComplianceReport,
    SeverityLevel,
    get_audit_manager,
)

router = APIRouter(tags=["System Extended"])


# =============================================================================
# Cache Endpoints
# =============================================================================


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats() -> CacheStats:
    """Get cache statistics."""
    manager = get_cache_manager()
    return manager.get_stats()


@router.post("/cache/clear")
async def clear_cache(
    cache_type: str | None = Query(default=None, pattern="^(query|embedding|response)$"),
) -> dict[str, Any]:
    """Clear cache entries."""
    manager = get_cache_manager()
    count = manager.clear_cache(cache_type)
    return {"status": "ok", "cleared_count": count}


@router.post("/cache/invalidate/{agent_id}")
async def invalidate_agent_cache(agent_id: str) -> dict[str, Any]:
    """Invalidate cache for a specific agent."""
    manager = get_cache_manager()
    count = manager.invalidate_agent_cache(agent_id)
    return {"status": "ok", "invalidated_count": count}


# =============================================================================
# Rate Limiting Endpoints
# =============================================================================


class SetUserLimitsRequest(BaseModel):
    """Request to set user rate limits."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    tokens_per_day: int = 1000000
    cost_limit_per_day: float = 100.0


class SetDepartmentLimitsRequest(BaseModel):
    """Request to set department limits."""

    daily_requests: int | None = None
    daily_tokens: int | None = None
    daily_cost: float | None = None


@router.get("/ratelimit/check/{user_id}", response_model=RateLimitResult)
async def check_rate_limit(
    user_id: str,
    department: str = "General",
) -> RateLimitResult:
    """Check if a user is within rate limits."""
    manager = get_rate_limit_manager()
    return manager.check_rate_limit(user_id, department)


@router.get("/ratelimit/usage/{user_id}", response_model=QuotaUsageReport)
async def get_user_usage(user_id: str) -> QuotaUsageReport:
    """Get usage report for a user."""
    manager = get_rate_limit_manager()
    return manager.get_usage_report(user_id=user_id)


@router.get("/ratelimit/usage/department/{department}", response_model=QuotaUsageReport)
async def get_department_usage(department: str) -> QuotaUsageReport:
    """Get usage report for a department."""
    manager = get_rate_limit_manager()
    return manager.get_usage_report(department=department)


@router.put("/ratelimit/users/{user_id}/limits")
async def set_user_limits(user_id: str, request: SetUserLimitsRequest) -> dict[str, str]:
    """Set custom rate limits for a user."""
    manager = get_rate_limit_manager()
    limits = RateLimitConfig(**request.model_dump())
    manager.set_user_limits(user_id, limits)
    return {"status": "ok", "message": f"Limits updated for {user_id}"}


@router.put("/ratelimit/departments/{department}/limits")
async def set_department_limits(
    department: str,
    request: SetDepartmentLimitsRequest,
) -> dict[str, str]:
    """Set limits for a department."""
    manager = get_rate_limit_manager()
    manager.set_department_limits(
        department,
        daily_requests=request.daily_requests,
        daily_tokens=request.daily_tokens,
        daily_cost=request.daily_cost,
    )
    return {"status": "ok", "message": f"Limits updated for {department}"}


@router.post("/ratelimit/users/{user_id}/reset")
async def reset_user_quota(user_id: str) -> dict[str, str]:
    """Reset a user's quota."""
    manager = get_rate_limit_manager()
    if manager.reset_user_quota(user_id):
        return {"status": "ok", "message": f"Quota reset for {user_id}"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User '{user_id}' not found",
    )


# =============================================================================
# Templates Endpoints
# =============================================================================


class TemplateListResponse(BaseModel):
    """Response containing list of templates."""

    templates: list[AgentTemplate]
    total: int


@router.get("/templates", response_model=TemplateListResponse)
async def list_agent_templates(
    category: str | None = None,
) -> TemplateListResponse:
    """List available agent templates."""
    templates = list_templates(category)
    return TemplateListResponse(templates=templates, total=len(templates))


@router.get("/templates/categories")
async def list_template_categories() -> dict[str, list[str]]:
    """List available template categories."""
    return {"categories": list_categories()}


@router.get("/templates/search", response_model=TemplateListResponse)
async def search_agent_templates(
    query: str = Query(..., min_length=1),
) -> TemplateListResponse:
    """Search templates by name, description, or tags."""
    templates = search_templates(query)
    return TemplateListResponse(templates=templates, total=len(templates))


@router.get("/templates/{template_id}", response_model=AgentTemplate)
async def get_agent_template(template_id: str) -> AgentTemplate:
    """Get a specific template by ID."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    return template


# =============================================================================
# Audit Endpoints
# =============================================================================


class AuditEventListResponse(BaseModel):
    """Response containing list of audit events."""

    events: list[AuditEvent]
    total: int


class LogEventRequest(BaseModel):
    """Request to log an audit event."""

    event_type: str
    action: str
    user_id: str = "system"
    user_department: str = "System"
    user_role: str = "system"
    agent_id: str | None = None
    agent_name: str | None = None
    session_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    severity: str = "INFO"


class GenerateReportRequest(BaseModel):
    """Request to generate a compliance report."""

    start_date: str
    end_date: str
    generated_by: str = "system"
    filters: dict[str, Any] = Field(default_factory=dict)


@router.get("/audit/events", response_model=AuditEventListResponse)
async def list_audit_events(
    start_date: str | None = None,
    end_date: str | None = None,
    event_type: str | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    severity: str | None = None,
    requires_review: bool | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> AuditEventListResponse:
    """List audit events with filtering."""
    manager = get_audit_manager()

    audit_type = AuditEventType(event_type) if event_type else None
    audit_severity = SeverityLevel(severity) if severity else None

    events = manager.get_events(
        start_date=start_date,
        end_date=end_date,
        event_type=audit_type,
        user_id=user_id,
        agent_id=agent_id,
        severity=audit_severity,
        requires_review=requires_review,
        limit=limit,
    )
    return AuditEventListResponse(events=events, total=len(events))


@router.get("/audit/summary", response_model=AuditSummary)
async def get_audit_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> AuditSummary:
    """Get audit summary for a period."""
    manager = get_audit_manager()
    return manager.get_summary(start_date=start_date, end_date=end_date)


@router.post("/audit/events", response_model=AuditEvent)
async def log_audit_event(request: LogEventRequest) -> AuditEvent:
    """Log an audit event."""
    manager = get_audit_manager()
    return manager.log_event(
        event_type=AuditEventType(request.event_type),
        action=request.action,
        user_id=request.user_id,
        user_department=request.user_department,
        user_role=request.user_role,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        session_id=request.session_id,
        details=request.details,
        severity=SeverityLevel(request.severity),
    )


@router.post("/audit/report", response_model=ComplianceReport)
async def generate_compliance_report(request: GenerateReportRequest) -> ComplianceReport:
    """Generate a FOIA-ready compliance report."""
    manager = get_audit_manager()
    return manager.generate_compliance_report(
        start_date=request.start_date,
        end_date=request.end_date,
        generated_by=request.generated_by,
        filters=request.filters,
    )


@router.post("/audit/events/{event_id}/review")
async def mark_event_reviewed(
    event_id: str,
    reviewer_id: str,
) -> dict[str, str]:
    """Mark an audit event as reviewed."""
    manager = get_audit_manager()
    if manager.mark_reviewed(event_id, reviewer_id):
        return {"status": "ok", "message": "Event marked as reviewed"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Event '{event_id}' not found",
    )


@router.get("/audit/pii/check")
async def check_pii(text: str = Query(..., min_length=1)) -> dict[str, Any]:
    """Check text for PII."""
    manager = get_audit_manager()
    pii = manager.detect_pii(text)
    sanitized = manager.sanitize_text(text)
    return {
        "pii_detected": pii,
        "has_pii": bool(pii),
        "sanitized_text": sanitized,
    }
