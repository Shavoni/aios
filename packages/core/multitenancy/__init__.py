"""Multi-tenant support for aiOS.

Provides complete tenant isolation and management:
- Tenant (organization) management
- Per-tenant configuration
- Data isolation
- Resource quotas and rate limiting
- Tenant-scoped governance policies
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class TenantStatus(str, Enum):
    """Tenant status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    ARCHIVED = "archived"


class TenantTier(str, Enum):
    """Tenant subscription tier."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"


@dataclass
class ResourceQuota:
    """Resource quota configuration."""

    # API Limits
    daily_api_calls: int = 1000
    monthly_api_calls: int = 25000
    max_tokens_per_request: int = 8000
    max_requests_per_minute: int = 60

    # Agent Limits
    max_agents: int = 5
    max_active_agents: int = 3
    max_concurrent_queries: int = 10

    # Storage Limits
    max_kb_documents: int = 100
    max_kb_size_mb: int = 50
    max_attachments_mb: int = 10

    # LLM Budget
    daily_llm_budget_usd: float = 10.0
    monthly_llm_budget_usd: float = 200.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "daily_api_calls": self.daily_api_calls,
            "monthly_api_calls": self.monthly_api_calls,
            "max_tokens_per_request": self.max_tokens_per_request,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_agents": self.max_agents,
            "max_active_agents": self.max_active_agents,
            "max_concurrent_queries": self.max_concurrent_queries,
            "max_kb_documents": self.max_kb_documents,
            "max_kb_size_mb": self.max_kb_size_mb,
            "max_attachments_mb": self.max_attachments_mb,
            "daily_llm_budget_usd": self.daily_llm_budget_usd,
            "monthly_llm_budget_usd": self.monthly_llm_budget_usd,
        }


# Tier-based quota defaults
TIER_QUOTAS = {
    TenantTier.FREE: ResourceQuota(
        daily_api_calls=100,
        monthly_api_calls=2000,
        max_tokens_per_request=4000,
        max_requests_per_minute=10,
        max_agents=2,
        max_active_agents=1,
        max_concurrent_queries=2,
        max_kb_documents=20,
        max_kb_size_mb=10,
        daily_llm_budget_usd=1.0,
        monthly_llm_budget_usd=20.0,
    ),
    TenantTier.STARTER: ResourceQuota(
        daily_api_calls=500,
        monthly_api_calls=10000,
        max_tokens_per_request=8000,
        max_requests_per_minute=30,
        max_agents=5,
        max_active_agents=3,
        max_concurrent_queries=5,
        max_kb_documents=50,
        max_kb_size_mb=25,
        daily_llm_budget_usd=5.0,
        monthly_llm_budget_usd=100.0,
    ),
    TenantTier.PROFESSIONAL: ResourceQuota(
        daily_api_calls=2000,
        monthly_api_calls=50000,
        max_tokens_per_request=16000,
        max_requests_per_minute=60,
        max_agents=20,
        max_active_agents=10,
        max_concurrent_queries=20,
        max_kb_documents=200,
        max_kb_size_mb=100,
        daily_llm_budget_usd=25.0,
        monthly_llm_budget_usd=500.0,
    ),
    TenantTier.ENTERPRISE: ResourceQuota(
        daily_api_calls=10000,
        monthly_api_calls=250000,
        max_tokens_per_request=32000,
        max_requests_per_minute=200,
        max_agents=100,
        max_active_agents=50,
        max_concurrent_queries=100,
        max_kb_documents=1000,
        max_kb_size_mb=500,
        daily_llm_budget_usd=100.0,
        monthly_llm_budget_usd=2000.0,
    ),
    TenantTier.GOVERNMENT: ResourceQuota(
        daily_api_calls=50000,
        monthly_api_calls=1000000,
        max_tokens_per_request=64000,
        max_requests_per_minute=500,
        max_agents=500,
        max_active_agents=250,
        max_concurrent_queries=500,
        max_kb_documents=5000,
        max_kb_size_mb=2000,
        daily_llm_budget_usd=500.0,
        monthly_llm_budget_usd=10000.0,
    ),
}


@dataclass
class TenantUsage:
    """Usage tracking for a tenant."""

    tenant_id: str
    date: str  # YYYY-MM-DD

    # API usage
    api_calls_today: int = 0
    api_calls_this_month: int = 0
    tokens_used_today: int = 0
    tokens_used_this_month: int = 0

    # LLM costs
    llm_cost_today_usd: float = 0.0
    llm_cost_this_month_usd: float = 0.0

    # Agent usage
    active_agents: int = 0
    queries_today: int = 0
    queries_this_month: int = 0

    # Storage
    kb_documents: int = 0
    kb_size_mb: float = 0.0

    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "date": self.date,
            "api_calls_today": self.api_calls_today,
            "api_calls_this_month": self.api_calls_this_month,
            "tokens_used_today": self.tokens_used_today,
            "tokens_used_this_month": self.tokens_used_this_month,
            "llm_cost_today_usd": self.llm_cost_today_usd,
            "llm_cost_this_month_usd": self.llm_cost_this_month_usd,
            "active_agents": self.active_agents,
            "queries_today": self.queries_today,
            "queries_this_month": self.queries_this_month,
            "kb_documents": self.kb_documents,
            "kb_size_mb": self.kb_size_mb,
            "last_updated": self.last_updated,
        }


@dataclass
class TenantSettings:
    """Tenant-specific settings."""

    # LLM preferences
    preferred_models: dict[str, str] = field(default_factory=dict)  # tier -> model
    fallback_models: dict[str, str] = field(default_factory=dict)
    default_temperature: float = 0.7
    default_max_tokens: int = 2000

    # Governance
    default_hitl_mode: str = "INFORM"
    require_approval_for_domains: list[str] = field(default_factory=list)
    prohibited_topics: list[str] = field(default_factory=list)

    # Branding
    custom_branding: dict[str, str] = field(default_factory=dict)
    welcome_message: str = ""
    escalation_email: str = ""

    # Features
    enabled_features: list[str] = field(default_factory=list)
    disabled_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_models": self.preferred_models,
            "fallback_models": self.fallback_models,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "default_hitl_mode": self.default_hitl_mode,
            "require_approval_for_domains": self.require_approval_for_domains,
            "prohibited_topics": self.prohibited_topics,
            "custom_branding": self.custom_branding,
            "welcome_message": self.welcome_message,
            "escalation_email": self.escalation_email,
            "enabled_features": self.enabled_features,
            "disabled_features": self.disabled_features,
        }


@dataclass
class Tenant:
    """A tenant (organization) in the system."""

    id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    tier: TenantTier = TenantTier.FREE

    # Contact
    admin_email: str = ""
    admin_name: str = ""

    # Configuration
    settings: TenantSettings = field(default_factory=TenantSettings)
    quota: ResourceQuota | None = None  # If None, uses tier default

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_quota(self) -> ResourceQuota:
        """Get effective quota (custom or tier default)."""
        if self.quota:
            return self.quota
        return TIER_QUOTAS.get(self.tier, TIER_QUOTAS[TenantTier.FREE])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "tier": self.tier.value,
            "admin_email": self.admin_email,
            "admin_name": self.admin_name,
            "settings": self.settings.to_dict(),
            "quota": self.quota.to_dict() if self.quota else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tenant:
        settings_data = data.get("settings", {})
        settings = TenantSettings(
            preferred_models=settings_data.get("preferred_models", {}),
            fallback_models=settings_data.get("fallback_models", {}),
            default_temperature=settings_data.get("default_temperature", 0.7),
            default_max_tokens=settings_data.get("default_max_tokens", 2000),
            default_hitl_mode=settings_data.get("default_hitl_mode", "INFORM"),
            require_approval_for_domains=settings_data.get("require_approval_for_domains", []),
            prohibited_topics=settings_data.get("prohibited_topics", []),
            custom_branding=settings_data.get("custom_branding", {}),
            welcome_message=settings_data.get("welcome_message", ""),
            escalation_email=settings_data.get("escalation_email", ""),
            enabled_features=settings_data.get("enabled_features", []),
            disabled_features=settings_data.get("disabled_features", []),
        )

        quota = None
        if data.get("quota"):
            q = data["quota"]
            quota = ResourceQuota(
                daily_api_calls=q.get("daily_api_calls", 1000),
                monthly_api_calls=q.get("monthly_api_calls", 25000),
                max_tokens_per_request=q.get("max_tokens_per_request", 8000),
                max_requests_per_minute=q.get("max_requests_per_minute", 60),
                max_agents=q.get("max_agents", 5),
                max_active_agents=q.get("max_active_agents", 3),
                max_concurrent_queries=q.get("max_concurrent_queries", 10),
                max_kb_documents=q.get("max_kb_documents", 100),
                max_kb_size_mb=q.get("max_kb_size_mb", 50),
                daily_llm_budget_usd=q.get("daily_llm_budget_usd", 10.0),
                monthly_llm_budget_usd=q.get("monthly_llm_budget_usd", 200.0),
            )

        return cls(
            id=data["id"],
            name=data["name"],
            status=TenantStatus(data.get("status", "active")),
            tier=TenantTier(data.get("tier", "free")),
            admin_email=data.get("admin_email", ""),
            admin_name=data.get("admin_name", ""),
            settings=settings,
            quota=quota,
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {}),
        )


class QuotaExceededError(Exception):
    """Raised when a tenant exceeds their quota."""

    def __init__(self, tenant_id: str, quota_type: str, current: float, limit: float):
        self.tenant_id = tenant_id
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Tenant {tenant_id} exceeded {quota_type} quota: {current}/{limit}"
        )


class TenantManager:
    """Manages tenants and their configurations.

    Provides:
    - Tenant CRUD operations
    - Usage tracking
    - Quota enforcement
    - Tenant-scoped data isolation
    """

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path("data/tenants")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tenants: dict[str, Tenant] = {}
        self._usage: dict[str, TenantUsage] = {}
        self._rate_limiters: dict[str, list[datetime]] = {}

        self._load_tenants()

    def _load_tenants(self) -> None:
        """Load tenants from storage."""
        tenants_file = self._storage_path / "tenants.json"
        if tenants_file.exists():
            try:
                data = json.loads(tenants_file.read_text())
                for tid, tdata in data.items():
                    self._tenants[tid] = Tenant.from_dict(tdata)
            except Exception:
                pass

        usage_file = self._storage_path / "usage.json"
        if usage_file.exists():
            try:
                data = json.loads(usage_file.read_text())
                for tid, udata in data.items():
                    self._usage[tid] = TenantUsage(
                        tenant_id=tid,
                        date=udata.get("date", ""),
                        api_calls_today=udata.get("api_calls_today", 0),
                        api_calls_this_month=udata.get("api_calls_this_month", 0),
                        tokens_used_today=udata.get("tokens_used_today", 0),
                        tokens_used_this_month=udata.get("tokens_used_this_month", 0),
                        llm_cost_today_usd=udata.get("llm_cost_today_usd", 0.0),
                        llm_cost_this_month_usd=udata.get("llm_cost_this_month_usd", 0.0),
                        active_agents=udata.get("active_agents", 0),
                        queries_today=udata.get("queries_today", 0),
                        queries_this_month=udata.get("queries_this_month", 0),
                        kb_documents=udata.get("kb_documents", 0),
                        kb_size_mb=udata.get("kb_size_mb", 0.0),
                    )
            except Exception:
                pass

    def _save_tenants(self) -> None:
        """Save tenants to storage."""
        tenants_file = self._storage_path / "tenants.json"
        data = {tid: t.to_dict() for tid, t in self._tenants.items()}
        tenants_file.write_text(json.dumps(data, indent=2))

    def _save_usage(self) -> None:
        """Save usage data to storage."""
        usage_file = self._storage_path / "usage.json"
        data = {tid: u.to_dict() for tid, u in self._usage.items()}
        usage_file.write_text(json.dumps(data, indent=2))

    # =========================================================================
    # Tenant CRUD
    # =========================================================================

    def create_tenant(
        self,
        name: str,
        tier: TenantTier = TenantTier.FREE,
        admin_email: str = "",
        admin_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = str(uuid.uuid4())[:8]

        tenant = Tenant(
            id=tenant_id,
            name=name,
            tier=tier,
            admin_email=admin_email,
            admin_name=admin_name,
            metadata=metadata or {},
        )

        self._tenants[tenant_id] = tenant
        self._usage[tenant_id] = TenantUsage(
            tenant_id=tenant_id,
            date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        self._save_tenants()
        self._save_usage()

        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def list_tenants(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
    ) -> list[Tenant]:
        """List tenants with optional filters."""
        results = []
        for tenant in self._tenants.values():
            if status and tenant.status != status:
                continue
            if tier and tenant.tier != tier:
                continue
            results.append(tenant)
        return results

    def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        tier: TenantTier | None = None,
        status: TenantStatus | None = None,
        admin_email: str | None = None,
        settings: TenantSettings | None = None,
        quota: ResourceQuota | None = None,
    ) -> Tenant | None:
        """Update a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        if name is not None:
            tenant.name = name
        if tier is not None:
            tenant.tier = tier
        if status is not None:
            tenant.status = status
        if admin_email is not None:
            tenant.admin_email = admin_email
        if settings is not None:
            tenant.settings = settings
        if quota is not None:
            tenant.quota = quota

        tenant.updated_at = datetime.utcnow().isoformat()
        self._save_tenants()

        return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant (archives them)."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.ARCHIVED
        tenant.updated_at = datetime.utcnow().isoformat()
        self._save_tenants()

        return True

    # =========================================================================
    # Usage Tracking
    # =========================================================================

    def get_usage(self, tenant_id: str) -> TenantUsage | None:
        """Get usage for a tenant."""
        usage = self._usage.get(tenant_id)
        if usage:
            # Check if we need to reset daily/monthly counters
            today = datetime.utcnow().strftime("%Y-%m-%d")
            if usage.date != today:
                # Reset daily counters
                usage.api_calls_today = 0
                usage.tokens_used_today = 0
                usage.llm_cost_today_usd = 0.0
                usage.queries_today = 0

                # Check for month reset
                if usage.date[:7] != today[:7]:
                    usage.api_calls_this_month = 0
                    usage.tokens_used_this_month = 0
                    usage.llm_cost_this_month_usd = 0.0
                    usage.queries_this_month = 0

                usage.date = today
                self._save_usage()

        return usage

    def record_api_call(
        self,
        tenant_id: str,
        tokens_used: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """Record an API call for a tenant."""
        usage = self.get_usage(tenant_id)
        if not usage:
            usage = TenantUsage(
                tenant_id=tenant_id,
                date=datetime.utcnow().strftime("%Y-%m-%d"),
            )
            self._usage[tenant_id] = usage

        usage.api_calls_today += 1
        usage.api_calls_this_month += 1
        usage.tokens_used_today += tokens_used
        usage.tokens_used_this_month += tokens_used
        usage.llm_cost_today_usd += llm_cost
        usage.llm_cost_this_month_usd += llm_cost
        usage.last_updated = datetime.utcnow().isoformat()

        self._save_usage()

    def record_query(self, tenant_id: str) -> None:
        """Record a query for a tenant."""
        usage = self.get_usage(tenant_id)
        if usage:
            usage.queries_today += 1
            usage.queries_this_month += 1
            self._save_usage()

    # =========================================================================
    # Quota Enforcement
    # =========================================================================

    def check_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int | float = 1,
    ) -> bool:
        """Check if a tenant can perform an operation without exceeding quota.

        Args:
            tenant_id: Tenant ID
            quota_type: Type of quota to check
            amount: Amount of the resource to consume

        Returns:
            True if within quota, False otherwise
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return False

        quota = tenant.get_quota()
        usage = self.get_usage(tenant_id)

        if not usage:
            return True

        checks = {
            "daily_api_calls": (usage.api_calls_today + amount, quota.daily_api_calls),
            "monthly_api_calls": (usage.api_calls_this_month + amount, quota.monthly_api_calls),
            "tokens_per_request": (amount, quota.max_tokens_per_request),
            "daily_llm_budget": (usage.llm_cost_today_usd + amount, quota.daily_llm_budget_usd),
            "monthly_llm_budget": (usage.llm_cost_this_month_usd + amount, quota.monthly_llm_budget_usd),
            "max_agents": (usage.active_agents + amount, quota.max_agents),
            "max_kb_documents": (usage.kb_documents + amount, quota.max_kb_documents),
        }

        if quota_type in checks:
            current, limit = checks[quota_type]
            return current <= limit

        return True

    def enforce_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int | float = 1,
    ) -> None:
        """Enforce quota, raising exception if exceeded.

        Args:
            tenant_id: Tenant ID
            quota_type: Type of quota to check
            amount: Amount of the resource to consume

        Raises:
            QuotaExceededError: If quota is exceeded
        """
        if not self.check_quota(tenant_id, quota_type, amount):
            tenant = self.get_tenant(tenant_id)
            usage = self.get_usage(tenant_id)

            if tenant and usage:
                quota = tenant.get_quota()

                current_values = {
                    "daily_api_calls": usage.api_calls_today,
                    "monthly_api_calls": usage.api_calls_this_month,
                    "daily_llm_budget": usage.llm_cost_today_usd,
                    "monthly_llm_budget": usage.llm_cost_this_month_usd,
                }

                limits = {
                    "daily_api_calls": quota.daily_api_calls,
                    "monthly_api_calls": quota.monthly_api_calls,
                    "daily_llm_budget": quota.daily_llm_budget_usd,
                    "monthly_llm_budget": quota.monthly_llm_budget_usd,
                }

                raise QuotaExceededError(
                    tenant_id=tenant_id,
                    quota_type=quota_type,
                    current=current_values.get(quota_type, 0),
                    limit=limits.get(quota_type, 0),
                )

    def check_rate_limit(
        self,
        tenant_id: str,
    ) -> bool:
        """Check if tenant is within rate limit.

        Returns:
            True if within rate limit
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        quota = tenant.get_quota()
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Get recent requests
        if tenant_id not in self._rate_limiters:
            self._rate_limiters[tenant_id] = []

        # Clean old entries
        self._rate_limiters[tenant_id] = [
            ts for ts in self._rate_limiters[tenant_id]
            if ts > minute_ago
        ]

        return len(self._rate_limiters[tenant_id]) < quota.max_requests_per_minute

    def record_rate_limit(self, tenant_id: str) -> None:
        """Record a request for rate limiting."""
        if tenant_id not in self._rate_limiters:
            self._rate_limiters[tenant_id] = []
        self._rate_limiters[tenant_id].append(datetime.utcnow())

    # =========================================================================
    # Tenant Context
    # =========================================================================

    def get_tenant_context(self, tenant_id: str) -> dict[str, Any]:
        """Get complete context for a tenant request.

        Returns all tenant info needed for request processing.
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}

        usage = self.get_usage(tenant_id)
        quota = tenant.get_quota()

        return {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "tier": tenant.tier.value,
            "status": tenant.status.value,
            "settings": tenant.settings.to_dict(),
            "quota": quota.to_dict(),
            "usage": usage.to_dict() if usage else {},
            "within_budget": self.check_quota(tenant_id, "daily_llm_budget"),
            "rate_limited": not self.check_rate_limit(tenant_id),
        }


# Singleton
_tenant_manager: TenantManager | None = None


def get_tenant_manager() -> TenantManager:
    """Get the tenant manager singleton."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


