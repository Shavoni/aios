"""Tenant management API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.core.multitenancy import (
    Tenant,
    TenantStatus,
    TenantTier,
    TenantSettings,
    ResourceQuota,
    TenantUsage,
    get_tenant_manager,
)

router = APIRouter(prefix="/tenants", tags=["Tenant Management"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateTenantRequest(BaseModel):
    """Request to create a tenant."""

    name: str
    tier: str = Field(default="free", pattern="^(free|starter|professional|enterprise|government)$")
    admin_email: str = ""
    admin_name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant."""

    name: str | None = None
    tier: str | None = Field(default=None, pattern="^(free|starter|professional|enterprise|government)$")
    status: str | None = Field(default=None, pattern="^(active|suspended|pending|archived)$")
    admin_email: str | None = None


class UpdateSettingsRequest(BaseModel):
    """Request to update tenant settings."""

    preferred_models: dict[str, str] | None = None
    default_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    default_max_tokens: int | None = Field(default=None, ge=100, le=100000)
    default_hitl_mode: str | None = Field(default=None, pattern="^(INFORM|DRAFT|EXECUTE|ESCALATE)$")
    require_approval_for_domains: list[str] | None = None
    prohibited_topics: list[str] | None = None
    welcome_message: str | None = None
    escalation_email: str | None = None


class UpdateQuotaRequest(BaseModel):
    """Request to update tenant quota."""

    daily_api_calls: int | None = Field(default=None, ge=0)
    monthly_api_calls: int | None = Field(default=None, ge=0)
    max_tokens_per_request: int | None = Field(default=None, ge=100)
    max_requests_per_minute: int | None = Field(default=None, ge=1)
    max_agents: int | None = Field(default=None, ge=1)
    max_active_agents: int | None = Field(default=None, ge=1)
    max_concurrent_queries: int | None = Field(default=None, ge=1)
    max_kb_documents: int | None = Field(default=None, ge=1)
    max_kb_size_mb: int | None = Field(default=None, ge=1)
    daily_llm_budget_usd: float | None = Field(default=None, ge=0)
    monthly_llm_budget_usd: float | None = Field(default=None, ge=0)


class TenantResponse(BaseModel):
    """Tenant response model."""

    id: str
    name: str
    status: str
    tier: str
    admin_email: str
    admin_name: str
    created_at: str
    updated_at: str


class TenantListResponse(BaseModel):
    """Response containing list of tenants."""

    tenants: list[TenantResponse]
    total: int


class UsageResponse(BaseModel):
    """Usage response model."""

    tenant_id: str
    date: str
    api_calls_today: int
    api_calls_this_month: int
    tokens_used_today: int
    tokens_used_this_month: int
    llm_cost_today_usd: float
    llm_cost_this_month_usd: float
    queries_today: int
    queries_this_month: int


class QuotaStatusResponse(BaseModel):
    """Quota status response."""

    quota: dict[str, Any]
    usage: dict[str, Any]
    remaining: dict[str, Any]
    percentage_used: dict[str, float]


