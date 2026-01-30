"""Agent management API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator

from packages.core.agents import AgentConfig, get_agent_manager
from packages.core.knowledge import (
    KnowledgeDocument,
    WebSource,
    get_knowledge_manager,
    start_knowledge_scheduler,
)
from packages.core.concierge import route_to_agent, RoutingResult
from packages.core.governance.manager import get_governance_manager
from packages.core.grounding import get_grounding_engine, create_grounding_summary
from packages.core.schemas.models import HITLMode

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
    user_id: str = "anonymous"  # For HITL tracking
    department: str = "General"  # For HITL tracking


class AgentQueryResponse(BaseModel):
    """Response from agent query.

    ENTERPRISE-GRADE: Supports grounded AI with full source attribution.
    Every response can answer: "What authoritative source justifies this output?"
    """

    response: str
    agent_id: str
    agent_name: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    hitl_mode: str = "INFORM"
    governance_triggered: bool = False
    escalation_reason: str | None = None
    policy_ids: list[str] = Field(default_factory=list)
    approval_id: str | None = None  # ENTERPRISE: Set when response pending approval
    approval_required: bool = False  # ENTERPRISE: True if awaiting human review

    # === GROUNDED AI: Source Attribution ===
    source_citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured citations mapping claims to sources"
    )
    grounding_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well-grounded is this response (0=speculation, 1=fully cited)"
    )
    authority_basis: str | None = Field(
        default=None,
        description="Primary authority backing this response (e.g., 'HR Policy 4.2', 'City Ordinance 12.4')"
    )

    # === ATTRIBUTION & VERIFICATION ===
    attribution: str = Field(
        default="ai_generated",
        description="'ai_generated', 'ai_assisted', 'human_authored', 'human_verified'"
    )
    verification_status: str = Field(
        default="unverified",
        description="'verified', 'unverified', 'ai_generated', 'requires_review'"
    )
    requires_human_verification: bool = Field(
        default=False,
        description="Whether this response should be flagged for human review"
    )

    # === DECISION REASONING ===
    governance_reasoning: str | None = Field(
        default=None,
        description="Explanation of why governance decided on this HITL mode"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this response"
    )


class AgentListResponse(BaseModel):
    """Response containing list of agents."""

    agents: list[AgentConfig]
    total: int


class WebSourceCreateRequest(BaseModel):
    """Request to add a web source."""

    url: str = Field(..., min_length=1)
    name: str | None = None
    description: str = ""
    refresh_interval_hours: int = Field(default=24, ge=1, le=720)
    selector: str | None = None
    auto_refresh: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format and scheme."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(v)
            # Only allow http and https schemes
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Only HTTP and HTTPS URLs are allowed")
            # Must have a valid netloc (domain)
            if not parsed.netloc:
                raise ValueError("Invalid URL: missing domain")
            # Block localhost and internal IPs for security
            netloc_lower = parsed.netloc.lower()
            if any(blocked in netloc_lower for blocked in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]):
                raise ValueError("Internal URLs are not allowed")
            return v
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid URL format")


class WebSourceListResponse(BaseModel):
    """Response containing list of web sources."""

    sources: list[WebSource]
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

    # Read file content with size limit
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
        )

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


@router.get("/{agent_id}/knowledge/{document_id}/download")
async def download_knowledge(agent_id: str, document_id: str) -> FileResponse:
    """Download a document from an agent's knowledge base."""
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

    # Get the file path with path traversal protection
    file_path = knowledge_manager._files_path / f"{document_id}.{doc.file_type}"

    # Validate resolved path is within the expected directory (prevent path traversal)
    try:
        resolved = file_path.resolve()
        base_resolved = knowledge_manager._files_path.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document path",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for document '{document_id}' not found on disk",
        )

    # Determine media type
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    media_type = media_types.get(doc.file_type, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type=media_type,
    )


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
    """Query an agent with optional knowledge base retrieval.

    Applies HAAIS governance to determine the appropriate HITL mode:
    - INFORM: Agent responds directly
    - DRAFT: Response requires human review before sending (BLOCKS response)
    - EXECUTE: Response requires manager approval (BLOCKS response)
    - ESCALATE: Request escalated to human, agent cannot respond

    ENTERPRISE CRITICAL: DRAFT and EXECUTE modes now properly BLOCK responses
    and create approval requests. Users receive a pending status, not the response.
    """
    from packages.core.router import get_router
    from packages.core.hitl import get_hitl_manager, HITLMode as HITLModeEnum

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

    # ==========================================================================
    # HAAIS GOVERNANCE EVALUATION
    # Evaluate governance policies before processing the query
    # ==========================================================================
    governance_mgr = get_governance_manager()
    decision = governance_mgr.evaluate_for_agent(
        query=request.query,
        agent_id=agent_id,
        domain=agent.domain,
    )

    # Get HITL manager for approval workflow
    hitl_manager = get_hitl_manager()

    # Handle ESCALATE mode - do not process, create escalation request
    if decision.hitl_mode == HITLMode.ESCALATE:
        # Create escalation approval request
        approval = hitl_manager.create_approval_request(
            hitl_mode=HITLModeEnum.ESCALATE,
            user_id=request.user_id,
            agent_id=agent_id,
            agent_name=agent.name,
            original_query=request.query,
            proposed_response="",  # No response generated for escalation
            user_department=request.department,
            risk_signals=decision.policy_trigger_ids,
            escalation_reason=decision.escalation_reason,
            priority="urgent",
        )

        return AgentQueryResponse(
            response=f"This request has been escalated to a human supervisor. Reason: {decision.escalation_reason or 'Policy violation detected'}. Approval ID: {approval.id}",
            agent_id=agent_id,
            agent_name=agent.name,
            sources=[],
            hitl_mode="ESCALATE",
            governance_triggered=True,
            escalation_reason=decision.escalation_reason,
            policy_ids=decision.policy_trigger_ids,
            approval_id=approval.id,
            approval_required=True,
        )

    # Get relevant context from knowledge base
    sources: list[dict[str, Any]] = []
    context = ""

    if request.use_knowledge_base:
        knowledge_manager = get_knowledge_manager()
        # Query both shared canon AND agent-specific knowledge
        results = knowledge_manager.query_with_canon(agent_id, request.query, n_results=5)
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

    # Add governance-triggered guardrails
    if decision.policy_trigger_ids:
        system_prompt += "\n\n## GOVERNANCE NOTICE:\nThis query triggered governance policies. Exercise additional caution."
        if decision.hitl_mode in (HITLMode.DRAFT, HITLMode.EXECUTE):
            system_prompt += "\nYour response will be reviewed by a human before delivery."

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

    # ==========================================================================
    # ENTERPRISE CRITICAL: HITL RESPONSE BLOCKING
    # For DRAFT and EXECUTE modes, DO NOT return response to user.
    # Instead, create approval request and return pending status.
    # ==========================================================================
    if decision.hitl_mode in (HITLMode.DRAFT, HITLMode.EXECUTE):
        # Map to HITL enum
        hitl_mode_enum = HITLModeEnum.DRAFT if decision.hitl_mode == HITLMode.DRAFT else HITLModeEnum.EXECUTE

        # Determine priority based on mode
        priority = "high" if decision.hitl_mode == HITLMode.EXECUTE else "normal"

        # Create approval request with the generated response
        approval = hitl_manager.create_approval_request(
            hitl_mode=hitl_mode_enum,
            user_id=request.user_id,
            agent_id=agent_id,
            agent_name=agent.name,
            original_query=request.query,
            proposed_response=response_text,  # Store generated response for review
            user_department=request.department,
            risk_signals=decision.policy_trigger_ids,
            guardrails_triggered=agent.guardrails if agent.guardrails else [],
            escalation_reason=decision.escalation_reason,
            priority=priority,
            context={
                "sources": [s.get("metadata", {}).get("filename", "unknown") for s in sources],
                "governance_triggered": len(decision.policy_trigger_ids) > 0,
            },
        )

        # BLOCK: Return pending status instead of actual response
        mode_label = "DRAFT" if decision.hitl_mode == HITLMode.DRAFT else "EXECUTE"
        return AgentQueryResponse(
            response=f"Your request is pending human review ({mode_label} mode). Approval ID: {approval.id}. You will be notified when the response is approved.",
            agent_id=agent_id,
            agent_name=agent.name,
            sources=[],  # Don't expose sources until approved
            hitl_mode=decision.hitl_mode.value,
            governance_triggered=len(decision.policy_trigger_ids) > 0,
            escalation_reason=decision.escalation_reason,
            policy_ids=decision.policy_trigger_ids,
            approval_id=approval.id,
            approval_required=True,
        )

    # INFORM mode - return response directly with grounding
    # ==========================================================================
    # GROUNDED AI: Compute source attribution and authority basis
    # Every response answers: "What authoritative source justifies this output?"
    # ==========================================================================
    grounding = create_grounding_summary(
        response_text=response_text,
        sources=sources,
        governance_decision={
            "hitl_mode": decision.hitl_mode.value,
            "policy_trigger_ids": decision.policy_trigger_ids,
            "approval_required": decision.approval_required,
            "escalation_reason": decision.escalation_reason,
        },
    )

    return AgentQueryResponse(
        response=response_text,
        agent_id=agent_id,
        agent_name=agent.name,
        sources=sources,
        hitl_mode=decision.hitl_mode.value,
        governance_triggered=len(decision.policy_trigger_ids) > 0,
        escalation_reason=decision.escalation_reason,
        policy_ids=decision.policy_trigger_ids,
        approval_id=None,
        approval_required=False,
        # === GROUNDED AI FIELDS ===
        source_citations=grounding.get("source_citations", []),
        grounding_score=grounding.get("grounding_score", 0.0),
        authority_basis=grounding.get("authority_basis"),
        governance_reasoning=grounding.get("governance_reasoning"),
        attribution="ai_generated",
        verification_status="unverified" if grounding.get("requires_human_verification") else "ai_generated",
        requires_human_verification=grounding.get("requires_human_verification", False),
        confidence=1.0 - (0.5 * (1 - grounding.get("grounding_score", 0.0))),  # Higher grounding = higher confidence
    )


