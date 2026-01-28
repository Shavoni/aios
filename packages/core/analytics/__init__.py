"""Analytics module for tracking queries, costs, and performance metrics."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class QueryEvent(BaseModel):
    """A single query event for analytics."""

    id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: str = "anonymous"
    department: str = "General"
    agent_id: str
    agent_name: str
    query_text: str
    response_text: str = ""
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
    feedback_rating: int | None = None  # 1-5 stars
    feedback_text: str | None = None
    session_id: str | None = None
    routed_from: str | None = None  # For multi-agent routing


class DailyMetrics(BaseModel):
    """Aggregated metrics for a single day."""

    date: str
    total_queries: int = 0
    unique_users: int = 0
    queries_by_agent: dict[str, int] = Field(default_factory=dict)
    queries_by_department: dict[str, int] = Field(default_factory=dict)
    queries_by_hour: dict[int, int] = Field(default_factory=dict)
    escalation_count: int = 0
    approval_count: int = 0
    guardrail_triggers: int = 0
    total_latency_ms: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    success_count: int = 0
    error_count: int = 0
    avg_rating: float | None = None
    rating_count: int = 0


class AnalyticsSummary(BaseModel):
    """Summary analytics for dashboard display."""

    # Overall stats
    total_queries: int = 0
    total_queries_30d: int = 0
    total_queries_7d: int = 0
    total_queries_today: int = 0

    # User stats
    unique_users_30d: int = 0
    unique_users_7d: int = 0
    unique_users_today: int = 0

    # Performance
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    success_rate: float = 100.0

    # Governance
    escalation_rate: float = 0.0
    approval_rate: float = 0.0
    guardrails_enforced: int = 0

    # Cost
    total_cost_30d: float = 0.0
    total_cost_7d: float = 0.0
    avg_cost_per_query: float = 0.0
    estimated_savings: float = 0.0  # vs manual processing

    # Tokens
    total_tokens_30d: int = 0
    avg_tokens_per_query: float = 0.0

    # Agent breakdown
    queries_by_agent: dict[str, int] = Field(default_factory=dict)
    queries_by_department: dict[str, int] = Field(default_factory=dict)

    # Time series (last 30 days)
    daily_queries: list[dict[str, Any]] = Field(default_factory=list)
    hourly_distribution: dict[int, int] = Field(default_factory=dict)

    # Top items
    top_agents: list[dict[str, Any]] = Field(default_factory=list)
    top_departments: list[dict[str, Any]] = Field(default_factory=list)
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsManager:
    """Manages analytics collection and aggregation."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "analytics"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Events storage
        self._events_path = self.storage_path / "events.json"
        self._events: list[QueryEvent] = []
        self._load_events()

        # Daily metrics cache
        self._daily_path = self.storage_path / "daily_metrics.json"
        self._daily_metrics: dict[str, DailyMetrics] = {}
        self._load_daily_metrics()

    def _load_events(self) -> None:
        """Load events from storage."""
        if self._events_path.exists():
            try:
                with open(self._events_path) as f:
                    data = json.load(f)
                    self._events = [QueryEvent(**e) for e in data.get("events", [])]
            except Exception:
                self._events = []

    def _save_events(self) -> None:
        """Save events to storage."""
        # Keep only last 90 days of events
        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
        self._events = [e for e in self._events if e.timestamp > cutoff]

        data = {"events": [e.model_dump() for e in self._events]}
        with open(self._events_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_daily_metrics(self) -> None:
        """Load daily metrics from storage."""
        if self._daily_path.exists():
            try:
                with open(self._daily_path) as f:
                    data = json.load(f)
                    for date_str, metrics in data.items():
                        self._daily_metrics[date_str] = DailyMetrics(**metrics)
            except Exception:
                self._daily_metrics = {}

    def _save_daily_metrics(self) -> None:
        """Save daily metrics to storage."""
        data = {k: v.model_dump() for k, v in self._daily_metrics.items()}
        with open(self._daily_path, "w") as f:
            json.dump(data, f, indent=2)

    def record_query(self, event: QueryEvent) -> None:
        """Record a query event."""
        self._events.append(event)
        self._update_daily_metrics(event)
        self._save_events()
        self._save_daily_metrics()

    def _update_daily_metrics(self, event: QueryEvent) -> None:
        """Update daily metrics with a new event."""
        date_str = event.timestamp[:10]  # YYYY-MM-DD

        if date_str not in self._daily_metrics:
            self._daily_metrics[date_str] = DailyMetrics(date=date_str)

        metrics = self._daily_metrics[date_str]
        metrics.total_queries += 1

        # Agent breakdown
        if event.agent_id not in metrics.queries_by_agent:
            metrics.queries_by_agent[event.agent_id] = 0
        metrics.queries_by_agent[event.agent_id] += 1

        # Department breakdown
        if event.department not in metrics.queries_by_department:
            metrics.queries_by_department[event.department] = 0
        metrics.queries_by_department[event.department] += 1

        # Hour breakdown
        try:
            hour = int(event.timestamp[11:13])
            if hour not in metrics.queries_by_hour:
                metrics.queries_by_hour[hour] = 0
            metrics.queries_by_hour[hour] += 1
        except (ValueError, IndexError):
            pass

        # Escalations and approvals
        if event.was_escalated:
            metrics.escalation_count += 1
        if event.was_approved:
            metrics.approval_count += 1

        # Guardrails
        if event.guardrails_triggered:
            metrics.guardrail_triggers += len(event.guardrails_triggered)

        # Performance
        metrics.total_latency_ms += event.latency_ms
        metrics.total_tokens_in += event.tokens_in
        metrics.total_tokens_out += event.tokens_out
        metrics.total_cost_usd += event.cost_usd

        # Success/error
        if event.success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1

        # Ratings
        if event.feedback_rating is not None:
            if metrics.avg_rating is None:
                metrics.avg_rating = event.feedback_rating
            else:
                total_rating = metrics.avg_rating * metrics.rating_count + event.feedback_rating
                metrics.rating_count += 1
                metrics.avg_rating = total_rating / metrics.rating_count

    def get_summary(self, days: int = 30) -> AnalyticsSummary:
        """Get analytics summary for the specified period."""
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        cutoff_30d = (now - timedelta(days=30)).isoformat()
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        cutoff_today = now.strftime("%Y-%m-%d")

        summary = AnalyticsSummary()

        # Collect events for different periods
        events_30d = [e for e in self._events if e.timestamp >= cutoff_30d]
        events_7d = [e for e in self._events if e.timestamp >= cutoff_7d]
        events_today = [e for e in self._events if e.timestamp.startswith(cutoff_today)]

        # Total queries
        summary.total_queries = len(self._events)
        summary.total_queries_30d = len(events_30d)
        summary.total_queries_7d = len(events_7d)
        summary.total_queries_today = len(events_today)

        # Unique users
        summary.unique_users_30d = len(set(e.user_id for e in events_30d))
        summary.unique_users_7d = len(set(e.user_id for e in events_7d))
        summary.unique_users_today = len(set(e.user_id for e in events_today))

        # Performance metrics
        if events_30d:
            latencies = [e.latency_ms for e in events_30d if e.latency_ms > 0]
            if latencies:
                summary.avg_latency_ms = sum(latencies) / len(latencies)
                sorted_lat = sorted(latencies)
                p95_idx = int(len(sorted_lat) * 0.95)
                summary.p95_latency_ms = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

            success_count = sum(1 for e in events_30d if e.success)
            summary.success_rate = (success_count / len(events_30d)) * 100 if events_30d else 100.0

        # Governance metrics
        if events_30d:
            escalated = sum(1 for e in events_30d if e.was_escalated)
            summary.escalation_rate = (escalated / len(events_30d)) * 100

            approved = sum(1 for e in events_30d if e.was_approved)
            summary.approval_rate = (approved / len(events_30d)) * 100

            summary.guardrails_enforced = sum(len(e.guardrails_triggered) for e in events_30d)

        # Cost metrics
        summary.total_cost_30d = sum(e.cost_usd for e in events_30d)
        summary.total_cost_7d = sum(e.cost_usd for e in events_7d)
        if events_30d:
            summary.avg_cost_per_query = summary.total_cost_30d / len(events_30d)

        # Estimated savings (assuming $15/hr manual processing, 5 min per query)
        manual_cost_per_query = (15 / 60) * 5  # $1.25 per query manually
        summary.estimated_savings = (manual_cost_per_query - summary.avg_cost_per_query) * len(events_30d)

        # Token metrics
        summary.total_tokens_30d = sum(e.tokens_in + e.tokens_out for e in events_30d)
        if events_30d:
            summary.avg_tokens_per_query = summary.total_tokens_30d / len(events_30d)

        # Agent breakdown
        agent_counts: dict[str, int] = defaultdict(int)
        for e in events_30d:
            agent_counts[e.agent_id] += 1
        summary.queries_by_agent = dict(agent_counts)

        # Department breakdown
        dept_counts: dict[str, int] = defaultdict(int)
        for e in events_30d:
            dept_counts[e.department] += 1
        summary.queries_by_department = dict(dept_counts)

        # Daily time series
        daily_data: dict[str, int] = defaultdict(int)
        for e in events_30d:
            date = e.timestamp[:10]
            daily_data[date] += 1

        # Fill in missing days
        for i in range(30):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            if date not in daily_data:
                daily_data[date] = 0

        summary.daily_queries = [
            {"date": k, "queries": v}
            for k, v in sorted(daily_data.items())
        ]

        # Hourly distribution
        hourly: dict[int, int] = defaultdict(int)
        for e in events_30d:
            try:
                hour = int(e.timestamp[11:13])
                hourly[hour] += 1
            except (ValueError, IndexError):
                pass
        summary.hourly_distribution = dict(hourly)

        # Top agents
        summary.top_agents = [
            {"agent_id": k, "queries": v}
            for k, v in sorted(agent_counts.items(), key=lambda x: -x[1])[:10]
        ]

        # Top departments
        summary.top_departments = [
            {"department": k, "queries": v}
            for k, v in sorted(dept_counts.items(), key=lambda x: -x[1])[:10]
        ]

        # Recent errors
        errors = [e for e in events_30d if not e.success][-10:]
        summary.recent_errors = [
            {
                "timestamp": e.timestamp,
                "agent_id": e.agent_id,
                "error": e.error_message,
                "query": e.query_text[:100],
            }
            for e in errors
        ]

        return summary

    def get_agent_metrics(self, agent_id: str, days: int = 30) -> dict[str, Any]:
        """Get metrics for a specific agent."""
        now = datetime.utcnow()
        cutoff = (now - timedelta(days=days)).isoformat()

        events = [e for e in self._events if e.timestamp >= cutoff and e.agent_id == agent_id]

        if not events:
            return {
                "agent_id": agent_id,
                "total_queries": 0,
                "avg_latency_ms": 0,
                "success_rate": 100.0,
                "escalation_rate": 0.0,
                "total_cost": 0.0,
            }

        latencies = [e.latency_ms for e in events if e.latency_ms > 0]

        return {
            "agent_id": agent_id,
            "total_queries": len(events),
            "unique_users": len(set(e.user_id for e in events)),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "success_rate": (sum(1 for e in events if e.success) / len(events)) * 100,
            "escalation_rate": (sum(1 for e in events if e.was_escalated) / len(events)) * 100,
            "total_cost": sum(e.cost_usd for e in events),
            "total_tokens": sum(e.tokens_in + e.tokens_out for e in events),
            "avg_rating": sum(e.feedback_rating for e in events if e.feedback_rating) / len([e for e in events if e.feedback_rating]) if any(e.feedback_rating for e in events) else None,
        }

    def add_feedback(self, event_id: str, rating: int, text: str | None = None) -> bool:
        """Add feedback to an existing event."""
        for event in self._events:
            if event.id == event_id:
                event.feedback_rating = rating
                event.feedback_text = text
                self._save_events()
                return True
        return False

    def get_events(
        self,
        agent_id: str | None = None,
        user_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QueryEvent]:
        """Get filtered events."""
        events = self._events

        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]

        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        return events[offset:offset + limit]


# Singleton instance
_analytics_manager: AnalyticsManager | None = None


def get_analytics_manager() -> AnalyticsManager:
    """Get the analytics manager singleton."""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager


__all__ = [
    "QueryEvent",
    "DailyMetrics",
    "AnalyticsSummary",
    "AnalyticsManager",
    "get_analytics_manager",
]
