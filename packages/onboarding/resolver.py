"""
Organization Name Resolver

Resolves organization names to their official website URLs.
Supports company names, abbreviations, and domain inference.
"""

from __future__ import annotations
import re
from typing import Optional
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTP = True
except ImportError:
    HAS_HTTP = False


# Well-known organization mappings
KNOWN_ORGANIZATIONS = {
    # Tech Giants
    "ibm": "https://www.ibm.com",
    "microsoft": "https://www.microsoft.com",
    "google": "https://www.google.com",
    "apple": "https://www.apple.com",
    "amazon": "https://www.amazon.com",
    "meta": "https://about.meta.com",
    "facebook": "https://about.meta.com",
    "netflix": "https://www.netflix.com",
    "salesforce": "https://www.salesforce.com",
    "oracle": "https://www.oracle.com",
    "adobe": "https://www.adobe.com",
    "nvidia": "https://www.nvidia.com",
    "intel": "https://www.intel.com",
    "cisco": "https://www.cisco.com",
    "vmware": "https://www.vmware.com",
    "dell": "https://www.dell.com",
    "hp": "https://www.hp.com",
    "hewlett packard": "https://www.hp.com",
    "sap": "https://www.sap.com",
    "slack": "https://slack.com",
    "zoom": "https://zoom.us",
    "dropbox": "https://www.dropbox.com",
    "spotify": "https://www.spotify.com",
    "twitter": "https://about.twitter.com",
    "x": "https://about.twitter.com",
    "linkedin": "https://www.linkedin.com",
    "uber": "https://www.uber.com",
    "lyft": "https://www.lyft.com",
    "airbnb": "https://www.airbnb.com",
    "stripe": "https://stripe.com",
    "square": "https://squareup.com",
    "shopify": "https://www.shopify.com",
    "twilio": "https://www.twilio.com",
    "github": "https://github.com",
    "gitlab": "https://about.gitlab.com",
    "atlassian": "https://www.atlassian.com",
    "servicenow": "https://www.servicenow.com",
    "workday": "https://www.workday.com",
    "snowflake": "https://www.snowflake.com",
    "databricks": "https://www.databricks.com",
    "palantir": "https://www.palantir.com",
    "openai": "https://openai.com",
    "anthropic": "https://www.anthropic.com",

    # Media
    "cnn": "https://www.cnn.com",
    "bbc": "https://www.bbc.com",
    "nbc": "https://www.nbc.com",
    "abc": "https://abc.com",
    "cbs": "https://www.cbs.com",
    "fox": "https://www.fox.com",
    "espn": "https://www.espn.com",
    "nytimes": "https://www.nytimes.com",
    "new york times": "https://www.nytimes.com",
    "washington post": "https://www.washingtonpost.com",
    "wsj": "https://www.wsj.com",
    "wall street journal": "https://www.wsj.com",
    "bloomberg": "https://www.bloomberg.com",
    "reuters": "https://www.reuters.com",
    "associated press": "https://apnews.com",
    "ap": "https://apnews.com",
    "disney": "https://thewaltdisneycompany.com",
    "warner bros": "https://www.warnerbros.com",
    "paramount": "https://www.paramount.com",
    "sony": "https://www.sony.com",
    "viacom": "https://www.viacom.com",

    # Finance
    "jpmorgan": "https://www.jpmorganchase.com",
    "jp morgan": "https://www.jpmorganchase.com",
    "chase": "https://www.chase.com",
    "bank of america": "https://www.bankofamerica.com",
    "bofa": "https://www.bankofamerica.com",
    "wells fargo": "https://www.wellsfargo.com",
    "citi": "https://www.citigroup.com",
    "citibank": "https://www.citigroup.com",
    "goldman sachs": "https://www.goldmansachs.com",
    "morgan stanley": "https://www.morganstanley.com",
    "blackrock": "https://www.blackrock.com",
    "vanguard": "https://www.vanguard.com",
    "fidelity": "https://www.fidelity.com",
    "charles schwab": "https://www.schwab.com",
    "american express": "https://www.americanexpress.com",
    "amex": "https://www.americanexpress.com",
    "visa": "https://www.visa.com",
    "mastercard": "https://www.mastercard.com",
    "paypal": "https://www.paypal.com",

    # Retail
    "walmart": "https://corporate.walmart.com",
    "target": "https://corporate.target.com",
    "costco": "https://www.costco.com",
    "home depot": "https://corporate.homedepot.com",
    "lowes": "https://corporate.lowes.com",
    "best buy": "https://corporate.bestbuy.com",
    "walgreens": "https://www.walgreens.com",
    "cvs": "https://www.cvs.com",
    "kroger": "https://www.thekrogerco.com",
    "starbucks": "https://www.starbucks.com",
    "mcdonalds": "https://corporate.mcdonalds.com",

    # Healthcare
    "unitedhealth": "https://www.unitedhealthgroup.com",
    "cvs health": "https://cvshealth.com",
    "pfizer": "https://www.pfizer.com",
    "johnson johnson": "https://www.jnj.com",
    "jnj": "https://www.jnj.com",
    "merck": "https://www.merck.com",
    "abbvie": "https://www.abbvie.com",
    "eli lilly": "https://www.lilly.com",
    "moderna": "https://www.modernatx.com",
    "bristol myers": "https://www.bms.com",

    # Automotive
    "tesla": "https://www.tesla.com",
    "ford": "https://corporate.ford.com",
    "gm": "https://www.gm.com",
    "general motors": "https://www.gm.com",
    "toyota": "https://www.toyota.com",
    "honda": "https://www.honda.com",
    "bmw": "https://www.bmw.com",
    "mercedes": "https://www.mercedes-benz.com",
    "volkswagen": "https://www.volkswagen.com",
    "vw": "https://www.volkswagen.com",

    # Energy
    "exxon": "https://corporate.exxonmobil.com",
    "exxonmobil": "https://corporate.exxonmobil.com",
    "chevron": "https://www.chevron.com",
    "shell": "https://www.shell.com",
    "bp": "https://www.bp.com",
    "conocophillips": "https://www.conocophillips.com",

    # Telecom
    "att": "https://www.att.com",
    "at&t": "https://www.att.com",
    "verizon": "https://www.verizon.com",
    "t-mobile": "https://www.t-mobile.com",
    "comcast": "https://corporate.comcast.com",
    "charter": "https://corporate.charter.com",

    # Consulting
    "mckinsey": "https://www.mckinsey.com",
    "bain": "https://www.bain.com",
    "bcg": "https://www.bcg.com",
    "deloitte": "https://www.deloitte.com",
    "pwc": "https://www.pwc.com",
    "ey": "https://www.ey.com",
    "ernst young": "https://www.ey.com",
    "kpmg": "https://kpmg.com",
    "accenture": "https://www.accenture.com",
    "booz allen": "https://www.boozallen.com",

    # Government/Cities (for municipal discovery)
    "cleveland": "https://www.clevelandohio.gov",
    "city of cleveland": "https://www.clevelandohio.gov",
    "new york city": "https://www.nyc.gov",
    "nyc": "https://www.nyc.gov",
    "los angeles": "https://www.lacity.gov",
    "chicago": "https://www.chicago.gov",
    "houston": "https://www.houstontx.gov",
    "phoenix": "https://www.phoenix.gov",
    "philadelphia": "https://www.phila.gov",
    "san antonio": "https://www.sanantonio.gov",
    "san diego": "https://www.sandiego.gov",
    "dallas": "https://www.dallascityhall.com",
    "san jose": "https://www.sanjoseca.gov",
    "austin": "https://www.austintexas.gov",
    "detroit": "https://detroitmi.gov",
    "seattle": "https://www.seattle.gov",
    "denver": "https://www.denvergov.org",
    "boston": "https://www.boston.gov",
    "atlanta": "https://www.atlantaga.gov",
    "miami": "https://www.miamigov.com",
}