# =============================================================================
# Web Source Endpoints
# =============================================================================


@router.get("/{agent_id}/web-sources", response_model=WebSourceListResponse)
async def list_web_sources(agent_id: str) -> WebSourceListResponse:
    """List all web sources for an agent."""
    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()
    sources = knowledge_manager.list_web_sources(agent_id)
    return WebSourceListResponse(sources=sources, total=len(sources))


@router.post(
    "/{agent_id}/web-sources",
    response_model=WebSource,
    status_code=status.HTTP_201_CREATED,
)
async def add_web_source(
    agent_id: str,
    request: WebSourceCreateRequest,
) -> WebSource:
    """Add a web source to an agent's knowledge base."""
    # Verify agent exists
    agent_manager = get_agent_manager()
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    knowledge_manager = get_knowledge_manager()
    try:
        source = knowledge_manager.add_web_source(
            agent_id=agent_id,
            url=request.url,
            name=request.name,
            description=request.description,
            refresh_interval_hours=request.refresh_interval_hours,
            selector=request.selector,
            auto_refresh=request.auto_refresh,
        )
        return source
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add web source: {e}",
        )


@router.post("/{agent_id}/web-sources/{source_id}/refresh", response_model=WebSource)
async def refresh_web_source(agent_id: str, source_id: str) -> WebSource:
    """Refresh a web source by re-fetching its content."""
    knowledge_manager = get_knowledge_manager()
    source = knowledge_manager.get_web_source(source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Web source '{source_id}' not found",
        )

    if source.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Web source does not belong to agent '{agent_id}'",
        )

    try:
        return knowledge_manager.refresh_web_source(source_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh web source: {e}",
        )


