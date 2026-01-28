"""Human-in-the-Loop workflow management."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class HITLMode(str, Enum):
    """HITL operational modes."""

    INFORM = "INFORM"      # Auto-respond, inform user
    DRAFT = "DRAFT"        # Queue for human review before sending
    EXECUTE = "EXECUTE"    # Requires manager approval before action
    ESCALATE = "ESCALATE"  # Route to human immediately


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalRequest(BaseModel):
    """A request awaiting human approval."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Request details
    hitl_mode: HITLMode
    user_id: str
    user_department: str = "General"
    agent_id: str
    agent_name: str

    # Content
    original_query: str
    proposed_response: str
    context: dict[str, Any] = Field(default_factory=dict)

    # Risk/governance info
    risk_signals: list[str] = Field(default_factory=list)
    guardrails_triggered: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None

    # Resolution
    resolved_at: str | None = None
    resolved_by: str | None = None
    reviewer_notes: str | None = None
    modified_response: str | None = None

    # Routing
    assigned_to: str | None = None  # User ID of assigned reviewer
    priority: str = "normal"  # low, normal, high, urgent


class ApprovalQueue(BaseModel):
    """Summary of approval queue status."""

    pending_count: int = 0
    pending_by_mode: dict[str, int] = Field(default_factory=dict)
    pending_by_agent: dict[str, int] = Field(default_factory=dict)
    pending_by_priority: dict[str, int] = Field(default_factory=dict)
    oldest_pending: str | None = None
    avg_resolution_time_hrs: float | None = None


