"""Rate limiting and quota management."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    tokens_per_day: int = 1000000
    cost_limit_per_day: float = 100.0  # USD


class UserQuota(BaseModel):
    """User quota tracking."""

    user_id: str
    department: str = "General"

    # Current usage
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    requests_this_day: int = 0
    tokens_this_day: int = 0
    cost_this_day: float = 0.0

    # Timestamps for window tracking
    minute_window_start: float = Field(default_factory=time.time)
    hour_window_start: float = Field(default_factory=time.time)
    day_window_start: float = Field(default_factory=time.time)

    # Custom limits (if different from defaults)
    custom_limits: RateLimitConfig | None = None


class DepartmentQuota(BaseModel):
    """Department-level quota tracking."""

    department: str
    requests_this_day: int = 0
    tokens_this_day: int = 0
    cost_this_day: float = 0.0
    day_window_start: float = Field(default_factory=time.time)

    # Department limits
    daily_request_limit: int = 50000
    daily_token_limit: int = 5000000
    daily_cost_limit: float = 500.0


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""

    allowed: bool
    reason: str | None = None
    retry_after_seconds: int | None = None
    current_usage: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)


class QuotaUsageReport(BaseModel):
    """Usage report for quotas."""

    user_id: str | None = None
    department: str | None = None
    period: str = "day"
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    limit_requests: int = 0
    limit_tokens: int = 0
    limit_cost: float = 0.0
    usage_percent_requests: float = 0.0
    usage_percent_tokens: float = 0.0
    usage_percent_cost: float = 0.0


class RateLimitManager:
    """Manages rate limiting and quotas."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "ratelimit"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Default limits
        self.default_limits = RateLimitConfig()

        # User quotas
        self._users_path = self.storage_path / "user_quotas.json"
        self._user_quotas: dict[str, UserQuota] = {}
        self._load_user_quotas()

        # Department quotas
        self._depts_path = self.storage_path / "dept_quotas.json"
        self._dept_quotas: dict[str, DepartmentQuota] = {}
        self._load_dept_quotas()

        # Config
        self._config_path = self.storage_path / "config.json"
        self._load_config()

    def _load_user_quotas(self) -> None:
        """Load user quotas from storage."""
        if self._users_path.exists():
            try:
                with open(self._users_path) as f:
                    data = json.load(f)
                    for user_id, quota_data in data.items():
                        self._user_quotas[user_id] = UserQuota(**quota_data)
            except Exception:
                self._user_quotas = {}

    def _save_user_quotas(self) -> None:
        """Save user quotas to storage."""
        data = {k: v.model_dump() for k, v in self._user_quotas.items()}
        with open(self._users_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_dept_quotas(self) -> None:
        """Load department quotas from storage."""
        if self._depts_path.exists():
            try:
                with open(self._depts_path) as f:
                    data = json.load(f)
                    for dept, quota_data in data.items():
                        self._dept_quotas[dept] = DepartmentQuota(**quota_data)
            except Exception:
                self._dept_quotas = {}

    def _save_dept_quotas(self) -> None:
        """Save department quotas to storage."""
        data = {k: v.model_dump() for k, v in self._dept_quotas.items()}
        with open(self._depts_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_config(self) -> None:
        """Load rate limit config."""
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    data = json.load(f)
                    self.default_limits = RateLimitConfig(**data.get("default_limits", {}))
            except Exception:
                pass

    def _save_config(self) -> None:
        """Save rate limit config."""
        data = {"default_limits": self.default_limits.model_dump()}
        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

    def _get_user_quota(self, user_id: str, department: str = "General") -> UserQuota:
        """Get or create user quota."""
        if user_id not in self._user_quotas:
            self._user_quotas[user_id] = UserQuota(user_id=user_id, department=department)
        return self._user_quotas[user_id]

    def _get_dept_quota(self, department: str) -> DepartmentQuota:
        """Get or create department quota."""
        if department not in self._dept_quotas:
            self._dept_quotas[department] = DepartmentQuota(department=department)
        return self._dept_quotas[department]

    def _reset_windows(self, quota: UserQuota) -> None:
        """Reset time windows if needed."""
        now = time.time()

        # Minute window (60 seconds)
        if now - quota.minute_window_start >= 60:
            quota.requests_this_minute = 0
            quota.minute_window_start = now

        # Hour window (3600 seconds)
        if now - quota.hour_window_start >= 3600:
            quota.requests_this_hour = 0
            quota.hour_window_start = now

        # Day window (86400 seconds)
        if now - quota.day_window_start >= 86400:
            quota.requests_this_day = 0
            quota.tokens_this_day = 0
            quota.cost_this_day = 0.0
            quota.day_window_start = now

    def _reset_dept_window(self, quota: DepartmentQuota) -> None:
        """Reset department day window if needed."""
        now = time.time()
        if now - quota.day_window_start >= 86400:
            quota.requests_this_day = 0
            quota.tokens_this_day = 0
            quota.cost_this_day = 0.0
            quota.day_window_start = now

    # =========================================================================
    # Rate Limit Checks
    # =========================================================================

    def check_rate_limit(
        self,
        user_id: str,
        department: str = "General",
    ) -> RateLimitResult:
        """Check if a request is allowed under rate limits."""
        quota = self._get_user_quota(user_id, department)
        self._reset_windows(quota)

        limits = quota.custom_limits or self.default_limits

        # Check minute limit
        if quota.requests_this_minute >= limits.requests_per_minute:
            retry_after = int(60 - (time.time() - quota.minute_window_start))
            return RateLimitResult(
                allowed=False,
                reason="Rate limit exceeded (per minute)",
                retry_after_seconds=max(1, retry_after),
                current_usage={"requests_this_minute": quota.requests_this_minute},
                limits={"requests_per_minute": limits.requests_per_minute},
            )

        # Check hour limit
        if quota.requests_this_hour >= limits.requests_per_hour:
            retry_after = int(3600 - (time.time() - quota.hour_window_start))
            return RateLimitResult(
                allowed=False,
                reason="Rate limit exceeded (per hour)",
                retry_after_seconds=max(1, retry_after),
                current_usage={"requests_this_hour": quota.requests_this_hour},
                limits={"requests_per_hour": limits.requests_per_hour},
            )

        # Check day limit
        if quota.requests_this_day >= limits.requests_per_day:
            retry_after = int(86400 - (time.time() - quota.day_window_start))
            return RateLimitResult(
                allowed=False,
                reason="Daily request limit exceeded",
                retry_after_seconds=max(1, retry_after),
                current_usage={"requests_this_day": quota.requests_this_day},
                limits={"requests_per_day": limits.requests_per_day},
            )

        # Check token limit
        if quota.tokens_this_day >= limits.tokens_per_day:
            return RateLimitResult(
                allowed=False,
                reason="Daily token limit exceeded",
                current_usage={"tokens_this_day": quota.tokens_this_day},
                limits={"tokens_per_day": limits.tokens_per_day},
            )

        # Check cost limit
        if quota.cost_this_day >= limits.cost_limit_per_day:
            return RateLimitResult(
                allowed=False,
                reason="Daily cost limit exceeded",
                current_usage={"cost_this_day": quota.cost_this_day},
                limits={"cost_limit_per_day": limits.cost_limit_per_day},
            )

        # Check department limits
        dept_quota = self._get_dept_quota(department)
        self._reset_dept_window(dept_quota)

        if dept_quota.requests_this_day >= dept_quota.daily_request_limit:
            return RateLimitResult(
                allowed=False,
                reason=f"Department '{department}' daily limit exceeded",
                current_usage={"department_requests": dept_quota.requests_this_day},
                limits={"department_daily_limit": dept_quota.daily_request_limit},
            )

        return RateLimitResult(
            allowed=True,
            current_usage={
                "requests_this_minute": quota.requests_this_minute,
                "requests_this_hour": quota.requests_this_hour,
                "requests_this_day": quota.requests_this_day,
                "tokens_this_day": quota.tokens_this_day,
                "cost_this_day": quota.cost_this_day,
            },
            limits={
                "requests_per_minute": limits.requests_per_minute,
                "requests_per_hour": limits.requests_per_hour,
                "requests_per_day": limits.requests_per_day,
                "tokens_per_day": limits.tokens_per_day,
                "cost_limit_per_day": limits.cost_limit_per_day,
            },
        )

    def record_usage(
        self,
        user_id: str,
        department: str = "General",
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record usage after a successful request."""
        quota = self._get_user_quota(user_id, department)
        self._reset_windows(quota)

        quota.requests_this_minute += 1
        quota.requests_this_hour += 1
        quota.requests_this_day += 1
        quota.tokens_this_day += tokens
        quota.cost_this_day += cost

        # Update department
        dept_quota = self._get_dept_quota(department)
        self._reset_dept_window(dept_quota)
        dept_quota.requests_this_day += 1
        dept_quota.tokens_this_day += tokens
        dept_quota.cost_this_day += cost

        self._save_user_quotas()
        self._save_dept_quotas()

    # =========================================================================
    # Quota Management
    # =========================================================================

    def set_user_limits(
        self,
        user_id: str,
        limits: RateLimitConfig,
    ) -> UserQuota:
        """Set custom limits for a user."""
        quota = self._get_user_quota(user_id)
        quota.custom_limits = limits
        self._save_user_quotas()
        return quota

    def set_department_limits(
        self,
        department: str,
        daily_requests: int | None = None,
        daily_tokens: int | None = None,
        daily_cost: float | None = None,
    ) -> DepartmentQuota:
        """Set limits for a department."""
        quota = self._get_dept_quota(department)
        if daily_requests is not None:
            quota.daily_request_limit = daily_requests
        if daily_tokens is not None:
            quota.daily_token_limit = daily_tokens
        if daily_cost is not None:
            quota.daily_cost_limit = daily_cost
        self._save_dept_quotas()
        return quota

    def get_usage_report(
        self,
        user_id: str | None = None,
        department: str | None = None,
    ) -> QuotaUsageReport:
        """Get usage report."""
        if user_id:
            quota = self._get_user_quota(user_id)
            self._reset_windows(quota)
            limits = quota.custom_limits or self.default_limits

            return QuotaUsageReport(
                user_id=user_id,
                department=quota.department,
                period="day",
                total_requests=quota.requests_this_day,
                total_tokens=quota.tokens_this_day,
                total_cost=quota.cost_this_day,
                limit_requests=limits.requests_per_day,
                limit_tokens=limits.tokens_per_day,
                limit_cost=limits.cost_limit_per_day,
                usage_percent_requests=(quota.requests_this_day / limits.requests_per_day) * 100 if limits.requests_per_day else 0,
                usage_percent_tokens=(quota.tokens_this_day / limits.tokens_per_day) * 100 if limits.tokens_per_day else 0,
                usage_percent_cost=(quota.cost_this_day / limits.cost_limit_per_day) * 100 if limits.cost_limit_per_day else 0,
            )

        if department:
            quota = self._get_dept_quota(department)
            self._reset_dept_window(quota)

            return QuotaUsageReport(
                department=department,
                period="day",
                total_requests=quota.requests_this_day,
                total_tokens=quota.tokens_this_day,
                total_cost=quota.cost_this_day,
                limit_requests=quota.daily_request_limit,
                limit_tokens=quota.daily_token_limit,
                limit_cost=quota.daily_cost_limit,
                usage_percent_requests=(quota.requests_this_day / quota.daily_request_limit) * 100 if quota.daily_request_limit else 0,
                usage_percent_tokens=(quota.tokens_this_day / quota.daily_token_limit) * 100 if quota.daily_token_limit else 0,
                usage_percent_cost=(quota.cost_this_day / quota.daily_cost_limit) * 100 if quota.daily_cost_limit else 0,
            )

        return QuotaUsageReport()

    def reset_user_quota(self, user_id: str) -> bool:
        """Reset a user's quota."""
        if user_id in self._user_quotas:
            quota = self._user_quotas[user_id]
            quota.requests_this_minute = 0
            quota.requests_this_hour = 0
            quota.requests_this_day = 0
            quota.tokens_this_day = 0
            quota.cost_this_day = 0.0
            quota.minute_window_start = time.time()
            quota.hour_window_start = time.time()
            quota.day_window_start = time.time()
            self._save_user_quotas()
            return True
        return False


# Singleton instance
_rate_limit_manager: RateLimitManager | None = None


def get_rate_limit_manager() -> RateLimitManager:
    """Get the rate limit manager singleton."""
    global _rate_limit_manager
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    return _rate_limit_manager


__all__ = [
    "RateLimitConfig",
    "UserQuota",
    "DepartmentQuota",
    "RateLimitResult",
    "QuotaUsageReport",
    "RateLimitManager",
    "get_rate_limit_manager",
]
