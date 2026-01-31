"""Advanced HITL workflow management.

Provides:
- Escalation chain management
- Notification system
- Reviewer workload balancing
- SLA monitoring
- Integration with governance
"""

from __future__ import annotations

import json
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from packages.core.hitl import (
    HITLMode,
    ApprovalStatus,
    ApprovalRequest,
    HITLManager,
    get_hitl_manager,
)

# PERFORMANCE: Maximum notifications to keep in memory
MAX_NOTIFICATIONS_IN_MEMORY = 10000
NOTIFICATION_CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes


class NotificationType(str, Enum):
    """Types of HITL notifications."""

    APPROVAL_CREATED = "approval_created"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_ASSIGNED = "approval_assigned"
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"
    ESCALATION_TRIGGERED = "escalation_triggered"


class EscalationLevel(str, Enum):
    """Escalation levels."""

    L1_SUPERVISOR = "L1_SUPERVISOR"
    L2_MANAGER = "L2_MANAGER"
    L3_DIRECTOR = "L3_DIRECTOR"
    L4_EXECUTIVE = "L4_EXECUTIVE"


@dataclass
class Notification:
    """A HITL notification."""

    id: str
    type: NotificationType
    recipient_id: str
    title: str
    message: str
    approval_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    read: bool = False
    read_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationRule:
    """Rule for escalation."""

    from_level: EscalationLevel
    to_level: EscalationLevel
    trigger_after_minutes: int
    notify_on_escalation: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewerProfile:
    """Profile for a reviewer."""

    reviewer_id: str
    name: str
    email: str
    level: EscalationLevel
    departments: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    max_concurrent_reviews: int = 10
    active: bool = True
    current_load: int = 0
    total_reviews: int = 0
    avg_review_time_minutes: float = 0.0


@dataclass
class SLAConfig:
    """SLA configuration for HITL modes."""

    mode: HITLMode
    warning_minutes: int
    breach_minutes: int
    escalate_on_breach: bool = True


@dataclass
class WorkflowStats:
    """Statistics for HITL workflow."""

    period_start: str
    period_end: str
    total_requests: int
    approved: int
    rejected: int
    expired: int
    cancelled: int
    avg_resolution_time_minutes: float
    sla_compliance_percentage: float
    escalations: int
    by_mode: dict[str, dict[str, int]]
    by_department: dict[str, dict[str, int]]
    by_reviewer: dict[str, dict[str, int]]
    busiest_hours: list[int]
    top_agents_by_volume: list[dict[str, Any]]


