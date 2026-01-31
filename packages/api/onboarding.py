"""Onboarding API endpoints for municipal AI deployment."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CrawlConfigRequest(BaseModel):
    """Configuration for controlled discovery crawl."""
    max_pages: int = Field(default=50, ge=10, le=250, description="Maximum pages to crawl")
    max_depth: int = Field(default=2, ge=1, le=4, description="Maximum crawl depth")
    timeout_seconds: int = Field(default=120, ge=30, le=600, description="Timeout in seconds")
    mode: str = Field(default="shallow", description="Discovery mode: shallow, targeted, or full")

    # Scope controls
    include_leadership: bool = Field(default=True, description="Include leadership/executives")
    include_departments: bool = Field(default=True, description="Include departments")
    include_services: bool = Field(default=True, description="Include services")
    include_data_portals: bool = Field(default=True, description="Include data portals")

    # Caching
    use_cache: bool = Field(default=True, description="Use cached results if available")


class DiscoverRequest(BaseModel):
    """Request to start discovery.

    Accepts either:
    - query: Organization name (e.g., 'IBM', 'CNN') or URL
    - url: Website URL (deprecated, use 'query' instead)
    """
    query: str | None = Field(default=None, description="Organization name or website URL (e.g., 'IBM', 'CNN', 'clevelandohio.gov')")
    config: CrawlConfigRequest | None = Field(default=None, description="Optional crawl configuration")

    # Backwards compatibility - accept 'url' as alias for 'query'
    url: str | None = Field(default=None, description="Deprecated: use 'query' instead")

    @property
    def input(self) -> str:
        """Get the actual input (query or url for backwards compat)."""
        return self.query or self.url or ""

    @field_validator("query", mode="after")
    @classmethod
    def validate_not_empty(cls, v, info):
        """Validate query is not empty if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("query cannot be empty")
        return v

    def model_post_init(self, __context):
        """Ensure at least one of query or url is provided."""
        if not self.query and not self.url:
            raise ValueError("Either 'query' or 'url' must be provided")


class CandidateSelectionRequest(BaseModel):
    """Request to update candidate selections."""
    selections: dict[str, bool] = Field(..., description="Map of candidate ID to selected status")


