"""
Cleveland Public Data Importer

Fetches real-time governance documents from Cleveland city websites
and uploads them to each agent's knowledge base.

Usage:
    python scripts/import_cleveland_data.py --agent all
    python scripts/import_cleveland_data.py --agent public-health
    python scripts/import_cleveland_data.py --list
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import html2text

# API Configuration
API_BASE = os.getenv("AIOS_API_URL", "http://localhost:8000")

# HTML to Markdown converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = True
h2t.body_width = 0  # No wrapping


@dataclass
class DataSource:
    """A public data source to import."""
    name: str
    url: str
    description: str
    doc_type: str = "html"  # html, pdf, json
    selector: Optional[str] = None  # CSS selector for content extraction


# ============================================================================
# AGENT DATA SOURCES - VERIFIED WORKING URLS
# ============================================================================

AGENT_SOURCES = {
    "concierge": [
        DataSource(
            name="CITY_SERVICES_DIRECTORY",
            url="https://www.clevelandohio.gov/residents",
            description="Cleveland Resident Services Directory",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="311_SERVICES_PORTAL",
            url="https://www.clevelandohio.gov/311",
            description="Cleveland 311 Services Portal",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CITY_DEPARTMENTS_LIST",
            url="https://www.clevelandohio.gov/city-hall/departments",
            description="Cleveland City Departments Directory",
            selector="main, .content, article, body"
        ),
    ],

    "urban-ai": [
        DataSource(
            name="NIST_AI_RMF",
            url="https://www.nist.gov/itl/ai-risk-management-framework",
            description="NIST AI Risk Management Framework",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CLEVELAND_OPEN_DATA",
            url="https://data.clevelandohio.gov/",
            description="Cleveland Open Data Portal",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="SMART_CITIES_OVERVIEW",
            url="https://www.smartcitiesworld.net/special-reports/special-reports/smart-city-strategies",
            description="Smart Cities Strategy Overview",
            selector="main, .content, article, body"
        ),
    ],

    "council-president": [
        DataSource(
            name="CITY_COUNCIL_MAIN",
            url="https://www.clevelandcitycouncil.org/",
            description="Cleveland City Council Official Site",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CHARTER_ORDINANCES_PAGE",
            url="https://www.clevelandcitycouncil.org/legislation-laws/charter-codified-ordinances",
            description="Charter & Codified Ordinances",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CODES_ORDINANCES_HUB",
            url="https://www.clevelandohio.gov/residents/codes-ordinances",
            description="Cleveland Codes & Ordinances Hub",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="ROBERTS_RULES_SIMPLIFIED",
            url="http://www.rulesonline.com/",
            description="Robert's Rules of Order - Full Reference",
            selector="body"
        ),
    ],

    "public-utilities": [
        DataSource(
            name="EPA_SAFE_DRINKING_WATER",
            url="https://www.epa.gov/dwreginfo/drinking-water-regulations",
            description="EPA Safe Drinking Water Act Regulations",
            selector="main, .main-content, article, body"
        ),
        DataSource(
            name="EPA_LEAD_COPPER_RULE",
            url="https://www.epa.gov/dwreginfo/lead-and-copper-rule",
            description="EPA Lead and Copper Rule",
            selector="main, .main-content, article, body"
        ),
        DataSource(
            name="CLEVELAND_PUBLIC_POWER",
            url="https://www.cpp.org/",
            description="Cleveland Public Power",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="EPA_CLEAN_WATER_ACT",
            url="https://www.epa.gov/laws-regulations/summary-clean-water-act",
            description="EPA Clean Water Act Summary",
            selector="main, .main-content, article, body"
        ),
        DataSource(
            name="PUCO_OVERVIEW",
            url="https://puco.ohio.gov/about-us",
            description="Public Utilities Commission of Ohio",
            selector="main, .content, article, body"
        ),
    ],

    "communications": [
        DataSource(
            name="CITY_NEWS_PRESS",
            url="https://www.clevelandohio.gov/news",
            description="Cleveland City News & Press Releases",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="MAYOR_OFFICE",
            url="https://www.clevelandohio.gov/city-hall/mayor",
            description="Mayor's Office Communications",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="AP_STYLE_GUIDE_BASICS",
            url="https://owl.purdue.edu/owl/subject_specific_writing/journalism_and_journalistic_writing/ap_style.html",
            description="AP Style Guide Basics (Purdue OWL)",
            selector="main, .content, article, body"
        ),
    ],

    "public-health": [
        DataSource(
            name="CDPH_MAIN",
            url="https://www.clevelandhealth.org/",
            description="Cleveland Dept of Public Health",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="OHIO_DEPT_HEALTH",
            url="https://odh.ohio.gov/",
            description="Ohio Department of Health",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CDC_LEAD_PREVENTION",
            url="https://www.cdc.gov/lead-prevention/about/index.html",
            description="CDC Lead Poisoning Prevention",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CDC_COMMUNITY_HEALTH",
            url="https://www.cdc.gov/places/index.html",
            description="CDC PLACES - Community Health Data",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="HEALTH_EQUITY_CDC",
            url="https://www.cdc.gov/healthequity/index.html",
            description="CDC Health Equity Resources",
            selector="main, .content, article, body"
        ),
    ],

    "building-housing": [
        DataSource(
            name="OHIO_BUILDING_CODE",
            url="https://com.ohio.gov/divisions-and-programs/industrial-compliance/bureau-of-building-code-compliance/ohio-building-code",
            description="Ohio Building Code Overview",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CLEVELAND_BUILDING_HOUSING",
            url="https://www.clevelandohio.gov/city-hall/departments/building-housing",
            description="Cleveland Building & Housing Dept",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="HUD_HOUSING_STANDARDS",
            url="https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_rights_and_obligations",
            description="HUD Fair Housing Standards",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="LEAD_SAFE_INFO",
            url="https://www.epa.gov/lead/protect-your-family-sources-lead",
            description="EPA Lead Safety Information",
            selector="main, .content, article, body"
        ),
    ],

    "public-safety": [
        DataSource(
            name="CLEVELAND_PUBLIC_SAFETY",
            url="https://www.clevelandohio.gov/city-hall/departments/public-safety",
            description="Cleveland Public Safety Department",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CONSENT_DECREE_PAGE",
            url="https://www.clevelandohio.gov/city-hall/office-professional-standards/consent-decree",
            description="Cleveland Consent Decree Information",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="POLICE_COMMISSION",
            url="https://clecpc.org/",
            description="Cleveland Community Police Commission",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CONSENT_DECREE_RESOURCES",
            url="https://clecpc.org/resources/consent-decree/",
            description="Consent Decree Resources & Documents",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="DOJ_USE_OF_FORCE",
            url="https://cops.usdoj.gov/useof force",
            description="DOJ Use of Force Guidelines",
            doc_type="info_only"  # Reference - manual upload
        ),
    ],

    "parks-recreation": [
        DataSource(
            name="CLEVELAND_METROPARKS",
            url="https://www.clevelandmetroparks.com/",
            description="Cleveland Metroparks",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CLEVELAND_PARKS_REC",
            url="https://www.clevelandohio.gov/city-hall/departments/parks-recreation",
            description="Cleveland Parks & Recreation Dept",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="METROPARKS_RESERVATIONS",
            url="https://www.clevelandmetroparks.com/parks",
            description="Metroparks Reservations & Locations",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="REC_PROGRAMS",
            url="https://www.clevelandohio.gov/residents/recreation",
            description="Cleveland Recreation Programs",
            selector="main, .content, article, body"
        ),
    ],

    # Additional HR agent if needed
    "hr": [
        DataSource(
            name="HR_POLICIES_MAIN",
            url="https://www.clevelandohio.gov/city-hall/departments/human-resources/policies",
            description="Cleveland HR Policies",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="HR_DEPARTMENT_SERVICES",
            url="https://www.clevelandohio.gov/city-hall/departments/human-resources/department-services",
            description="HR Department Services",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CIVIL_SERVICE_COMMISSION",
            url="https://www.clevelandohio.gov/city-hall/departments/civil-service-commission",
            description="Civil Service Commission",
            selector="main, .content, article, body"
        ),
    ],

    # Additional Finance agent if needed
    "finance": [
        DataSource(
            name="FINANCE_DEPARTMENT",
            url="https://www.clevelandohio.gov/city-hall/departments/finance",
            description="Cleveland Finance Department",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="PURCHASES_SUPPLIES",
            url="https://www.clevelandohio.gov/city-hall/departments/finance/divisions/purchases-supplies",
            description="Division of Purchases & Supplies",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="VENDOR_SERVICES",
            url="https://www.clevelandohio.gov/city-hall/departments/finance/vendor-services",
            description="Vendor Services Information",
            selector="main, .content, article, body"
        ),
    ],

    # Additional 311 agent if needed
    "311": [
        DataSource(
            name="311_MAIN_PORTAL",
            url="https://www.clevelandohio.gov/311",
            description="Cleveland 311 Main Portal",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="SERVICE_REQUESTS",
            url="https://www.clevelandohio.gov/residents/report-issue",
            description="Report an Issue / Service Requests",
            selector="main, .content, article, body"
        ),
        DataSource(
            name="CITY_SERVICES_GUIDE",
            url="https://www.clevelandohio.gov/residents",
            description="City Services Guide for Residents",
            selector="main, .content, article, body"
        ),
    ],
}


# ============================================================================
# FETCHER FUNCTIONS
# ============================================================================

def fetch_html(url: str, selector: Optional[str] = None) -> tuple[str, str]:
    """Fetch HTML page and convert to markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as e:
        return "", f"Error fetching {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        element.decompose()

    # Try to find main content
    content = None
    if selector:
        for sel in selector.split(", "):
            content = soup.select_one(sel.strip())
            if content:
                break

    if not content:
        content = soup.find("main") or soup.find("article") or soup.find("body")

    if not content:
        return "", "Could not find content"

    # Convert to markdown
    html_content = str(content)
    markdown = h2t.handle(html_content)

    # Clean up markdown
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Remove excessive newlines
    markdown = markdown.strip()

    return markdown, ""