class HITLWorkflowManager:
    """Advanced HITL workflow management.

    Extends the base HITLManager with:
    - Escalation chains
    - Notifications
    - Reviewer management
    - SLA monitoring
    """

    def __init__(
        self,
        hitl_manager: HITLManager | None = None,
        storage_path: Path | None = None,
    ):
        self._hitl = hitl_manager or get_hitl_manager()
        self._storage_path = storage_path or Path("data/hitl/workflow")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Configuration
        self._reviewers: dict[str, ReviewerProfile] = {}
        self._escalation_rules: list[EscalationRule] = []
        self._sla_configs: dict[HITLMode, SLAConfig] = {}

        # PERFORMANCE: Use bounded deque instead of unbounded list
        # Prevents memory exhaustion under high load
        self._notifications: deque[Notification] = deque(maxlen=MAX_NOTIFICATIONS_IN_MEMORY)
        # Index for O(1) lookup by recipient
        self._notifications_by_recipient: defaultdict[str, list[Notification]] = defaultdict(list)
        self._notification_handlers: list[Callable[[Notification], None]] = []
        self._last_notification_cleanup = datetime.now(timezone.utc)

        # Load configuration
        self._load_config()

        # Set up default SLAs
        self._setup_default_slas()

    def _load_config(self) -> None:
        """Load workflow configuration from storage."""
        # Load reviewers
        reviewers_path = self._storage_path / "reviewers.json"
        if reviewers_path.exists():
            try:
                data = json.loads(reviewers_path.read_text())
                for rid, rdata in data.items():
                    self._reviewers[rid] = ReviewerProfile(**rdata)
            except Exception:
                pass

        # Load escalation rules
        rules_path = self._storage_path / "escalation_rules.json"
        if rules_path.exists():
            try:
                data = json.loads(rules_path.read_text())
                for rule_data in data:
                    self._escalation_rules.append(EscalationRule(
                        from_level=EscalationLevel(rule_data["from_level"]),
                        to_level=EscalationLevel(rule_data["to_level"]),
                        trigger_after_minutes=rule_data["trigger_after_minutes"],
                        notify_on_escalation=rule_data.get("notify_on_escalation", True),
                        conditions=rule_data.get("conditions", {}),
                    ))
            except Exception:
                pass

    def _save_config(self) -> None:
        """Save workflow configuration."""
        # Save reviewers
        reviewers_path = self._storage_path / "reviewers.json"
        data = {rid: {
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
            "avg_review_time_minutes": r.avg_review_time_minutes,
        } for rid, r in self._reviewers.items()}
        reviewers_path.write_text(json.dumps(data, indent=2))

    def _setup_default_slas(self) -> None:
        """Set up default SLA configurations."""
        self._sla_configs = {
            HITLMode.DRAFT: SLAConfig(
                mode=HITLMode.DRAFT,
                warning_minutes=60,  # 1 hour warning
                breach_minutes=240,  # 4 hour breach
            ),
            HITLMode.EXECUTE: SLAConfig(
                mode=HITLMode.EXECUTE,
                warning_minutes=120,  # 2 hour warning
                breach_minutes=480,  # 8 hour breach
            ),
            HITLMode.ESCALATE: SLAConfig(
                mode=HITLMode.ESCALATE,
                warning_minutes=15,  # 15 min warning
                breach_minutes=60,  # 1 hour breach
            ),
        }

    # =========================================================================
    # Reviewer Management
    # =========================================================================

    def register_reviewer(self, profile: ReviewerProfile) -> None:
        """Register a reviewer."""
        self._reviewers[profile.reviewer_id] = profile
        self._save_config()

    def get_reviewer(self, reviewer_id: str) -> ReviewerProfile | None:
        """Get a reviewer profile."""
        return self._reviewers.get(reviewer_id)

    def list_reviewers(
        self,
        level: EscalationLevel | None = None,
        department: str | None = None,
        active_only: bool = True,
    ) -> list[ReviewerProfile]:
        """List reviewers with optional filters."""
        results = []
        for reviewer in self._reviewers.values():
            if active_only and not reviewer.active:
                continue
            if level and reviewer.level != level:
                continue
            if department and department not in reviewer.departments:
                continue
            results.append(reviewer)
        return results

    def find_available_reviewer(
        self,
        department: str | None = None,
        domain: str | None = None,
        level: EscalationLevel = EscalationLevel.L1_SUPERVISOR,
    ) -> ReviewerProfile | None:
        """Find an available reviewer for assignment.

        Uses workload balancing to distribute work evenly.
        """
        candidates = self.list_reviewers(level=level, department=department)

        # Filter by domain if specified
        if domain:
            candidates = [c for c in candidates if domain in c.domains or not c.domains]

        # Filter by capacity
        candidates = [c for c in candidates if c.current_load < c.max_concurrent_reviews]

        if not candidates:
            return None

        # Sort by current load (least loaded first)
        candidates.sort(key=lambda c: c.current_load)

        return candidates[0]

    def update_reviewer_load(self, reviewer_id: str, delta: int) -> None:
        """Update a reviewer's current load."""
        reviewer = self._reviewers.get(reviewer_id)
        if reviewer:
            reviewer.current_load = max(0, reviewer.current_load + delta)
            self._save_config()

    # =========================================================================
    # Auto-Assignment
    # =========================================================================

    def auto_assign(self, approval_id: str) -> ReviewerProfile | None:
        """Automatically assign a reviewer to an approval.

        Returns the assigned reviewer or None if no suitable reviewer found.
        """
        approval = self._hitl.get_approval_request(approval_id)
        if not approval or approval.assigned_to:
            return None

        # Find appropriate reviewer
        reviewer = self.find_available_reviewer(
            department=approval.user_department,
            domain=approval.agent_id,
        )

        if reviewer:
            self._hitl.assign_request(approval_id, reviewer.reviewer_id)
            self.update_reviewer_load(reviewer.reviewer_id, 1)

            # Send notification
            self._send_notification(
                type=NotificationType.APPROVAL_ASSIGNED,
                recipient_id=reviewer.reviewer_id,
                title="New Approval Assigned",
                message=f"You have been assigned to review: {approval.original_query[:100]}",
                approval_id=approval_id,
            )

            return reviewer

        return None

    def auto_assign_all_pending(self) -> dict[str, str]:
        """Auto-assign all unassigned pending approvals.

        Returns dict mapping approval_id to assigned reviewer_id.
        """
        pending = self._hitl.list_pending_approvals()
        unassigned = [a for a in pending if not a.assigned_to]

        assignments = {}
        for approval in unassigned:
            reviewer = self.auto_assign(approval.id)
            if reviewer:
                assignments[approval.id] = reviewer.reviewer_id

        return assignments

    # =========================================================================
    # SLA Monitoring
    # =========================================================================

    def check_sla_status(self) -> list[dict[str, Any]]:
        """Check SLA status for all pending approvals.

        Returns list of approvals with SLA issues.
        """
        now = datetime.utcnow()
        issues = []

        pending = self._hitl.list_pending_approvals()

        for approval in pending:
            sla = self._sla_configs.get(approval.hitl_mode)
            if not sla:
                continue

            created = datetime.fromisoformat(approval.created_at)
            age_minutes = (now - created).total_seconds() / 60

            status = "ok"
            if age_minutes >= sla.breach_minutes:
                status = "breach"
            elif age_minutes >= sla.warning_minutes:
                status = "warning"

            if status != "ok":
                issues.append({
                    "approval_id": approval.id,
                    "status": status,
                    "age_minutes": round(age_minutes, 1),
                    "sla_breach_minutes": sla.breach_minutes,
                    "sla_warning_minutes": sla.warning_minutes,
                    "hitl_mode": approval.hitl_mode.value,
                    "assigned_to": approval.assigned_to,
                    "priority": approval.priority,
                })

        return issues

    def process_sla_violations(self) -> list[str]:
        """Process SLA violations and trigger escalations.

        Returns list of escalated approval IDs.
        """
        issues = self.check_sla_status()
        escalated = []

        for issue in issues:
            if issue["status"] == "breach":
                sla = self._sla_configs.get(HITLMode(issue["hitl_mode"]))
                if sla and sla.escalate_on_breach:
                    self.escalate(issue["approval_id"], f"SLA breach: {issue['age_minutes']} minutes")
                    escalated.append(issue["approval_id"])

                # Notify about breach
                self._send_notification(
                    type=NotificationType.SLA_BREACH,
                    recipient_id=issue.get("assigned_to") or "system",
                    title="SLA Breach Alert",
                    message=f"Approval {issue['approval_id']} has breached SLA ({issue['age_minutes']} minutes)",
                    approval_id=issue["approval_id"],
                    metadata=issue,
                )

            elif issue["status"] == "warning":
                # Send warning notification
                self._send_notification(
                    type=NotificationType.SLA_WARNING,
                    recipient_id=issue.get("assigned_to") or "system",
                    title="SLA Warning",
                    message=f"Approval {issue['approval_id']} approaching SLA breach",
                    approval_id=issue["approval_id"],
                    metadata=issue,
                )

        return escalated

    # =========================================================================
    # Escalation
    # =========================================================================

    def escalate(
        self,
        approval_id: str,
        reason: str,
    ) -> bool:
        """Escalate an approval to the next level.

        Returns True if escalation was successful.
        """
        approval = self._hitl.get_approval_request(approval_id)
        if not approval or approval.status != ApprovalStatus.PENDING:
            return False

        # Determine current level
        current_reviewer = self._reviewers.get(approval.assigned_to or "")
        current_level = current_reviewer.level if current_reviewer else EscalationLevel.L1_SUPERVISOR

        # Find applicable escalation rule
        rule = None
        for r in self._escalation_rules:
            if r.from_level == current_level:
                rule = r
                break

        if not rule:
            # Default escalation path
            level_order = list(EscalationLevel)
            try:
                current_idx = level_order.index(current_level)
                if current_idx < len(level_order) - 1:
                    next_level = level_order[current_idx + 1]
                else:
                    return False  # Already at highest level
            except ValueError:
                next_level = EscalationLevel.L2_MANAGER
        else:
            next_level = rule.to_level

        # Find reviewer at next level
        new_reviewer = self.find_available_reviewer(
            department=approval.user_department,
            level=next_level,
        )

        if not new_reviewer:
            return False

        # Update assignment
        if approval.assigned_to:
            self.update_reviewer_load(approval.assigned_to, -1)

        self._hitl.assign_request(approval_id, new_reviewer.reviewer_id)
        self.update_reviewer_load(new_reviewer.reviewer_id, 1)

        # Update approval context with escalation info
        approval.context["escalation_history"] = approval.context.get("escalation_history", [])
        approval.context["escalation_history"].append({
            "from_reviewer": approval.assigned_to,
            "to_reviewer": new_reviewer.reviewer_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "from_level": current_level.value,
            "to_level": next_level.value,
        })
        self._hitl._save_approvals()

        # Send notifications
        self._send_notification(
            type=NotificationType.ESCALATION_TRIGGERED,
            recipient_id=new_reviewer.reviewer_id,
            title="Escalated Approval",
            message=f"Escalated from {current_level.value}: {reason}",
            approval_id=approval_id,
        )

        if approval.assigned_to:
            self._send_notification(
                type=NotificationType.ESCALATION_TRIGGERED,
                recipient_id=approval.assigned_to,
                title="Approval Escalated",
                message=f"Your assigned approval has been escalated: {reason}",
                approval_id=approval_id,
            )

        return True

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def batch_approve(
        self,
        approval_ids: list[str],
        reviewer_id: str,
        notes: str | None = None,
    ) -> dict[str, bool]:
        """Approve multiple requests at once.

        Returns dict mapping approval_id to success status.
        """
        results = {}
        for approval_id in approval_ids:
            approval = self._hitl.approve_request(
                request_id=approval_id,
                reviewer_id=reviewer_id,
                notes=notes,
            )
            results[approval_id] = approval is not None

            if approval:
                self.update_reviewer_load(reviewer_id, -1)
                self._send_notification(
                    type=NotificationType.APPROVAL_APPROVED,
                    recipient_id=approval.user_id,
                    title="Request Approved",
                    message=f"Your request has been approved",
                    approval_id=approval_id,
                )

        return results

    def batch_reject(
        self,
        approval_ids: list[str],
        reviewer_id: str,
        reason: str,
    ) -> dict[str, bool]:
        """Reject multiple requests at once."""
        results = {}
        for approval_id in approval_ids:
            approval = self._hitl.reject_request(
                request_id=approval_id,
                reviewer_id=reviewer_id,
                reason=reason,
            )
            results[approval_id] = approval is not None

            if approval:
                self.update_reviewer_load(reviewer_id, -1)
                self._send_notification(
                    type=NotificationType.APPROVAL_REJECTED,
                    recipient_id=approval.user_id,
                    title="Request Rejected",
                    message=f"Your request was not approved: {reason}",
                    approval_id=approval_id,
                )

        return results

    # =========================================================================
    # Notifications
    # =========================================================================

    def register_notification_handler(
        self,
        handler: Callable[[Notification], None],
    ) -> None:
        """Register a notification handler."""
        self._notification_handlers.append(handler)

    def _cleanup_old_notifications(self) -> None:
        """Periodically clean up old notifications from recipient index.

        PERFORMANCE: The deque auto-limits total count, but we need to
        sync the recipient index to avoid stale references.
        """
        now = datetime.now(timezone.utc)
        if (now - self._last_notification_cleanup).total_seconds() < NOTIFICATION_CLEANUP_INTERVAL_SECONDS:
            return

        # Get IDs still in deque
        valid_ids = {n.id for n in self._notifications}

        # Clean up recipient index
        for recipient_id in list(self._notifications_by_recipient.keys()):
            self._notifications_by_recipient[recipient_id] = [
                n for n in self._notifications_by_recipient[recipient_id]
                if n.id in valid_ids
            ]
            # Remove empty lists
            if not self._notifications_by_recipient[recipient_id]:
                del self._notifications_by_recipient[recipient_id]

        self._last_notification_cleanup = now

    def _send_notification(
        self,
        type: NotificationType,
        recipient_id: str,
        title: str,
        message: str,
        approval_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification."""
        import uuid

        notification = Notification(
            id=str(uuid.uuid4()),
            type=type,
            recipient_id=recipient_id,
            title=title,
            message=message,
            approval_id=approval_id,
            metadata=metadata or {},
        )

        # Add to bounded deque (auto-removes oldest when full)
        self._notifications.append(notification)

        # Add to recipient index for O(1) lookup
        self._notifications_by_recipient[recipient_id].append(notification)

        # Periodic cleanup of stale index entries
        self._cleanup_old_notifications()

        # Call handlers
        for handler in self._notification_handlers:
            try:
                handler(notification)
            except Exception:
                pass

        return notification

    def get_notifications(
        self,
        recipient_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a recipient.

        PERFORMANCE: Uses recipient index for O(1) lookup instead of O(n) scan.
        """
        # Use indexed lookup instead of scanning all notifications
        results = self._notifications_by_recipient.get(recipient_id, [])

        if unread_only:
            results = [n for n in results if not n.read]

        return results[-limit:]

    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for notification in self._notifications:
            if notification.id == notification_id:
                notification.read = True
                notification.read_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_workflow_stats(
        self,
        days: int = 30,
    ) -> WorkflowStats:
        """Get comprehensive workflow statistics."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        # Get all approvals in period
        all_approvals = list(self._hitl._approvals.values())
        period_approvals = [a for a in all_approvals if a.created_at >= cutoff_iso]

        # Count by status
        approved = len([a for a in period_approvals if a.status == ApprovalStatus.APPROVED])
        rejected = len([a for a in period_approvals if a.status == ApprovalStatus.REJECTED])
        expired = len([a for a in period_approvals if a.status == ApprovalStatus.EXPIRED])
        cancelled = len([a for a in period_approvals if a.status == ApprovalStatus.CANCELLED])

        # Calculate average resolution time
        resolved = [
            a for a in period_approvals
            if a.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}
            and a.resolved_at
        ]
        avg_time = 0.0
        if resolved:
            times = []
            for a in resolved:
                try:
                    created = datetime.fromisoformat(a.created_at)
                    resolved_dt = datetime.fromisoformat(a.resolved_at)
                    times.append((resolved_dt - created).total_seconds() / 60)
                except Exception:
                    pass
            if times:
                avg_time = sum(times) / len(times)

        # SLA compliance
        sla_compliant = 0
        for a in resolved:
            sla = self._sla_configs.get(a.hitl_mode)
            if sla:
                try:
                    created = datetime.fromisoformat(a.created_at)
                    resolved_dt = datetime.fromisoformat(a.resolved_at)
                    resolution_minutes = (resolved_dt - created).total_seconds() / 60
                    if resolution_minutes <= sla.breach_minutes:
                        sla_compliant += 1
                except Exception:
                    pass
        sla_compliance = (sla_compliant / len(resolved) * 100) if resolved else 100.0

        # Count escalations
        escalations = 0
        for a in period_approvals:
            if a.context.get("escalation_history"):
                escalations += len(a.context["escalation_history"])

        # By mode
        by_mode: dict[str, dict[str, int]] = {}
        for a in period_approvals:
            mode = a.hitl_mode.value
            if mode not in by_mode:
                by_mode[mode] = {"total": 0, "approved": 0, "rejected": 0}
            by_mode[mode]["total"] += 1
            if a.status == ApprovalStatus.APPROVED:
                by_mode[mode]["approved"] += 1
            elif a.status == ApprovalStatus.REJECTED:
                by_mode[mode]["rejected"] += 1

        # By department
        by_department: dict[str, dict[str, int]] = {}
        for a in period_approvals:
            dept = a.user_department
            if dept not in by_department:
                by_department[dept] = {"total": 0, "approved": 0, "rejected": 0}
            by_department[dept]["total"] += 1
            if a.status == ApprovalStatus.APPROVED:
                by_department[dept]["approved"] += 1
            elif a.status == ApprovalStatus.REJECTED:
                by_department[dept]["rejected"] += 1

        # By reviewer
        by_reviewer: dict[str, dict[str, int]] = {}
        for a in resolved:
            reviewer = a.resolved_by or "unknown"
            if reviewer not in by_reviewer:
                by_reviewer[reviewer] = {"total": 0, "approved": 0, "rejected": 0}
            by_reviewer[reviewer]["total"] += 1
            if a.status == ApprovalStatus.APPROVED:
                by_reviewer[reviewer]["approved"] += 1
            elif a.status == ApprovalStatus.REJECTED:
                by_reviewer[reviewer]["rejected"] += 1

        # Busiest hours
        hour_counts: dict[int, int] = {}
        for a in period_approvals:
            try:
                hour = datetime.fromisoformat(a.created_at).hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except Exception:
                pass
        busiest = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)[:5]

        # Top agents by volume
        agent_counts: dict[str, int] = {}
        for a in period_approvals:
            agent_counts[a.agent_id] = agent_counts.get(a.agent_id, 0) + 1
        top_agents = [
            {"agent_id": aid, "count": count}
            for aid, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return WorkflowStats(
            period_start=cutoff_iso,
            period_end=datetime.utcnow().isoformat(),
            total_requests=len(period_approvals),
            approved=approved,
            rejected=rejected,
            expired=expired,
            cancelled=cancelled,
            avg_resolution_time_minutes=round(avg_time, 1),
            sla_compliance_percentage=round(sla_compliance, 1),
            escalations=escalations,
            by_mode=by_mode,
            by_department=by_department,
            by_reviewer=by_reviewer,
            busiest_hours=busiest,
            top_agents_by_volume=top_agents,
        )


# Singleton
_workflow_manager: HITLWorkflowManager | None = None


def get_hitl_workflow_manager() -> HITLWorkflowManager:
    """Get the HITL workflow manager singleton."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = HITLWorkflowManager()
    return _workflow_manager
