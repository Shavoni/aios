"""Intent classification and risk detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from re import Pattern

from packages.core.schemas.models import Intent, RiskSignals


@dataclass
class IntentPattern:
    """Pattern for intent classification."""

    domain: str
    task: str
    audience: str = "internal"
    impact: str = "low"
    patterns: list[Pattern[str]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class RiskPattern:
    """Pattern for risk detection."""

    signal: str
    patterns: list[Pattern[str]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# Default intent patterns (extended for Cleveland municipal agents)
DEFAULT_INTENT_PATTERNS: list[IntentPattern] = [
    # Public Health Department
    IntentPattern(
        domain="PublicHealth",
        task="health_guidance",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"health\s+(department|services?|program)", re.IGNORECASE),
            re.compile(r"public\s+health", re.IGNORECASE),
            re.compile(r"(cdph|clinic|medical)", re.IGNORECASE),
            re.compile(r"(disease|outbreak|vaccine|vaccination)", re.IGNORECASE),
            re.compile(r"(opioid|narcan|overdose)", re.IGNORECASE),
            re.compile(r"(lead\s+poisoning|lead\s+testing)", re.IGNORECASE),
        ],
        keywords=["health", "clinic", "medical", "disease", "vaccine", "cdph", "opioid",
                  "narcan", "lead", "immunization", "wic", "nutrition"],
    ),
    # HR Department
    IntentPattern(
        domain="HR",
        task="hr_guidance",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"(human\s+resources?|hr\s+)", re.IGNORECASE),
            re.compile(r"hr\s+(assist|assistance|help|question|support)", re.IGNORECASE),
            re.compile(r"(need|want|looking\s+for)\s+.{0,10}hr", re.IGNORECASE),
            re.compile(r"employee\s+.{0,20}(info|information|lookup|look\s*up|benefits?)", re.IGNORECASE),
            re.compile(r"(hiring|recruitment|job\s+posting)", re.IGNORECASE),
            re.compile(r"(leave|pto|vacation|sick\s+day)", re.IGNORECASE),
            re.compile(r"(termination|discipline|grievance)", re.IGNORECASE),
            re.compile(r"(benefits?|insurance|401k|retirement)", re.IGNORECASE),
            re.compile(r"(civil\s+service|union|collective\s+bargaining)", re.IGNORECASE),
        ],
        keywords=["employee", "hr", "hiring", "benefits", "leave", "pto", "termination",
                  "policy", "manager", "staff", "union", "grievance", "civil service"],
    ),
    # Finance Department
    IntentPattern(
        domain="Finance",
        task="finance_guidance",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"(financial?|finance\s+department)", re.IGNORECASE),
            re.compile(r"finance\s+(assist|assistance|help|question|support)", re.IGNORECASE),
            re.compile(r"(need|want|looking\s+for)\s+.{0,10}finance", re.IGNORECASE),
            re.compile(r"(budget|appropriation|expenditure)", re.IGNORECASE),
            re.compile(r"(procurement|purchasing|vendor|requisition)", re.IGNORECASE),
            re.compile(r"(invoice|payment|reimbursement)", re.IGNORECASE),
            re.compile(r"(p-card|purchase\s+card|procurement\s+card)", re.IGNORECASE),
            re.compile(r"(audit|compliance|financial\s+report)", re.IGNORECASE),
            re.compile(r"(rfp|bid|contract\s+award)", re.IGNORECASE),
        ],
        keywords=["budget", "procurement", "vendor", "purchasing", "invoice", "payment",
                  "financial", "finance", "audit", "p-card", "requisition", "bid", "rfp"],
    ),
    # Building & Housing Department
    IntentPattern(
        domain="Building",
        task="building_guidance",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"(building\s+(department|code|permit))", re.IGNORECASE),
            re.compile(r"building\s+(assist|assistance|help|question|support)", re.IGNORECASE),
            re.compile(r"(need|want|looking\s+for)\s+.{0,10}(building|permit)", re.IGNORECASE),
            re.compile(r"(housing\s+(code|inspection|violation))", re.IGNORECASE),
            re.compile(r"(permit|inspection|certificate\s+of\s+occupancy)", re.IGNORECASE),
            re.compile(r"(zoning|variance|planning)", re.IGNORECASE),
            re.compile(r"(demolition|renovation|construction)", re.IGNORECASE),
            re.compile(r"(code\s+violation|citation|enforcement)", re.IGNORECASE),
        ],
        keywords=["permit", "inspection", "building", "housing", "zoning", "code",
                  "violation", "demolition", "construction", "occupancy"],
    ),
    # 311 Services
    IntentPattern(
        domain="311",
        task="311_guidance",
        audience="internal",
        impact="low",
        patterns=[
            re.compile(r"311\s*(service|request|call|center)?", re.IGNORECASE),
            re.compile(r"(service\s+request|citizen\s+complaint)", re.IGNORECASE),
            re.compile(r"(pothole|trash|garbage|recycling)", re.IGNORECASE),
            re.compile(r"(street\s+light|traffic\s+signal|sign)", re.IGNORECASE),
            re.compile(r"(noise\s+complaint|animal|parking)", re.IGNORECASE),
            re.compile(r"(water\s+(main|leak)|sewer)", re.IGNORECASE),
            re.compile(r"(abandoned\s+(vehicle|property)|blight)", re.IGNORECASE),
        ],
        keywords=["311", "pothole", "trash", "garbage", "noise", "complaint", "street",
                  "water", "sewer", "parking", "blight", "abandoned"],
    ),
    # Strategy & Leadership
    IntentPattern(
        domain="Strategy",
        task="strategic_guidance",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"(strateg(y|ic)|initiative|pilot)", re.IGNORECASE),
            re.compile(r"(ai\s+(strategy|governance|policy))", re.IGNORECASE),
            re.compile(r"(partnership|collaboration|stakeholder)", re.IGNORECASE),
            re.compile(r"(mayor|council|administration)", re.IGNORECASE),
            re.compile(r"(policy\s+development|program\s+design)", re.IGNORECASE),
        ],
        keywords=["strategy", "initiative", "pilot", "partnership", "stakeholder",
                  "governance", "policy", "program"],
    ),
    # Regional / GCP (Greater Cleveland Partnership)
    IntentPattern(
        domain="Regional",
        task="regional_coordination",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"(regional|gcp|greater\s+cleveland)", re.IGNORECASE),
            re.compile(r"(intergovernmental|cross[-\s]?sector)", re.IGNORECASE),
            re.compile(r"(economic\s+development|workforce)", re.IGNORECASE),
            re.compile(r"(county|cuyahoga|northeast\s+ohio)", re.IGNORECASE),
        ],
        keywords=["regional", "gcp", "intergovernmental", "coordination", "economic",
                  "workforce", "county", "northeast ohio"],
    ),
    # Executive / Mayor's Office
    IntentPattern(
        domain="Executive",
        task="executive_support",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"(mayor|mayor'?s?\s+office)", re.IGNORECASE),
            re.compile(r"(executive|chief\s+of\s+staff)", re.IGNORECASE),
            re.compile(r"(bibb|justin\s+bibb)", re.IGNORECASE),
            re.compile(r"(command\s+center|executive\s+decision)", re.IGNORECASE),
            re.compile(r"(cabinet|administration\s+priorities?)", re.IGNORECASE),
        ],
        keywords=["mayor", "executive", "bibb", "cabinet", "administration",
                  "chief of staff", "command center", "priority"],
    ),
    # Legislative / City Council
    IntentPattern(
        domain="Legislative",
        task="legislative_support",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"(city\s+council|council\s+president)", re.IGNORECASE),
            re.compile(r"(legislative|legislation|ordinance)", re.IGNORECASE),
            re.compile(r"(blaine\s+griffin|griffin)", re.IGNORECASE),
            re.compile(r"(ward\s+\d+|constituent)", re.IGNORECASE),
            re.compile(r"(robert'?s?\s+rules?|parliamentary)", re.IGNORECASE),
        ],
        keywords=["council", "legislative", "ordinance", "ward", "constituent",
                  "griffin", "legislation", "committee", "resolution"],
    ),
    # Utilities
    IntentPattern(
        domain="Utilities",
        task="utilities_support",
        audience="internal",
        impact="medium",
        patterns=[
            re.compile(r"(public\s+utilities?|cleveland\s+water)", re.IGNORECASE),
            re.compile(r"(cleveland\s+public\s+power|cpp)", re.IGNORECASE),
            re.compile(r"(water\s+pollution|sewer|wastewater)", re.IGNORECASE),
            re.compile(r"(water\s+service|power\s+outage|electric)", re.IGNORECASE),
            re.compile(r"(utility\s+bill|rate|meter)", re.IGNORECASE),
        ],
        keywords=["utilities", "water", "power", "electric", "sewer", "wastewater",
                  "meter", "outage", "cpp", "cleveland water"],
    ),
    # Parks & Recreation
    IntentPattern(
        domain="ParksRec",
        task="parks_support",
        audience="internal",
        impact="low",
        patterns=[
            re.compile(r"(parks?\s+(&|and)?\s*rec(reation)?)", re.IGNORECASE),
            re.compile(r"(recreation\s+center|community\s+center)", re.IGNORECASE),
            re.compile(r"(park\s+(facility|reservation|permit))", re.IGNORECASE),
            re.compile(r"(pool|playground|athletic\s+field)", re.IGNORECASE),
            re.compile(r"(youth\s+program|summer\s+camp)", re.IGNORECASE),
        ],
        keywords=["parks", "recreation", "pool", "playground", "community center",
                  "athletic", "youth program", "camp", "facility"],
    ),
    # Public Safety
    IntentPattern(
        domain="PublicSafety",
        task="public_safety_support",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"(public\s+safety|police|fire\s+department)", re.IGNORECASE),
            re.compile(r"(ems|emergency\s+services?)", re.IGNORECASE),
            re.compile(r"(crime|criminal|compstat)", re.IGNORECASE),
            re.compile(r"(doj|consent\s+decree|constitutional\s+policing)", re.IGNORECASE),
            re.compile(r"(chief\s+of\s+police|division\s+of\s+police)", re.IGNORECASE),
        ],
        keywords=["police", "fire", "ems", "safety", "crime", "emergency",
                  "consent decree", "doj", "compstat", "dispatch"],
    ),
    # Communications (public-facing)
    IntentPattern(
        domain="Comms",
        task="draft_statement",
        audience="public",
        impact="high",
        patterns=[
            re.compile(r"public\s+statement", re.IGNORECASE),
            re.compile(r"press\s+release", re.IGNORECASE),
            re.compile(r"public\s+announcement", re.IGNORECASE),
            re.compile(r"(media\s+response|news\s+release)", re.IGNORECASE),
        ],
        keywords=["public", "statement", "announcement", "press", "media"],
    ),
    # Legal
    IntentPattern(
        domain="Legal",
        task="contract_review",
        audience="internal",
        impact="high",
        patterns=[
            re.compile(r"review\s+.{0,20}contract", re.IGNORECASE),
            re.compile(r"contract\s+.{0,20}review", re.IGNORECASE),
            re.compile(r"(nda|agreement|legal\s+question)", re.IGNORECASE),
            re.compile(r"(law\s+department|city\s+attorney)", re.IGNORECASE),
        ],
        keywords=["contract", "review", "legal", "nda", "agreement", "attorney"],
    ),
    # General fallback - must be last
    IntentPattern(
        domain="General",
        task="answer_question",
        audience="internal",
        impact="low",
        patterns=[
            re.compile(r"what\s+is", re.IGNORECASE),
            re.compile(r"how\s+(do|does|can)", re.IGNORECASE),
            re.compile(r"(help|assist|question)", re.IGNORECASE),
        ],
        keywords=["what", "how", "why", "when", "where", "help"],
    ),
]


# Domain to Agent ID mapping for Cleveland
DOMAIN_TO_AGENT_MAP: dict[str, str] = {
    "PublicHealth": "public-health",
    "HR": "hr",
    "Finance": "finance",
    "Building": "building-housing",
    "311": "311",
    "Strategy": "urban-ai",
    "Regional": "gcp",
    "General": "concierge",
    "Comms": "communications",
    "Legal": "finance",   # Route to finance for legal/contracts
    "Executive": "mayors-command-center",
    "Legislative": "council-president",
    "Utilities": "public-utilities",
    "PublicSafety": "public-safety",
    "ParksRec": "parks-recreation",
}


# Default risk patterns
DEFAULT_RISK_PATTERNS: list[RiskPattern] = [
    RiskPattern(
        signal="PII",
        patterns=[
            re.compile(r"social\s+security", re.IGNORECASE),
            re.compile(r"(home\s+)?address", re.IGNORECASE),
            re.compile(r"salary", re.IGNORECASE),
            re.compile(r"personal\s+.{0,10}(info|information|data)", re.IGNORECASE),
        ],
        keywords=["ssn", "social security", "address", "salary", "personal"],
    ),
    RiskPattern(
        signal="LEGAL_CONTRACT",
        patterns=[
            re.compile(r"(nda|contract|agreement)", re.IGNORECASE),
            re.compile(r"legal\s+.{0,10}(review|document)", re.IGNORECASE),
        ],
        keywords=["contract", "nda", "agreement", "legal"],
    ),
    RiskPattern(
        signal="PUBLIC_STATEMENT",
        patterns=[
            re.compile(r"public\s+(statement|announcement)", re.IGNORECASE),
            re.compile(r"press\s+release", re.IGNORECASE),
        ],
        keywords=["public statement", "press release", "announcement"],
    ),
    RiskPattern(
        signal="FINANCIAL",
        patterns=[
            re.compile(r"wire\s+transfer", re.IGNORECASE),
            re.compile(r"payment", re.IGNORECASE),
            re.compile(r"invoice", re.IGNORECASE),
        ],
        keywords=["wire transfer", "payment", "invoice", "transaction"],
    ),
]


@dataclass
class RoutingResult:
    """Result of agent routing decision."""

    primary_agent_id: str
    primary_domain: str
    confidence: float
    alternative_agents: list[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_prompt: str | None = None


class IntentClassifier:
    """Classifies user requests into intents."""

    def __init__(self, patterns: list[IntentPattern] | None = None) -> None:
        self.patterns = patterns if patterns is not None else DEFAULT_INTENT_PATTERNS

    def classify_intent(self, text: str) -> Intent:
        """Classify the intent of a text input."""
        if not text or not text.strip():
            return Intent(domain="General", task="unknown", confidence=0.1)

        text_lower = text.lower()
        best_match: IntentPattern | None = None
        best_score = 0.0

        for pattern in self.patterns:
            score = self._score_pattern(text, text_lower, pattern)
            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match and best_score > 0.2:
            confidence = min(0.95, best_score)
            return Intent(
                domain=best_match.domain,
                task=best_match.task,
                audience=best_match.audience,
                impact=best_match.impact,
                confidence=confidence,
            )

        return Intent(domain="General", task="unknown", confidence=0.1)

    def classify_all_intents(self, text: str) -> list[tuple[Intent, float]]:
        """Classify text and return all matching intents with scores.

        Useful for detecting ambiguous queries that may span multiple domains.
        """
        if not text or not text.strip():
            return [(Intent(domain="General", task="unknown", confidence=0.1), 0.1)]

        text_lower = text.lower()
        scored_intents: list[tuple[Intent, float]] = []

        for pattern in self.patterns:
            score = self._score_pattern(text, text_lower, pattern)
            if score > 0.15:  # Lower threshold for secondary intents
                intent = Intent(
                    domain=pattern.domain,
                    task=pattern.task,
                    audience=pattern.audience,
                    impact=pattern.impact,
                    confidence=min(0.95, score),
                )
                scored_intents.append((intent, score))

        # Sort by score descending
        scored_intents.sort(key=lambda x: x[1], reverse=True)

        if not scored_intents:
            return [(Intent(domain="General", task="unknown", confidence=0.1), 0.1)]

        return scored_intents

    def _score_pattern(self, text: str, text_lower: str, pattern: IntentPattern) -> float:
        """Score how well a pattern matches the text."""
        score = 0.0

        # Check regex patterns (higher weight)
        pattern_matches = 0
        for regex in pattern.patterns:
            if regex.search(text):
                pattern_matches += 1
                score += 0.35

        # Check keywords (lower weight, with diminishing returns)
        keyword_matches = 0
        for keyword in pattern.keywords:
            if keyword.lower() in text_lower:
                keyword_matches += 1
                # Diminishing returns for multiple keyword matches
                if keyword_matches <= 2:
                    score += 0.15
                elif keyword_matches <= 4:
                    score += 0.08
                else:
                    score += 0.03

        # Bonus for combined regex + keyword match (high confidence)
        if pattern_matches > 0 and keyword_matches > 0:
            score += 0.1

        return min(1.0, score)


class AgentRouter:
    """Routes queries to the appropriate agent based on intent classification."""

    CONFIDENCE_THRESHOLD_HIGH = 0.6
    CONFIDENCE_THRESHOLD_LOW = 0.3

    def __init__(
        self,
        classifier: IntentClassifier | None = None,
        domain_agent_map: dict[str, str] | None = None,
    ) -> None:
        self.classifier = classifier or IntentClassifier()
        self.domain_agent_map = domain_agent_map or DOMAIN_TO_AGENT_MAP

    def route(self, text: str, available_agents: list[str] | None = None) -> RoutingResult:
        """Route a query to the appropriate agent.

        Args:
            text: The user's query text
            available_agents: Optional list of available agent IDs to consider

        Returns:
            RoutingResult with primary agent and alternatives
        """
        intents = self.classifier.classify_all_intents(text)
        primary_intent, primary_score = intents[0]

        # Map domain to agent ID
        primary_agent_id = self.domain_agent_map.get(
            primary_intent.domain, "concierge"
        )

        # Check if agent is available
        if available_agents and primary_agent_id not in available_agents:
            primary_agent_id = "concierge"

        # Find alternative agents from secondary intents
        alternative_agents: list[str] = []
        for intent, score in intents[1:4]:  # Up to 3 alternatives
            agent_id = self.domain_agent_map.get(intent.domain)
            if agent_id and agent_id != primary_agent_id:
                if not available_agents or agent_id in available_agents:
                    alternative_agents.append(agent_id)

        # Determine if clarification is needed
        requires_clarification = False
        clarification_prompt = None

        if primary_score < self.CONFIDENCE_THRESHOLD_LOW:
            # Very low confidence - ask for clarification
            requires_clarification = True
            clarification_prompt = self._generate_clarification_prompt(intents[:3])
        elif (
            primary_score < self.CONFIDENCE_THRESHOLD_HIGH
            and len(intents) > 1
            and intents[1][1] > primary_score * 0.8
        ):
            # Close competition between top intents
            requires_clarification = True
            clarification_prompt = self._generate_clarification_prompt(intents[:2])

        return RoutingResult(
            primary_agent_id=primary_agent_id,
            primary_domain=primary_intent.domain,
            confidence=primary_score,
            alternative_agents=alternative_agents,
            requires_clarification=requires_clarification,
            clarification_prompt=clarification_prompt,
        )

    def _generate_clarification_prompt(
        self, intents: list[tuple[Intent, float]]
    ) -> str:
        """Generate a clarification prompt for ambiguous queries."""
        if len(intents) <= 1:
            return "Could you please provide more details about your request?"

        domains = [intent.domain for intent, _ in intents[:3]]
        domain_names = {
            "PublicHealth": "Public Health",
            "HR": "Human Resources",
            "Finance": "Finance/Procurement",
            "Building": "Building & Housing",
            "311": "311 Services",
            "Strategy": "Strategy & Leadership",
            "Regional": "Regional Coordination",
            "Comms": "Communications",
            "Legal": "Legal",
            "General": "General Assistance",
            "Executive": "Mayor's Office",
            "Legislative": "City Council",
            "Utilities": "Public Utilities",
            "ParksRec": "Parks & Recreation",
            "PublicSafety": "Public Safety",
        }

        options = [domain_names.get(d, d) for d in domains]
        return f"I want to make sure I route you to the right place. Is this about: {', '.join(options[:-1])} or {options[-1]}?"

    def get_agent_for_domain(self, domain: str) -> str:
        """Get the agent ID for a given domain."""
        return self.domain_agent_map.get(domain, "concierge")


class RiskDetector:
    """Detects risk signals in user requests."""

    def __init__(self, patterns: list[RiskPattern] | None = None) -> None:
        self.patterns = patterns if patterns is not None else DEFAULT_RISK_PATTERNS

    def detect_risks(self, text: str) -> RiskSignals:
        """Detect risk signals in text."""
        if not text or not text.strip():
            return RiskSignals(signals=[])

        text_lower = text.lower()
        detected: list[str] = []

        for pattern in self.patterns:
            if self._matches_pattern(text, text_lower, pattern):
                detected.append(pattern.signal)

        return RiskSignals(signals=detected)

    def _matches_pattern(self, text: str, text_lower: str, pattern: RiskPattern) -> bool:
        """Check if pattern matches text."""
        # Check regex patterns
        for regex in pattern.patterns:
            if regex.search(text):
                return True

        # Check keywords
        return any(keyword.lower() in text_lower for keyword in pattern.keywords)
