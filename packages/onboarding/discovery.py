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

# Title patterns for detecting executives and department heads
EXECUTIVE_PATTERNS = [
    r"mayor",
    r"city\s*manager",
    r"chief\s*(of\s*staff|executive|operating|financial|administrative)",
    r"deputy\s*mayor",
    r"city\s*administrator",
]

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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "source_url": self.source_url,
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
                        "email": d.contact.email,
                        "phone": d.contact.phone,
                        "address": d.contact.address,
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
        }


class DiscoveryEngine:
    """Crawls municipal websites to discover organizational structure."""

    def __init__(
        self,
        storage_path: Path | None = None,
        max_pages: int = 100,
        rate_limit_delay: float = 0.5,
    ) -> None:
        if not HAS_CRAWLER_DEPS:
            raise RuntimeError(
                "Crawler dependencies not installed. "
                "Install with: pip install httpx beautifulsoup4"
            )

        self.storage_path = storage_path or Path("data/onboarding")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_pages = max_pages
        self.rate_limit_delay = rate_limit_delay
        self._jobs: dict[str, DiscoveryResult] = {}
        self._load_jobs()

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

    def start_discovery(self, url: str) -> str:
        """Start a discovery job for a URL.

        Args:
            url: The municipal website URL to discover

        Returns:
            Job ID for tracking progress
        """
        job_id = self._generate_job_id(url)

        result = DiscoveryResult(
            id=job_id,
            status=DiscoveryStatus.PENDING,
            started_at=datetime.utcnow().isoformat(),
            source_url=url,
        )
        self._jobs[job_id] = result
        self._save_jobs()

        # Start discovery in background thread
        thread = threading.Thread(
            target=self._run_discovery,
            args=(job_id, url),
            daemon=True,
        )
        thread.start()

        return job_id

    def get_status(self, job_id: str) -> DiscoveryResult | None:
        """Get the status of a discovery job."""
        return self._jobs.get(job_id)

    def _run_discovery(self, job_id: str, url: str) -> None:
        """Run the discovery process."""
        import ssl
        import certifi

        result = self._jobs[job_id]
        result.status = DiscoveryStatus.CRAWLING
        self._save_jobs()

        try:
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
                # Crawl the site
                pages_content = self._crawl_site(client, base_url, url, result)
                result.pages_crawled = len(pages_content)

                if not pages_content:
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
                        pages_content = self._crawl_site(fallback_client, base_url, url, result)
                        result.pages_crawled = len(pages_content)

                # Extract organization info
                result.status = DiscoveryStatus.EXTRACTING
                self._save_jobs()

                self._extract_municipality(result, pages_content, base_url)
                self._extract_executive(result, pages_content)
                self._extract_departments(result, pages_content, base_url)
                self._extract_data_portals(result, pages_content, base_url)
                self._extract_governance_docs(result, pages_content, base_url)

                result.status = DiscoveryStatus.COMPLETED
                result.completed_at = datetime.utcnow().isoformat()

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

    def _extract_municipality(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract basic municipality information."""
        # Try to get from homepage title
        home_content = pages.get(base_url) or pages.get(base_url + "/") or ""
        soup = BeautifulSoup(home_content, "html.parser")

        title = soup.find("title")
        title_text = title.get_text() if title else ""

        # Try to extract city name
        city_name = ""
        state = None

        # Pattern: "City of X" or "X City"
        match = re.search(r"City\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", title_text)
        if match:
            city_name = f"City of {match.group(1)}"
        else:
            match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+City", title_text)
            if match:
                city_name = f"{match.group(1)} City"

        # Try to extract state
        state_match = re.search(r",\s*([A-Z]{2}|[A-Z][a-z]+)\s*$", title_text)
        if state_match:
            state = state_match.group(1)

        # Fallback to domain name
        if not city_name:
            parsed = urlparse(base_url)
            domain_parts = parsed.netloc.replace("www.", "").split(".")
            if domain_parts:
                city_name = domain_parts[0].replace("-", " ").title()

        result.municipality = Municipality(
            name=city_name,
            state=state,
            website=base_url,
        )

    def _extract_executive(
        self, result: DiscoveryResult, pages: dict[str, str]
    ) -> None:
        """Extract mayor and chief officers."""
        for url, content in pages.items():
            soup = BeautifulSoup(content, "html.parser")
            text_content = soup.get_text().lower()

            # Look for mayor
            if not result.executive and "mayor" in text_content:
                # Try to find mayor's name
                for pattern in [
                    r"Mayor\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+Mayor",
                ]:
                    match = re.search(pattern, content)
                    if match:
                        result.executive = Executive(
                            name=match.group(1).strip(),
                            title="Mayor",
                            office="Office of the Mayor",
                            url=url,
                        )
                        break

            # Look for chief officers
            for officer_pattern in EXECUTIVE_PATTERNS[1:]:  # Skip mayor
                if re.search(officer_pattern, text_content):
                    # Try to extract name
                    for name_pattern in [
                        rf"({officer_pattern.replace(r'\s*', ' ')})\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                        rf"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+({officer_pattern.replace(r'\s*', ' ')})",
                    ]:
                        matches = re.finditer(name_pattern, content, re.IGNORECASE)
                        for match in matches:
                            groups = match.groups()
                            name = groups[1] if len(groups) > 1 else groups[0]
                            title = groups[0] if len(groups) > 1 else ""

                            if name and len(name.split()) >= 2:
                                officer = Executive(
                                    name=name.strip(),
                                    title=title.strip().title() if title else "Chief Officer",
                                    office="Executive Office",
                                    url=url,
                                )
                                # Avoid duplicates
                                if not any(o.name == officer.name for o in result.chief_officers):
                                    result.chief_officers.append(officer)
                                    break

    def _extract_departments(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract departments and their directors."""
        seen_departments: set[str] = set()

        for url, content in pages.items():
            soup = BeautifulSoup(content, "html.parser")

            # Look for department patterns in links and headings
            for element in soup.find_all(["a", "h1", "h2", "h3", "h4"]):
                text = element.get_text().strip()

                # Check if this looks like a department
                text_lower = text.lower()

                for template_id, keywords in DEPARTMENT_KEYWORDS.items():
                    if any(kw in text_lower for kw in keywords):
                        # Avoid duplicates
                        dept_key = text_lower[:50]
                        if dept_key in seen_departments:
                            continue
                        seen_departments.add(dept_key)

                        # Generate department ID
                        dept_id = re.sub(r"[^a-z0-9]+", "-", text_lower)[:30].strip("-")

                        # Get URL if it's a link
                        dept_url = None
                        if element.name == "a" and element.get("href"):
                            dept_url = urljoin(base_url, element["href"])

                        # Try to find director
                        director_name = None
                        director_title = None

                        # Look in surrounding content
                        parent = element.parent
                        if parent:
                            parent_text = parent.get_text()
                            for title_pattern in DEPARTMENT_HEAD_PATTERNS:
                                match = re.search(
                                    rf"({title_pattern})[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                                    parent_text,
                                    re.IGNORECASE,
                                )
                                if match:
                                    director_title = match.group(1).strip().title()
                                    director_name = match.group(2).strip()
                                    break

                        department = Department(
                            id=dept_id,
                            name=text,
                            director=director_name,
                            director_title=director_title,
                            url=dept_url,
                            suggested_template=template_id,
                            keywords_matched=[kw for kw in keywords if kw in text_lower],
                        )
                        result.departments.append(department)
                        break

    def _extract_data_portals(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract links to open data portals."""
        seen_portals: set[str] = set()

        for url, content in pages.items():
            soup = BeautifulSoup(content, "html.parser")

            # Check all links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(base_url, href)

                # Check against portal patterns
                for pattern, portal_type in DATA_PORTAL_PATTERNS:
                    if re.search(pattern, full_url, re.IGNORECASE):
                        # Normalize URL
                        parsed = urlparse(full_url)
                        portal_url = f"{parsed.scheme}://{parsed.netloc}"

                        if portal_url not in seen_portals:
                            seen_portals.add(portal_url)

                            # Determine API endpoint
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

            # Also check page text for data portal mentions
            text = soup.get_text().lower()
            if "open data" in text or "data portal" in text:
                # The page mentions open data - check for associated links
                for link in soup.find_all("a", href=True):
                    link_text = link.get_text().lower()
                    if "data" in link_text or "open" in link_text:
                        href = link["href"]
                        full_url = urljoin(base_url, href)
                        if full_url not in seen_portals and "data" in full_url.lower():
                            seen_portals.add(full_url)
                            result.data_portals.append(DataPortal(
                                type="unknown",
                                url=full_url,
                                detected_via=url,
                            ))

    def _extract_governance_docs(
        self, result: DiscoveryResult, pages: dict[str, str], base_url: str
    ) -> None:
        """Extract links to governance documents (charter, ordinances, etc.)."""
        doc_patterns = {
            "charter": [r"city\s*charter", r"municipal\s*charter"],
            "ordinance": [r"ordinance", r"codified\s*ordinances", r"municipal\s*code"],
            "policy": [r"policy", r"policies", r"administrative\s*rules"],
            "budget": [r"budget", r"annual\s*budget", r"financial\s*report"],
        }

        seen_docs: set[str] = set()

        for url, content in pages.items():
            soup = BeautifulSoup(content, "html.parser")

            for link in soup.find_all("a", href=True):
                link_text = link.get_text().lower()
                href = link["href"]

                for doc_type, patterns in doc_patterns.items():
                    if any(re.search(p, link_text) for p in patterns):
                        full_url = urljoin(base_url, href)
                        if full_url not in seen_docs:
                            seen_docs.add(full_url)
                            result.governance_docs.append(GovernanceDoc(
                                type=doc_type,
                                title=link.get_text().strip(),
                                url=full_url,
                            ))
                        break


# Module-level singleton
_discovery_engine: DiscoveryEngine | None = None


def get_discovery_engine() -> DiscoveryEngine:
    """Get the discovery engine singleton."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = DiscoveryEngine()
    return _discovery_engine


def start_discovery(url: str) -> str:
    """Start a discovery job for a URL."""
    return get_discovery_engine().start_discovery(url)


def get_discovery_status(job_id: str) -> DiscoveryResult | None:
    """Get the status of a discovery job."""
    return get_discovery_engine().get_status(job_id)