# Corporate domains to try for unknown companies
CORPORATE_DOMAIN_PATTERNS = [
    "{name}.com",
    "www.{name}.com",
    "{name}.io",
    "{name}.co",
    "about.{name}.com",
    "corporate.{name}.com",
]

# Enterprise priority paths for crawling
ENTERPRISE_PRIORITY_PATHS = [
    # Leadership pages
    "/about/leadership",
    "/about/team",
    "/about/management",
    "/about/executives",
    "/company/leadership",
    "/company/team",
    "/company/management",
    "/company/about",
    "/corporate/leadership",
    "/corporate/team",
    "/leadership",
    "/team",
    "/management",
    "/executives",
    "/our-team",
    "/our-leadership",
    "/about-us/leadership",
    "/about-us/team",
    "/who-we-are/leadership",
    "/who-we-are/team",

    # Department/Organization pages
    "/about",
    "/about-us",
    "/company",
    "/corporate",
    "/who-we-are",
    "/our-company",
    "/organization",
    "/departments",
    "/divisions",
    "/business-units",

    # Contact/Directory
    "/contact",
    "/contact-us",
    "/directory",
    "/locations",

    # Careers (often has org structure)
    "/careers",
    "/jobs",
    "/careers/teams",

    # Investor relations (has executives)
    "/investors",
    "/investor-relations",
    "/ir",
]

