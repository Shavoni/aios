"""Open Data Catalog Extractor for municipal data portals."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import httpx
    HAS_HTTP = True
except ImportError:
    HAS_HTTP = False

# Department keyword mapping for auto-categorization
DEPARTMENT_KEYWORDS = {
    "311": ["311", "service request", "complaint", "citizen", "call center"],
    "public-health": ["health", "disease", "clinic", "vaccination", "vital", "death", "birth"],
    "public-safety": ["police", "crime", "incident", "arrest", "safety", "shooting"],
    "fire": ["fire", "ems", "emergency", "rescue", "response"],
    "building": ["permit", "inspection", "building", "housing", "construction", "code violation"],
    "finance": ["budget", "expenditure", "revenue", "tax", "financial", "payment", "vendor"],
    "public-works": ["street", "road", "pothole", "water", "sewer", "utility", "sanitation", "trash"],
    "parks": ["park", "recreation", "facility", "community center", "pool"],
    "planning": ["zoning", "planning", "land use", "parcel", "development"],
    "hr": ["employee", "payroll", "salary", "workforce", "personnel"],
    "it": ["technology", "network", "wifi", "connectivity"],
    "transportation": ["traffic", "transit", "parking", "transportation", "bike", "pedestrian"],
}


@dataclass
class Dataset:
    """A dataset from an open data portal."""
    id: str
    name: str
    description: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)
    update_frequency: str = ""
    record_count: int | None = None
    api_endpoint: str = ""
    web_url: str = ""
    last_updated: str | None = None
    created_at: str | None = None
    suggested_department: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetCatalog:
    """A complete catalog from a data portal."""
    portal_type: str
    portal_url: str
    extracted_at: str
    dataset_count: int = 0
    datasets: list[Dataset] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "portal": {
                "type": self.portal_type,
                "url": self.portal_url,
                "dataset_count": self.dataset_count,
            },
            "extracted_at": self.extracted_at,
            "datasets": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "category": d.category,
                    "tags": d.tags,
                    "formats": d.formats,
                    "update_frequency": d.update_frequency,
                    "record_count": d.record_count,
                    "api_endpoint": d.api_endpoint,
                    "web_url": d.web_url,
                    "last_updated": d.last_updated,
                    "suggested_department": d.suggested_department,
                }
                for d in self.datasets
            ],
            "error": self.error,
        }


class CatalogExtractor:
    """Extracts dataset catalogs from various open data platforms."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if not HAS_HTTP:
            raise RuntimeError("httpx not installed. Install with: pip install httpx")

        self.storage_path = storage_path or Path("data/onboarding/catalogs")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def extract_catalog(self, portal_url: str, portal_type: str = "auto") -> DatasetCatalog:
        """Extract the complete dataset catalog from a portal.

        Args:
            portal_url: The base URL of the data portal
            portal_type: The portal type (socrata, ckan, arcgis, opendatasoft, auto)

        Returns:
            DatasetCatalog with all discovered datasets
        """
        # Auto-detect portal type if not specified
        if portal_type == "auto":
            portal_type = self._detect_portal_type(portal_url)

        catalog = DatasetCatalog(
            portal_type=portal_type,
            portal_url=portal_url,
            extracted_at=datetime.utcnow().isoformat(),
        )

        try:
            if portal_type == "socrata":
                self._extract_socrata(catalog)
            elif portal_type == "ckan":
                self._extract_ckan(catalog)
            elif portal_type == "arcgis":
                self._extract_arcgis(catalog)
            elif portal_type == "opendatasoft":
                self._extract_opendatasoft(catalog)
            else:
                catalog.error = f"Unknown portal type: {portal_type}"

            catalog.dataset_count = len(catalog.datasets)

            # Auto-categorize datasets
            for dataset in catalog.datasets:
                if not dataset.suggested_department:
                    dataset.suggested_department = self._suggest_department(dataset)

        except Exception as e:
            catalog.error = str(e)

        # Save catalog
        self._save_catalog(catalog)

        return catalog

    def _detect_portal_type(self, url: str) -> str:
        """Detect the portal type from the URL."""
        url_lower = url.lower()

        if "socrata" in url_lower or re.search(r"data\.[^/]+\.(gov|org|us)", url_lower):
            return "socrata"
        if "ckan" in url_lower:
            return "ckan"
        if "arcgis" in url_lower or "hub.arcgis" in url_lower:
            return "arcgis"
        if "opendatasoft" in url_lower:
            return "opendatasoft"

        # Try to detect via API probing
        with httpx.Client(timeout=10.0) as client:
            # Check for Socrata
            try:
                response = client.get(f"{url}/api/catalog/v1")
                if response.status_code == 200:
                    return "socrata"
            except Exception:
                pass

            # Check for CKAN
            try:
                response = client.get(f"{url}/api/3/action/package_list")
                if response.status_code == 200:
                    return "ckan"
            except Exception:
                pass

        return "unknown"

    def _extract_socrata(self, catalog: DatasetCatalog) -> None:
        """Extract datasets from a Socrata portal."""
        base_url = catalog.portal_url.rstrip("/")

        with httpx.Client(timeout=30.0) as client:
            # Use the discovery API
            offset = 0
            limit = 100

            while True:
                try:
                    response = client.get(
                        f"{base_url}/api/catalog/v1",
                        params={"limit": limit, "offset": offset},
                    )

                    if response.status_code != 200:
                        break

                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break

                    for item in results:
                        resource = item.get("resource", {})
                        classification = item.get("classification", {})

                        # Determine formats
                        formats = ["json"]  # Socrata always supports JSON
                        if resource.get("type") == "dataset":
                            formats.extend(["csv", "geojson"])

                        dataset = Dataset(
                            id=resource.get("id", ""),
                            name=resource.get("name", ""),
                            description=resource.get("description", ""),
                            category=classification.get("domain_category", ""),
                            tags=classification.get("domain_tags", []),
                            formats=formats,
                            update_frequency=resource.get("data_updated_at", ""),
                            record_count=resource.get("download_count"),
                            api_endpoint=f"{base_url}/resource/{resource.get('id', '')}.json",
                            web_url=item.get("link", ""),
                            last_updated=resource.get("updatedAt"),
                            created_at=resource.get("createdAt"),
                            metadata={
                                "type": resource.get("type"),
                                "attribution": resource.get("attribution"),
                            },
                        )
                        catalog.datasets.append(dataset)

                    offset += limit

                    # Safety limit
                    if offset > 5000:
                        break

                except Exception as e:
                    if not catalog.datasets:
                        catalog.error = f"Failed to extract Socrata catalog: {e}"
                    break

    def _extract_ckan(self, catalog: DatasetCatalog) -> None:
        """Extract datasets from a CKAN portal."""
        base_url = catalog.portal_url.rstrip("/")

        with httpx.Client(timeout=30.0) as client:
            try:
                # Get package list
                response = client.get(f"{base_url}/api/3/action/package_list")
                if response.status_code != 200:
                    catalog.error = f"CKAN API returned {response.status_code}"
                    return

                data = response.json()
                package_names = data.get("result", [])

                # Get details for each package (limit to first 500)
                for name in package_names[:500]:
                    try:
                        pkg_response = client.get(
                            f"{base_url}/api/3/action/package_show",
                            params={"id": name},
                        )
                        if pkg_response.status_code == 200:
                            pkg_data = pkg_response.json().get("result", {})

                            # Extract formats from resources
                            formats = list(set(
                                r.get("format", "").lower()
                                for r in pkg_data.get("resources", [])
                                if r.get("format")
                            ))

                            dataset = Dataset(
                                id=pkg_data.get("id", name),
                                name=pkg_data.get("title", name),
                                description=pkg_data.get("notes", ""),
                                category=pkg_data.get("organization", {}).get("title", ""),
                                tags=[t.get("name", "") for t in pkg_data.get("tags", [])],
                                formats=formats,
                                record_count=pkg_data.get("num_resources"),
                                web_url=f"{base_url}/dataset/{name}",
                                last_updated=pkg_data.get("metadata_modified"),
                                created_at=pkg_data.get("metadata_created"),
                            )

                            # Find best API endpoint from resources
                            for resource in pkg_data.get("resources", []):
                                if resource.get("format", "").lower() in ["json", "api"]:
                                    dataset.api_endpoint = resource.get("url", "")
                                    break

                            catalog.datasets.append(dataset)

                    except Exception:
                        continue

            except Exception as e:
                catalog.error = f"Failed to extract CKAN catalog: {e}"

    def _extract_arcgis(self, catalog: DatasetCatalog) -> None:
        """Extract datasets from an ArcGIS Hub/Open Data portal."""
        base_url = catalog.portal_url.rstrip("/")

        with httpx.Client(timeout=30.0) as client:
            try:
                # ArcGIS Hub uses a different API pattern
                # Try the Hub API first
                search_url = f"{base_url}/api/v3/datasets"

                response = client.get(search_url, params={"page[size]": 100})

                if response.status_code == 200:
                    data = response.json()

                    for item in data.get("data", []):
                        attrs = item.get("attributes", {})

                        formats = ["json"]
                        if attrs.get("geometryType"):
                            formats.append("geojson")

                        dataset = Dataset(
                            id=item.get("id", ""),
                            name=attrs.get("name", ""),
                            description=attrs.get("description", ""),
                            category=attrs.get("source", ""),
                            tags=attrs.get("tags", []) or [],
                            formats=formats,
                            record_count=attrs.get("recordCount"),
                            api_endpoint=attrs.get("url", ""),
                            web_url=attrs.get("landingPage", ""),
                            last_updated=attrs.get("modified"),
                            created_at=attrs.get("created"),
                        )
                        catalog.datasets.append(dataset)

                else:
                    # Try alternative endpoint
                    alt_url = f"{base_url}/search"
                    response = client.get(alt_url, params={"collection": "Dataset", "num": 100})
                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("results", []):
                            dataset = Dataset(
                                id=item.get("id", ""),
                                name=item.get("title", ""),
                                description=item.get("snippet", ""),
                                web_url=item.get("url", ""),
                            )
                            catalog.datasets.append(dataset)

            except Exception as e:
                catalog.error = f"Failed to extract ArcGIS catalog: {e}"

    def _extract_opendatasoft(self, catalog: DatasetCatalog) -> None:
        """Extract datasets from an OpenDataSoft portal."""
        base_url = catalog.portal_url.rstrip("/")

        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.get(
                    f"{base_url}/api/v2/catalog/datasets",
                    params={"limit": 100},
                )

                if response.status_code == 200:
                    data = response.json()

                    for item in data.get("datasets", []):
                        dataset_info = item.get("dataset", {})
                        metas = dataset_info.get("metas", {}).get("default", {})

                        dataset = Dataset(
                            id=dataset_info.get("dataset_id", ""),
                            name=metas.get("title", ""),
                            description=metas.get("description", ""),
                            category=metas.get("theme", ""),
                            tags=metas.get("keyword", []) or [],
                            formats=["json", "csv"],
                            record_count=dataset_info.get("records_count"),
                            api_endpoint=f"{base_url}/api/v2/catalog/datasets/{dataset_info.get('dataset_id')}/records",
                            last_updated=metas.get("modified"),
                        )
                        catalog.datasets.append(dataset)

            except Exception as e:
                catalog.error = f"Failed to extract OpenDataSoft catalog: {e}"

    def _suggest_department(self, dataset: Dataset) -> str | None:
        """Suggest a department for a dataset based on keywords."""
        # Combine searchable text
        search_text = " ".join([
            dataset.name.lower(),
            dataset.description.lower(),
            dataset.category.lower(),
            " ".join(dataset.tags).lower(),
        ])

        best_match = None
        best_score = 0

        for dept_id, keywords in DEPARTMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in search_text)
            if score > best_score:
                best_score = score
                best_match = dept_id

        return best_match if best_score > 0 else None

    def _save_catalog(self, catalog: DatasetCatalog) -> None:
        """Save catalog to storage."""
        # Generate filename from URL
        safe_name = re.sub(r"[^a-z0-9]+", "-", catalog.portal_url.lower())[:50]
        filename = f"catalog-{safe_name}.json"

        filepath = self.storage_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(catalog.to_dict(), f, indent=2)


# Module-level singleton
_catalog_extractor: CatalogExtractor | None = None


def get_catalog_extractor() -> CatalogExtractor:
    """Get the catalog extractor singleton."""
    global _catalog_extractor
    if _catalog_extractor is None:
        _catalog_extractor = CatalogExtractor()
    return _catalog_extractor


def extract_catalog(portal_url: str, portal_type: str = "auto") -> DatasetCatalog:
    """Extract a catalog from a data portal."""
    return get_catalog_extractor().extract_catalog(portal_url, portal_type)