class DiscoverResponse(BaseModel):
    """Response with discovery job ID."""
    job_id: str
    status: str
    message: str
    cached: bool = False
    # Organization info from resolution
    organization_name: str | None = None
    organization_url: str | None = None
    organization_type: str | None = None  # "enterprise", "municipal", "education", "nonprofit"
    resolution_confidence: str | None = None  # "known", "provided", "guessed"


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
    """Start discovery for an organization.

    Accepts either an organization name (e.g., "IBM", "CNN", "Cleveland")
    or a URL (e.g., "clevelandohio.gov").

    For enterprise organizations, focuses on:
    - Leadership/Executive team (CEO, COO, CFO, etc.)
    - Departments and divisions
    - Organizational structure

    For municipal organizations, focuses on:
    - Government departments
    - Officials and leadership
    - Services and data portals

    With controlled discovery (default mode=shallow):
    1. Fast inventory scan with configurable limits
    2. Returns candidates for user selection
    3. User selects which items to deep crawl
    4. Deep crawl only approved selections
    """
    try:
        from packages.onboarding.discovery import (
            start_discovery as _start_discovery,
            CrawlConfig,
            DiscoveryMode,
            get_discovery_engine,
        )
        from packages.onboarding.resolver import resolve_organization, get_resolver

        # Resolve input (name or URL) to organization info
        # Supports intent queries like "IBM leadership" or "Microsoft corporate team"
        org_info = resolve_organization(request.input)
        url = org_info["url"]
        org_name = org_info["name"]
        org_type = org_info["type"]
        confidence = org_info["confidence"]
        detected_intents = org_info.get("intent", [])

        # Get priority paths - use intent-based paths if detected, else org-type defaults
        resolver = get_resolver()
        intent_paths = org_info.get("priority_paths", [])
        if intent_paths:
            # User specified intent (e.g., "leadership", "executives")
            # Combine intent paths with org-type defaults
            priority_paths = intent_paths + resolver.get_priority_paths(org_type)
        else:
            priority_paths = resolver.get_priority_paths(org_type)

        # Build config from request, always including org_type and priority_paths
        use_cache = True

        if request.config:
            try:
                mode = DiscoveryMode(request.config.mode)
            except ValueError:
                mode = DiscoveryMode.SHALLOW

            config = CrawlConfig(
                max_pages=request.config.max_pages,
                max_depth=request.config.max_depth,
                timeout_seconds=request.config.timeout_seconds,
                mode=mode,
                include_leadership=request.config.include_leadership,
                include_departments=request.config.include_departments,
                include_services=request.config.include_services,
                include_data_portals=request.config.include_data_portals,
                priority_paths=priority_paths,
                org_type=org_type,
            )
            use_cache = request.config.use_cache
        else:
            config = CrawlConfig(
                priority_paths=priority_paths,
                org_type=org_type,
            )

        # Try to use cached results if enabled
        if use_cache:
            engine = get_discovery_engine()
            job_id, is_cached = engine.get_cached_or_start(url, config)
            if is_cached:
                return DiscoverResponse(
                    job_id=job_id,
                    status="cached",
                    message=f"Using cached discovery results for {org_name} ({url})",
                    cached=True,
                    organization_name=org_name,
                    organization_url=url,
                    organization_type=org_type,
                    resolution_confidence=confidence,
                )

        # Start fresh discovery
        job_id = _start_discovery(url, config)

        # Build response message based on confidence and intent
        intent_str = f" focusing on {', '.join(detected_intents)}" if detected_intents else ""
        if confidence == "known":
            message = f"Discovery started for {org_name} ({url}){intent_str}"
        elif confidence == "guessed":
            message = f"Discovery started for {org_name} (inferred URL: {url}){intent_str}"
        else:
            message = f"Discovery started for {url}{intent_str}"

        return DiscoverResponse(
            job_id=job_id,
            status="started",
            message=message,
            cached=False,
            organization_name=org_name,
            organization_url=url,
            organization_type=org_type,
            resolution_confidence=confidence,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/discover/{job_id}/cancel")
async def cancel_discovery(job_id: str) -> dict[str, Any]:
    """Cancel a running discovery job."""
    from packages.onboarding.discovery import cancel_discovery as _cancel_discovery

    success = _cancel_discovery(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found or cannot be cancelled",
        )

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Discovery job cancelled successfully",
    }


@router.get("/discover/{job_id}/candidates")
async def get_discovery_candidates(job_id: str) -> dict[str, Any]:
    """Get discovered candidates for user selection.

    Returns the list of discovered items (departments, leadership, etc.)
    that the user can select or deselect before proceeding with deep crawl.
    """
    from packages.onboarding.discovery import get_discovery_status as _get_status

    result = _get_status(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found",
        )

    return {
        "job_id": job_id,
        "status": result.status.value,
        "total_candidates": len(result.candidates),
        "candidates": [c.to_dict() for c in result.candidates],
        "progress": {
            "pages_crawled": result.pages_crawled,
            "departments_detected": result.departments_detected,
            "leaders_detected": result.leaders_detected,
            "data_portals_detected": result.data_portals_detected,
        },
    }


@router.put("/discover/{job_id}/candidates")
async def update_candidate_selections(
    job_id: str,
    request: CandidateSelectionRequest,
) -> dict[str, Any]:
    """Update which candidates are selected for deep crawl.

    Send a map of candidate IDs to their selected status (true/false).
    Only selected candidates will be included in agent creation.
    """
    from packages.onboarding.discovery import (
        update_candidate_selection as _update_selection,
        get_discovery_status as _get_status,
    )

    success = _update_selection(job_id, request.selections)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found",
        )

    result = _get_status(job_id)
    selected_count = sum(1 for c in result.candidates if c.selected) if result else 0

    return {
        "job_id": job_id,
        "status": "updated",
        "total_candidates": len(result.candidates) if result else 0,
        "selected_count": selected_count,
        "message": f"Updated candidate selections: {selected_count} selected",
    }


@router.get("/discover/{job_id}/selected")
async def get_selected_candidates(job_id: str) -> dict[str, Any]:
    """Get only the selected candidates from a discovery job."""
    from packages.onboarding.discovery import get_selected_candidates as _get_selected

    selected = _get_selected(job_id)
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found",
        )

    return {
        "job_id": job_id,
        "selected_count": len(selected),
        "candidates": [c.to_dict() for c in selected],
    }


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