# Executive title patterns for enterprise
ENTERPRISE_EXECUTIVE_PATTERNS = [
    # C-Suite
    r"chief\s+executive\s+officer|ceo",
    r"chief\s+operating\s+officer|coo",
    r"chief\s+financial\s+officer|cfo",
    r"chief\s+technology\s+officer|cto",
    r"chief\s+information\s+officer|cio",
    r"chief\s+marketing\s+officer|cmo",
    r"chief\s+product\s+officer|cpo",
    r"chief\s+people\s+officer|chro",
    r"chief\s+human\s+resources\s+officer",
    r"chief\s+legal\s+officer|clo|general\s+counsel",
    r"chief\s+revenue\s+officer|cro",
    r"chief\s+strategy\s+officer|cso",
    r"chief\s+data\s+officer|cdo",
    r"chief\s+security\s+officer|ciso",
    r"chief\s+compliance\s+officer|cco",

    # Presidents/VPs
    r"president",
    r"executive\s+vice\s+president|evp",
    r"senior\s+vice\s+president|svp",
    r"vice\s+president|vp",

    # Board
    r"chairman|chairwoman|chair\s+of\s+the\s+board",
    r"board\s+member|director\s+\(board\)",

    # Other executives
    r"managing\s+director",
    r"general\s+manager",
    r"division\s+head",
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


# Intent keywords that modify crawl behavior
INTENT_KEYWORDS = {
    "leadership": {
        "paths": ["/about/leadership", "/leadership", "/about/team", "/team", "/executives", "/management", "/about/executives", "/company/leadership"],
        "focus": "leadership",
    },
    "executives": {
        "paths": ["/executives", "/about/executives", "/leadership", "/about/leadership", "/c-suite", "/management"],
        "focus": "leadership",
    },
    "team": {
        "paths": ["/team", "/our-team", "/about/team", "/people", "/about/people", "/staff"],
        "focus": "leadership",
    },
    "departments": {
        "paths": ["/departments", "/divisions", "/business-units", "/organization", "/about/organization"],
        "focus": "departments",
    },
    "contact": {
        "paths": ["/contact", "/contact-us", "/locations", "/offices", "/directory"],
        "focus": "contact",
    },
    "careers": {
        "paths": ["/careers", "/jobs", "/careers/teams", "/join-us", "/work-with-us"],
        "focus": "careers",
    },
    "investors": {
        "paths": ["/investors", "/investor-relations", "/ir", "/financials", "/annual-report"],
        "focus": "investors",
    },
    "global": {
        "paths": ["/global", "/worldwide", "/international", "/locations/global"],
        "focus": "global",
    },
    "corporate": {
        "paths": ["/corporate", "/about", "/company", "/about-us", "/who-we-are"],
        "focus": "corporate",
    },
}


class OrganizationResolver:
    """Resolves organization names to URLs and provides enterprise crawl patterns."""

    def __init__(self):
        self.known_orgs = KNOWN_ORGANIZATIONS
        self.priority_paths = ENTERPRISE_PRIORITY_PATHS
        self.exec_patterns = ENTERPRISE_EXECUTIVE_PATTERNS
        self.dept_keywords = ENTERPRISE_DEPARTMENT_KEYWORDS

    def resolve(self, input_str: str) -> dict:
        """
        Resolve an input string to organization info.

        Supports intent-based queries like:
        - "IBM leadership" -> IBM + prioritize leadership pages
        - "Microsoft corporate team" -> Microsoft + prioritize team pages
        - "CNN executives global" -> CNN + prioritize executive/global pages

        Args:
            input_str: Company name, abbreviation, URL, or intent query

        Returns:
            Dict with:
                - url: The resolved URL
                - name: Organization name
                - type: "enterprise", "municipal", "education", etc.
                - is_url: Whether input was already a URL
                - confidence: "known", "inferred", "guessed"
                - intent: Detected intent (leadership, departments, etc.)
                - priority_paths: Paths to prioritize based on intent
        """
        input_str = input_str.strip()

        # Parse intent keywords from query
        org_name, intents = self._parse_intent(input_str)

        # Check if it's already a URL
        if self._is_url(org_name):
            result = self._resolve_from_url(org_name)
        else:
            # Try known organizations
            result = self._try_known_org(org_name)
            if not result:
                # Try to infer URL from name
                result = self._infer_url(org_name)

        # Add intent-based priority paths
        if intents:
            result["intent"] = intents
            result["priority_paths"] = self._get_intent_paths(intents)
        else:
            result["intent"] = []
            result["priority_paths"] = []

        return result

    def _parse_intent(self, query: str) -> tuple[str, list[str]]:
        """Parse intent keywords from query.

        Returns:
            Tuple of (org_name, list of detected intents)
        """
        words = query.lower().split()
        intents = []
        org_words = []

        for word in words:
            # Check if word is an intent keyword
            if word in INTENT_KEYWORDS:
                intents.append(word)
            else:
                org_words.append(word)

        # Reconstruct org name from non-intent words
        org_name = " ".join(org_words).strip()

        return org_name, intents

    def _get_intent_paths(self, intents: list[str]) -> list[str]:
        """Get prioritized paths based on detected intents."""
        paths = []
        seen = set()

        for intent in intents:
            if intent in INTENT_KEYWORDS:
                for path in INTENT_KEYWORDS[intent]["paths"]:
                    if path not in seen:
                        paths.append(path)
                        seen.add(path)

        return paths

    def _is_url(self, s: str) -> bool:
        """Check if string is a URL."""
        # Has protocol
        if s.startswith(("http://", "https://")):
            return True
        # Looks like a domain
        if re.match(r'^[\w-]+\.(com|org|gov|edu|net|io|co|us|uk)(/.*)?$', s, re.IGNORECASE):
            return True
        return False

    def _resolve_from_url(self, url: str) -> dict:
        """Resolve from an existing URL."""
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # Infer name from domain
        name_part = domain.split(".")[0]
        name = name_part.replace("-", " ").title()

        # Infer type from domain
        org_type = "enterprise"
        if ".gov" in domain:
            org_type = "municipal"
        elif ".edu" in domain:
            org_type = "education"
        elif ".org" in domain:
            org_type = "nonprofit"

        return {
            "url": url,
            "name": name,
            "type": org_type,
            "is_url": True,
            "confidence": "provided",
        }

    def _try_known_org(self, name: str) -> Optional[dict]:
        """Try to find in known organizations."""
        name_lower = name.lower().strip()

        # Direct match
        if name_lower in self.known_orgs:
            url = self.known_orgs[name_lower]
            return {
                "url": url,
                "name": name.title(),
                "type": self._infer_type_from_url(url),
                "is_url": False,
                "confidence": "known",
            }

        # Partial match (e.g., "IBM Corporation" → "ibm")
        for known_name, url in self.known_orgs.items():
            if known_name in name_lower or name_lower in known_name:
                return {
                    "url": url,
                    "name": name.title(),
                    "type": self._infer_type_from_url(url),
                    "is_url": False,
                    "confidence": "known",
                }

        return None

    def _infer_url(self, name: str) -> dict:
        """Infer URL from organization name."""
        # Clean up name for URL
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
        clean_name = clean_name.replace(" ", "")

        # Try common patterns
        url = f"https://www.{clean_name}.com"

        return {
            "url": url,
            "name": name.title(),
            "type": "enterprise",
            "is_url": False,
            "confidence": "guessed",
            "alternate_urls": [
                f"https://{clean_name}.com",
                f"https://www.{clean_name}.io",
                f"https://about.{clean_name}.com",
                f"https://corporate.{clean_name}.com",
            ]
        }

    def _infer_type_from_url(self, url: str) -> str:
        """Infer organization type from URL."""
        if ".gov" in url:
            return "municipal"
        elif ".edu" in url:
            return "education"
        elif ".org" in url:
            return "nonprofit"
        elif "corporate." in url or "about." in url or any(c in url for c in ["investor", "ir."]):
            return "enterprise"
        return "enterprise"

    def get_priority_paths(self, org_type: str = "enterprise") -> list[str]:
        """Get priority crawl paths for organization type."""
        if org_type == "municipal":
            return [
                "/government", "/departments", "/mayor", "/city-hall",
                "/about", "/leadership", "/officials", "/administration",
                "/services", "/directory", "/contact",
            ]
        elif org_type == "education":
            return [
                "/about", "/about/leadership", "/about/administration",
                "/president", "/provost", "/administration",
                "/academics", "/departments", "/schools", "/colleges",
                "/directory", "/contact",
            ]
        else:  # enterprise
            return self.priority_paths

    def get_executive_patterns(self, org_type: str = "enterprise") -> list[str]:
        """Get executive title patterns for organization type."""
        if org_type == "municipal":
            return [
                r"mayor", r"city\s*manager", r"chief\s*of\s*staff",
                r"director", r"commissioner", r"superintendent",
            ]
        else:
            return self.exec_patterns

    def get_department_keywords(self, org_type: str = "enterprise") -> dict:
        """Get department keywords for organization type."""
        if org_type == "municipal":
            from .discovery import DEPARTMENT_KEYWORDS
            return DEPARTMENT_KEYWORDS
        else:
            return self.dept_keywords


# Singleton instance
_resolver: Optional[OrganizationResolver] = None


def get_resolver() -> OrganizationResolver:
    """Get the organization resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = OrganizationResolver()
    return _resolver


def resolve_organization(input_str: str) -> dict:
    """Resolve an organization name or URL to full organization info."""
    return get_resolver().resolve(input_str)


async def verify_url(url: str) -> bool:
    """Verify that a URL is reachable."""
    if not HAS_HTTP:
        return True  # Assume valid if we can't check

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url, follow_redirects=True)
            return response.status_code < 400
    except Exception:
        return False