class HITLManager:
    """Manages HITL workflow and approvals."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "hitl"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Approvals storage
        self._approvals_path = self.storage_path / "approvals.json"
        self._approvals: dict[str, ApprovalRequest] = {}
        self._load_approvals()

        # Default expiration (hours) by mode
        self._expiration_hours = {
            HITLMode.DRAFT: 24,
            HITLMode.EXECUTE: 48,
            HITLMode.ESCALATE: 4,
        }

    def _load_approvals(self) -> None:
        """Load approvals from storage."""
        if self._approvals_path.exists():
            try:
                with open(self._approvals_path) as f:
                    data = json.load(f)
                    for approval_id, approval_data in data.items():
                        self._approvals[approval_id] = ApprovalRequest(**approval_data)
            except Exception:
                self._approvals = {}

    def _save_approvals(self) -> None:
        """Save approvals to storage."""
        data = {k: v.model_dump() for k, v in self._approvals.items()}
        with open(self._approvals_path, "w") as f:
            json.dump(data, f, indent=2)

    def _check_expirations(self) -> None:
        """Check and update expired approvals."""
        now = datetime.utcnow().isoformat()
        for approval in self._approvals.values():
            if (
                approval.status == ApprovalStatus.PENDING
                and approval.expires_at
                and approval.expires_at < now
            ):
                approval.status = ApprovalStatus.EXPIRED
                approval.resolved_at = now
        self._save_approvals()

    # =========================================================================
    # HITL Mode Determination
    # =========================================================================

    def determine_hitl_mode(
        self,
        intent_domain: str,
        intent_impact: str,
        risk_signals: list[str],
        user_role: str = "employee",
    ) -> HITLMode:
        """Determine the appropriate HITL mode based on context."""
        # High-risk signals always escalate
        high_risk_signals = {"PII", "PHI", "LEGAL_CONTRACT", "FINANCIAL_LARGE"}
        if any(s in high_risk_signals for s in risk_signals):
            return HITLMode.ESCALATE

        # High impact requires approval
        if intent_impact == "high":
            return HITLMode.EXECUTE

        # Medium impact gets draft review
        if intent_impact == "medium":
            return HITLMode.DRAFT

        # External-facing content gets draft review
        if intent_domain in {"Communications", "PublicRelations", "Legal"}:
            return HITLMode.DRAFT

        # Default: inform only
        return HITLMode.INFORM

    # =========================================================================
    # Approval Management
    # =========================================================================

    def create_approval_request(
        self,
        hitl_mode: HITLMode,
        user_id: str,
        agent_id: str,
        agent_name: str,
        original_query: str,
        proposed_response: str,
        user_department: str = "General",
        risk_signals: list[str] | None = None,
        guardrails_triggered: list[str] | None = None,
        escalation_reason: str | None = None,
        context: dict[str, Any] | None = None,
        priority: str = "normal",
        assigned_to: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        # Calculate expiration
        exp_hours = self._expiration_hours.get(hitl_mode, 24)
        expires_at = (datetime.utcnow() + timedelta(hours=exp_hours)).isoformat()

        request = ApprovalRequest(
            hitl_mode=hitl_mode,
            user_id=user_id,
            user_department=user_department,
            agent_id=agent_id,
            agent_name=agent_name,
            original_query=original_query,
            proposed_response=proposed_response,
            expires_at=expires_at,
            risk_signals=risk_signals or [],
            guardrails_triggered=guardrails_triggered or [],
            escalation_reason=escalation_reason,
            context=context or {},
            priority=priority,
            assigned_to=assigned_to,
        )

        self._approvals[request.id] = request
        self._save_approvals()
        return request

    def get_approval_request(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        self._check_expirations()
        return self._approvals.get(request_id)

    def approve_request(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str | None = None,
        modified_response: str | None = None,
    ) -> ApprovalRequest | None:
        """Approve a pending request."""
        request = self._approvals.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.APPROVED
        request.resolved_at = datetime.utcnow().isoformat()
        request.resolved_by = reviewer_id
        request.reviewer_notes = notes
        if modified_response:
            request.modified_response = modified_response

        self._save_approvals()
        return request

    def reject_request(
        self,
        request_id: str,
        reviewer_id: str,
        reason: str,
    ) -> ApprovalRequest | None:
        """Reject a pending request."""
        request = self._approvals.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.REJECTED
        request.resolved_at = datetime.utcnow().isoformat()
        request.resolved_by = reviewer_id
        request.reviewer_notes = reason

        self._save_approvals()
        return request

    def cancel_request(self, request_id: str, reason: str = "") -> bool:
        """Cancel a pending request."""
        request = self._approvals.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.CANCELLED
        request.resolved_at = datetime.utcnow().isoformat()
        request.reviewer_notes = reason

        self._save_approvals()
        return True

    def assign_request(
        self,
        request_id: str,
        assignee_id: str,
    ) -> ApprovalRequest | None:
        """Assign a request to a reviewer."""
        request = self._approvals.get(request_id)
        if not request:
            return None

        request.assigned_to = assignee_id
        self._save_approvals()
        return request

    # =========================================================================
    # Queue Management
    # =========================================================================

    def list_pending_approvals(
        self,
        hitl_mode: HITLMode | None = None,
        agent_id: str | None = None,
        assigned_to: str | None = None,
        priority: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List pending approval requests."""
        self._check_expirations()

        results = []
        for request in self._approvals.values():
            if request.status != ApprovalStatus.PENDING:
                continue
            if hitl_mode and request.hitl_mode != hitl_mode:
                continue
            if agent_id and request.agent_id != agent_id:
                continue
            if assigned_to and request.assigned_to != assigned_to:
                continue
            if priority and request.priority != priority:
                continue
            results.append(request)

        # Sort by priority and created_at
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        results.sort(key=lambda r: (priority_order.get(r.priority, 2), r.created_at))

        return results[:limit]

    def get_queue_summary(self) -> ApprovalQueue:
        """Get summary of the approval queue."""
        self._check_expirations()

        pending = [r for r in self._approvals.values() if r.status == ApprovalStatus.PENDING]

        # Count by mode
        by_mode: dict[str, int] = {}
        for r in pending:
            mode = r.hitl_mode.value
            by_mode[mode] = by_mode.get(mode, 0) + 1

        # Count by agent
        by_agent: dict[str, int] = {}
        for r in pending:
            by_agent[r.agent_id] = by_agent.get(r.agent_id, 0) + 1

        # Count by priority
        by_priority: dict[str, int] = {}
        for r in pending:
            by_priority[r.priority] = by_priority.get(r.priority, 0) + 1

        # Oldest pending
        oldest = None
        if pending:
            oldest = min(r.created_at for r in pending)

        # Average resolution time
        resolved = [
            r for r in self._approvals.values()
            if r.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}
            and r.resolved_at
        ]
        avg_time = None
        if resolved:
            times = []
            for r in resolved:
                try:
                    created = datetime.fromisoformat(r.created_at)
                    resolved_dt = datetime.fromisoformat(r.resolved_at)
                    times.append((resolved_dt - created).total_seconds() / 3600)
                except Exception:
                    pass
            if times:
                avg_time = sum(times) / len(times)

        return ApprovalQueue(
            pending_count=len(pending),
            pending_by_mode=by_mode,
            pending_by_agent=by_agent,
            pending_by_priority=by_priority,
            oldest_pending=oldest,
            avg_resolution_time_hrs=avg_time,
        )

    def get_approval_history(
        self,
        user_id: str | None = None,
        agent_id: str | None = None,
        status: ApprovalStatus | None = None,
        days: int = 30,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """Get approval history."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        results = []
        for request in self._approvals.values():
            if request.created_at < cutoff:
                continue
            if user_id and request.user_id != user_id:
                continue
            if agent_id and request.agent_id != agent_id:
                continue
            if status and request.status != status:
                continue
            results.append(request)

        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]


# Singleton instance
_hitl_manager: HITLManager | None = None


def get_hitl_manager() -> HITLManager:
    """Get the HITL manager singleton."""
    global _hitl_manager
    if _hitl_manager is None:
        _hitl_manager = HITLManager()
    return _hitl_manager


__all__ = [
    "HITLMode",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalQueue",
    "HITLManager",
    "get_hitl_manager",
]