# =============================================================================
# Tenant CRUD Endpoints
# =============================================================================


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(request: CreateTenantRequest) -> TenantResponse:
    """Create a new tenant."""
    manager = get_tenant_manager()

    tenant = manager.create_tenant(
        name=request.name,
        tier=TenantTier(request.tier),
        admin_email=request.admin_email,
        admin_name=request.admin_name,
        metadata=request.metadata,
    )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=tenant.status.value,
        tier=tenant.tier.value,
        admin_email=tenant.admin_email,
        admin_name=tenant.admin_name,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    status_filter: str | None = Query(default=None, alias="status"),
    tier: str | None = None,
) -> TenantListResponse:
    """List all tenants."""
    manager = get_tenant_manager()

    tenant_status = TenantStatus(status_filter) if status_filter else None
    tenant_tier = TenantTier(tier) if tier else None

    tenants = manager.list_tenants(status=tenant_status, tier=tenant_tier)

    return TenantListResponse(
        tenants=[
            TenantResponse(
                id=t.id,
                name=t.name,
                status=t.status.value,
                tier=t.tier.value,
                admin_email=t.admin_email,
                admin_name=t.admin_name,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tenants
        ],
        total=len(tenants),
    )


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str) -> dict[str, Any]:
    """Get a tenant by ID."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    return tenant.to_dict()


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, request: UpdateTenantRequest) -> TenantResponse:
    """Update a tenant."""
    manager = get_tenant_manager()

    tenant = manager.update_tenant(
        tenant_id=tenant_id,
        name=request.name,
        tier=TenantTier(request.tier) if request.tier else None,
        status=TenantStatus(request.status) if request.status else None,
        admin_email=request.admin_email,
    )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=tenant.status.value,
        tier=tenant.tier.value,
        admin_email=tenant.admin_email,
        admin_name=tenant.admin_name,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str) -> dict[str, str]:
    """Delete (archive) a tenant."""
    manager = get_tenant_manager()

    if manager.delete_tenant(tenant_id):
        return {"status": "ok", "message": f"Tenant '{tenant_id}' archived"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tenant '{tenant_id}' not found",
    )


# =============================================================================
# Settings Endpoints
# =============================================================================


@router.get("/{tenant_id}/settings")
async def get_tenant_settings(tenant_id: str) -> dict[str, Any]:
    """Get tenant settings."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    return tenant.settings.to_dict()


@router.put("/{tenant_id}/settings")
async def update_tenant_settings(
    tenant_id: str,
    request: UpdateSettingsRequest,
) -> dict[str, Any]:
    """Update tenant settings."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    settings = tenant.settings

    if request.preferred_models is not None:
        settings.preferred_models = request.preferred_models
    if request.default_temperature is not None:
        settings.default_temperature = request.default_temperature
    if request.default_max_tokens is not None:
        settings.default_max_tokens = request.default_max_tokens
    if request.default_hitl_mode is not None:
        settings.default_hitl_mode = request.default_hitl_mode
    if request.require_approval_for_domains is not None:
        settings.require_approval_for_domains = request.require_approval_for_domains
    if request.prohibited_topics is not None:
        settings.prohibited_topics = request.prohibited_topics
    if request.welcome_message is not None:
        settings.welcome_message = request.welcome_message
    if request.escalation_email is not None:
        settings.escalation_email = request.escalation_email

    manager.update_tenant(tenant_id, settings=settings)

    return settings.to_dict()


# =============================================================================
# Quota Endpoints
# =============================================================================


@router.get("/{tenant_id}/quota")
async def get_tenant_quota(tenant_id: str) -> dict[str, Any]:
    """Get tenant quota."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    quota = tenant.get_quota()
    return {
        "is_custom": tenant.quota is not None,
        "tier_default": tenant.tier.value,
        **quota.to_dict(),
    }


@router.put("/{tenant_id}/quota")
async def update_tenant_quota(
    tenant_id: str,
    request: UpdateQuotaRequest,
) -> dict[str, Any]:
    """Update tenant quota (set custom quota)."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    # Start with current or tier default
    current_quota = tenant.get_quota()

    # Apply updates
    new_quota = ResourceQuota(
        daily_api_calls=request.daily_api_calls or current_quota.daily_api_calls,
        monthly_api_calls=request.monthly_api_calls or current_quota.monthly_api_calls,
        max_tokens_per_request=request.max_tokens_per_request or current_quota.max_tokens_per_request,
        max_requests_per_minute=request.max_requests_per_minute or current_quota.max_requests_per_minute,
        max_agents=request.max_agents or current_quota.max_agents,
        max_active_agents=request.max_active_agents or current_quota.max_active_agents,
        max_concurrent_queries=request.max_concurrent_queries or current_quota.max_concurrent_queries,
        max_kb_documents=request.max_kb_documents or current_quota.max_kb_documents,
        max_kb_size_mb=request.max_kb_size_mb or current_quota.max_kb_size_mb,
        daily_llm_budget_usd=request.daily_llm_budget_usd if request.daily_llm_budget_usd is not None else current_quota.daily_llm_budget_usd,
        monthly_llm_budget_usd=request.monthly_llm_budget_usd if request.monthly_llm_budget_usd is not None else current_quota.monthly_llm_budget_usd,
    )

    manager.update_tenant(tenant_id, quota=new_quota)

    return new_quota.to_dict()


@router.delete("/{tenant_id}/quota")
async def reset_tenant_quota(tenant_id: str) -> dict[str, str]:
    """Reset tenant quota to tier default."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    manager.update_tenant(tenant_id, quota=None)  # type: ignore

    return {"status": "ok", "message": "Quota reset to tier default"}


