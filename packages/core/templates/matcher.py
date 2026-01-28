"""Template matching engine with confidence scoring.

Matches organizational structures and requirements to the most
appropriate agent templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from packages.core.templates.types import (
    AgentTemplate,
    TemplateDomain,
    TemplateComplexity,
    HITLRequirement,
    MatchResult,
    MatchRequest,
)
from packages.core.templates.registry import TemplateRegistry, get_template_registry


# Domain keyword mappings for fuzzy matching
DOMAIN_KEYWORDS: dict[TemplateDomain, list[str]] = {
    TemplateDomain.EXECUTIVE: [
        "executive", "mayor", "ceo", "director", "chief", "president",
        "administrator", "manager", "leadership", "strategy", "office of"
    ],
    TemplateDomain.LEGISLATIVE: [
        "council", "legislative", "legislator", "ordinance", "law",
        "policy", "chamber", "assembly", "representative", "delegate"
    ],
    TemplateDomain.JUDICIAL: [
        "court", "judge", "judicial", "magistrate", "clerk of courts",
        "prosecutor", "attorney", "legal"
    ],
    TemplateDomain.PUBLIC_SAFETY: [
        "police", "fire", "ems", "safety", "emergency", "911",
        "dispatch", "sheriff", "corrections", "enforcement"
    ],
    TemplateDomain.PUBLIC_HEALTH: [
        "health", "medical", "clinic", "epidemic", "disease",
        "wellness", "mental health", "public health", "nursing"
    ],
    TemplateDomain.PUBLIC_WORKS: [
        "public works", "streets", "roads", "sanitation", "garbage",
        "maintenance", "fleet", "engineering", "infrastructure"
    ],
    TemplateDomain.UTILITIES: [
        "utility", "utilities", "water", "sewer", "electric",
        "power", "gas", "wastewater", "stormwater"
    ],
    TemplateDomain.FINANCE: [
        "finance", "budget", "treasury", "accounting", "audit",
        "procurement", "purchasing", "fiscal", "revenue", "tax"
    ],
    TemplateDomain.HR: [
        "human resources", "hr", "personnel", "employment", "hiring",
        "benefits", "payroll", "recruitment", "training"
    ],
    TemplateDomain.IT: [
        "it", "technology", "information technology", "systems",
        "computer", "software", "network", "helpdesk", "tech support"
    ],
    TemplateDomain.LEGAL: [
        "legal", "law", "attorney", "counsel", "compliance",
        "regulatory", "contracts", "risk", "liability"
    ],
    TemplateDomain.PARKS_RECREATION: [
        "parks", "recreation", "community center", "pool", "sports",
        "playground", "trails", "facilities", "programs"
    ],
    TemplateDomain.COMMUNITY_DEVELOPMENT: [
        "community development", "neighborhood", "revitalization",
        "grants", "community", "development", "cdbg"
    ],
    TemplateDomain.HOUSING: [
        "housing", "building", "permits", "inspection", "code",
        "zoning", "construction", "property", "land use"
    ],
    TemplateDomain.SOCIAL_SERVICES: [
        "social services", "welfare", "assistance", "aging",
        "seniors", "youth", "family", "veterans", "disabilities"
    ],
    TemplateDomain.COMMUNICATIONS: [
        "communications", "media", "press", "public relations",
        "social media", "marketing", "outreach", "spokesperson"
    ],
    TemplateDomain.PUBLIC_AFFAIRS: [
        "public affairs", "government relations", "intergovernmental",
        "lobbying", "advocacy", "stakeholder"
    ],
    TemplateDomain.PLANNING: [
        "planning", "zoning", "land use", "urban", "development",
        "comprehensive plan", "master plan", "gis"
    ],
    TemplateDomain.ECONOMIC_DEVELOPMENT: [
        "economic development", "business", "jobs", "workforce",
        "incentives", "investment", "commerce", "industry"
    ],
    TemplateDomain.ROUTER: [
        "router", "concierge", "hub", "central", "gateway",
        "orchestrator", "dispatcher", "entry point"
    ],
    TemplateDomain.STRATEGY: [
        "strategy", "strategic", "innovation", "transformation",
        "digital", "analytics", "intelligence", "planning"
    ],
    TemplateDomain.COMPLIANCE: [
        "compliance", "ethics", "integrity", "inspector general",
        "audit", "oversight", "regulation"
    ],
}


# Capability synonyms for matching
CAPABILITY_SYNONYMS: dict[str, list[str]] = {
    "data analysis": ["analytics", "reporting", "metrics", "dashboards", "insights"],
    "policy research": ["policy analysis", "research", "legislative research"],
    "customer service": ["constituent services", "citizen services", "public service"],
    "grant management": ["grants", "grant writing", "funding"],
    "budget": ["budgeting", "fiscal", "financial planning"],
    "compliance": ["regulatory", "standards", "audit", "oversight"],
    "communications": ["messaging", "media", "public relations", "outreach"],
    "training": ["education", "learning", "curriculum", "onboarding"],
    "project management": ["projects", "planning", "coordination"],
}


@dataclass
class MatchScores:
    """Breakdown of matching scores."""

    domain_score: float = 0.0
    capability_score: float = 0.0
    complexity_score: float = 0.0
    hitl_score: float = 0.0
    tag_score: float = 0.0
    context_score: float = 0.0

    @property
    def total(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "domain": 0.30,
            "capability": 0.25,
            "complexity": 0.15,
            "hitl": 0.10,
            "tag": 0.10,
            "context": 0.10,
        }
        return (
            self.domain_score * weights["domain"] +
            self.capability_score * weights["capability"] +
            self.complexity_score * weights["complexity"] +
            self.hitl_score * weights["hitl"] +
            self.tag_score * weights["tag"] +
            self.context_score * weights["context"]
        )


class TemplateMatcher:
    """Matches organizational requirements to agent templates.

    Uses multi-factor scoring to find the best template match:
    - Domain alignment (30%)
    - Capability coverage (25%)
    - Complexity fit (15%)
    - HITL preference (10%)
    - Tag relevance (10%)
    - Context signals (10%)
    """

    def __init__(self, registry: TemplateRegistry | None = None):
        self._registry = registry or get_template_registry()

    def match(self, request: MatchRequest) -> list[MatchResult]:
        """Find best matching templates for a request.

        Args:
            request: Match request with requirements

        Returns:
            List of MatchResults sorted by confidence (highest first)
        """
        templates = self._registry.get_all()
        results: list[tuple[MatchResult, MatchScores]] = []

        # Pre-process request text for matching
        search_text = self._build_search_text(request)

        for template in templates:
            scores = self._score_template(template, request, search_text)
            result = self._build_result(template, request, scores)
            results.append((result, scores))

        # Sort by confidence
        results.sort(key=lambda x: x[0].confidence, reverse=True)

        # Return top N results
        return [r for r, _ in results[:request.max_results]]

    def match_by_text(
        self,
        text: str,
        max_results: int = 5,
    ) -> list[MatchResult]:
        """Match templates based on free-form text description.

        Args:
            text: Description of the role/department
            max_results: Maximum results to return

        Returns:
            Matching templates with confidence scores
        """
        # Extract components from text
        request = self._parse_text_to_request(text, max_results)
        return self.match(request)

    def recommend_for_organization(
        self,
        org_name: str,
        departments: list[dict[str, Any]],
    ) -> dict[str, list[MatchResult]]:
        """Recommend templates for an entire organization.

        Args:
            org_name: Organization name
            departments: List of department info dicts

        Returns:
            Dict mapping department names to recommended templates
        """
        recommendations: dict[str, list[MatchResult]] = {}

        for dept in departments:
            request = MatchRequest(
                organization_name=org_name,
                department_name=dept.get("name", "Unknown"),
                domain_hint=dept.get("domain"),
                role_title=dept.get("director_title"),
                role_description=dept.get("description"),
                requested_capabilities=dept.get("capabilities", []),
            )

            matches = self.match(request)
            recommendations[dept.get("name", "Unknown")] = matches

        return recommendations

    def _build_search_text(self, request: MatchRequest) -> str:
        """Build combined search text from request."""
        parts = [
            request.organization_name,
            request.department_name,
            request.domain_hint or "",
            request.role_title or "",
            request.role_description or "",
            " ".join(request.requested_capabilities),
        ]
        return " ".join(parts).lower()

    def _score_template(
        self,
        template: AgentTemplate,
        request: MatchRequest,
        search_text: str,
    ) -> MatchScores:
        """Score a template against a request."""
        scores = MatchScores()

        # Domain scoring
        scores.domain_score = self._score_domain(template, request, search_text)

        # Capability scoring
        scores.capability_score = self._score_capabilities(template, request)

        # Complexity scoring
        scores.complexity_score = self._score_complexity(template, request)

        # HITL scoring
        scores.hitl_score = self._score_hitl(template, request)

        # Tag scoring
        scores.tag_score = self._score_tags(template, search_text)

        # Context scoring
        scores.context_score = self._score_context(template, request)

        return scores

    def _score_domain(
        self,
        template: AgentTemplate,
        request: MatchRequest,
        search_text: str,
    ) -> float:
        """Score domain match."""
        # Direct domain hint match
        if request.domain_hint:
            hint_lower = request.domain_hint.lower()
            if hint_lower == template.domain.value:
                return 1.0
            # Partial match
            if hint_lower in template.domain.value or template.domain.value in hint_lower:
                return 0.8

        # Keyword-based domain detection
        keywords = DOMAIN_KEYWORDS.get(template.domain, [])
        if not keywords:
            return 0.3  # Unknown domain, neutral score

        matched = sum(1 for kw in keywords if kw in search_text)
        if matched == 0:
            return 0.0

        # More matches = higher confidence
        max_possible = min(len(keywords), 5)  # Cap at 5 for normalization
        return min(1.0, matched / max_possible * 1.2)

    def _score_capabilities(
        self,
        template: AgentTemplate,
        request: MatchRequest,
    ) -> float:
        """Score capability coverage."""
        if not request.requested_capabilities:
            return 0.5  # Neutral if no specific capabilities requested

        template_caps = set(c.lower() for c in template.capability_names)

        # Add capability descriptions if available
        for cap in template.capabilities:
            template_caps.add(cap.name.lower())
            if cap.description:
                template_caps.add(cap.description.lower())

        matched = 0
        for req_cap in request.requested_capabilities:
            req_lower = req_cap.lower()

            # Direct match
            if req_lower in template_caps:
                matched += 1
                continue

            # Check if any template cap contains the request
            if any(req_lower in tc for tc in template_caps):
                matched += 0.8
                continue

            # Check synonyms
            for base, synonyms in CAPABILITY_SYNONYMS.items():
                if req_lower in [base] + synonyms:
                    if any(s in " ".join(template_caps) for s in [base] + synonyms):
                        matched += 0.6
                        break

        return min(1.0, matched / len(request.requested_capabilities))

    def _score_complexity(
        self,
        template: AgentTemplate,
        request: MatchRequest,
    ) -> float:
        """Score complexity fit."""
        if not request.complexity_preference:
            return 0.5  # Neutral

        if template.complexity == request.complexity_preference:
            return 1.0

        # Adjacent complexity levels
        complexity_order = [
            TemplateComplexity.BASIC,
            TemplateComplexity.STANDARD,
            TemplateComplexity.ADVANCED,
            TemplateComplexity.ENTERPRISE,
        ]

        try:
            template_idx = complexity_order.index(template.complexity)
            pref_idx = complexity_order.index(request.complexity_preference)
            diff = abs(template_idx - pref_idx)

            if diff == 1:
                return 0.7
            elif diff == 2:
                return 0.4
            else:
                return 0.2
        except ValueError:
            return 0.3

    def _score_hitl(
        self,
        template: AgentTemplate,
        request: MatchRequest,
    ) -> float:
        """Score HITL preference match."""
        if not request.hitl_preference:
            return 0.5  # Neutral

        if template.default_hitl_mode == request.hitl_preference:
            return 1.0

        # Partial matches
        hitl_order = [HITLRequirement.INFORM, HITLRequirement.DRAFT, HITLRequirement.ESCALATE]
        try:
            template_idx = hitl_order.index(template.default_hitl_mode)
            pref_idx = hitl_order.index(request.hitl_preference)

            # More restrictive is OK (template is stricter than requested)
            if template_idx > pref_idx:
                return 0.7
            # Less restrictive may be concerning
            else:
                return 0.4
        except ValueError:
            return 0.3

    def _score_tags(
        self,
        template: AgentTemplate,
        search_text: str,
    ) -> float:
        """Score tag relevance."""
        if not template.tags:
            return 0.3

        matched = sum(1 for tag in template.tags if tag.lower() in search_text)

        if matched == 0:
            return 0.0

        return min(1.0, matched / len(template.tags) * 2)

    def _score_context(
        self,
        template: AgentTemplate,
        request: MatchRequest,
    ) -> float:
        """Score based on organizational context."""
        score = 0.5  # Start neutral

        # Existing agents context
        if request.existing_agents:
            # Prefer router if no router exists
            if template.domain == TemplateDomain.ROUTER:
                if "router" not in [a.lower() for a in request.existing_agents]:
                    score += 0.3
                else:
                    score -= 0.3  # Already have a router

        # Required integrations
        if request.required_integrations:
            # Check if template suggests compatible data sources
            compatible = sum(
                1 for src in template.suggested_data_sources
                if any(req.lower() in src.lower() for req in request.required_integrations)
            )
            if compatible:
                score += 0.2

        return min(1.0, max(0.0, score))

    def _build_result(
        self,
        template: AgentTemplate,
        request: MatchRequest,
        scores: MatchScores,
    ) -> MatchResult:
        """Build a MatchResult from scores."""
        confidence = scores.total
        match_reasons = []
        missing_requirements = []
        customization_suggestions = []

        # Determine match reasons
        if scores.domain_score > 0.7:
            match_reasons.append(f"Strong domain match ({template.domain.value})")
        elif scores.domain_score > 0.4:
            match_reasons.append(f"Partial domain match ({template.domain.value})")

        if scores.capability_score > 0.7:
            match_reasons.append("High capability coverage")
        elif scores.capability_score > 0.4:
            match_reasons.append("Partial capability coverage")

        if scores.complexity_score > 0.7:
            match_reasons.append("Complexity level matches requirements")

        if scores.tag_score > 0.5:
            match_reasons.append("Relevant tags found")

        # Identify missing requirements
        if request.requested_capabilities:
            template_caps_lower = set(c.lower() for c in template.capability_names)
            for cap in request.requested_capabilities:
                if cap.lower() not in template_caps_lower:
                    # Check if partially covered
                    if not any(cap.lower() in tc for tc in template_caps_lower):
                        missing_requirements.append(f"Capability: {cap}")

        if request.hitl_preference and template.default_hitl_mode != request.hitl_preference:
            customization_suggestions.append(
                f"Adjust HITL mode from {template.default_hitl_mode.value} to {request.hitl_preference.value}"
            )

        # Suggest customizations
        if scores.domain_score < 0.5:
            customization_suggestions.append("Review and customize domain-specific guardrails")

        if missing_requirements:
            customization_suggestions.append("Add custom capabilities for missing requirements")

        return MatchResult(
            template=template,
            confidence=confidence,
            match_reasons=match_reasons,
            missing_requirements=missing_requirements,
            customization_suggestions=customization_suggestions,
            domain_match=scores.domain_score > 0.5,
            capability_coverage=scores.capability_score,
        )

    def _parse_text_to_request(
        self,
        text: str,
        max_results: int,
    ) -> MatchRequest:
        """Parse free-form text into a MatchRequest."""
        text_lower = text.lower()

        # Try to extract department name
        dept_patterns = [
            r"department of (\w+(?:\s+\w+)?)",
            r"(\w+(?:\s+\w+)?)\s+department",
            r"(\w+(?:\s+\w+)?)\s+office",
            r"office of (\w+(?:\s+\w+)?)",
        ]

        department_name = "Unknown Department"
        for pattern in dept_patterns:
            match = re.search(pattern, text_lower)
            if match:
                department_name = match.group(1).title()
                break

        # Try to detect domain
        detected_domain = None
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_domain = domain.value
                break

        # Extract potential capabilities from text
        capability_patterns = [
            r"(?:need|require|want|should)\s+(?:to\s+)?(\w+(?:\s+\w+)?)",
            r"(?:capabilities?|features?|functions?)\s*:\s*([^.]+)",
        ]

        capabilities = []
        for pattern in capability_patterns:
            matches = re.findall(pattern, text_lower)
            capabilities.extend(matches)

        return MatchRequest(
            organization_name="Organization",
            department_name=department_name,
            domain_hint=detected_domain,
            role_description=text,
            requested_capabilities=capabilities[:10],  # Limit
            max_results=max_results,
        )


def get_template_matcher(registry: TemplateRegistry | None = None) -> TemplateMatcher:
    """Get a template matcher instance."""
    return TemplateMatcher(registry)