__all__ = [
    "Tenant",
    "TenantStatus",
    "TenantTier",
    "TenantSettings",
    "TenantUsage",
    "ResourceQuota",
    "QuotaExceededError",
    "TenantManager",
    "TIER_QUOTAS",
    "get_tenant_manager",
]

# Export database-level isolation components
from .database import (
    IsolationLevel,
    TenantConnection,
    TenantEncryptionKey,
    TenantContext,
    require_tenant,
    TenantDatabaseManager,
    TenantAwareRepository,
    FileTenantIsolation,
    get_db_manager,
    get_file_isolation,
)

__all__ += [
    "IsolationLevel",
    "TenantConnection",
    "TenantEncryptionKey",
    "TenantContext",
    "require_tenant",
    "TenantDatabaseManager",
    "TenantAwareRepository",
    "FileTenantIsolation",
    "get_db_manager",
    "get_file_isolation",
]

# Export middleware components
from .middleware import (
    TenantMiddleware,
    TenantMiddlewareError,
    MissingOrgIdError,
    extract_org_id,
    set_tenant_context_postgres,
    clear_tenant_context_postgres,
    require_org_id,
    get_current_org_id,
    TenantScopedSession,
)

__all__ += [
    "TenantMiddleware",
    "TenantMiddlewareError",
    "MissingOrgIdError",
    "extract_org_id",
    "set_tenant_context_postgres",
    "clear_tenant_context_postgres",
    "require_org_id",
    "get_current_org_id",
    "TenantScopedSession",
]
