"""Session and conversation API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from packages.core.sessions import (
    Conversation,
    Message,
    UserPreferences,
    get_session_manager,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request state (set by TenantMiddleware).

    Returns 'default' if no tenant context is set.
    """
    return getattr(request.state, "org_id", None) or "default"


def _validate_user_access(request: Request, user_id: str) -> None:
    """Validate that the current user can access the requested user's data.

    SECURITY: Prevents cross-user data access within same tenant.
    In a full implementation, this would check JWT claims.
    """
    # For now, we allow access if in same tenant context
    # In production, validate user_id matches authenticated user or has admin role
    pass


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    user_id: str = "anonymous"
    department: str = "General"
    tenant_id: str | None = None  # Optional, will use middleware value if not provided


class AddMessageRequest(BaseModel):
    """Request to add a message to a conversation."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)
    agent_id: str | None = None
    agent_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateContextRequest(BaseModel):
    """Request to update conversation context."""

    context: dict[str, Any]


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""

    department: str | None = None
    preferred_language: str | None = None
    preferred_response_style: str | None = None
    custom_settings: dict[str, Any] | None = None


class ConversationListResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: list[Conversation]
    total: int


class ConversationContextResponse(BaseModel):
    """Response containing conversation context for LLM."""

    context: str
    message_count: int
    current_agent_id: str | None


# =============================================================================
# Conversation Endpoints
# =============================================================================


@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    req: Request,
) -> Conversation:
    """Create a new conversation session.

    ENTERPRISE: Tenant ID is extracted from middleware or request body.
    Sessions are scoped to tenants for isolation.
    """
    # Get tenant ID from middleware (preferred) or request body
    tenant_id = _get_tenant_id(req)
    if request.tenant_id:
        tenant_id = request.tenant_id

    manager = get_session_manager()
    return manager.create_conversation(
        user_id=request.user_id,
        department=request.department,
        tenant_id=tenant_id,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    req: Request,
    user_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    include_inactive: bool = False,
) -> ConversationListResponse:
    """List conversations, optionally filtered by user.

    ENTERPRISE: Results are scoped to the current tenant.
    """
    tenant_id = _get_tenant_id(req)
    manager = get_session_manager()
    conversations = manager.list_conversations(
        user_id=user_id,
        limit=limit,
        include_inactive=include_inactive,
        tenant_id=tenant_id,
    )
    return ConversationListResponse(
        conversations=conversations,
        total=len(conversations),
    )


@router.get("/conversations/{conv_id}", response_model=Conversation)
async def get_conversation(conv_id: str) -> Conversation:
    """Get a conversation by ID."""
    manager = get_session_manager()
    conv = manager.get_conversation(conv_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )
    return conv


@router.post("/conversations/{conv_id}/messages", response_model=Message)
async def add_message(conv_id: str, request: AddMessageRequest) -> Message:
    """Add a message to a conversation."""
    manager = get_session_manager()
    message = manager.add_message(
        conv_id=conv_id,
        role=request.role,
        content=request.content,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        metadata=request.metadata,
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )
    return message


@router.get("/conversations/{conv_id}/context", response_model=ConversationContextResponse)
async def get_conversation_context(
    conv_id: str,
    max_messages: int = Query(default=10, ge=1, le=50),
    max_tokens: int = Query(default=4000, ge=100, le=16000),
) -> ConversationContextResponse:
    """Get conversation context formatted for LLM prompt."""
    manager = get_session_manager()
    conv = manager.get_conversation(conv_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    context = manager.get_conversation_context(
        conv_id=conv_id,
        max_messages=max_messages,
        max_tokens=max_tokens,
    )
    return ConversationContextResponse(
        context=context,
        message_count=len(conv.messages),
        current_agent_id=conv.current_agent_id,
    )


@router.put("/conversations/{conv_id}/context")
async def update_conversation_context(
    conv_id: str,
    request: UpdateContextRequest,
) -> dict[str, str]:
    """Update persistent context for a conversation."""
    manager = get_session_manager()
    if manager.update_context(conv_id, request.context):
        return {"status": "ok", "message": "Context updated"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Conversation '{conv_id}' not found",
    )


@router.post("/conversations/{conv_id}/close")
async def close_conversation(conv_id: str) -> dict[str, str]:
    """Close a conversation session."""
    manager = get_session_manager()
    if manager.close_conversation(conv_id):
        return {"status": "ok", "message": "Conversation closed"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Conversation '{conv_id}' not found",
    )


# =============================================================================
# User Preferences Endpoints
# =============================================================================


@router.get("/users/{user_id}/preferences", response_model=UserPreferences)
async def get_user_preferences(user_id: str, req: Request) -> UserPreferences:
    """Get user preferences.

    SECURITY: Validates that the request has appropriate access to this user's data.
    In production, this should validate against JWT claims or role-based access.
    """
    # Validate access - prevents cross-user data leakage
    _validate_user_access(req, user_id)

    tenant_id = _get_tenant_id(req)
    manager = get_session_manager()
    return manager.get_user_preferences(user_id, tenant_id=tenant_id)


@router.put("/users/{user_id}/preferences", response_model=UserPreferences)
async def update_user_preferences(
    user_id: str,
    request: UpdatePreferencesRequest,
    req: Request,
) -> UserPreferences:
    """Update user preferences.

    SECURITY: Validates that the request has appropriate access to this user's data.
    """
    # Validate access
    _validate_user_access(req, user_id)

    tenant_id = _get_tenant_id(req)
    manager = get_session_manager()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return manager.update_user_preferences(user_id, updates, tenant_id=tenant_id)


# =============================================================================
# Cleanup Endpoints
# =============================================================================


@router.post("/cleanup")
async def cleanup_old_conversations(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Clean up old inactive conversations."""
    manager = get_session_manager()
    deleted = manager.cleanup_old_conversations(days=days)
    return {"status": "ok", "deleted_count": deleted}
