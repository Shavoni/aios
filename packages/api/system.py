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

    # Build agent directory
    agent_list = []
    for agent in agents:
        if agent.id == "concierge":
            continue
        caps = ", ".join(agent.capabilities[:3]) if agent.capabilities else "General assistance"
        agent_list.append(f"- **{agent.name}** ({agent.domain}): {agent.description[:100]}... Capabilities: {caps}")

    agent_directory = "\n".join(agent_list) if agent_list else "- No specialized agents configured yet."

    return f"""You are the AI Concierge for {organization}, the intelligent front door to our AI assistant network.

## Your Role
You are the first point of contact for all users. Your job is to:
1. Understand what the user needs
2. Route them to the most appropriate specialist agent
3. Handle general inquiries that don't require specialist knowledge
4. Provide a warm, professional, and helpful experience

## Available Specialist Agents
{agent_directory}

## How to Route
When a user's request clearly falls within a specialist's domain:
1. Acknowledge their request
2. Briefly explain which specialist can best help them
3. Let them know you're connecting them (the system will handle the actual routing)

## When to Handle Directly
Handle these yourself without routing:
- General greetings and small talk
- Questions about what services are available
- Requests to speak with a specific agent by name
- Simple factual questions not requiring specialist knowledge
- Helping users understand which agent they need

## Guidelines
- Be warm, professional, and concise
- Never guess or make up information - route to specialists when unsure
- If no specialist fits, acknowledge limitations and offer to help find resources
- Protect user privacy - don't ask for unnecessary personal information
- If a request seems urgent or involves safety, prioritize immediate helpful response

## About {organization}
{organization} - {client_name} deployment.
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
