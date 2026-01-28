"""Onboarding API endpoints for municipal AI deployment."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# Request/Response Models
# =============================================================================


class DiscoverRequest(BaseModel):
    """Request to start discovery."""
    url: str = Field(..., min_length=1, description="Municipal website URL")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format for municipal website discovery."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(v)
            # Only allow http and https
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Only HTTP and HTTPS URLs are allowed")
            if not parsed.netloc:
                raise ValueError("Invalid URL: missing domain")
            # Block obviously non-municipal URLs
            netloc_lower = parsed.netloc.lower()
            if any(blocked in netloc_lower for blocked in ["localhost", "127.0.0.1", "0.0.0.0"]):
                raise ValueError("Internal URLs are not allowed")
            return v
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid URL format")


class DiscoverResponse(BaseModel):
    """Response with discovery job ID."""
    job_id: str
    status: str
    message: str


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""
    departments: list[dict[str, Any]] | None = None
    data_sources: list[dict[str, Any]] | None = None
    executive: dict[str, Any] | None = None
    sync: dict[str, Any] | None = None


class DeployRequest(BaseModel):
    """Request to start deployment."""
    config_id: str


class DeployResponse(BaseModel):
    """Response with deployment job ID."""
    deploy_id: str
    status: str
    message: str


# =============================================================================
# Discovery Endpoints
# =============================================================================


@router.post("/discover", response_model=DiscoverResponse)
async def start_discovery(request: DiscoverRequest) -> DiscoverResponse:
    """Start discovery for a municipal website.

    Crawls the website to discover organizational structure,
    departments, officials, and open data portals.
    """
    try:
        from packages.onboarding.discovery import start_discovery as _start_discovery

        job_id = _start_discovery(request.url)
        return DiscoverResponse(
            job_id=job_id,
            status="started",
            message=f"Discovery started for {request.url}",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.get("/discover/{job_id}")
async def get_discovery_status(job_id: str) -> dict[str, Any]:
    """Get the status of a discovery job."""
    from packages.onboarding.discovery import get_discovery_status as _get_status

    result = _get_status(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found",
        )

    return result.to_dict()


@router.get("/discover")
async def list_discoveries() -> dict[str, Any]:
    """List all discovery jobs."""
    from packages.onboarding.discovery import get_discovery_engine

    engine = get_discovery_engine()
    jobs = list(engine._jobs.values())
    return {
        "total": len(jobs),
        "discoveries": [j.to_dict() for j in jobs],
    }


# =============================================================================
# Catalog Endpoints
# =============================================================================


@router.get("/catalog/{discovery_id}")
async def get_catalog(discovery_id: str) -> dict[str, Any]:
    """Get the data catalog for a discovery.

    Extracts datasets from any discovered open data portals.
    """
    from packages.onboarding.discovery import get_discovery_status
    from packages.onboarding.catalog import extract_catalog

    # Get discovery result
    discovery = get_discovery_status(discovery_id)
    if not discovery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery '{discovery_id}' not found",
        )

    if not discovery.data_portals:
        return {
            "discovery_id": discovery_id,
            "catalogs": [],
            "total_datasets": 0,
        }

    # Extract catalogs from discovered portals
    catalogs = []
    total_datasets = 0

    for portal in discovery.data_portals:
        try:
            catalog = extract_catalog(portal.url, portal.type)
            catalogs.append(catalog.to_dict())
            total_datasets += catalog.dataset_count
        except Exception as e:
            catalogs.append({
                "portal": {"url": portal.url, "type": portal.type},
                "error": str(e),
                "datasets": [],
            })

    return {
        "discovery_id": discovery_id,
        "catalogs": catalogs,
        "total_datasets": total_datasets,
    }


# =============================================================================
# Configuration Endpoints
# =============================================================================


@router.post("/config/{discovery_id}")
async def create_config(discovery_id: str) -> dict[str, Any]:
    """Create a configuration from discovery results."""
    from packages.onboarding.discovery import get_discovery_status
    from packages.onboarding.catalog import extract_catalog
    from packages.onboarding.config import get_config_manager

    # Get discovery result
    discovery = get_discovery_status(discovery_id)
    if not discovery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery '{discovery_id}' not found",
        )

    if discovery.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discovery not complete. Status: {discovery.status.value}",
        )

    # Get catalog if data portals exist
    catalog = None
    if discovery.data_portals:
        try:
            # Use first portal
            catalog = extract_catalog(
                discovery.data_portals[0].url,
                discovery.data_portals[0].type,
            )
        except Exception:
            pass

    # Create configuration
    manager = get_config_manager()
    config = manager.create_from_discovery(discovery, catalog)
    manager.save(config)

    return config.to_dict()


@router.get("/config/{config_id}")
async def get_config(config_id: str) -> dict[str, Any]:
    """Get a configuration by ID."""
    from packages.onboarding.config import load_config

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    return config.to_dict()


@router.put("/config/{config_id}")
async def update_config(config_id: str, request: ConfigUpdateRequest) -> dict[str, Any]:
    """Update a configuration."""
    from packages.onboarding.config import load_config, save_config, DepartmentConfig, DataSourceConfig

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    # Update departments
    if request.departments is not None:
        config.departments = [
            DepartmentConfig(
                id=d.get("id", ""),
                name=d.get("name", ""),
                enabled=d.get("enabled", True),
                template_id=d.get("template_id"),
                director_name=d.get("director_name"),
                director_title=d.get("director_title"),
                custom_name=d.get("custom_name"),
                custom_description=d.get("custom_description"),
                data_source_ids=d.get("data_source_ids", []),
            )
            for d in request.departments
        ]

    # Update data sources
    if request.data_sources is not None:
        config.data_sources = [
            DataSourceConfig(
                id=s.get("id", ""),
                name=s.get("name", ""),
                enabled=s.get("enabled", True),
                department_id=s.get("department_id"),
                sync_frequency=s.get("sync_frequency", "daily"),
                api_endpoint=s.get("api_endpoint"),
            )
            for s in request.data_sources
        ]

    # Update executive
    if request.executive is not None:
        config.executive.enable_mayor = request.executive.get("enable_mayor", True)
        config.executive.mayor_name = request.executive.get("mayor_name")
        config.executive.mayor_title = request.executive.get("mayor_title", "Mayor")

    # Update sync config
    if request.sync is not None:
        config.sync.default_refresh_hours = request.sync.get("default_refresh_hours", 24)
        config.sync.notify_on_sync_failure = request.sync.get("notify_on_sync_failure", True)
        config.sync.notification_email = request.sync.get("notification_email")

    save_config(config)
    return config.to_dict()


@router.get("/config")
async def list_configs() -> dict[str, Any]:
    """List all configurations."""
    from packages.onboarding.config import get_config_manager

    manager = get_config_manager()
    configs = manager.list_configs()
    return {
        "total": len(configs),
        "configs": [c.to_dict() for c in configs],
    }


@router.post("/config/{config_id}/validate")
async def validate_config(config_id: str) -> dict[str, Any]:
    """Validate a configuration before deployment."""
    from packages.onboarding.config import load_config, validate_config as _validate

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    return _validate(config)


# =============================================================================
# Manifest Endpoints
# =============================================================================


@router.post("/manifest/{config_id}")
async def generate_manifest(config_id: str) -> dict[str, Any]:
    """Generate a deployment manifest from configuration."""
    from packages.onboarding.config import load_config
    from packages.onboarding.manifest import generate_manifest as _generate

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    manifest = _generate(config)
    return manifest.to_dict()


# =============================================================================
# Deployment Endpoints
# =============================================================================


@router.post("/deploy", response_model=DeployResponse)
async def start_deployment(request: DeployRequest) -> DeployResponse:
    """Start deployment of a configuration."""
    from packages.onboarding.config import load_config
    from packages.onboarding.manifest import generate_manifest
    from packages.onboarding.deploy import start_deployment as _start_deploy

    config = load_config(request.config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{request.config_id}' not found",
        )

    # Generate manifest
    manifest = generate_manifest(config)

    # Start deployment
    deploy_id = _start_deploy(manifest)

    return DeployResponse(
        deploy_id=deploy_id,
        status="started",
        message=f"Deployment started for {config.municipality_name}",
    )


@router.get("/deploy/{deploy_id}")
async def get_deployment_status(deploy_id: str) -> dict[str, Any]:
    """Get the status of a deployment."""
    from packages.onboarding.deploy import get_deployment_status as _get_status

    result = _get_status(deploy_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment '{deploy_id}' not found",
        )

    return result.to_dict()


@router.get("/deploy")
async def list_deployments() -> dict[str, Any]:
    """List all deployments."""
    from packages.onboarding.deploy import get_orchestrator

    orchestrator = get_orchestrator()
    deployments = list(orchestrator._deployments.values())
    return {
        "total": len(deployments),
        "deployments": [d.to_dict() for d in deployments],
    }


# =============================================================================
# Templates Endpoint
# =============================================================================


@router.get("/templates")
async def get_agent_templates() -> dict[str, Any]:
    """Get available agent templates."""
    from packages.onboarding.manifest import AGENT_TEMPLATES

    templates = []
    for template_id, template in AGENT_TEMPLATES.items():
        templates.append({
            "id": template_id,
            "name_format": template["name_format"],
            "title_format": template["title_format"],
            "domain": template["domain"],
            "capabilities": template["capabilities"],
            "guardrails": template["guardrails"],
            "sensitivity": template["sensitivity"],
        })

    return {
        "total": len(templates),
        "templates": templates,
    }


# =============================================================================
# Platform Endpoints
# =============================================================================


class PlatformGenerateRequest(BaseModel):
    """Request for platform-specific generation."""
    platform_config: dict[str, Any] | None = None


class MultiPlatformGenerateRequest(BaseModel):
    """Request for multi-platform generation."""
    platforms: list[str] | None = None
    platform_configs: dict[str, dict[str, Any]] | None = None


@router.get("/platforms")
async def list_platforms() -> dict[str, Any]:
    """List all available AI platforms.

    Returns information about each supported platform including
    constraints, capabilities, and deployment requirements.
    """
    from packages.onboarding.platforms import get_available_platforms

    platforms = get_available_platforms()
    return {
        "total": len(platforms),
        "platforms": platforms,
    }


@router.get("/platforms/{platform_id}")
async def get_platform_info(platform_id: str) -> dict[str, Any]:
    """Get detailed information about a specific platform.

    Includes all constraints and capabilities.
    """
    from packages.onboarding.platforms import get_platform_constraints

    constraints = get_platform_constraints(platform_id)
    if not constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{platform_id}' not found",
        )

    return {
        "platform_id": platform_id,
        **constraints,
    }


@router.post("/manifest/{config_id}/platform/{platform}")
async def generate_for_platform(
    config_id: str,
    platform: str,
    request: PlatformGenerateRequest | None = None,
) -> dict[str, Any]:
    """Generate agent configuration for a specific platform.

    Converts the platform-agnostic manifest to a platform-specific
    configuration with appropriate truncation and adaptation.
    """
    from packages.onboarding.config import load_config
    from packages.onboarding.manifest import generate_manifest
    from packages.onboarding.platforms import (
        generate_for_platform as _generate,
        PlatformConfig,
        PlatformType,
    )

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    # Generate manifest
    manifest = generate_manifest(config)

    # Parse platform config if provided
    platform_config = None
    if request and request.platform_config:
        try:
            platform_type = PlatformType(platform)
            platform_config = PlatformConfig(
                platform=platform_type,
                **request.platform_config,
            )
        except (ValueError, TypeError):
            pass

    # Generate for each agent in the manifest
    results = []
    for agent_manifest in manifest.agents:
        try:
            output = _generate(agent_manifest, platform, platform_config)
            results.append(output.to_dict())
        except Exception as e:
            results.append({
                "agent_id": agent_manifest.id,
                "error": str(e),
            })

    return {
        "platform": platform,
        "config_id": config_id,
        "municipality": config.municipality_name,
        "agent_count": len(results),
        "agents": results,
    }


@router.post("/manifest/{config_id}/platforms")
async def generate_for_all_platforms(
    config_id: str,
    request: MultiPlatformGenerateRequest | None = None,
) -> dict[str, Any]:
    """Generate agent configurations for multiple platforms.

    Useful for comparing outputs or deploying to multiple platforms.
    """
    from packages.onboarding.config import load_config
    from packages.onboarding.manifest import generate_manifest
    from packages.onboarding.platforms import (
        generate_for_all_platforms as _generate_all,
        PlatformConfig,
        PlatformType,
    )

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    # Generate manifest
    manifest = generate_manifest(config)

    # Parse platforms list
    platforms = None
    if request and request.platforms:
        platforms = request.platforms

    # Parse platform configs
    platform_configs = {}
    if request and request.platform_configs:
        for plat, pc in request.platform_configs.items():
            try:
                platform_type = PlatformType(plat)
                platform_configs[plat] = PlatformConfig(
                    platform=platform_type,
                    **pc,
                )
            except (ValueError, TypeError):
                pass

    # Generate for each agent across all platforms
    all_results = {}
    for agent_manifest in manifest.agents:
        agent_results = _generate_all(
            agent_manifest,
            platforms=platforms,
            platform_configs=platform_configs,
        )
        all_results[agent_manifest.id] = {
            platform: output.to_dict()
            for platform, output in agent_results.items()
        }

    return {
        "config_id": config_id,
        "municipality": config.municipality_name,
        "agent_count": len(manifest.agents),
        "platforms": list(all_results.get(manifest.agents[0].id, {}).keys()) if manifest.agents else [],
        "agents": all_results,
    }


@router.post("/manifest/{config_id}/compare")
async def compare_platforms_for_manifest(
    config_id: str,
    request: MultiPlatformGenerateRequest | None = None,
) -> dict[str, Any]:
    """Compare how a manifest would be adapted across platforms.

    Shows what content would be truncated on each platform
    and recommends the best fit.
    """
    from packages.onboarding.config import load_config
    from packages.onboarding.manifest import generate_manifest
    from packages.onboarding.platforms import compare_platforms

    config = load_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    # Generate manifest
    manifest = generate_manifest(config)

    # Parse platforms list
    platforms = None
    if request and request.platforms:
        platforms = request.platforms

    # Compare each agent across platforms
    comparisons = {}
    for agent_manifest in manifest.agents:
        comparisons[agent_manifest.id] = compare_platforms(
            agent_manifest,
            platforms=platforms,
        )

    return {
        "config_id": config_id,
        "municipality": config.municipality_name,
        "agent_count": len(manifest.agents),
        "comparisons": comparisons,
    }
