"""Agent management API endpoints with enterprise security."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from packages.api.security import (
    AuthenticatedUser,
    Permission,
    Role,
    log_audit_event,
    require_permission,
    require_role,
    validate_agent_id,
    validate_file_upload,
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
)
from packages.core.agents import AgentConfig, get_agent_manager
from packages.core.knowledge import KnowledgeDocument, get_knowledge_manager

router = APIRouter(prefix="/agents", tags=["Agents"])


def _update_concierge_knowledge():
    """Update the Concierge's awareness of available agents."""
    from packages.api.system import create_concierge

    manager = get_agent_manager()
    agents = manager.list_agents()

    # Find existing concierge
    existing = manager.get_agent("concierge")
    if not existing:
        return

    # Extract org info from existing or use defaults
    org = "HAAIS AIOS"
    client = "Default"
    desc = existing.description
    if "'s AI" in desc:
        org = desc.split("'s AI")[0].replace("The front door to ", "")

    # Regenerate with current agents
    updated = create_concierge(client, org, agents)
    manager.update_agent("concierge", {
        "system_prompt": updated.system_prompt,
    })


# =============================================================================
# Request/Response Models
# =============================================================================


class AgentUpdateRequest(BaseModel):
    """Request to update an agent."""

    name: str | None = Field(None, max_length=100)
    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    capabilities: list[str] | None = Field(None, max_length=50)
    guardrails: list[str] | None = Field(None, max_length=50)
    escalates_to: str | None = Field(None, max_length=64)
    system_prompt: str | None = Field(None, max_length=50000)
    status: str | None = Field(None, pattern="^(active|inactive|maintenance)$")


class AgentCreateRequest(BaseModel):
    """Request to create a new agent."""

    id: str = Field(..., min_length=1, max_length=64, pattern="^[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    title: str = Field(default="", max_length=200)
    domain: str = Field(default="General", max_length=64)
    description: str = Field(default="", max_length=2000)
    capabilities: list[str] = Field(default_factory=list, max_length=50)
    guardrails: list[str] = Field(default_factory=list, max_length=50)
    escalates_to: str = Field(default="", max_length=64)
    system_prompt: str = Field(default="", max_length=50000)
    gpt_url: str = Field(default="", max_length=500)
    is_router: bool = False


class AgentQueryRequest(BaseModel):
    """Request to query an agent."""

    query: str = Field(..., min_length=1, max_length=10000)
    use_knowledge_base: bool = True
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class AgentQueryResponse(BaseModel):
    """Response from agent query."""

    response: str
    agent_id: str
    agent_name: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    hitl_mode: str = "INFORM"


class AgentListResponse(BaseModel):
    """Response containing list of agents."""

    agents: list[AgentConfig]
    total: int


# =============================================================================
# Agent CRUD Endpoints (Authenticated)
# =============================================================================


@router.get("", response_model=AgentListResponse)
async def list_agents(
    user: AuthenticatedUser = Depends(require_permission(Permission.READ_AGENTS)),
) -> AgentListResponse:
    """List all agents. Requires READ_AGENTS permission."""
    manager = get_agent_manager()
    agents = manager.list_agents()

    log_audit_event(
        event_type="agent_list",
        user=user,
        endpoint="/agents",
        method="GET",
        action="list_agents",
        status="success",
    )

    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.READ_AGENTS)),
) -> AgentConfig:
    """Get an agent by ID. Requires READ_AGENTS permission."""
    validate_agent_id(agent_id)

    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    log_audit_event(
        event_type="agent_read",
        user=user,
        endpoint=f"/agents/{agent_id}",
        method="GET",
        action="read_agent",
        status="success",
        resource_id=agent_id,
    )

    return agent


@router.post("", response_model=AgentConfig, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_AGENTS)),
) -> AgentConfig:
    """Create a new agent. Requires WRITE_AGENTS permission."""
    manager = get_agent_manager()

    # Check if agent already exists
    if manager.get_agent(request.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{request.id}' already exists",
        )

    # Validate system_prompt doesn't contain dangerous patterns
    if request.system_prompt:
        dangerous_patterns = [
            "ignore all previous",
            "ignore your instructions",
            "disregard your rules",
            "you are now",
            "pretend you are",
        ]
        prompt_lower = request.system_prompt.lower()
        for pattern in dangerous_patterns:
            if pattern in prompt_lower:
                log_audit_event(
                    event_type="security_violation",
                    user=user,
                    endpoint="/agents",
                    method="POST",
                    action="create_agent_blocked",
                    status="denied",
                    details={"reason": "dangerous_prompt_pattern", "pattern": pattern},
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="System prompt contains disallowed patterns",
                )

    agent = AgentConfig(**request.model_dump())
    created = manager.create_agent(agent)

    # Update Concierge to know about the new agent
    _update_concierge_knowledge()

    log_audit_event(
        event_type="agent_create",
        user=user,
        endpoint="/agents",
        method="POST",
        action="create_agent",
        status="success",
        resource_id=request.id,
    )

    return created