# =============================================================================
# Usage Endpoints
# =============================================================================


@router.get("/{tenant_id}/usage", response_model=UsageResponse)
async def get_tenant_usage(tenant_id: str) -> UsageResponse:
    """Get tenant usage."""
    manager = get_tenant_manager()

    if not manager.get_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    usage = manager.get_usage(tenant_id)
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No usage data for tenant '{tenant_id}'",
        )

    return UsageResponse(
        tenant_id=usage.tenant_id,
        date=usage.date,
        api_calls_today=usage.api_calls_today,
        api_calls_this_month=usage.api_calls_this_month,
        tokens_used_today=usage.tokens_used_today,
        tokens_used_this_month=usage.tokens_used_this_month,
        llm_cost_today_usd=usage.llm_cost_today_usd,
        llm_cost_this_month_usd=usage.llm_cost_this_month_usd,
        queries_today=usage.queries_today,
        queries_this_month=usage.queries_this_month,
    )


@router.get("/{tenant_id}/quota-status", response_model=QuotaStatusResponse)
async def get_quota_status(tenant_id: str) -> QuotaStatusResponse:
    """Get detailed quota status including remaining amounts."""
    manager = get_tenant_manager()
    tenant = manager.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    quota = tenant.get_quota()
    usage = manager.get_usage(tenant_id)

    quota_dict = quota.to_dict()
    usage_dict = usage.to_dict() if usage else {}

    # Calculate remaining
    remaining = {
        "daily_api_calls": quota.daily_api_calls - (usage.api_calls_today if usage else 0),
        "monthly_api_calls": quota.monthly_api_calls - (usage.api_calls_this_month if usage else 0),
        "daily_llm_budget_usd": quota.daily_llm_budget_usd - (usage.llm_cost_today_usd if usage else 0),
        "monthly_llm_budget_usd": quota.monthly_llm_budget_usd - (usage.llm_cost_this_month_usd if usage else 0),
        "max_agents": quota.max_agents - (usage.active_agents if usage else 0),
        "max_kb_documents": quota.max_kb_documents - (usage.kb_documents if usage else 0),
    }

    # Calculate percentage used
    percentage_used = {}
    if usage:
        percentage_used = {
            "daily_api_calls": (usage.api_calls_today / quota.daily_api_calls * 100) if quota.daily_api_calls else 0,
            "monthly_api_calls": (usage.api_calls_this_month / quota.monthly_api_calls * 100) if quota.monthly_api_calls else 0,
            "daily_llm_budget": (usage.llm_cost_today_usd / quota.daily_llm_budget_usd * 100) if quota.daily_llm_budget_usd else 0,
            "monthly_llm_budget": (usage.llm_cost_this_month_usd / quota.monthly_llm_budget_usd * 100) if quota.monthly_llm_budget_usd else 0,
        }

    return QuotaStatusResponse(
        quota=quota_dict,
        usage=usage_dict,
        remaining=remaining,
        percentage_used=percentage_used,
    )


# =============================================================================
# Context Endpoint
# =============================================================================


@router.get("/{tenant_id}/context")
async def get_tenant_context(tenant_id: str) -> dict[str, Any]:
    """Get complete tenant context for request processing."""
    manager = get_tenant_manager()

    context = manager.get_tenant_context(tenant_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    return context