def create_knowledge_doc(source: DataSource, content: str) -> str:
    """Create a formatted knowledge document."""
    doc = f"""# {source.name}

## Source Information
- **URL:** {source.url}
- **Description:** {source.description}
- **Retrieved:** {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Type:** Official Public Source

---

## Content

{content}

---

*This document was automatically imported from official public sources.*
*It should be periodically refreshed to ensure accuracy.*
*Last updated: {time.strftime('%Y-%m-%d')}*
"""
    return doc


def upload_to_agent(agent_id: str, filename: str, content: str) -> dict:
    """Upload a document to an agent's knowledge base."""
    url = f"{API_BASE}/agents/{agent_id}/knowledge"

    files = {
        "file": (filename, content.encode("utf-8"), "text/markdown")
    }

    try:
        response = requests.post(url, files=files, timeout=60)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def import_agent_data(agent_id: str, dry_run: bool = False) -> dict:
    """Import all data sources for an agent."""
    if agent_id not in AGENT_SOURCES:
        return {"error": f"No sources configured for agent: {agent_id}"}

    sources = AGENT_SOURCES[agent_id]
    results = {"agent": agent_id, "sources": [], "success": 0, "failed": 0}

    print(f"\n{'='*60}")
    print(f"Importing data for: {agent_id}")
    print(f"{'='*60}")

    for source in sources:
        print(f"\n  [{source.name}]")
        print(f"  URL: {source.url}")

        if source.doc_type == "info_only":
            print(f"  Status: Skipped (reference only - manual upload required)")
            results["sources"].append({
                "name": source.name,
                "status": "skipped",
                "reason": "Reference only - manual upload required"
            })
            continue

        # Fetch content
        print(f"  Fetching...")
        content, error = fetch_html(source.url, source.selector)

        if error:
            print(f"  Status: FAILED - {error}")
            results["sources"].append({
                "name": source.name,
                "status": "failed",
                "error": error
            })
            results["failed"] += 1
            continue

        if len(content) < 100:
            print(f"  Status: FAILED - Content too short ({len(content)} chars)")
            results["sources"].append({
                "name": source.name,
                "status": "failed",
                "error": "Content too short"
            })
            results["failed"] += 1
            continue

        print(f"  Fetched: {len(content):,} characters")

        # Create document
        doc_content = create_knowledge_doc(source, content)
        filename = f"{source.name}.md"

        if dry_run:
            print(f"  Status: DRY RUN - Would upload {filename}")
            results["sources"].append({
                "name": source.name,
                "status": "dry_run",
                "size": len(doc_content)
            })
            results["success"] += 1
            continue

        # Upload
        print(f"  Uploading {filename}...")
        result = upload_to_agent(agent_id, filename, doc_content)

        if result["success"]:
            print(f"  Status: SUCCESS")
            results["sources"].append({
                "name": source.name,
                "status": "success",
                "size": len(doc_content)
            })
            results["success"] += 1
        else:
            print(f"  Status: UPLOAD FAILED - {result['error']}")
            results["sources"].append({
                "name": source.name,
                "status": "upload_failed",
                "error": result["error"]
            })
            results["failed"] += 1

        # Rate limiting
        time.sleep(1)

    return results


