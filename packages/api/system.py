"""System management API endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.core.agents import AgentConfig, get_agent_manager
from packages.core.knowledge import get_knowledge_manager

router = APIRouter(prefix="/system", tags=["System"])


class ClientSetupRequest(BaseModel):
    """Request to set up for a new client."""

    client_name: str = Field(..., min_length=1, description="Client/deployment name")
    organization: str = Field(..., min_length=1, description="Organization name")
    description: str = Field(default="", description="Optional description")


class ResetResponse(BaseModel):
    """Response after system reset."""

    message: str
    concierge: AgentConfig


def generate_concierge_prompt(client_name: str, organization: str, agents: list[AgentConfig]) -> str:
    """Generate a dynamic system prompt for the Concierge based on available agents."""

    # Build agent directory with access information
    agent_list = []
    agent_routing_map = []
    for agent in agents:
        if agent.id == "concierge":
            continue
        caps = ", ".join(agent.capabilities[:3]) if agent.capabilities else "General assistance"
        # Include agent access information
        agent_list.append(f"- **{agent.name}** (ID: `{agent.id}`, Domain: {agent.domain})")
        agent_list.append(f"  - Description: {agent.description[:150]}...")
        agent_list.append(f"  - Capabilities: {caps}")
        if agent.gpt_url:
            agent_list.append(f"  - External GPT: {agent.gpt_url}")
        agent_list.append("")

        # Build routing map for quick reference
        agent_routing_map.append(f"- {agent.domain} questions → **{agent.name}** (agent ID: {agent.id})")

    agent_directory = "\n".join(agent_list) if agent_list else "- No specialized agents configured yet."
    routing_map = "\n".join(agent_routing_map) if agent_routing_map else "- No routing configured yet."

    return f"""You are the AI Concierge for {organization}, the intelligent front door to our AI Operating System.

## Your Primary Mission
You are the SINGLE ENTRY POINT for {organization}'s AI assistant suite. Your job is to:
1. Understand what the user needs
2. **ALWAYS recommend the appropriate INTERNAL specialist agent first**
3. Provide the agent's name and ID so users can access them
4. Provide a warm, professional, and helpful experience

## CRITICAL ROUTING RULE
When a user asks about ANY department or topic covered by our specialist agents, you MUST:
1. **First and foremost**: Recommend our INTERNAL specialist agent by name and ID
2. Tell them: "I recommend speaking with our **[Agent Name]**. You can start a chat with them directly."
3. Only AFTER recommending the internal agent, you may also provide external resource links if relevant

## Quick Routing Reference
{routing_map}

## Available Specialist Agents (INTERNAL)
{agent_directory}

## Example Response Format
When user asks "How do I handle HR issues?" or "I need help with human resources":
"I'd recommend speaking with our **[HR Agent Name]** who specializes in employee services, benefits, and HR policies.

**Start a conversation with them:**
- Agent: [HR Agent Name]
- Domain: HR

They can help you with [relevant capabilities].

Additionally, you may find these external resources helpful: [external links if any]"

## How to Route
When a user's request falls within a specialist's domain:
1. Acknowledge their request
2. **Recommend the specific internal agent by name**
3. Tell them the agent ID so they can access it
4. Optionally provide supplementary external resources

## When to Handle Directly
Handle these yourself without routing:
- General greetings and small talk
- Questions about what AI services are available
- Requests to speak with a specific agent by name
- Helping users understand which agent they need

## Guidelines
- **ALWAYS prioritize internal agents over external resources**
- Be warm, professional, and concise
- Never guess or make up information - route to specialists when unsure
- Protect user privacy - don't ask for unnecessary personal information
- If a request seems urgent or involves safety, prioritize immediate helpful response

