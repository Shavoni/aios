"""HITL (Human-in-the-Loop) workflow API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.core.hitl import (
    ApprovalQueue,
    ApprovalRequest,
    ApprovalStatus,
    HITLMode,
    get_hitl_manager,
)
from packages.core.hitl.workflow import (
    HITLWorkflowManager,
    ReviewerProfile,
    EscalationLevel,
    WorkflowStats,
    Notification,
    get_hitl_workflow_manager,
)

router = APIRouter(prefix="/hitl", tags=["HITL Workflow"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateApprovalRequest(BaseModel):
    """Request to create an approval."""

    hitl_mode: str = Field(..., pattern="^(INFORM|DRAFT|EXECUTE|ESCALATE)$")
    user_id: str
    user_department: str = "General"
    agent_id: str
    agent_name: str
    original_query: str
    proposed_response: str
    risk_signals: list[str] = Field(default_factory=list)
    guardrails_triggered: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    assigned_to: str | None = None


class ApproveRequest(BaseModel):
    """Request to approve a pending item."""

    reviewer_id: str
    notes: str | None = None
    modified_response: str | None = None


class RejectRequest(BaseModel):
    """Request to reject a pending item."""

    reviewer_id: str
    reason: str


class AssignRequest(BaseModel):
    """Request to assign a reviewer."""

    assignee_id: str


class DetermineHITLModeRequest(BaseModel):
    """Request to determine HITL mode."""

    intent_domain: str
    intent_impact: str = "low"
    risk_signals: list[str] = Field(default_factory=list)
    user_role: str = "employee"


class ApprovalListResponse(BaseModel):
    """Response containing list of approvals."""

    approvals: list[ApprovalRequest]
    total: int


# =============================================================================
# HITL Mode Endpoints
# =============================================================================


@router.post("/determine-mode")
async def determine_hitl_mode(request: DetermineHITLModeRequest) -> dict[str, str]:
    """Determine the appropriate HITL mode for a request."""
    manager = get_hitl_manager()
    mode = manager.determine_hitl_mode(
        intent_domain=request.intent_domain,
        intent_impact=request.intent_impact,
        risk_signals=request.risk_signals,
        user_role=request.user_role,
    )
    return {"mode": mode.value}


# =============================================================================
# Approval Queue Endpoints
# =============================================================================


@router.get("/queue/summary", response_model=ApprovalQueue)
async def get_queue_summary() -> ApprovalQueue:
    """Get summary of the approval queue."""
    manager = get_hitl_manager()
    return manager.get_queue_summary()


@router.get("/queue", response_model=ApprovalListResponse)
async def list_pending_approvals(
    hitl_mode: str | None = None,
    agent_id: str | None = None,
    assigned_to: str | None = None,
    priority: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> ApprovalListResponse:
    """List pending approval requests."""
    manager = get_hitl_manager()

    mode = HITLMode(hitl_mode) if hitl_mode else None
    approvals = manager.list_pending_approvals(
        hitl_mode=mode,
        agent_id=agent_id,
        assigned_to=assigned_to,
        priority=priority,
        limit=limit,
    )
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


# =============================================================================
# Approval CRUD Endpoints
# =============================================================================


@router.post("/approvals", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
async def create_approval(request: CreateApprovalRequest) -> ApprovalRequest:
    """Create a new approval request."""
    manager = get_hitl_manager()
    return manager.create_approval_request(
        hitl_mode=HITLMode(request.hitl_mode),
        user_id=request.user_id,
        user_department=request.user_department,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        original_query=request.original_query,
        proposed_response=request.proposed_response,
        risk_signals=request.risk_signals,
        guardrails_triggered=request.guardrails_triggered,
        escalation_reason=request.escalation_reason,
        context=request.context,
        priority=request.priority,
        assigned_to=request.assigned_to,
    )


@router.get("/approvals/{request_id}", response_model=ApprovalRequest)
async def get_approval(request_id: str) -> ApprovalRequest:
    """Get an approval request by ID."""
    manager = get_hitl_manager()
    approval = manager.get_approval_request(request_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{request_id}' not found",
        )
    return approval


@router.post("/approvals/{request_id}/approve", response_model=ApprovalRequest)
async def approve_request(request_id: str, request: ApproveRequest) -> ApprovalRequest:
    """Approve a pending request."""
    manager = get_hitl_manager()
    approval = manager.approve_request(
        request_id=request_id,
        reviewer_id=request.reviewer_id,
        notes=request.notes,
        modified_response=request.modified_response,
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request '{request_id}' - not found or not pending",
        )
    return approval


@router.post("/approvals/{request_id}/reject", response_model=ApprovalRequest)
async def reject_request(request_id: str, request: RejectRequest) -> ApprovalRequest:
    """Reject a pending request."""
    manager = get_hitl_manager()
    approval = manager.reject_request(
        request_id=request_id,
        reviewer_id=request.reviewer_id,
        reason=request.reason,
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request '{request_id}' - not found or not pending",
        )
    return approval


@router.post("/approvals/{request_id}/cancel")
async def cancel_request(request_id: str, reason: str = "") -> dict[str, str]:
    """Cancel a pending request."""
    manager = get_hitl_manager()
    if manager.cancel_request(request_id, reason):
        return {"status": "ok", "message": "Request cancelled"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Cannot cancel request '{request_id}' - not found or not pending",
    )


@router.put("/approvals/{request_id}/assign", response_model=ApprovalRequest)
async def assign_request(request_id: str, request: AssignRequest) -> ApprovalRequest:
    """Assign a request to a reviewer."""
    manager = get_hitl_manager()
    approval = manager.assign_request(request_id, request.assignee_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{request_id}' not found",
        )
    return approval


# =============================================================================
# History Endpoints
# =============================================================================


@router.get("/history", response_model=ApprovalListResponse)
async def get_approval_history(
    user_id: str | None = None,
    agent_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=500),
) -> ApprovalListResponse:
    """Get approval history."""
    manager = get_hitl_manager()

    approval_status = ApprovalStatus(status_filter) if status_filter else None
    approvals = manager.get_approval_history(
        user_id=user_id,
        agent_id=agent_id,
        status=approval_status,
        days=days,
        limit=limit,
    )
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


# =============================================================================
# Advanced Workflow Request/Response Models
# =============================================================================


class RegisterReviewerRequest(BaseModel):
    """Request to register a reviewer."""

    reviewer_id: str
    name: str
    email: str
    level: str = Field(default="L1_SUPERVISOR", pattern="^(L1_SUPERVISOR|L2_MANAGER|L3_DIRECTOR|L4_EXECUTIVE)$")
    departments: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    max_concurrent_reviews: int = Field(default=10, ge=1, le=100)


class BatchApproveRequest(BaseModel):
    """Request for batch approval."""

    approval_ids: list[str]
    reviewer_id: str
    notes: str | None = None


class BatchRejectRequest(BaseModel):
    """Request for batch rejection."""

    approval_ids: list[str]
    reviewer_id: str
    reason: str


class EscalateRequest(BaseModel):
    """Request to escalate an approval."""

    reason: str


class ReviewerListResponse(BaseModel):
    """Response containing list of reviewers."""

    reviewers: list[dict[str, Any]]
    total: int


class SLAStatusResponse(BaseModel):
    """Response for SLA status check."""

    issues: list[dict[str, Any]]
    total_issues: int
    warnings: int
    breaches: int


class NotificationListResponse(BaseModel):
    """Response containing notifications."""

    notifications: list[dict[str, Any]]
    total: int
    unread: int


# =============================================================================
# Reviewer Management Endpoints
# =============================================================================


@router.post("/reviewers", status_code=status.HTTP_201_CREATED)
async def register_reviewer(request: RegisterReviewerRequest) -> dict[str, str]:
    """Register a new reviewer."""
    workflow = get_hitl_workflow_manager()

    profile = ReviewerProfile(
        reviewer_id=request.reviewer_id,
        name=request.name,
        email=request.email,
        level=EscalationLevel(request.level),
        departments=request.departments,
        domains=request.domains,
        max_concurrent_reviews=request.max_concurrent_reviews,
    )

    workflow.register_reviewer(profile)
    return {"status": "ok", "message": f"Reviewer {request.reviewer_id} registered"}


@router.get("/reviewers", response_model=ReviewerListResponse)
async def list_reviewers(
    level: str | None = None,
    department: str | None = None,
    active_only: bool = Query(default=True),
) -> ReviewerListResponse:
    """List registered reviewers."""
    workflow = get_hitl_workflow_manager()

    escalation_level = EscalationLevel(level) if level else None
    reviewers = workflow.list_reviewers(
        level=escalation_level,
        department=department,
        active_only=active_only,
    )

    reviewer_dicts = [
        {
            "reviewer_id": r.reviewer_id,
            "name": r.name,
            "email": r.email,
            "level": r.level.value,
            "departments": r.departments,
            "domains": r.domains,
            "max_concurrent_reviews": r.max_concurrent_reviews,
            "active": r.active,
            "current_load": r.current_load,
            "total_reviews": r.total_reviews,
        }
        for r in reviewers
    ]

    return ReviewerListResponse(reviewers=reviewer_dicts, total=len(reviewer_dicts))


@router.get("/reviewers/{reviewer_id}")
async def get_reviewer(reviewer_id: str) -> dict[str, Any]:
    """Get a reviewer profile."""
    workflow = get_hitl_workflow_manager()
    reviewer = workflow.get_reviewer(reviewer_id)

    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reviewer '{reviewer_id}' not found",
        )

    return {
        "reviewer_id": reviewer.reviewer_id,
        "name": reviewer.name,
        "email": reviewer.email,
        "level": reviewer.level.value,
        "departments": reviewer.departments,
        "domains": reviewer.domains,
        "max_concurrent_reviews": reviewer.max_concurrent_reviews,
        "active": reviewer.active,
        "current_load": reviewer.current_load,
        "total_reviews": reviewer.total_reviews,
        "avg_review_time_minutes": reviewer.avg_review_time_minutes,
    }


# =============================================================================
# Auto-Assignment Endpoints
# =============================================================================


@router.post("/approvals/{request_id}/auto-assign")
async def auto_assign_approval(request_id: str) -> dict[str, Any]:
    """Automatically assign a reviewer to an approval."""
    workflow = get_hitl_workflow_manager()
    reviewer = workflow.auto_assign(request_id)

    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No suitable reviewer available or approval already assigned",
        )

    return {
        "status": "ok",
        "assigned_to": reviewer.reviewer_id,
        "reviewer_name": reviewer.name,
    }


@router.post("/queue/auto-assign-all")
async def auto_assign_all_pending() -> dict[str, Any]:
    """Auto-assign all unassigned pending approvals."""
    workflow = get_hitl_workflow_manager()
    assignments = workflow.auto_assign_all_pending()

    return {
        "status": "ok",
        "assignments_made": len(assignments),
        "assignments": assignments,
    }


# =============================================================================
# Escalation Endpoints
# =============================================================================


@router.post("/approvals/{request_id}/escalate")
async def escalate_approval(request_id: str, request: EscalateRequest) -> dict[str, str]:
    """Escalate an approval to the next level."""
    workflow = get_hitl_workflow_manager()

    if workflow.escalate(request_id, request.reason):
        return {"status": "ok", "message": "Approval escalated"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot escalate - approval not found, not pending, or no higher level available",
    )


# =============================================================================
# SLA Monitoring Endpoints
# =============================================================================


@router.get("/sla/status", response_model=SLAStatusResponse)
async def check_sla_status() -> SLAStatusResponse:
    """Check SLA status for all pending approvals."""
    workflow = get_hitl_workflow_manager()
    issues = workflow.check_sla_status()

    warnings = len([i for i in issues if i["status"] == "warning"])
    breaches = len([i for i in issues if i["status"] == "breach"])

    return SLAStatusResponse(
        issues=issues,
        total_issues=len(issues),
        warnings=warnings,
        breaches=breaches,
    )


@router.post("/sla/process-violations")
async def process_sla_violations() -> dict[str, Any]:
    """Process SLA violations and trigger escalations."""
    workflow = get_hitl_workflow_manager()
    escalated = workflow.process_sla_violations()

    return {
        "status": "ok",
        "escalated_count": len(escalated),
        "escalated_approvals": escalated,
    }


# =============================================================================
# Batch Operations Endpoints
# =============================================================================


@router.post("/batch/approve")
async def batch_approve(request: BatchApproveRequest) -> dict[str, Any]:
    """Approve multiple requests at once."""
    workflow = get_hitl_workflow_manager()
    results = workflow.batch_approve(
        approval_ids=request.approval_ids,
        reviewer_id=request.reviewer_id,
        notes=request.notes,
    )

    succeeded = sum(1 for v in results.values() if v)
    failed = len(results) - succeeded

    return {
        "status": "ok",
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


@router.post("/batch/reject")
async def batch_reject(request: BatchRejectRequest) -> dict[str, Any]:
    """Reject multiple requests at once."""
    workflow = get_hitl_workflow_manager()
    results = workflow.batch_reject(
        approval_ids=request.approval_ids,
        reviewer_id=request.reviewer_id,
        reason=request.reason,
    )

    succeeded = sum(1 for v in results.values() if v)
    failed = len(results) - succeeded

    return {
        "status": "ok",
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


# =============================================================================
# Notification Endpoints
# =============================================================================


@router.get("/notifications/{recipient_id}", response_model=NotificationListResponse)
async def get_notifications(
    recipient_id: str,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationListResponse:
    """Get notifications for a recipient."""
    workflow = get_hitl_workflow_manager()
    notifications = workflow.get_notifications(
        recipient_id=recipient_id,
        unread_only=unread_only,
        limit=limit,
    )

    notification_dicts = [
        {
            "id": n.id,
            "type": n.type.value,
            "title": n.title,
            "message": n.message,
            "approval_id": n.approval_id,
            "created_at": n.created_at,
            "read": n.read,
            "read_at": n.read_at,
        }
        for n in notifications
    ]

    unread = len([n for n in notifications if not n.read])

    return NotificationListResponse(
        notifications=notification_dicts,
        total=len(notification_dicts),
        unread=unread,
    )


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str) -> dict[str, str]:
    """Mark a notification as read."""
    workflow = get_hitl_workflow_manager()

    if workflow.mark_notification_read(notification_id):
        return {"status": "ok", "message": "Notification marked as read"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Notification '{notification_id}' not found",
    )


# =============================================================================
# Statistics Endpoints
# =============================================================================


@router.get("/stats/workflow")
async def get_workflow_stats(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Get comprehensive workflow statistics."""
    workflow = get_hitl_workflow_manager()
    stats = workflow.get_workflow_stats(days=days)

    return {
        "period_start": stats.period_start,
        "period_end": stats.period_end,
        "total_requests": stats.total_requests,
        "approved": stats.approved,
        "rejected": stats.rejected,
        "expired": stats.expired,
        "cancelled": stats.cancelled,
        "avg_resolution_time_minutes": stats.avg_resolution_time_minutes,
        "sla_compliance_percentage": stats.sla_compliance_percentage,
        "escalations": stats.escalations,
        "by_mode": stats.by_mode,
        "by_department": stats.by_department,
        "by_reviewer": stats.by_reviewer,
        "busiest_hours": stats.busiest_hours,
        "top_agents_by_volume": stats.top_agents_by_volume,
    }


@router.get("/stats/dashboard")
async def get_dashboard_stats() -> dict[str, Any]:
    """Get stats optimized for dashboard display."""
    manager = get_hitl_manager()
    workflow = get_hitl_workflow_manager()

    queue_summary = manager.get_queue_summary()
    sla_issues = workflow.check_sla_status()
    stats = workflow.get_workflow_stats(days=7)

    return {
        "queue": {
            "pending_count": queue_summary.pending_count,
            "by_priority": queue_summary.pending_by_priority,
            "by_mode": queue_summary.pending_by_mode,
            "oldest_pending": queue_summary.oldest_pending,
        },
        "sla": {
            "total_issues": len(sla_issues),
            "warnings": len([i for i in sla_issues if i["status"] == "warning"]),
            "breaches": len([i for i in sla_issues if i["status"] == "breach"]),
        },
        "week_summary": {
            "total": stats.total_requests,
            "approved": stats.approved,
            "rejected": stats.rejected,
            "avg_resolution_minutes": stats.avg_resolution_time_minutes,
            "sla_compliance": stats.sla_compliance_percentage,
        },
    }