def list_sources():
    """List all configured data sources."""
    print("\n" + "="*70)
    print("CLEVELAND PUBLIC DATA SOURCES")
    print("="*70)

    total = 0
    for agent_id, sources in AGENT_SOURCES.items():
        print(f"\n[{agent_id}] ({len(sources)} sources)")
        for source in sources:
            status = "REF ONLY" if source.doc_type == "info_only" else "ACTIVE"
            print(f"  [{status}] {source.name}")
            print(f"          {source.url}")
        total += len(sources)

    print("\n" + "="*70)
    print(f"Total: {total} sources across {len(AGENT_SOURCES)} agents")


def main():
    parser = argparse.ArgumentParser(
        description="Import Cleveland public data into agent knowledge bases"
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Agent ID to import (or 'all' for all agents)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured data sources"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch but don't upload (test mode)"
    )

    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    if not args.agent:
        parser.print_help()
        return

    # Check dependencies
    try:
        import html2text
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install beautifulsoup4 html2text requests")
        sys.exit(1)

    # Import
    if args.agent == "all":
        all_results = []
        for agent_id in AGENT_SOURCES.keys():
            result = import_agent_data(agent_id, args.dry_run)
            all_results.append(result)

        # Summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        total_success = sum(r.get("success", 0) for r in all_results)
        total_failed = sum(r.get("failed", 0) for r in all_results)
        print(f"Total: {total_success} succeeded, {total_failed} failed")
    else:
        result = import_agent_data(args.agent, args.dry_run)
        print(f"\nResult: {result.get('success', 0)} succeeded, {result.get('failed', 0)} failed")


if __name__ == "__main__":
    main()