## About {organization}
{organization} - {client_name} deployment.
This AI Operating System includes {len([a for a in agents if a.id != "concierge"])} specialist agents ready to assist.
"""


def create_concierge(client_name: str, organization: str, agents: list[AgentConfig]) -> AgentConfig:
    """Create or update the Concierge agent with current agent awareness."""

    system_prompt = generate_concierge_prompt(client_name, organization, agents)

    return AgentConfig(
        id="concierge",
        name="AI Concierge",
        title="Intelligent Assistant Router",
        domain="Router",
        description=f"The front door to {organization}'s AI assistant network. Routes requests to the right specialist.",
        capabilities=[
            "Intent classification",
            "Intelligent routing",
            "General inquiries",
            "Service discovery",
            "Agent recommendations",
        ],
        guardrails=[
            "Never impersonate specialist agents",
            "Route when uncertain - don't guess",
            "Protect user privacy",
            "Be transparent about AI nature",
            "Escalate urgent/safety issues immediately",
        ],
        escalates_to="human-support",
        gpt_url="",
        system_prompt=system_prompt,
        is_router=True,
    )


@router.post("/reset", response_model=ResetResponse)
async def reset_for_new_client(request: ClientSetupRequest) -> ResetResponse:
    """Reset the system for a new client deployment.

    This will:
    1. Delete all existing agents
    2. Clear all knowledge bases
    3. Create a fresh Concierge agent configured for the new client
    """
    agent_manager = get_agent_manager()
    knowledge_manager = get_knowledge_manager()

    # Get all current agents and delete them
    current_agents = agent_manager.list_agents()
    for agent in current_agents:
        # Clear knowledge base first
        knowledge_manager.clear_agent_knowledge(agent.id)
        # Delete agent
        agent_manager.delete_agent(agent.id)

    # Also clean up the knowledge storage directory to ensure clean slate
    try:
        knowledge_path = knowledge_manager.storage_path
        if knowledge_path.exists():
            # Remove chroma data
            chroma_path = knowledge_path / "chroma"
            if chroma_path.exists():
                shutil.rmtree(chroma_path, ignore_errors=True)
            # Remove files
            files_path = knowledge_path / "files"
            if files_path.exists():
                shutil.rmtree(files_path, ignore_errors=True)
                files_path.mkdir(exist_ok=True)
    except Exception:
        pass  # Continue even if cleanup fails

    # Create the new Concierge
    concierge = create_concierge(
        client_name=request.client_name,
        organization=request.organization,
        agents=[],  # No other agents yet
    )

    # Save the concierge
    created = agent_manager.create_agent(concierge)

    return ResetResponse(
        message=f"System reset complete. Ready for {request.organization} ({request.client_name}).",
        concierge=created,
    )


@router.post("/regenerate-concierge", response_model=AgentConfig)
async def regenerate_concierge() -> AgentConfig:
    """Regenerate the Concierge agent with awareness of all current agents.

    Call this after adding/removing agents to update the Concierge's knowledge
    of available specialists.
    """
    agent_manager = get_agent_manager()

    # Get current agents
    agents = agent_manager.list_agents()

    # Find existing concierge to get client info, or use defaults
    existing_concierge = agent_manager.get_agent("concierge")

    if existing_concierge:
        # Extract organization from existing prompt or use default
        # Try to parse from the description
        description = existing_concierge.description
        if "'" in description:
            org_start = description.find("'s AI")
            if org_start > 0:
                organization = description[:org_start].replace("The front door to ", "")
            else:
                organization = "HAAIS AIOS"
        else:
            organization = "HAAIS AIOS"
        client_name = "Default Deployment"
    else:
        organization = "HAAIS AIOS"
        client_name = "Default Deployment"

    # Create updated concierge
    concierge = create_concierge(
        client_name=client_name,
        organization=organization,
        agents=agents,
    )

    # Update or create
    if existing_concierge:
        updated = agent_manager.update_agent("concierge", {
            "system_prompt": concierge.system_prompt,
            "description": concierge.description,
        })
        if updated:
            return updated

    # Create new if doesn't exist
    return agent_manager.create_agent(concierge)


@router.get("/info")
async def get_system_info() -> dict:
    """Get current system configuration info."""
    agent_manager = get_agent_manager()
    agents = agent_manager.list_agents()

    concierge = agent_manager.get_agent("concierge")

    return {
        "total_agents": len(agents),
        "active_agents": len([a for a in agents if a.status == "active"]),
        "has_concierge": concierge is not None,
        "concierge_status": concierge.status if concierge else None,
        "agent_domains": list(set(a.domain for a in agents)),
    }


# =============================================================================
# Template Export/Import
# =============================================================================


class ExportTemplateRequest(BaseModel):
    """Request to export current setup as template."""
    template_name: str = Field(..., min_length=1, description="Name for the template")
    description: str = Field(default="", description="Template description")


class ImportTemplateRequest(BaseModel):
    """Request to import agents from a template."""
    template_id: str = Field(..., description="Template ID to import")
    merge: bool = Field(default=True, description="Merge with existing agents (vs replace)")


@router.post("/export-template")
async def export_as_template(request: ExportTemplateRequest) -> dict:
    """Export current agent configuration as a reusable template.

    Creates a template file that can be loaded later to recreate the setup.
    """
    import json
    from datetime import datetime

    agent_manager = get_agent_manager()
    agents = agent_manager.list_agents()

    # Build template
    template = {
        "id": request.template_name.lower().replace(" ", "-"),
        "name": request.template_name,
        "description": request.description,
        "created_at": datetime.utcnow().isoformat(),
        "agent_count": len([a for a in agents if a.id != "concierge"]),
        "agents": []
    }

    for agent in agents:
        if agent.id == "concierge":
            continue  # Don't include concierge in templates

        template["agents"].append({
            "id": agent.id,
            "name": agent.name,
            "title": agent.title,
            "domain": agent.domain,
            "description": agent.description,
            "capabilities": agent.capabilities,
            "guardrails": agent.guardrails,
            "escalates_to": agent.escalates_to,
            "gpt_url": agent.gpt_url,
            "system_prompt": agent.system_prompt,
        })

    # Save to templates directory
    templates_path = Path("data/templates")
    templates_path.mkdir(parents=True, exist_ok=True)

    template_file = templates_path / f"{template['id']}.json"
    with open(template_file, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    return {
        "success": True,
        "template_id": template["id"],
        "template_name": template["name"],
        "agent_count": template["agent_count"],
        "file_path": str(template_file),
    }


@router.get("/templates")
async def list_templates() -> dict:
    """List all available templates."""
    import json

    templates_path = Path("data/templates")
    if not templates_path.exists():
        return {"templates": []}

    templates = []
    for file in templates_path.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                template = json.load(f)
                templates.append({
                    "id": template.get("id"),
                    "name": template.get("name"),
                    "description": template.get("description"),
                    "agent_count": template.get("agent_count"),
                    "created_at": template.get("created_at"),
                })
        except Exception:
            continue

    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> dict:
    """Get a specific template by ID."""
    import json

    template_file = Path(f"data/templates/{template_id}.json")
    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )

    with open(template_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/import-template")
async def import_template(request: ImportTemplateRequest) -> dict:
    """Import agents from a saved template.

    This will create agents from the template. If merge=False, existing
    non-router agents will be deleted first.
    """
    import json

    template_file = Path(f"data/templates/{request.template_id}.json")
    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_id}' not found"
        )

    with open(template_file, "r", encoding="utf-8") as f:
        template = json.load(f)

    agent_manager = get_agent_manager()
    knowledge_manager = get_knowledge_manager()

    # If not merging, delete existing non-router agents first
    if not request.merge:
        current_agents = agent_manager.list_agents()
        for agent in current_agents:
            if not agent.is_router:  # Keep the concierge
                knowledge_manager.clear_agent_knowledge(agent.id)
                agent_manager.delete_agent(agent.id)

    # Create agents from template
    created = []
    skipped = []
    for agent_data in template.get("agents", []):
        # Check if agent already exists
        existing = agent_manager.get_agent(agent_data["id"])
        if existing:
            skipped.append(agent_data["name"])
            continue

        new_agent = AgentConfig(
            id=agent_data["id"],
            name=agent_data["name"],
            title=agent_data.get("title", ""),
            domain=agent_data.get("domain", "General"),
            description=agent_data.get("description", ""),
            capabilities=agent_data.get("capabilities", []),
            guardrails=agent_data.get("guardrails", []),
            escalates_to=agent_data.get("escalates_to", ""),
            gpt_url=agent_data.get("gpt_url", ""),
            system_prompt=agent_data.get("system_prompt", ""),
        )

        try:
            agent_manager.create_agent(new_agent)
            created.append(agent_data["name"])
        except Exception as e:
            skipped.append(f"{agent_data['name']} (error: {str(e)})")

    # Regenerate concierge to include new agents
    if created:
        await regenerate_concierge()

    return {
        "success": True,
        "template_name": template.get("name"),
        "created": len(created),
        "skipped": len(skipped),
        "created_agents": created,
        "skipped_agents": skipped,
        "message": f"Imported {len(created)} agents from '{template.get('name')}'"
    }


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str) -> dict:
    """Delete a saved template."""
    template_file = Path(f"data/templates/{template_id}.json")
    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )

    template_file.unlink()
    return {"success": True, "message": f"Template '{template_id}' deleted"}


# =============================================================================
# Pending Agents Queue (Human-in-the-Loop)
# =============================================================================

# In-memory pending queue (in production, use database)
_pending_agents: dict[str, dict] = {}


class PendingAgentRequest(BaseModel):
    """Request to add an agent to pending approval queue."""
    id: str
    name: str
    title: str = ""
    domain: str = "General"
    description: str = ""
    capabilities: list[str] = []
    guardrails: list[str] = []
    gpt_url: str = ""
    system_prompt: str = ""
    source: str = "manual"  # "manual", "discovery", "template"


@router.post("/pending-agents")
async def add_pending_agent(request: PendingAgentRequest) -> dict:
    """Add an agent to the pending approval queue.

    Agents in the pending queue require human approval before being created.
    """
    from datetime import datetime

    pending_id = f"pending-{request.id}-{int(datetime.utcnow().timestamp())}"

    _pending_agents[pending_id] = {
        "pending_id": pending_id,
        "agent": request.model_dump(),
        "submitted_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "source": request.source,
    }

    return {
        "pending_id": pending_id,
        "status": "pending",
        "message": f"Agent '{request.name}' added to approval queue",
    }


@router.post("/pending-agents/bulk")
async def add_pending_agents_bulk(agents: list[PendingAgentRequest]) -> dict:
    """Add multiple agents to the pending approval queue."""
    from datetime import datetime

    results = []
    for request in agents:
        pending_id = f"pending-{request.id}-{int(datetime.utcnow().timestamp())}"

        _pending_agents[pending_id] = {
            "pending_id": pending_id,
            "agent": request.model_dump(),
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "source": request.source,
        }
        results.append({"pending_id": pending_id, "name": request.name})

    return {
        "added": len(results),
        "agents": results,
    }


@router.get("/pending-agents")
async def list_pending_agents() -> dict:
    """List all agents pending approval."""
    return {
        "total": len(_pending_agents),
        "pending": list(_pending_agents.values()),
    }


@router.post("/pending-agents/{pending_id}/approve")
async def approve_pending_agent(pending_id: str) -> dict:
    """Approve a pending agent and create it."""
    if pending_id not in _pending_agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending agent '{pending_id}' not found"
        )

    pending = _pending_agents[pending_id]
    agent_data = pending["agent"]

    # Create the agent
    agent_manager = get_agent_manager()

    new_agent = AgentConfig(
        id=agent_data["id"],
        name=agent_data["name"],
        title=agent_data.get("title", ""),
        domain=agent_data.get("domain", "General"),
        description=agent_data.get("description", ""),
        capabilities=agent_data.get("capabilities", []),
        guardrails=agent_data.get("guardrails", []),
        escalates_to=agent_data.get("escalates_to", ""),
        gpt_url=agent_data.get("gpt_url", ""),
        system_prompt=agent_data.get("system_prompt", ""),
    )

    created = agent_manager.create_agent(new_agent)

    # Remove from pending
    del _pending_agents[pending_id]

    # Regenerate concierge to include new agent
    await regenerate_concierge()

    return {
        "success": True,
        "agent": created.model_dump() if hasattr(created, 'model_dump') else created.__dict__,
        "message": f"Agent '{created.name}' approved and created",
    }


@router.post("/pending-agents/{pending_id}/reject")
async def reject_pending_agent(pending_id: str, reason: str = "") -> dict:
    """Reject a pending agent."""
    if pending_id not in _pending_agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending agent '{pending_id}' not found"
        )

    pending = _pending_agents[pending_id]
    agent_name = pending["agent"]["name"]

    # Remove from pending
    del _pending_agents[pending_id]

    return {
        "success": True,
        "message": f"Agent '{agent_name}' rejected",
        "reason": reason,
    }


@router.post("/pending-agents/approve-all")
async def approve_all_pending_agents() -> dict:
    """Approve all pending agents at once."""
    agent_manager = get_agent_manager()
    approved = []

    for pending_id, pending in list(_pending_agents.items()):
        agent_data = pending["agent"]

        new_agent = AgentConfig(
            id=agent_data["id"],
            name=agent_data["name"],
            title=agent_data.get("title", ""),
            domain=agent_data.get("domain", "General"),
            description=agent_data.get("description", ""),
            capabilities=agent_data.get("capabilities", []),
            guardrails=agent_data.get("guardrails", []),
            escalates_to=agent_data.get("escalates_to", ""),
            gpt_url=agent_data.get("gpt_url", ""),
            system_prompt=agent_data.get("system_prompt", ""),
        )

        try:
            created = agent_manager.create_agent(new_agent)
            approved.append(created.name)
            del _pending_agents[pending_id]
        except Exception as e:
            continue

    # Regenerate concierge
    if approved:
        await regenerate_concierge()

    return {
        "approved": len(approved),
        "agents": approved,
    }


@router.delete("/pending-agents")
async def clear_pending_agents() -> dict:
    """Clear all pending agents."""
    count = len(_pending_agents)
    _pending_agents.clear()
    return {"cleared": count}