@router.put("/{agent_id}", response_model=AgentConfig)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_AGENTS)),
) -> AgentConfig:
    """Update an agent. Requires WRITE_AGENTS permission."""
    validate_agent_id(agent_id)

    manager = get_agent_manager()

    # Validate system_prompt if being updated
    if request.system_prompt:
        dangerous_patterns = [
            "ignore all previous",
            "ignore your instructions",
            "disregard your rules",
            "you are now",
            "pretend you are",
        ]
        prompt_lower = request.system_prompt.lower()
        for pattern in dangerous_patterns:
            if pattern in prompt_lower:
                log_audit_event(
                    event_type="security_violation",
                    user=user,
                    endpoint=f"/agents/{agent_id}",
                    method="PUT",
                    action="update_agent_blocked",
                    status="denied",
                    details={"reason": "dangerous_prompt_pattern"},
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="System prompt contains disallowed patterns",
                )

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    agent = manager.update_agent(agent_id, updates)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    log_audit_event(
        event_type="agent_update",
        user=user,
        endpoint=f"/agents/{agent_id}",
        method="PUT",
        action="update_agent",
        status="success",
        resource_id=agent_id,
        details={"updated_fields": list(updates.keys())},
    )

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_AGENTS)),
) -> None:
    """Delete an agent. Requires WRITE_AGENTS permission."""
    validate_agent_id(agent_id)

    # Don't allow deleting the Concierge
    if agent_id == "concierge":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the Concierge agent. Use system reset for new client setup.",
        )

    manager = get_agent_manager()
    if not manager.delete_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Update Concierge to remove knowledge of deleted agent
    _update_concierge_knowledge()

    log_audit_event(
        event_type="agent_delete",
        user=user,
        endpoint=f"/agents/{agent_id}",
        method="DELETE",
        action="delete_agent",
        status="success",
        resource_id=agent_id,
    )


@router.post("/{agent_id}/enable", response_model=AgentConfig)
async def enable_agent(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_AGENTS)),
) -> AgentConfig:
    """Enable an agent. Requires WRITE_AGENTS permission."""
    validate_agent_id(agent_id)

    manager = get_agent_manager()
    agent = manager.enable_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    log_audit_event(
        event_type="agent_status_change",
        user=user,
        endpoint=f"/agents/{agent_id}/enable",
        method="POST",
        action="enable_agent",
        status="success",
        resource_id=agent_id,
    )

    return agent


@router.post("/{agent_id}/disable", response_model=AgentConfig)
async def disable_agent(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_AGENTS)),
) -> AgentConfig:
    """Disable an agent. Requires WRITE_AGENTS permission."""
    validate_agent_id(agent_id)

    manager = get_agent_manager()
    agent = manager.disable_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    log_audit_event(
        event_type="agent_status_change",
        user=user,
        endpoint=f"/agents/{agent_id}/disable",
        method="POST",
        action="disable_agent",
        status="success",
        resource_id=agent_id,
    )

    return agent


# =============================================================================
# Knowledge Base Endpoints (Authenticated)
# =============================================================================


@router.get("/{agent_id}/knowledge", response_model=list[KnowledgeDocument])
async def list_knowledge(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> list[KnowledgeDocument]:
    """List all documents in an agent's knowledge base. Requires READ_KNOWLEDGE permission."""
    validate_agent_id(agent_id)

    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()

    log_audit_event(
        event_type="knowledge_list",
        user=user,
        endpoint=f"/agents/{agent_id}/knowledge",
        method="GET",
        action="list_knowledge",
        status="success",
        resource_id=agent_id,
    )

    return knowledge_manager.list_documents(agent_id)


@router.post("/{agent_id}/knowledge", response_model=KnowledgeDocument)
async def upload_knowledge(
    agent_id: str,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_KNOWLEDGE)),
) -> KnowledgeDocument:
    """Upload a document to an agent's knowledge base. Requires WRITE_KNOWLEDGE permission."""
    validate_agent_id(agent_id)

    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Read and validate file content
    content = await file.read()

    # Security validation
    validate_file_upload(
        filename=file.filename or "unknown.txt",
        content=content,
        content_type=file.content_type,
    )

    knowledge_manager = get_knowledge_manager()
    doc = knowledge_manager.add_document(
        agent_id=agent_id,
        filename=file.filename or "unknown.txt",
        content=content,
    )

    log_audit_event(
        event_type="knowledge_upload",
        user=user,
        endpoint=f"/agents/{agent_id}/knowledge",
        method="POST",
        action="upload_knowledge",
        status="success",
        resource_id=agent_id,
        details={"filename": file.filename, "size_bytes": len(content)},
    )

    return doc