@router.delete(
    "/{agent_id}/web-sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_web_source(agent_id: str, source_id: str) -> None:
    """Delete a web source from an agent's knowledge base."""
    knowledge_manager = get_knowledge_manager()
    source = knowledge_manager.get_web_source(source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Web source '{source_id}' not found",
        )

    if source.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Web source does not belong to agent '{agent_id}'",
        )

    knowledge_manager.delete_web_source(source_id)


@router.get("/web-sources/all", response_model=WebSourceListResponse)
async def list_all_web_sources() -> WebSourceListResponse:
    """List all web sources across all agents."""
    knowledge_manager = get_knowledge_manager()
    sources = knowledge_manager.list_web_sources()
    return WebSourceListResponse(sources=sources, total=len(sources))


@router.post("/web-sources/refresh-all")
async def refresh_all_web_sources() -> dict[str, Any]:
    """Refresh all web sources that are due for refresh."""
    knowledge_manager = get_knowledge_manager()
    results = knowledge_manager.refresh_all_due_sources()
    return {
        "refreshed": len(results),
        "results": results,
    }


# =============================================================================
# Intelligent Routing Endpoint
# =============================================================================


class RoutingRequest(BaseModel):
    """Request for intelligent agent routing."""

    query: str = Field(..., min_length=1)
    consider_only_active: bool = True


class RoutingResponse(BaseModel):
    """Response from intelligent routing."""

    primary_agent_id: str
    primary_domain: str
    confidence: float
    alternative_agents: list[str]
    requires_clarification: bool
    clarification_prompt: str | None


@router.post("/route", response_model=RoutingResponse)
async def route_query(request: RoutingRequest) -> RoutingResponse:
    """Intelligently route a query to the most appropriate agent.

    Uses enhanced intent classification with confidence scoring and
    multi-intent detection to determine the best agent for a query.
    """
    # Get available agents if filtering to active only
    available_agents: list[str] | None = None
    if request.consider_only_active:
        agent_manager = get_agent_manager()
        agents = agent_manager.list_agents()
        available_agents = [a.id for a in agents if a.status == "active"]

    # Route the query
    result = route_to_agent(request.query, available_agents)

    return RoutingResponse(
        primary_agent_id=result.primary_agent_id,
        primary_domain=result.primary_domain,
        confidence=result.confidence,
        alternative_agents=result.alternative_agents,
        requires_clarification=result.requires_clarification,
        clarification_prompt=result.clarification_prompt,
    )
