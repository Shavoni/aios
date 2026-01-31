"""Discovery Engine for municipal website crawling and org structure extraction."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:
    import httpx
    from bs4 import BeautifulSoup
    HAS_CRAWLER_DEPS = True
except ImportError:
    HAS_CRAWLER_DEPS = False

# Title patterns for detecting executives and department heads (municipal)
EXECUTIVE_PATTERNS = [
    r"mayor",
    r"city\s*manager",
    r"chief\s*(of\s*staff|executive|operating|financial|administrative)",
    r"deputy\s*mayor",
    r"city\s*administrator",
]

# Enterprise executive patterns (C-suite and leadership)
ENTERPRISE_EXECUTIVE_PATTERNS = [
    # C-Suite
    (r"chief\s+executive\s+officer|(?<![a-z])ceo(?![a-z])", "Chief Executive Officer"),
    (r"chief\s+operating\s+officer|(?<![a-z])coo(?![a-z])", "Chief Operating Officer"),
    (r"chief\s+financial\s+officer|(?<![a-z])cfo(?![a-z])", "Chief Financial Officer"),
    (r"chief\s+technology\s+officer|(?<![a-z])cto(?![a-z])", "Chief Technology Officer"),
    (r"chief\s+information\s+officer|(?<![a-z])cio(?![a-z])", "Chief Information Officer"),
    (r"chief\s+marketing\s+officer|(?<![a-z])cmo(?![a-z])", "Chief Marketing Officer"),
    (r"chief\s+product\s+officer|(?<![a-z])cpo(?![a-z])", "Chief Product Officer"),
    (r"chief\s+human\s+resources\s+officer|(?<![a-z])chro(?![a-z])", "Chief Human Resources Officer"),
    (r"chief\s+legal\s+officer|(?<![a-z])clo(?![a-z])|general\s+counsel", "General Counsel"),
    (r"chief\s+revenue\s+officer|(?<![a-z])cro(?![a-z])", "Chief Revenue Officer"),
    (r"chief\s+strategy\s+officer|(?<![a-z])cso(?![a-z])", "Chief Strategy Officer"),
    (r"chief\s+data\s+officer|(?<![a-z])cdo(?![a-z])", "Chief Data Officer"),
    (r"chief\s+security\s+officer|(?<![a-z])ciso(?![a-z])", "Chief Security Officer"),

    # Presidents/VPs
    (r"(?<![a-z])president(?![a-z])", "President"),
    (r"executive\s+vice\s+president|(?<![a-z])evp(?![a-z])", "Executive Vice President"),
    (r"senior\s+vice\s+president|(?<![a-z])svp(?![a-z])", "Senior Vice President"),
    (r"vice\s+president|(?<![a-z])vp(?![a-z])", "Vice President"),

    # Board
    (r"chairman|chairwoman|chair\s+of\s+the\s+board", "Chairman"),
    (r"board\s+member", "Board Member"),

    # Other executives
    (r"managing\s+director", "Managing Director"),
    (r"general\s+manager", "General Manager"),
]

# Enterprise department patterns
ENTERPRISE_DEPARTMENT_KEYWORDS = {
    "engineering": ["engineering", "technology", "development", "r&d", "research and development", "product development"],
    "product": ["product", "product management", "product development"],
    "sales": ["sales", "business development", "revenue", "commercial"],
    "marketing": ["marketing", "brand", "communications", "pr", "public relations", "advertising"],
    "finance": ["finance", "accounting", "treasury", "investor relations", "financial planning"],
    "hr": ["human resources", "hr", "people", "talent", "recruiting", "people operations"],
    "legal": ["legal", "compliance", "regulatory", "general counsel", "corporate affairs"],
    "operations": ["operations", "supply chain", "logistics", "manufacturing", "procurement"],
    "customer": ["customer success", "customer service", "customer support", "client services"],
    "it": ["information technology", "it", "infrastructure", "security", "cybersecurity"],
    "strategy": ["strategy", "corporate development", "m&a", "mergers"],
    "data": ["data", "analytics", "data science", "business intelligence"],
}

DEPARTMENT_HEAD_PATTERNS = [
    r"director",
    r"commissioner",
    r"superintendent",
    r"chief\s*(of\s*police|of\s*fire)?",
    r"secretary",
    r"administrator",
    r"manager",
]

# Common municipal department keywords
DEPARTMENT_KEYWORDS = {
    "public-health": ["health", "public health", "cdph", "epidemiology", "clinic"],
    "hr": ["human resources", "hr", "personnel", "civil service", "employee"],
    "finance": ["finance", "treasury", "fiscal", "budget", "accounting", "procurement"],
    "building": ["building", "housing", "permits", "inspections", "code enforcement"],
    "311": ["311", "citizen services", "constituent services", "call center"],
    "strategy": ["planning", "development", "economic development", "strategy"],
    "public-safety": ["police", "public safety", "law enforcement"],
    "fire": ["fire", "emergency services", "ems", "emergency management"],
    "parks": ["parks", "recreation", "community centers"],
    "public-works": ["public works", "streets", "utilities", "water", "sewer", "sanitation"],
    "law": ["law", "legal", "city attorney", "solicitor"],
    "it": ["technology", "it", "information technology", "innovation"],
    "communications": ["communications", "public affairs", "media relations"],
}

# Open data portal patterns
DATA_PORTAL_PATTERNS = [
    (r"data\.[^/]+\.(gov|org|us)", "socrata"),
    (r"opendata\.[^/]+", "socrata"),
    (r"hub\.arcgis\.com", "arcgis"),
    (r"[^/]+\.arcgis\.com/home", "arcgis"),
    (r"ckan", "ckan"),
    (r"opendatasoft\.com", "opendatasoft"),
]


class DiscoveryStatus(str, Enum):
    """Status of a discovery job."""
    PENDING = "pending"
    CRAWLING = "crawling"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_SELECTION = "awaiting_selection"  # New: shallow crawl done, waiting for user selection


class DiscoveryMode(str, Enum):
    """Discovery mode controls crawl depth."""
    SHALLOW = "shallow"  # Fast inventory scan (Phase 1 of new workflow)
    TARGETED = "targeted"  # Deep crawl only selected items
    FULL = "full"  # Legacy: crawl everything (deprecated)


class CandidateType(str, Enum):
    """Granular candidate type classification."""
    # Leadership hierarchy
    EXECUTIVE = "executive"  # Mayor, Governor, CEO, City Manager
    CABINET = "cabinet"  # Chief Officers (CFO, COO, Chief of Staff)
    DIRECTOR = "director"  # Department Directors/Heads
    DEPUTY = "deputy"  # Deputy/Assistant Directors

    # Department categories
    PUBLIC_SAFETY = "public-safety"  # Police, Fire, Emergency Management
    PUBLIC_WORKS = "public-works"  # Streets, Water, Utilities
    FINANCE = "finance"  # Budget, Accounting, Procurement
    LEGAL = "legal"  # Law, City Attorney, Clerk
    PLANNING = "planning"  # Development, Zoning, Building
    HEALTH = "health"  # Health, Human Services
    PARKS_REC = "parks-rec"  # Parks, Recreation, Libraries
    ADMIN = "admin"  # HR, IT, Communications

    # Other
    DATA_PORTAL = "data-portal"  # Open data platforms
    SERVICE = "service"  # Citizen-facing services
    BOARD = "board"  # Boards, Commissions, Councils
    DEPARTMENT = "department"  # Generic department (fallback)
    LEADERSHIP = "leadership"  # Generic leadership (fallback)


# Map keywords to candidate types for classification
CANDIDATE_TYPE_KEYWORDS = {
    # Leadership patterns - Executives (top of org)
    CandidateType.EXECUTIVE: [
        "mayor", "governor", "city manager", "county executive", "ceo", "president",
        "county manager", "town manager", "village manager", "administrator"
    ],
    # Leadership patterns - Cabinet level (C-suite, chiefs)
    CandidateType.CABINET: [
        "chief of staff", "chief operating", "chief financial", "cfo", "coo",
        "chief administrative", "deputy mayor", "chief of police", "police chief",
        "fire chief", "chief information", "cio", "cto", "chief technology",
        "city attorney", "county attorney", "solicitor general"
    ],
    # Leadership patterns - Department Directors
    CandidateType.DIRECTOR: [
        "director", "commissioner", "superintendent", "secretary", "administrator",
        "head of", "manager of", "chief", "executive director"
    ],
    # Leadership patterns - Deputies
    CandidateType.DEPUTY: [
        "deputy director", "assistant director", "deputy commissioner",
        "deputy chief", "assistant chief", "vice", "associate director"
    ],

    # Department categories (for classifying departments/orgs, not people)
    CandidateType.PUBLIC_SAFETY: ["police", "fire", "emergency", "public safety", "law enforcement", "sheriff", "corrections", "911"],
    CandidateType.PUBLIC_WORKS: ["public works", "streets", "water", "sewer", "utilities", "sanitation", "transportation", "infrastructure", "roads"],
    CandidateType.FINANCE: ["finance", "treasury", "budget", "accounting", "procurement", "fiscal", "revenue", "tax", "auditor"],
    CandidateType.LEGAL: ["law department", "legal department", "city attorney", "solicitor", "clerk", "court", "prosecutor", "public defender"],
    CandidateType.PLANNING: ["planning", "development", "zoning", "building", "housing", "permits", "economic development", "community development"],
    CandidateType.HEALTH: ["health", "human services", "social services", "senior", "aging", "mental health", "welfare", "family services"],
    CandidateType.PARKS_REC: ["parks", "recreation", "library", "libraries", "cultural", "arts", "community center", "zoo", "museum"],
    CandidateType.ADMIN: ["human resources", "hr", "personnel", "technology", "it", "communications", "media", "public affairs", "general services"],

    # Other
    CandidateType.BOARD: ["board", "commission", "council", "committee", "authority", "advisory"],
    CandidateType.SERVICE: ["311", "citizen service", "constituent", "customer service", "one-stop"],
    CandidateType.DATA_PORTAL: ["data portal", "open data", "data hub", "data catalog"],
}

# Keywords that indicate a leadership/person role vs a department
LEADERSHIP_INDICATORS = [
    "chief", "director", "commissioner", "superintendent", "secretary",
    "administrator", "manager", "head", "officer", "executive",
    "mayor", "governor", "president", "chair", "chairman", "chairwoman"
]


def classify_candidate_type(name: str, context: str = "", is_person: bool = False) -> str:
    """Classify a candidate into a granular type based on name and context."""
    text = f"{name} {context}".lower()

    # Auto-detect if this looks like a person/leadership role
    if not is_person:
        is_person = any(indicator in text for indicator in LEADERSHIP_INDICATORS)

    # Check leadership types first if this appears to be a person/leadership role
    if is_person:
        # Check specific leadership levels
        for candidate_type in [CandidateType.EXECUTIVE, CandidateType.CABINET, CandidateType.DIRECTOR, CandidateType.DEPUTY]:
            keywords = CANDIDATE_TYPE_KEYWORDS.get(candidate_type, [])
            if any(kw in text for kw in keywords):
                return candidate_type.value
        # Default to director for leadership roles
        return CandidateType.DIRECTOR.value

    # Check department/org categories (only for non-person entities)
    for candidate_type in [
        CandidateType.PUBLIC_SAFETY, CandidateType.PUBLIC_WORKS, CandidateType.FINANCE,
        CandidateType.LEGAL, CandidateType.PLANNING, CandidateType.HEALTH,
        CandidateType.PARKS_REC, CandidateType.ADMIN, CandidateType.BOARD,
        CandidateType.SERVICE, CandidateType.DATA_PORTAL
    ]:
        keywords = CANDIDATE_TYPE_KEYWORDS.get(candidate_type, [])
        if any(kw in text for kw in keywords):
            return candidate_type.value

    return CandidateType.DEPARTMENT.value


@dataclass
class CrawlConfig:
    """Configuration for crawl behavior."""
    max_pages: int = 50
    max_depth: int = 2
    timeout_seconds: int = 120
    rate_limit_delay: float = 0.3
    mode: DiscoveryMode = DiscoveryMode.SHALLOW

    # Scope controls
    include_leadership: bool = True
    include_departments: bool = True
    include_services: bool = True
    include_data_portals: bool = True

    # Enterprise-specific paths to prioritize during crawl
    priority_paths: list[str] = field(default_factory=list)

    # Organization type hint (municipal, enterprise, education, nonprofit)
    org_type: str = "municipal"


@dataclass
class DiscoveryCandidate:
    """A discovered candidate before user selection."""
    id: str
    name: str
    type: str  # "department", "leadership", "service", "data_portal"
    url: str
    confidence: str  # "high", "medium", "low"
    source_urls: list[str] = field(default_factory=list)
    suggested_agent_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    selected: bool = True  # Default to selected

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "confidence": self.confidence,
            "source_urls": self.source_urls,
            "suggested_agent_name": self.suggested_agent_name,
            "metadata": self.metadata,
            "selected": self.selected,
        }


@dataclass
class ContactInfo:
    """Contact information for a person or department."""
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    office: str | None = None


@dataclass
class Executive:
    """An executive official."""
    name: str
    title: str
    office: str
    contact: ContactInfo = field(default_factory=ContactInfo)
    url: str | None = None
    image_url: str | None = None


@dataclass
class Department:
    """A discovered department."""
    id: str
    name: str
    director: str | None = None
    director_title: str | None = None
    url: str | None = None
    description: str | None = None
    contact: ContactInfo = field(default_factory=ContactInfo)
    suggested_template: str | None = None
    keywords_matched: list[str] = field(default_factory=list)


@dataclass
class DataPortal:
    """A discovered data portal."""
    type: str  # socrata, ckan, arcgis, opendatasoft
    url: str
    api_endpoint: str | None = None
    detected_via: str | None = None


@dataclass
class GovernanceDoc:
    """A discovered governance document."""
    type: str  # charter, ordinance, policy, etc.
    title: str
    url: str


@dataclass
class Municipality:
    """Basic municipality information."""
    name: str
    state: str | None = None
    website: str = ""
    population: int | None = None


@dataclass
class DiscoveryResult:
    """Complete discovery result."""
    id: str
    status: DiscoveryStatus
    started_at: str
    completed_at: str | None = None
    source_url: str = ""
    municipality: Municipality | None = None
    executive: Executive | None = None
    chief_officers: list[Executive] = field(default_factory=list)
    departments: list[Department] = field(default_factory=list)
    data_portals: list[DataPortal] = field(default_factory=list)
    governance_docs: list[GovernanceDoc] = field(default_factory=list)
    pages_crawled: int = 0
    error: str | None = None

    # New fields for controlled discovery
    config: CrawlConfig = field(default_factory=CrawlConfig)
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    mode: DiscoveryMode = DiscoveryMode.SHALLOW
    cancelled: bool = False

    # Progress indicators (more meaningful than page count)
    departments_detected: int = 0
    leaders_detected: int = 0
    services_detected: int = 0
    data_portals_detected: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "source_url": self.source_url,
            "mode": self.mode.value if isinstance(self.mode, DiscoveryMode) else self.mode,
            "municipality": {
                "name": self.municipality.name if self.municipality else "",
                "state": self.municipality.state if self.municipality else None,
                "website": self.municipality.website if self.municipality else "",
                "population": self.municipality.population if self.municipality else None,
            } if self.municipality else None,
            "executive": {
                "name": self.executive.name,
                "title": self.executive.title,
                "office": self.executive.office,
                "url": self.executive.url,
            } if self.executive else None,
            "chief_officers": [
                {"name": o.name, "title": o.title, "office": o.office, "url": o.url}
                for o in self.chief_officers
            ],
            "departments": [
                {
                    "id": d.id,
                    "name": d.name,
                    "director": d.director,
                    "director_title": d.director_title,
                    "url": d.url,
                    "description": d.description,
                    "suggested_template": d.suggested_template,
                    "contact": {
                        "email": d.contact.email if d.contact else None,
                        "phone": d.contact.phone if d.contact else None,
                        "address": d.contact.address if d.contact else None,
                    },
                }
                for d in self.departments
            ],
            "data_portals": [
                {"type": p.type, "url": p.url, "api_endpoint": p.api_endpoint}
                for p in self.data_portals
            ],
            "governance_docs": [
                {"type": d.type, "title": d.title, "url": d.url}
                for d in self.governance_docs
            ],
            "pages_crawled": self.pages_crawled,
            "error": self.error,
            # New fields
            "candidates": [c.to_dict() for c in self.candidates],
            "config": {
                "max_pages": self.config.max_pages,
                "max_depth": self.config.max_depth,
                "timeout_seconds": self.config.timeout_seconds,
                "mode": self.config.mode.value if isinstance(self.config.mode, DiscoveryMode) else self.config.mode,
            } if self.config else None,
            "progress": {
                "departments_detected": self.departments_detected,
                "leaders_detected": self.leaders_detected,
                "services_detected": self.services_detected,
                "data_portals_detected": self.data_portals_detected,
            },
            "cancelled": self.cancelled,
        }


class DiscoveryEngine:
    """Crawls municipal websites to discover organizational structure."""

    def __init__(
        self,
        storage_path: Path | None = None,
        max_pages: int = 50,  # Reduced default for controlled discovery
        rate_limit_delay: float = 0.3,
    ) -> None:
        if not HAS_CRAWLER_DEPS:
            raise RuntimeError(
                "Crawler dependencies not installed. "
                "Install with: pip install httpx beautifulsoup4"
            )

        # Use absolute path relative to this file's location to avoid Windows path issues
        if storage_path:
            self.storage_path = storage_path
        else:
            # Go up from packages/onboarding/ to project root, then into data/onboarding
            project_root = Path(__file__).parent.parent.parent
            self.storage_path = project_root / "data" / "onboarding"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_pages = max_pages
        self.rate_limit_delay = rate_limit_delay
        self._jobs: dict[str, DiscoveryResult] = {}
        self._cancel_flags: dict[str, bool] = {}  # Track cancellation requests
        self._load_jobs()

    def cancel_discovery(self, job_id: str) -> bool:
        """Cancel a running discovery job."""
        if job_id in self._jobs:
            self._cancel_flags[job_id] = True
            result = self._jobs[job_id]
            if result.status in (DiscoveryStatus.CRAWLING, DiscoveryStatus.EXTRACTING, DiscoveryStatus.PENDING):
                result.cancelled = True
                result.status = DiscoveryStatus.CANCELLED
                result.completed_at = datetime.utcnow().isoformat()
                self._save_jobs()
                return True
        return False

    def _is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled."""
        return self._cancel_flags.get(job_id, False)

    # =========================================================================
    # DISCOVERY CACHING
    # =========================================================================

    def _get_cache_key(self, url: str, config: CrawlConfig) -> str:
        """Generate a cache key for discovery results.

        Cache key is based on:
        - Normalized domain
        - Crawl settings
        - Time bucket (1 hour intervals)
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Time bucket: floor to nearest hour
        time_bucket = int(time.time() // 3600)

        # Create cache key from domain + settings + time
        cache_data = f"{domain}:{config.max_pages}:{config.max_depth}:{config.mode.value}:{time_bucket}"
        return hashlib.sha256(cache_data.encode()).hexdigest()[:16]

    def _get_cached_discovery(self, url: str, config: CrawlConfig) -> DiscoveryResult | None:
        """Check if we have a cached discovery result for this URL.

        Returns cached result if:
        - Same domain
        - Same crawl settings
        - Within the cache time window (1 hour)
        """
        cache_key = self._get_cache_key(url, config)
        cache_file = self.storage_path / f"cache_{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cached_result = self._dict_to_result(data)

                    # Only use cache if status is awaiting_selection or completed
                    if cached_result.status in (DiscoveryStatus.AWAITING_SELECTION, DiscoveryStatus.COMPLETED):
                        return cached_result
            except Exception:
                pass

        return None

    def _cache_discovery(self, result: DiscoveryResult, config: CrawlConfig) -> None:
        """Cache a discovery result for reuse."""
        cache_key = self._get_cache_key(result.source_url, config)
        cache_file = self.storage_path / f"cache_{cache_key}.json"

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
        except Exception:
            pass  # Caching is best-effort

    def get_cached_or_start(
        self,
        url: str,
        config: CrawlConfig | None = None,
    ) -> tuple[str, bool]:
        """Get cached discovery or start a new one.

        Returns:
            Tuple of (job_id, is_cached)
        """
        config = config or CrawlConfig()

        # Check for cached result
        cached = self._get_cached_discovery(url, config)
        if cached:
            # Create a new job that references the cached data
            job_id = self._generate_job_id(url)
            cached.id = job_id  # Update ID for this request
            self._jobs[job_id] = cached
            self._save_jobs()
            return (job_id, True)

        # No cache, start fresh discovery
        job_id = self.start_discovery(url, config)
        return (job_id, False)

    def _load_jobs(self) -> None:
        """Load existing discovery jobs from storage."""
        jobs_file = self.storage_path / "discovery_jobs.json"
        if jobs_file.exists():
            try:
                with open(jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job_id = job_data.get("id")
                        if job_id:
                            self._jobs[job_id] = self._dict_to_result(job_data)
            except Exception:
                pass

    def _save_jobs(self) -> None:
        """Save discovery jobs to storage."""
        jobs_file = self.storage_path / "discovery_jobs.json"
        with open(jobs_file, "w", encoding="utf-8") as f:
            json.dump(
                {"jobs": [job.to_dict() for job in self._jobs.values()]},
                f,
                indent=2,
            )

    def _dict_to_result(self, data: dict) -> DiscoveryResult:
        """Convert dictionary to DiscoveryResult."""
        municipality = None
        if data.get("municipality"):
            m = data["municipality"]
            municipality = Municipality(
                name=m.get("name", ""),
                state=m.get("state"),
                website=m.get("website", ""),
                population=m.get("population"),
            )

        executive = None
        if data.get("executive"):
            e = data["executive"]
            executive = Executive(
                name=e.get("name", ""),
                title=e.get("title", ""),
                office=e.get("office", ""),
                url=e.get("url"),
            )

        return DiscoveryResult(
            id=data.get("id", ""),
            status=DiscoveryStatus(data.get("status", "pending")),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            source_url=data.get("source_url", ""),
            municipality=municipality,
            executive=executive,
            chief_officers=[
                Executive(
                    name=o.get("name", ""),
                    title=o.get("title", ""),
                    office=o.get("office", ""),
                    url=o.get("url"),
                )
                for o in data.get("chief_officers", [])
            ],
            departments=[
                Department(
                    id=d.get("id", ""),
                    name=d.get("name", ""),
                    director=d.get("director"),
                    director_title=d.get("director_title"),
                    url=d.get("url"),
                    description=d.get("description"),
                    suggested_template=d.get("suggested_template"),
                    contact=ContactInfo(
                        email=d.get("contact", {}).get("email"),
                        phone=d.get("contact", {}).get("phone"),
                        address=d.get("contact", {}).get("address"),
                    ),
                )
                for d in data.get("departments", [])
            ],
            data_portals=[
                DataPortal(
                    type=p.get("type", ""),
                    url=p.get("url", ""),
                    api_endpoint=p.get("api_endpoint"),
                )
                for p in data.get("data_portals", [])
            ],
            governance_docs=[
                GovernanceDoc(
                    type=d.get("type", ""),
                    title=d.get("title", ""),
                    url=d.get("url", ""),
                )
                for d in data.get("governance_docs", [])
            ],
            pages_crawled=data.get("pages_crawled", 0),
            error=data.get("error"),
        )

    def _generate_job_id(self, url: str) -> str:
        """Generate a unique job ID."""
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(f"{url}:{timestamp}".encode()).hexdigest()[:12]

    def start_discovery(
        self,
        url: str,
        config: CrawlConfig | None = None,
    ) -> str:
        """Start a discovery job for a URL.

        Args:
            url: The municipal website URL to discover
            config: Optional crawl configuration

        Returns:
            Job ID for tracking progress
        """
        job_id = self._generate_job_id(url)
        config = config or CrawlConfig()

        result = DiscoveryResult(
            id=job_id,
            status=DiscoveryStatus.PENDING,
            started_at=datetime.utcnow().isoformat(),
            source_url=url,
            config=config,
            mode=config.mode,
        )
        self._jobs[job_id] = result
        self._cancel_flags[job_id] = False
        self._save_jobs()

        # Start discovery in background thread
        thread = threading.Thread(
            target=self._run_discovery,
            args=(job_id, url, config),
            daemon=True,
        )
        thread.start()

        return job_id

    def get_status(self, job_id: str) -> DiscoveryResult | None:
        """Get the status of a discovery job."""
        return self._jobs.get(job_id)

    def _run_discovery(self, job_id: str, url: str, config: CrawlConfig | None = None) -> None:
        """Run the discovery process."""
        import ssl
        import certifi

        config = config or CrawlConfig()
        result = self._jobs[job_id]
        result.status = DiscoveryStatus.CRAWLING
        self._save_jobs()

        start_time = time.time()

        try:
            # Check for cancellation
            if self._is_cancelled(job_id):
                return

            # Parse base URL
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Create HTTP client with browser-like headers and SSL handling
            with httpx.Client(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                verify=certifi.where(),  # Use certifi for SSL on Windows
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                },
            ) as client:
                # Check timeout
                if time.time() - start_time > config.timeout_seconds:
                    result.error = "Discovery timed out"
                    result.status = DiscoveryStatus.FAILED
                    result.completed_at = datetime.utcnow().isoformat()
                    self._save_jobs()
                    return

                # Check for cancellation
                if self._is_cancelled(job_id):
                    return

                # Crawl the site with config limits
                pages_content = self._crawl_site_controlled(
                    client, base_url, url, result, config, job_id, start_time
                )
                result.pages_crawled = len(pages_content)

                if not pages_content and not self._is_cancelled(job_id):
                    # If no pages were crawled, try once more with SSL verification disabled
                    with httpx.Client(
                        timeout=httpx.Timeout(30.0, connect=10.0),
                        follow_redirects=True,
                        verify=False,  # Fallback: disable SSL verification
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        },
                    ) as fallback_client:
                        pages_content = self._crawl_site_controlled(
                            fallback_client, base_url, url, result, config, job_id, start_time
                        )
                        result.pages_crawled = len(pages_content)

                # Check for cancellation
                if self._is_cancelled(job_id):
                    return

                # Extract organization info
                result.status = DiscoveryStatus.EXTRACTING
                self._save_jobs()

                self._extract_municipality_safe(result, pages_content, base_url)
                self._extract_executive_safe(result, pages_content, config)
                self._extract_departments_safe(result, pages_content, base_url, config)
                self._extract_data_portals_safe(result, pages_content, base_url)
                self._extract_governance_docs_safe(result, pages_content, base_url)

                # Build candidates from extracted data
                self._build_candidates(result)

                # Update progress counters
                result.departments_detected = len(result.departments)
                result.leaders_detected = len(result.chief_officers) + (1 if result.executive else 0)
                result.data_portals_detected = len(result.data_portals)

                # For shallow mode, await selection before proceeding
                if config.mode == DiscoveryMode.SHALLOW:
                    result.status = DiscoveryStatus.AWAITING_SELECTION
                else:
                    result.status = DiscoveryStatus.COMPLETED

                result.completed_at = datetime.utcnow().isoformat()

                # Cache successful discovery for reuse
                self._cache_discovery(result, config)

        except Exception as e:
            import traceback
            result.status = DiscoveryStatus.FAILED
            result.error = f"{str(e)}\n{traceback.format_exc()}"
            result.completed_at = datetime.utcnow().isoformat()

        self._save_jobs()

    def _crawl_site(
        self,
        client: httpx.Client,
        base_url: str,
        start_url: str,
        result: DiscoveryResult | None = None,
    ) -> dict[str, str]:
        """Crawl the site and collect page content.

        Returns:
            Dictionary mapping URLs to page content
        """
        visited: set[str] = set()
        to_visit: list[str] = [start_url]
        pages: dict[str, str] = {}

        # Priority pages to look for - expanded for various org types
        priority_paths = [
            "/government",
            "/departments",
            "/directory",
            "/mayor",
            "/city-hall",
            "/about",
            "/about-us",
            "/leadership",
            "/officials",
            "/administration",
            "/services",
            "/team",
            "/our-team",
            "/staff",
            "/contact",
            "/contact-us",
        ]

        # Add priority paths to queue
        for path in priority_paths:
            to_visit.append(urljoin(base_url, path))

        errors_count = 0
        max_errors = 10  # Give up after too many consecutive errors

        while to_visit and len(pages) < self.max_pages and errors_count < max_errors:
            url = to_visit.pop(0)

            # Normalize URL
            url = url.split("#")[0].rstrip("/")
            # Keep query params for some sites but remove common tracking params
            if "?" in url:
                clean_url = url.split("?")[0]
                url = clean_url

            # Skip if already visited or external
            if url in visited:
                continue
            if not url.startswith(base_url):
                continue
            # Skip common non-content URLs
            skip_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.json', '.zip', '.mp4', '.mp3')
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                continue

            visited.add(url)

            try:
                response = client.get(url)
                content_type = response.headers.get("content-type", "")

                if response.status_code == 200 and "text/html" in content_type:
                    pages[url] = response.text
                    errors_count = 0  # Reset error count on success

                    # Update result progress
                    if result:
                        result.pages_crawled = len(pages)

                    # Extract links for further crawling
                    soup = BeautifulSoup(response.text, "html.parser")
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        # Skip javascript links, mailto, tel, etc.
                        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                            continue

                        full_url = urljoin(url, href)

                        # Ensure it's on the same domain
                        if not full_url.startswith(base_url):
                            continue
                        if full_url in visited:
                            continue

                        # Prioritize certain pages
                        priority_keywords = [
                            "department", "government", "director", "office",
                            "team", "about", "leadership", "staff", "contact",
                            "executive", "management", "board", "council"
                        ]
                        if any(kw in full_url.lower() for kw in priority_keywords):
                            to_visit.insert(0, full_url)
                        else:
                            to_visit.append(full_url)

                elif response.status_code >= 400:
                    errors_count += 1

                time.sleep(self.rate_limit_delay)

            except httpx.TimeoutException:
                errors_count += 1
                time.sleep(1)  # Extra delay on timeout
                continue
            except httpx.RequestError as e:
                errors_count += 1
                continue
            except Exception as e:
                errors_count += 1
                continue

        return pages

    def _crawl_site_controlled(
        self,
        client: httpx.Client,
        base_url: str,
        start_url: str,
        result: DiscoveryResult,
        config: CrawlConfig,
        job_id: str,
        start_time: float,
    ) -> dict[str, str]:
        """Crawl the site with configurable limits and cancellation support.

        Returns:
            Dictionary mapping URLs to page content
        """
        visited: set[str] = set()
        # Track depth for each URL
        url_depths: dict[str, int] = {start_url: 0}
        to_visit: list[str] = [start_url]
        pages: dict[str, str] = {}

        # Priority pages to look for - use config-provided paths for enterprise,
        # or fall back to municipal defaults
        if config.priority_paths:
            # Use enterprise-specific priority paths from config
            priority_paths = config.priority_paths
        elif config.org_type == "enterprise":
            # Default enterprise paths (leadership, executives, departments)
            priority_paths = [
                "/about/leadership", "/about/team", "/about/management",
                "/company/leadership", "/company/team", "/company/about",
                "/leadership", "/team", "/executives", "/management",
                "/about", "/about-us", "/company", "/corporate",
                "/investors", "/investor-relations", "/careers",
            ]
        else:
            # Default municipal paths
            priority_paths = [
                "/government", "/departments", "/directory", "/mayor",
                "/city-hall", "/about", "/leadership", "/officials",
                "/administration", "/services", "/team", "/staff",
                "/contact", "/sitemap", "/site-map",
            ]

        # Add priority paths to queue at depth 1
        for path in priority_paths:
            full_url = urljoin(base_url, path)
            if full_url not in url_depths:
                url_depths[full_url] = 1
                to_visit.append(full_url)

        errors_count = 0
        max_errors = 10

        while to_visit and len(pages) < config.max_pages and errors_count < max_errors:
            # Check for cancellation
            if self._is_cancelled(job_id):
                break

            # Check timeout
            if time.time() - start_time > config.timeout_seconds:
                result.error = f"Discovery timed out after {config.timeout_seconds}s"
                break

            url = to_visit.pop(0)
            current_depth = url_depths.get(url, 0)

            # Skip if exceeds max depth
            if current_depth > config.max_depth:
                continue

            # Normalize URL
            url = url.split("#")[0].rstrip("/")
            if "?" in url:
                url = url.split("?")[0]

            # Skip if already visited or external
            if url in visited:
                continue
            if not url.startswith(base_url):
                continue

            # Skip common non-content URLs
            skip_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.json', '.zip', '.mp4', '.mp3')
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                continue

            visited.add(url)

            try:
                response = client.get(url)
                content_type = response.headers.get("content-type", "")

                if response.status_code == 200 and "text/html" in content_type:
                    pages[url] = response.text
                    errors_count = 0

                    # Update result progress
                    result.pages_crawled = len(pages)
                    self._save_jobs()

                    # Extract links for further crawling (only if within depth limit)
                    if current_depth < config.max_depth:
                        soup = BeautifulSoup(response.text, "html.parser")
                        for link in soup.find_all("a", href=True):
                            href = link.get("href", "")
                            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                                continue

                            full_url = urljoin(url, href)
                            if not full_url.startswith(base_url):
                                continue
                            if full_url in visited or full_url in url_depths:
                                continue

                            # Set depth for new URL
                            url_depths[full_url] = current_depth + 1

                            # Prioritize high-value pages based on org type
                            if config.org_type == "enterprise":
                                priority_keywords = [
                                    "leadership", "executive", "team", "about", "company",
                                    "management", "officers", "board", "directors", "ceo",
                                    "coo", "cfo", "president", "vice-president", "vp",
                                    "investor", "careers", "divisions", "business-units"
                                ]
                            else:
                                # Municipal priority keywords
                                priority_keywords = [
                                    "department", "government", "director", "office",
                                    "team", "about", "leadership", "staff", "contact",
                                    "executive", "management", "board", "council", "services"
                                ]
                            if any(kw in full_url.lower() for kw in priority_keywords):
                                to_visit.insert(0, full_url)
                            else:
                                to_visit.append(full_url)

                elif response.status_code >= 400:
                    errors_count += 1

                time.sleep(config.rate_limit_delay)

            except httpx.TimeoutException:
                errors_count += 1
                time.sleep(1)
            except httpx.RequestError:
                errors_count += 1
            except Exception:
                errors_count += 1

        return pages

    def _build_candidates(self, result: DiscoveryResult) -> None:
        """Build candidate list from extracted data for user selection."""
        candidates: list[DiscoveryCandidate] = []

        # Add executive as candidate (Mayor, Governor, etc.)
        if result.executive:
            exec_type = classify_candidate_type(
                result.executive.name,
                result.executive.title,
                is_person=True
            )
            candidates.append(DiscoveryCandidate(
                id="exec-mayor",
                name=result.executive.name,
                type=exec_type,
                url=result.executive.url or result.source_url,
                confidence="high",
                source_urls=[result.executive.url] if result.executive.url else [],
                suggested_agent_name=f"{result.executive.title}'s Office Assistant",
                metadata={
                    "title": result.executive.title,
                    "office": result.executive.office,
                    "category": "leadership",
                },
            ))

        # Add chief officers as candidates (Cabinet level)
        for i, officer in enumerate(result.chief_officers):
            officer_type = classify_candidate_type(
                officer.name,
                officer.title,
                is_person=True
            )
            candidates.append(DiscoveryCandidate(
                id=f"officer-{i}",
                name=officer.name,
                type=officer_type,
                url=officer.url or result.source_url,
                confidence="medium",
                source_urls=[officer.url] if officer.url else [],
                suggested_agent_name=f"{officer.title} Assistant",
                metadata={
                    "title": officer.title,
                    "office": officer.office,
                    "category": "leadership",
                },
            ))

        # Add departments and their directors as separate candidates
        for dept in result.departments:
            # Classify the department itself
            dept_type = classify_candidate_type(
                dept.name,
                dept.suggested_template or "",
                is_person=False
            )

            # Add the department as a candidate
            candidates.append(DiscoveryCandidate(
                id=f"dept-{dept.id}",
                name=dept.name,
                type=dept_type,
                url=dept.url or result.source_url,
                confidence="high" if dept.director else "medium",
                source_urls=[dept.url] if dept.url else [],
                suggested_agent_name=f"{dept.name} Assistant",
                metadata={
                    "director": dept.director,
                    "director_title": dept.director_title,
                    "template": dept.suggested_template,
                    "category": "department",
                },
            ))

            # If we have a director, also add them as a LEADERSHIP candidate
            if dept.director:
                director_title = dept.director_title or "Director"
                director_type = classify_candidate_type(
                    dept.director,
                    f"{director_title} {dept.name}",
                    is_person=True
                )
                candidates.append(DiscoveryCandidate(
                    id=f"leader-{dept.id}",
                    name=dept.director,
                    type=director_type,
                    url=dept.url or result.source_url,
                    confidence="high",
                    source_urls=[dept.url] if dept.url else [],
                    suggested_agent_name=f"{director_title} of {dept.name} Assistant",
                    metadata={
                        "title": director_title,
                        "department": dept.name,
                        "category": "leadership",
                    },
                ))

        # Add data portals as candidates
        for i, portal in enumerate(result.data_portals):
            candidates.append(DiscoveryCandidate(
                id=f"portal-{i}",
                name=f"Data Portal ({portal.type})",
                type=CandidateType.DATA_PORTAL.value,
                url=portal.url,
                confidence="high",
                source_urls=[portal.detected_via] if portal.detected_via else [],
                suggested_agent_name=f"Open Data Assistant",
                metadata={
                    "portal_type": portal.type,
                    "api_endpoint": portal.api_endpoint,
                    "category": "data",
                },
            ))

        result.candidates = candidates

    # =========================================================================
    # NULL-SAFE EXTRACTION METHODS
    # All extraction logic uses defensive programming to prevent crashes
    # =========================================================================

    def _safe_strip(self, value: Any) -> str:
        """Safely strip a value, returning empty string if None."""
        if value is None:
            return ""
        return str(value).strip()

    def _safe_group(self, match: re.Match | None, group: int = 1) -> str:
        """Safely get a regex group, returning empty string if None."""
        if match is None:
            return ""
        try:
            result = match.group(group)
            return self._safe_strip(result)
        except (IndexError, AttributeError):
            return ""

    def _extract_municipality_safe(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract basic municipality information with null-safety."""
        try:
            home_content = pages.get(base_url) or pages.get(base_url + "/") or ""
            if not home_content:
                # Try first available page
                home_content = next(iter(pages.values()), "")

            soup = BeautifulSoup(home_content, "html.parser")
            title = soup.find("title")
            title_text = self._safe_strip(title.get_text() if title else "")

            city_name = ""
            state = None

            # Pattern: "City of X" or "X City"
            match = re.search(r"City\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", title_text)
            if match:
                city_name = f"City of {self._safe_group(match, 1)}"
            else:
                match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+City", title_text)
                if match:
                    city_name = f"{self._safe_group(match, 1)} City"

            # Try to extract state
            state_match = re.search(r",\s*([A-Z]{2}|[A-Z][a-z]+)\s*$", title_text)
            if state_match:
                state = self._safe_group(state_match, 1) or None

            # Fallback to domain name
            if not city_name:
                parsed = urlparse(base_url)
                domain_parts = parsed.netloc.replace("www.", "").split(".")
                if domain_parts:
                    city_name = domain_parts[0].replace("-", " ").title()

            result.municipality = Municipality(
                name=city_name or "Unknown Organization",
                state=state,
                website=base_url,
            )
        except Exception as e:
            # Log but don't crash
            result.municipality = Municipality(
                name="Unknown Organization",
                website=base_url,
            )

    def _extract_executive_safe(
        self, result: DiscoveryResult, pages: dict[str, str], config: CrawlConfig
    ) -> None:
        """Extract executives with null-safety. Supports municipal and enterprise orgs."""
        try:
            is_enterprise = config.org_type == "enterprise"

            for url, content in pages.items():
                if not content:
                    continue

                soup = BeautifulSoup(content, "html.parser")
                text_content = (soup.get_text() or "").lower()

                if is_enterprise:
                    # Extract enterprise executives (CEO, COO, CFO, etc.)
                    self._extract_enterprise_executives(result, url, content, text_content)
                else:
                    # Extract municipal executives (Mayor, etc.)
                    self._extract_municipal_executives(result, url, content, text_content)

        except Exception:
            pass  # Log but don't crash

    def _extract_municipal_executives(
        self, result: DiscoveryResult, url: str, content: str, text_content: str
    ) -> None:
        """Extract municipal executives (Mayor, City Manager, etc.)."""
        # Look for mayor
        if not result.executive and "mayor" in text_content:
            for pattern in [
                r"Mayor\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+Mayor",
            ]:
                match = re.search(pattern, content or "")
                if match:
                    name = self._safe_group(match, 1)
                    if name and len(name.split()) >= 2:
                        result.executive = Executive(
                            name=name,
                            title="Mayor",
                            office="Office of the Mayor",
                            url=url,
                        )
                        break

        # Look for chief officers
        for officer_pattern in EXECUTIVE_PATTERNS[1:]:
            if not re.search(officer_pattern, text_content):
                continue

            for name_pattern in [
                rf"({officer_pattern.replace(chr(92) + 's*', ' ')})\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                rf"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+({officer_pattern.replace(chr(92) + 's*', ' ')})",
            ]:
                try:
                    matches = re.finditer(name_pattern, content or "", re.IGNORECASE)
                    for match in matches:
                        groups = match.groups()
                        if not groups or len(groups) < 2:
                            continue

                        name = self._safe_strip(groups[1] if groups[1] else groups[0])
                        title = self._safe_strip(groups[0] if groups[1] else "")

                        if name and len(name.split()) >= 2:
                            officer = Executive(
                                name=name,
                                title=title.title() if title else "Chief Officer",
                                office="Executive Office",
                                url=url,
                            )
                            if not any(o.name == officer.name for o in result.chief_officers):
                                result.chief_officers.append(officer)
                                break
                except Exception:
                    continue

    def _extract_enterprise_executives(
        self, result: DiscoveryResult, url: str, content: str, text_content: str
    ) -> None:
        """Extract enterprise executives (CEO, COO, CFO, VPs, etc.)."""
        # Check for C-suite and executive patterns
        for title_pattern, title_name in ENTERPRISE_EXECUTIVE_PATTERNS:
            if not re.search(title_pattern, text_content, re.IGNORECASE):
                continue

            # Look for name patterns near the title
            name_patterns = [
                # Title followed by name
                rf"(?:{title_pattern})[,:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                # Name followed by title
                rf"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)[,\s]+(?:{title_pattern})",
                # Name with title in context
                rf"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s*[-–—]\s*(?:{title_pattern})",
            ]

            for name_pattern in name_patterns:
                try:
                    matches = re.finditer(name_pattern, content or "", re.IGNORECASE)
                    for match in matches:
                        name = self._safe_group(match, 1)
                        if not name or len(name.split()) < 2:
                            continue

                        # Skip common false positives
                        if any(fp in name.lower() for fp in ["company", "corporation", "inc", "llc", "about", "contact"]):
                            continue

                        # CEO is the top executive
                        if "ceo" in title_name.lower() or "chief executive" in title_name.lower():
                            if not result.executive:
                                result.executive = Executive(
                                    name=name,
                                    title=title_name,
                                    office="Office of the CEO",
                                    url=url,
                                )
                        else:
                            # Other executives go to chief_officers
                            officer = Executive(
                                name=name,
                                title=title_name,
                                office="Executive Team",
                                url=url,
                            )
                            if not any(o.name == officer.name for o in result.chief_officers):
                                result.chief_officers.append(officer)
                        break
                except Exception:
                    continue

    def _extract_departments_safe(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str, config: CrawlConfig
    ) -> None:
        """Extract departments and their directors with null-safety."""
        seen_departments: set[str] = set()

        # Use appropriate department keywords based on org type
        if config.org_type == "enterprise":
            department_keywords = ENTERPRISE_DEPARTMENT_KEYWORDS
        else:
            department_keywords = DEPARTMENT_KEYWORDS

        try:
            for url, content in pages.items():
                if not content:
                    continue

                soup = BeautifulSoup(content, "html.parser")

                for element in soup.find_all(["a", "h1", "h2", "h3", "h4"]):
                    try:
                        text = self._safe_strip(element.get_text())
                        if not text or len(text) < 3 or len(text) > 100:
                            continue

                        text_lower = text.lower()

                        for template_id, keywords in department_keywords.items():
                            if any(kw in text_lower for kw in keywords):
                                dept_key = text_lower[:50]
                                if dept_key in seen_departments:
                                    continue
                                seen_departments.add(dept_key)

                                dept_id = re.sub(r"[^a-z0-9]+", "-", text_lower)[:30].strip("-")
                                if not dept_id:
                                    continue

                                dept_url = None
                                if element.name == "a":
                                    href = element.get("href")
                                    if href:
                                        dept_url = urljoin(base_url, href)

                                director_name = None
                                director_title = None

                                parent = element.parent
                                if parent:
                                    parent_text = self._safe_strip(parent.get_text())
                                    for title_pattern in DEPARTMENT_HEAD_PATTERNS:
                                        match = re.search(
                                            rf"({title_pattern})[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                                            parent_text,
                                            re.IGNORECASE,
                                        )
                                        if match:
                                            director_title = self._safe_group(match, 1).title()
                                            director_name = self._safe_group(match, 2)
                                            break

                                department = Department(
                                    id=dept_id,
                                    name=text,
                                    director=director_name or None,
                                    director_title=director_title or None,
                                    url=dept_url,
                                    suggested_template=template_id,
                                    keywords_matched=[kw for kw in keywords if kw in text_lower],
                                )
                                result.departments.append(department)
                                break
                    except Exception:
                        continue
        except Exception:
            pass  # Log but don't crash

    def _extract_data_portals_safe(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract links to open data portals with null-safety."""
        seen_portals: set[str] = set()

        try:
            for url, content in pages.items():
                if not content:
                    continue

                soup = BeautifulSoup(content, "html.parser")

                for link in soup.find_all("a", href=True):
                    try:
                        href = link.get("href", "")
                        if not href:
                            continue

                        full_url = urljoin(base_url, href)

                        for pattern, portal_type in DATA_PORTAL_PATTERNS:
                            if re.search(pattern, full_url, re.IGNORECASE):
                                parsed = urlparse(full_url)
                                portal_url = f"{parsed.scheme}://{parsed.netloc}"

                                if portal_url not in seen_portals:
                                    seen_portals.add(portal_url)

                                    api_endpoint = None
                                    if portal_type == "socrata":
                                        api_endpoint = f"{portal_url}/resource/"
                                    elif portal_type == "ckan":
                                        api_endpoint = f"{portal_url}/api/3/"

                                    result.data_portals.append(DataPortal(
                                        type=portal_type,
                                        url=portal_url,
                                        api_endpoint=api_endpoint,
                                        detected_via=url,
                                    ))
                                break
                    except Exception:
                        continue
        except Exception:
            pass  # Log but don't crash

    def _extract_governance_docs_safe(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract links to governance documents with null-safety."""
        doc_patterns = {
            "charter": [r"city\s*charter", r"municipal\s*charter"],
            "ordinance": [r"ordinance", r"codified\s*ordinances", r"municipal\s*code"],
            "policy": [r"policy", r"policies", r"administrative\s*rules"],
            "budget": [r"budget", r"annual\s*budget", r"financial\s*report"],
        }

        seen_docs: set[str] = set()

        try:
            for url, content in pages.items():
                if not content:
                    continue

                soup = BeautifulSoup(content, "html.parser")

                for link in soup.find_all("a", href=True):
                    try:
                        link_text = self._safe_strip(link.get_text()).lower()
                        href = link.get("href", "")
                        if not href:
                            continue

                        for doc_type, patterns in doc_patterns.items():
                            if any(re.search(p, link_text) for p in patterns):
                                full_url = urljoin(base_url, href)
                                if full_url not in seen_docs:
                                    seen_docs.add(full_url)
                                    result.governance_docs.append(GovernanceDoc(
                                        type=doc_type,
                                        title=self._safe_strip(link.get_text()),
                                        url=full_url,
                                    ))
                                break
                    except Exception:
                        continue
        except Exception:
            pass  # Log but don't crash



# Module-level singleton
_discovery_engine: DiscoveryEngine | None = None


def get_discovery_engine() -> DiscoveryEngine:
    """Get the discovery engine singleton."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = DiscoveryEngine()
    return _discovery_engine


def start_discovery(url: str, config: CrawlConfig | None = None) -> str:
    """Start a discovery job for a URL."""
    return get_discovery_engine().start_discovery(url, config)


def get_discovery_status(job_id: str) -> DiscoveryResult | None:
    """Get the status of a discovery job."""
    return get_discovery_engine().get_status(job_id)


def cancel_discovery(job_id: str) -> bool:
    """Cancel a running discovery job."""
    return get_discovery_engine().cancel_discovery(job_id)


def update_candidate_selection(job_id: str, selections: dict[str, bool]) -> bool:
    """Update candidate selections for a discovery job.

    Args:
        job_id: The discovery job ID
        selections: Dict mapping candidate IDs to selected status

    Returns:
        True if update was successful
    """
    engine = get_discovery_engine()
    result = engine.get_status(job_id)
    if not result:
        return False

    for candidate in result.candidates:
        if candidate.id in selections:
            candidate.selected = selections[candidate.id]

    engine._save_jobs()
    return True


def get_selected_candidates(job_id: str) -> list[DiscoveryCandidate]:
    """Get only the selected candidates from a discovery job."""
    result = get_discovery_status(job_id)
    if not result:
        return []
    return [c for c in result.candidates if c.selected]