@router.delete("/{agent_id}/knowledge/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    agent_id: str,
    document_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_KNOWLEDGE)),
) -> None:
    """Delete a document from an agent's knowledge base. Requires WRITE_KNOWLEDGE permission."""
    validate_agent_id(agent_id)

    knowledge_manager = get_knowledge_manager()
    doc = knowledge_manager.get_document(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )

    if doc.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document does not belong to agent '{agent_id}'",
        )

    knowledge_manager.delete_document(document_id)

    log_audit_event(
        event_type="knowledge_delete",
        user=user,
        endpoint=f"/agents/{agent_id}/knowledge/{document_id}",
        method="DELETE",
        action="delete_knowledge",
        status="success",
        resource_id=agent_id,
        details={"document_id": document_id},
    )


@router.delete("/{agent_id}/knowledge", status_code=status.HTTP_204_NO_CONTENT)
async def clear_knowledge(
    agent_id: str,
    user: AuthenticatedUser = Depends(require_role(Role.OPERATOR)),
) -> None:
    """Clear all documents from an agent's knowledge base. Requires OPERATOR role or higher."""
    validate_agent_id(agent_id)

    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()
    knowledge_manager.clear_agent_knowledge(agent_id)

    log_audit_event(
        event_type="knowledge_clear",
        user=user,
        endpoint=f"/agents/{agent_id}/knowledge",
        method="DELETE",
        action="clear_all_knowledge",
        status="success",
        resource_id=agent_id,
    )


# =============================================================================
# Agent Query Endpoint (with RAG) - Authenticated
# =============================================================================


@router.post("/{agent_id}/query", response_model=AgentQueryResponse)
async def query_agent(
    agent_id: str,
    request: AgentQueryRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_QUERY)),
) -> AgentQueryResponse:
    """Query an agent with optional knowledge base retrieval. Requires EXECUTE_QUERY permission."""
    from packages.core.router import get_router

    validate_agent_id(agent_id)

    # Get agent
    agent_manager = get_agent_manager()
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_id}' is not active",
        )

    # Get relevant context from knowledge base
    sources: list[dict[str, Any]] = []
    context = ""

    if request.use_knowledge_base:
        knowledge_manager = get_knowledge_manager()
        results = knowledge_manager.query(agent_id, request.query, n_results=5)
        sources = results

        if results:
            context_parts = []
            for r in results:
                context_parts.append(f"[Source: {r['metadata'].get('filename', 'unknown')}]\n{r['text']}")
            context = "\n\n---\n\n".join(context_parts)

    # Build system prompt
    system_prompt = agent.system_prompt
    if context:
        system_prompt += f"\n\n## Relevant Knowledge Base Documents:\n\n{context}"

    # Add guardrails to system prompt
    if agent.guardrails:
        guardrail_text = "\n".join(f"- {g}" for g in agent.guardrails)
        system_prompt += f"\n\n## Guardrails (You MUST follow these):\n{guardrail_text}"

    # Query the LLM
    router = get_router()
    try:
        response_text = router.llm.generate(
            prompt=request.query,
            system=system_prompt,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        log_audit_event(
            event_type="agent_query_error",
            user=user,
            endpoint=f"/agents/{agent_id}/query",
            method="POST",
            action="query_agent",
            status="error",
            resource_id=agent_id,
            details={"error": "LLM query failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query agent. Please try again.",
        )

    log_audit_event(
        event_type="agent_query",
        user=user,
        endpoint=f"/agents/{agent_id}/query",
        method="POST",
        action="query_agent",
        status="success",
        resource_id=agent_id,
        details={"sources_used": len(sources)},
    )

    return AgentQueryResponse(
        response=response_text,
        agent_id=agent_id,
        agent_name=agent.name,
        sources=sources,
        hitl_mode="INFORM",  # TODO: Apply governance
    )
