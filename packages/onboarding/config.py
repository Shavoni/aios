"""Configuration management for municipal onboarding."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ConfigSection(str, Enum):
    """Configuration sections matching the UI checklist."""
    CORE_INFRASTRUCTURE = "core_infrastructure"
    EXECUTIVE_OFFICE = "executive_office"
    DEPARTMENTS = "departments"
    DATA_SOURCES = "data_sources"
    GIS_SERVICES = "gis_services"
    EXTERNAL_APIS = "external_apis"
    MANUAL_IMPORTS = "manual_imports"
    SYNC_CONFIG = "sync_config"


@dataclass
class CoreInfraConfig:
    """Core infrastructure configuration (always included)."""
    enable_concierge: bool = True
    enable_governance: bool = True
    enable_analytics: bool = True
    enable_audit: bool = True
    enable_sessions: bool = True


@dataclass
class ExecutiveConfig:
    """Executive office agent configuration."""
    enable_mayor: bool = True
    mayor_name: str | None = None
    mayor_title: str = "Mayor"
    enable_chief_of_staff: bool = False
    chief_officers: list[dict[str, str]] = field(default_factory=list)


@dataclass
class DepartmentConfig:
    """Configuration for a single department."""
    id: str
    name: str
    enabled: bool = True
    template_id: str | None = None
    director_name: str | None = None
    director_title: str | None = None
    custom_name: str | None = None
    custom_description: str | None = None
    data_source_ids: list[str] = field(default_factory=list)


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    enabled: bool = True
    department_id: str | None = None
    sync_frequency: str = "daily"  # daily, hourly, weekly, manual
    api_endpoint: str | None = None


@dataclass
class GISConfig:
    """GIS services configuration."""
    enable_gis: bool = False
    map_layers: list[dict[str, Any]] = field(default_factory=list)
    parcel_data_url: str | None = None


@dataclass
class ExternalAPIConfig:
    """External API configuration."""
    enable_weather: bool = False
    weather_api_key: str | None = None
    enable_transit: bool = False
    transit_api_url: str | None = None


@dataclass
class SyncConfig:
    """Sync and refresh configuration."""
    default_refresh_hours: int = 24
    notify_on_sync_failure: bool = True
    notification_email: str | None = None


@dataclass
class OnboardingConfig:
    """Complete onboarding configuration."""
    id: str
    discovery_id: str
    municipality_name: str
    created_at: str
    updated_at: str
    status: str = "draft"  # draft, validated, deployed

    core: CoreInfraConfig = field(default_factory=CoreInfraConfig)
    executive: ExecutiveConfig = field(default_factory=ExecutiveConfig)
    departments: list[DepartmentConfig] = field(default_factory=list)
    data_sources: list[DataSourceConfig] = field(default_factory=list)
    gis: GISConfig = field(default_factory=GISConfig)
    external_apis: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    manual_imports: list[str] = field(default_factory=list)
    sync: SyncConfig = field(default_factory=SyncConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "discovery_id": self.discovery_id,
            "municipality_name": self.municipality_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "core": {
                "enable_concierge": self.core.enable_concierge,
                "enable_governance": self.core.enable_governance,
                "enable_analytics": self.core.enable_analytics,
                "enable_audit": self.core.enable_audit,
                "enable_sessions": self.core.enable_sessions,
            },
            "executive": {
                "enable_mayor": self.executive.enable_mayor,
                "mayor_name": self.executive.mayor_name,
                "mayor_title": self.executive.mayor_title,
                "enable_chief_of_staff": self.executive.enable_chief_of_staff,
                "chief_officers": self.executive.chief_officers,
            },
            "departments": [
                {
                    "id": d.id,
                    "name": d.name,
                    "enabled": d.enabled,
                    "template_id": d.template_id,
                    "director_name": d.director_name,
                    "director_title": d.director_title,
                    "custom_name": d.custom_name,
                    "custom_description": d.custom_description,
                    "data_source_ids": d.data_source_ids,
                }
                for d in self.departments
            ],
            "data_sources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "enabled": s.enabled,
                    "department_id": s.department_id,
                    "sync_frequency": s.sync_frequency,
                    "api_endpoint": s.api_endpoint,
                }
                for s in self.data_sources
            ],
            "gis": {
                "enable_gis": self.gis.enable_gis,
                "map_layers": self.gis.map_layers,
                "parcel_data_url": self.gis.parcel_data_url,
            },
            "external_apis": {
                "enable_weather": self.external_apis.enable_weather,
                "weather_api_key": self.external_apis.weather_api_key,
                "enable_transit": self.external_apis.enable_transit,
                "transit_api_url": self.external_apis.transit_api_url,
            },
            "manual_imports": self.manual_imports,
            "sync": {
                "default_refresh_hours": self.sync.default_refresh_hours,
                "notify_on_sync_failure": self.sync.notify_on_sync_failure,
                "notification_email": self.sync.notification_email,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OnboardingConfig":
        """Create from dictionary."""
        config = cls(
            id=data.get("id", ""),
            discovery_id=data.get("discovery_id", ""),
            municipality_name=data.get("municipality_name", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=data.get("status", "draft"),
        )

        # Core config
        core_data = data.get("core", {})
        config.core = CoreInfraConfig(
            enable_concierge=core_data.get("enable_concierge", True),
            enable_governance=core_data.get("enable_governance", True),
            enable_analytics=core_data.get("enable_analytics", True),
            enable_audit=core_data.get("enable_audit", True),
            enable_sessions=core_data.get("enable_sessions", True),
        )

        # Executive config
        exec_data = data.get("executive", {})
        config.executive = ExecutiveConfig(
            enable_mayor=exec_data.get("enable_mayor", True),
            mayor_name=exec_data.get("mayor_name"),
            mayor_title=exec_data.get("mayor_title", "Mayor"),
            enable_chief_of_staff=exec_data.get("enable_chief_of_staff", False),
            chief_officers=exec_data.get("chief_officers", []),
        )

        # Departments
        for dept_data in data.get("departments", []):
            config.departments.append(DepartmentConfig(
                id=dept_data.get("id", ""),
                name=dept_data.get("name", ""),
                enabled=dept_data.get("enabled", True),
                template_id=dept_data.get("template_id"),
                director_name=dept_data.get("director_name"),
                director_title=dept_data.get("director_title"),
                custom_name=dept_data.get("custom_name"),
                custom_description=dept_data.get("custom_description"),
                data_source_ids=dept_data.get("data_source_ids", []),
            ))

        # Data sources
        for source_data in data.get("data_sources", []):
            config.data_sources.append(DataSourceConfig(
                id=source_data.get("id", ""),
                name=source_data.get("name", ""),
                enabled=source_data.get("enabled", True),
                department_id=source_data.get("department_id"),
                sync_frequency=source_data.get("sync_frequency", "daily"),
                api_endpoint=source_data.get("api_endpoint"),
            ))

        # GIS config
        gis_data = data.get("gis", {})
        config.gis = GISConfig(
            enable_gis=gis_data.get("enable_gis", False),
            map_layers=gis_data.get("map_layers", []),
            parcel_data_url=gis_data.get("parcel_data_url"),
        )

        # External APIs
        api_data = data.get("external_apis", {})
        config.external_apis = ExternalAPIConfig(
            enable_weather=api_data.get("enable_weather", False),
            weather_api_key=api_data.get("weather_api_key"),
            enable_transit=api_data.get("enable_transit", False),
            transit_api_url=api_data.get("transit_api_url"),
        )

        # Manual imports
        config.manual_imports = data.get("manual_imports", [])

        # Sync config
        sync_data = data.get("sync", {})
        config.sync = SyncConfig(
            default_refresh_hours=sync_data.get("default_refresh_hours", 24),
            notify_on_sync_failure=sync_data.get("notify_on_sync_failure", True),
            notification_email=sync_data.get("notification_email"),
        )

        return config


class ConfigurationManager:
    """Manages onboarding configurations."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/onboarding/configs")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_from_discovery(
        self,
        discovery_result: Any,
        catalog: Any | None = None,
    ) -> OnboardingConfig:
        """Create a configuration from discovery results.

        Args:
            discovery_result: The DiscoveryResult object
            catalog: Optional DatasetCatalog object

        Returns:
            OnboardingConfig with all discovered items pre-populated
        """
        config_id = f"config-{discovery_result.id}"
        now = datetime.utcnow().isoformat()

        config = OnboardingConfig(
            id=config_id,
            discovery_id=discovery_result.id,
            municipality_name=discovery_result.municipality.name if discovery_result.municipality else "",
            created_at=now,
            updated_at=now,
        )

        # Populate executive
        if discovery_result.executive:
            config.executive.mayor_name = discovery_result.executive.name
            config.executive.mayor_title = discovery_result.executive.title

        # Add chief officers
        for officer in discovery_result.chief_officers[:5]:  # Limit to 5
            config.executive.chief_officers.append({
                "name": officer.name,
                "title": officer.title,
                "enabled": True,
            })

        # Populate departments
        for dept in discovery_result.departments:
            config.departments.append(DepartmentConfig(
                id=dept.id,
                name=dept.name,
                enabled=True,
                template_id=dept.suggested_template,
                director_name=dept.director,
                director_title=dept.director_title,
            ))

        # Populate data sources from catalog
        if catalog:
            for dataset in catalog.datasets:
                config.data_sources.append(DataSourceConfig(
                    id=dataset.id,
                    name=dataset.name,
                    enabled=True,
                    department_id=dataset.suggested_department,
                    api_endpoint=dataset.api_endpoint,
                ))

        return config

    def save(self, config: OnboardingConfig) -> None:
        """Save configuration to storage."""
        config.updated_at = datetime.utcnow().isoformat()
        filepath = self.storage_path / f"{config.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)

    def load(self, config_id: str) -> OnboardingConfig | None:
        """Load configuration from storage."""
        filepath = self.storage_path / f"{config_id}.json"
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return OnboardingConfig.from_dict(data)

    def list_configs(self) -> list[OnboardingConfig]:
        """List all saved configurations."""
        configs = []
        for filepath in self.storage_path.glob("config-*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    configs.append(OnboardingConfig.from_dict(data))
            except Exception:
                continue
        return configs

    def validate(self, config: OnboardingConfig) -> dict[str, Any]:
        """Validate a configuration before deployment.

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if not config.municipality_name:
            errors.append("Municipality name is required")

        # Check at least one department is enabled
        enabled_depts = [d for d in config.departments if d.enabled]
        if not enabled_depts:
            errors.append("At least one department must be enabled")

        # Warn about departments without templates
        for dept in enabled_depts:
            if not dept.template_id:
                warnings.append(f"Department '{dept.name}' has no template assigned")

        # Check data source assignments
        for source in config.data_sources:
            if source.enabled and not source.department_id:
                warnings.append(f"Data source '{source.name}' is not assigned to a department")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Module-level singleton
_config_manager: ConfigurationManager | None = None


def get_config_manager() -> ConfigurationManager:
    """Get the configuration manager singleton."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def save_config(config: OnboardingConfig) -> None:
    """Save a configuration."""
    get_config_manager().save(config)


def load_config(config_id: str) -> OnboardingConfig | None:
    """Load a configuration."""
    return get_config_manager().load(config_id)


def validate_config(config: OnboardingConfig) -> dict[str, Any]:
    """Validate a configuration."""
    return get_config_manager().validate(config)
