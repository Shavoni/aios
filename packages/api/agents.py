"""Agent management API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

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

    name: str | None = None
    title: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None
    guardrails: list[str] | None = None
    escalates_to: str | None = None
    system_prompt: str | None = None
    status: str | None = None


class AgentCreateRequest(BaseModel):
    """Request to create a new agent."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    title: str = ""
    domain: str = "General"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    escalates_to: str = ""
    system_prompt: str = ""
    gpt_url: str = ""
    is_router: bool = False


class AgentQueryRequest(BaseModel):
    """Request to query an agent."""

    query: str = Field(..., min_length=1)
    use_knowledge_base: bool = True
    max_tokens: int = 1024


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
# Agent CRUD Endpoints
# =============================================================================


@router.get("", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents."""
    manager = get_agent_manager()
    agents = manager.list_agents()
    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str) -> AgentConfig:
    """Get an agent by ID."""
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return agent


@router.post("", response_model=AgentConfig, status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest) -> AgentConfig:
    """Create a new agent."""
    manager = get_agent_manager()

    # Check if agent already exists
    if manager.get_agent(request.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{request.id}' already exists",
        )

    agent = AgentConfig(**request.model_dump())
    created = manager.create_agent(agent)

    # Update Concierge to know about the new agent
    _update_concierge_knowledge()

    return created


@router.put("/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: str, request: AgentUpdateRequest) -> AgentConfig:
    """Update an agent."""
    manager = get_agent_manager()

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    agent = manager.update_agent(agent_id, updates)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str) -> None:
    """Delete an agent."""
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


@router.post("/{agent_id}/enable", response_model=AgentConfig)
async def enable_agent(agent_id: str) -> AgentConfig:
    """Enable an agent."""
    manager = get_agent_manager()
    agent = manager.enable_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return agent


@router.post("/{agent_id}/disable", response_model=AgentConfig)
async def disable_agent(agent_id: str) -> AgentConfig:
    """Disable an agent."""
    manager = get_agent_manager()
    agent = manager.disable_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return agent


# =============================================================================
# Knowledge Base Endpoints
# =============================================================================


@router.get("/{agent_id}/knowledge", response_model=list[KnowledgeDocument])
async def list_knowledge(agent_id: str) -> list[KnowledgeDocument]:
    """List all documents in an agent's knowledge base."""
    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()
    return knowledge_manager.list_documents(agent_id)


@router.post("/{agent_id}/knowledge", response_model=KnowledgeDocument)
async def upload_knowledge(
    agent_id: str,
    file: UploadFile = File(...),
) -> KnowledgeDocument:
    """Upload a document to an agent's knowledge base."""
    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Validate file type
    allowed_types = {"txt", "pdf", "docx", "doc", "md"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {allowed_types}",
        )

    # Read file content
    content = await file.read()
    # No file size limit - allow any size for knowledge base uploads

    knowledge_manager = get_knowledge_manager()
    return knowledge_manager.add_document(
        agent_id=agent_id,
        filename=file.filename or "unknown.txt",
        content=content,
    )


@router.delete("/{agent_id}/knowledge/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(agent_id: str, document_id: str) -> None:
    """Delete a document from an agent's knowledge base."""
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


@router.delete("/{agent_id}/knowledge", status_code=status.HTTP_204_NO_CONTENT)
async def clear_knowledge(agent_id: str) -> None:
    """Clear all documents from an agent's knowledge base."""
    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()
    knowledge_manager.clear_agent_knowledge(agent_id)


# =============================================================================
# Agent Query Endpoint (with RAG)
# =============================================================================


@router.post("/{agent_id}/query", response_model=AgentQueryResponse)
async def query_agent(agent_id: str, request: AgentQueryRequest) -> AgentQueryResponse:
    """Query an agent with optional knowledge base retrieval."""
    from packages.core.router import get_router

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query LLM: {e}",
        )

    return AgentQueryResponse(
        response=response_text,
        agent_id=agent_id,
        agent_name=agent.name,
        sources=sources,
        hitl_mode="INFORM",  # TODO: Apply governance
    )
