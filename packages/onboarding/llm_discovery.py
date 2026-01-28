"""LLM-Enhanced Discovery Engine for intelligent organizational structure extraction.

Enhances the base DiscoveryEngine with LLM capabilities for:
- More accurate entity extraction
- Intelligent department classification
- Context-aware template matching
- Relationship inference
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from packages.onboarding.discovery import (
    DiscoveryEngine,
    DiscoveryResult,
    DiscoveryStatus,
    Department,
    Executive,
    ContactInfo,
    DataPortal,
    GovernanceDoc,
    Municipality,
    DEPARTMENT_KEYWORDS,
)


@dataclass
class LLMExtractionResult:
    """Result from LLM extraction."""

    success: bool
    data: dict[str, Any]
    confidence: float
    model_used: str
    tokens_used: int = 0
    extraction_type: str = ""
    raw_response: str = ""


@dataclass
class EnhancedDepartment(Department):
    """Department with LLM-enhanced metadata."""

    capabilities_detected: list[str] = field(default_factory=list)
    regulations_mentioned: list[str] = field(default_factory=list)
    services_offered: list[str] = field(default_factory=list)
    llm_confidence: float = 0.0
    extraction_notes: str = ""


@dataclass
class EnhancedDiscoveryResult(DiscoveryResult):
    """Discovery result with LLM enhancements."""

    llm_enhanced: bool = False
    llm_extractions: list[LLMExtractionResult] = field(default_factory=list)
    organizational_insights: dict[str, Any] = field(default_factory=dict)
    template_recommendations: dict[str, list[dict]] = field(default_factory=dict)


class LLMDiscoveryEngine(DiscoveryEngine):
    """Discovery engine enhanced with LLM capabilities.

    Uses the LLM orchestration layer for intelligent extraction and
    analysis of organizational structures.
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        storage_path: Any | None = None,
        max_pages: int = 100,
        rate_limit_delay: float = 0.5,
        use_llm_for_extraction: bool = True,
        llm_extraction_threshold: int = 3,  # Min departments before LLM kicks in
    ):
        """Initialize LLM-enhanced discovery engine.

        Args:
            llm_router: LLM router for intelligent extraction
            storage_path: Path to store discovery results
            max_pages: Maximum pages to crawl
            rate_limit_delay: Delay between requests
            use_llm_for_extraction: Whether to use LLM for entity extraction
            llm_extraction_threshold: Min regex matches before LLM enhancement
        """
        super().__init__(storage_path, max_pages, rate_limit_delay)
        self._llm_router = llm_router
        self._use_llm = use_llm_for_extraction
        self._llm_threshold = llm_extraction_threshold

    async def enhance_discovery(
        self,
        result: DiscoveryResult,
        pages_content: dict[str, str],
    ) -> EnhancedDiscoveryResult:
        """Enhance a discovery result with LLM analysis.

        Args:
            result: Base discovery result
            pages_content: Raw page content for analysis

        Returns:
            Enhanced discovery result with LLM insights
        """
        enhanced = EnhancedDiscoveryResult(
            id=result.id,
            status=result.status,
            started_at=result.started_at,
            completed_at=result.completed_at,
            source_url=result.source_url,
            municipality=result.municipality,
            executive=result.executive,
            chief_officers=result.chief_officers,
            departments=result.departments,
            data_portals=result.data_portals,
            governance_docs=result.governance_docs,
            pages_crawled=result.pages_crawled,
            error=result.error,
            llm_enhanced=True,
        )

        if not self._llm_router:
            enhanced.llm_enhanced = False
            return enhanced

        # Combine relevant page content for analysis
        combined_content = self._prepare_content_for_llm(pages_content)

        # Run LLM extractions
        extractions = []

        # 1. Extract organizational structure
        org_extraction = await self._extract_organization_structure(combined_content)
        extractions.append(org_extraction)

        if org_extraction.success:
            self._apply_organization_extraction(enhanced, org_extraction)

        # 2. Enhance departments with capabilities
        for dept in enhanced.departments:
            dept_content = self._get_department_content(dept, pages_content)
            if dept_content:
                dept_extraction = await self._extract_department_details(
                    dept, dept_content
                )
                extractions.append(dept_extraction)

                if dept_extraction.success:
                    self._apply_department_extraction(dept, dept_extraction)

        # 3. Generate template recommendations
        template_recs = await self._generate_template_recommendations(enhanced)
        extractions.append(template_recs)

        if template_recs.success:
            enhanced.template_recommendations = template_recs.data.get(
                "recommendations", {}
            )

        # 4. Extract organizational insights
        insights = await self._extract_organizational_insights(
            enhanced, combined_content
        )
        extractions.append(insights)

        if insights.success:
            enhanced.organizational_insights = insights.data

        enhanced.llm_extractions = extractions

        return enhanced

    def _prepare_content_for_llm(
        self,
        pages_content: dict[str, str],
        max_chars: int = 50000,
    ) -> str:
        """Prepare page content for LLM analysis."""
        # Priority ordering: government pages first
        priority_keywords = ["government", "department", "director", "mayor", "leadership"]

        prioritized: list[tuple[str, str, int]] = []

        for url, content in pages_content.items():
            # Calculate priority score
            score = 0
            url_lower = url.lower()
            for kw in priority_keywords:
                if kw in url_lower:
                    score += 10

            # Clean content
            cleaned = self._clean_html_content(content)

            for kw in priority_keywords:
                if kw in cleaned.lower():
                    score += 5

            prioritized.append((url, cleaned, score))

        # Sort by priority
        prioritized.sort(key=lambda x: x[2], reverse=True)

        # Combine up to max_chars
        combined = []
        current_chars = 0

        for url, content, _ in prioritized:
            if current_chars + len(content) > max_chars:
                # Truncate if needed
                remaining = max_chars - current_chars
                if remaining > 500:
                    combined.append(f"=== Page: {url} ===\n{content[:remaining]}\n")
                break

            combined.append(f"=== Page: {url} ===\n{content}\n")
            current_chars += len(content)

        return "\n".join(combined)

    def _clean_html_content(self, html: str) -> str:
        """Extract clean text from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n")]
            text = "\n".join(line for line in lines if line)

            return text
        except Exception:
            return ""

    def _get_department_content(
        self,
        dept: Department,
        pages_content: dict[str, str],
    ) -> str:
        """Get content relevant to a specific department."""
        content_parts = []

        # Get department page if URL is known
        if dept.url and dept.url in pages_content:
            content_parts.append(self._clean_html_content(pages_content[dept.url]))

        # Search for department mentions in other pages
        dept_name_lower = dept.name.lower()

        for url, html in pages_content.items():
            if url == dept.url:
                continue

            text = self._clean_html_content(html)
            if dept_name_lower in text.lower():
                # Extract relevant paragraphs
                paragraphs = text.split("\n\n")
                for para in paragraphs:
                    if dept_name_lower in para.lower():
                        content_parts.append(para)

        return "\n\n".join(content_parts[:5])  # Limit

    async def _extract_organization_structure(
        self,
        content: str,
    ) -> LLMExtractionResult:
        """Use LLM to extract organizational structure."""
        from packages.core.llm.types import Task, TaskType

        task = Task(
            task_id="org-structure-extraction",
            task_type=TaskType.ORG_STRUCTURE_EXTRACTION,
            prompt=f"""Extract the organizational structure from this municipal government website content.

CONTENT:
{content[:30000]}

Extract and return as JSON:
{{
  "municipality": {{
    "name": "City name",
    "state": "State abbreviation or name",
    "form_of_government": "mayor-council, council-manager, etc."
  }},
  "executive": {{
    "name": "Mayor/Manager name",
    "title": "Official title",
    "office": "Office name"
  }},
  "chief_officers": [
    {{"name": "Name", "title": "Title", "office": "Office"}}
  ],
  "departments": [
    {{
      "name": "Department name",
      "director": "Director name if found",
      "director_title": "Director title if found",
      "category": "suggested category: hr, finance, health, safety, etc.",
      "services": ["list of services mentioned"]
    }}
  ],
  "organizational_notes": "Any relevant observations about the structure"
}}

Be thorough but only include information that is explicitly stated or strongly implied.
For uncertain information, use null.""",
            requires_json=True,
            max_tokens=4000,
        )

        try:
            result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )

            if result.success and result.response:
                # Parse JSON from response
                content = result.response.content
                data = self._parse_json_response(content)

                return LLMExtractionResult(
                    success=True,
                    data=data,
                    confidence=0.85,
                    model_used=result.routing.selected_model if result.routing else "unknown",
                    tokens_used=result.response.prompt_tokens + result.response.completion_tokens,
                    extraction_type="organization_structure",
                    raw_response=content,
                )

        except Exception as e:
            return LLMExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                model_used="",
                extraction_type="organization_structure",
                raw_response=str(e),
            )

        return LLMExtractionResult(
            success=False,
            data={},
            confidence=0.0,
            model_used="",
            extraction_type="organization_structure",
        )

    async def _extract_department_details(
        self,
        dept: Department,
        content: str,
    ) -> LLMExtractionResult:
        """Use LLM to extract detailed department information."""
        from packages.core.llm.types import Task, TaskType

        task = Task(
            task_id=f"dept-extraction-{dept.id}",
            task_type=TaskType.ENTITY_EXTRACTION,
            prompt=f"""Extract detailed information about this municipal department.

DEPARTMENT: {dept.name}
CURRENT INFO:
- Director: {dept.director or 'Unknown'}
- Title: {dept.director_title or 'Unknown'}

CONTENT ABOUT THIS DEPARTMENT:
{content[:15000]}

Extract and return as JSON:
{{
  "director_name": "Full name if found",
  "director_title": "Official title if found",
  "description": "Department description/mission",
  "capabilities": ["list of services and capabilities"],
  "regulations": ["any regulations or compliance mentioned"],
  "contact": {{
    "email": "if found",
    "phone": "if found",
    "address": "if found"
  }},
  "suggested_template": "best template match: hr, finance, health, safety, utilities, building, parks, legal, it, communications, 311, or custom",
  "confidence": 0.0-1.0
}}

Only include information that is explicitly stated.""",
            requires_json=True,
            max_tokens=2000,
        )

        try:
            result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )

            if result.success and result.response:
                data = self._parse_json_response(result.response.content)

                return LLMExtractionResult(
                    success=True,
                    data=data,
                    confidence=data.get("confidence", 0.7),
                    model_used=result.routing.selected_model if result.routing else "unknown",
                    tokens_used=result.response.prompt_tokens + result.response.completion_tokens,
                    extraction_type=f"department_details_{dept.id}",
                    raw_response=result.response.content,
                )

        except Exception as e:
            pass

        return LLMExtractionResult(
            success=False,
            data={},
            confidence=0.0,
            model_used="",
            extraction_type=f"department_details_{dept.id}",
        )

    async def _generate_template_recommendations(
        self,
        result: EnhancedDiscoveryResult,
    ) -> LLMExtractionResult:
        """Generate template recommendations for discovered departments."""
        from packages.core.llm.types import Task, TaskType

        # Prepare department summary
        dept_summary = "\n".join([
            f"- {d.name}: {d.description or 'No description'} (suggested: {d.suggested_template or 'unknown'})"
            for d in result.departments
        ])

        task = Task(
            task_id="template-recommendations",
            task_type=TaskType.TEMPLATE_MATCHING,
            prompt=f"""Recommend AI assistant templates for these municipal departments.

MUNICIPALITY: {result.municipality.name if result.municipality else 'Unknown'}

DEPARTMENTS:
{dept_summary}

AVAILABLE TEMPLATES:
- router-concierge: Central routing for all requests
- executive-strategy: Strategic leadership support
- legislative-support: Council/legislative support
- public-utilities: Water, power, sewer services
- communications: Media and public relations
- public-health: Health department support
- building-housing: Permits and code enforcement
- public-safety: Police, fire, EMS support
- parks-recreation: Parks and community programs
- finance-department: Budget and procurement
- human-resources: HR policies and benefits
- information-technology: IT support
- legal-compliance: Legal research support
- community-development: Grants and neighborhood programs
- basic-faq: Simple information bot

For each department, recommend the best template and explain why.

Return as JSON:
{{
  "recommendations": {{
    "department_name": [
      {{
        "template_id": "template-id",
        "confidence": 0.0-1.0,
        "reason": "Why this template fits",
        "customizations_needed": ["list of customizations"]
      }}
    ]
  }},
  "additional_agents_recommended": [
    {{
      "template_id": "template-id",
      "reason": "Why this should be added"
    }}
  ]
}}""",
            requires_json=True,
            max_tokens=4000,
        )

        try:
            llm_result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )

            if llm_result.success and llm_result.response:
                data = self._parse_json_response(llm_result.response.content)

                return LLMExtractionResult(
                    success=True,
                    data=data,
                    confidence=0.8,
                    model_used=llm_result.routing.selected_model if llm_result.routing else "unknown",
                    tokens_used=llm_result.response.prompt_tokens + llm_result.response.completion_tokens,
                    extraction_type="template_recommendations",
                    raw_response=llm_result.response.content,
                )

        except Exception:
            pass

        return LLMExtractionResult(
            success=False,
            data={},
            confidence=0.0,
            model_used="",
            extraction_type="template_recommendations",
        )

    async def _extract_organizational_insights(
        self,
        result: EnhancedDiscoveryResult,
        content: str,
    ) -> LLMExtractionResult:
        """Extract high-level organizational insights."""
        from packages.core.llm.types import Task, TaskType

        task = Task(
            task_id="org-insights",
            task_type=TaskType.CONTENT_GENERATION,
            prompt=f"""Analyze this municipal organization and provide insights for AI deployment.

MUNICIPALITY: {result.municipality.name if result.municipality else 'Unknown'}
EXECUTIVE: {result.executive.name if result.executive else 'Unknown'}
DEPARTMENTS: {len(result.departments)}
DATA PORTALS: {len(result.data_portals)}

Provide strategic insights:

{{
  "governance_structure": "Description of the governance structure",
  "key_priorities": ["List of apparent priorities based on content"],
  "digital_maturity": "low/medium/high - assessment of digital presence",
  "data_availability": "low/medium/high - availability of open data",
  "ai_readiness_score": 1-10,
  "ai_readiness_factors": ["Factors affecting AI readiness"],
  "recommended_pilot_departments": [
    {{
      "department": "Department name",
      "reason": "Why start here",
      "expected_impact": "Expected impact"
    }}
  ],
  "potential_challenges": ["List of potential challenges"],
  "quick_wins": ["Easy wins for initial deployment"]
}}""",
            requires_json=True,
            max_tokens=3000,
        )

        try:
            llm_result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )

            if llm_result.success and llm_result.response:
                data = self._parse_json_response(llm_result.response.content)

                return LLMExtractionResult(
                    success=True,
                    data=data,
                    confidence=0.75,
                    model_used=llm_result.routing.selected_model if llm_result.routing else "unknown",
                    tokens_used=llm_result.response.prompt_tokens + llm_result.response.completion_tokens,
                    extraction_type="organizational_insights",
                    raw_response=llm_result.response.content,
                )

        except Exception:
            pass

        return LLMExtractionResult(
            success=False,
            data={},
            confidence=0.0,
            model_used="",
            extraction_type="organizational_insights",
        )

    def _apply_organization_extraction(
        self,
        result: EnhancedDiscoveryResult,
        extraction: LLMExtractionResult,
    ) -> None:
        """Apply LLM organization extraction to result."""
        data = extraction.data

        # Update municipality
        if data.get("municipality"):
            m = data["municipality"]
            if result.municipality:
                if m.get("name"):
                    result.municipality.name = m["name"]
                if m.get("state"):
                    result.municipality.state = m["state"]

        # Update executive
        if data.get("executive") and not result.executive:
            e = data["executive"]
            result.executive = Executive(
                name=e.get("name", ""),
                title=e.get("title", ""),
                office=e.get("office", ""),
            )

        # Add any new departments
        existing_names = {d.name.lower() for d in result.departments}

        for dept_data in data.get("departments", []):
            name = dept_data.get("name", "")
            if name and name.lower() not in existing_names:
                dept_id = re.sub(r"[^a-z0-9]+", "-", name.lower())[:30].strip("-")

                result.departments.append(Department(
                    id=dept_id,
                    name=name,
                    director=dept_data.get("director"),
                    director_title=dept_data.get("director_title"),
                    description=dept_data.get("description"),
                    suggested_template=dept_data.get("category"),
                ))
                existing_names.add(name.lower())

    def _apply_department_extraction(
        self,
        dept: Department,
        extraction: LLMExtractionResult,
    ) -> None:
        """Apply LLM department extraction to department."""
        data = extraction.data

        # Update director info if not already set
        if data.get("director_name") and not dept.director:
            dept.director = data["director_name"]
        if data.get("director_title") and not dept.director_title:
            dept.director_title = data["director_title"]

        # Update description
        if data.get("description") and not dept.description:
            dept.description = data["description"]

        # Update contact
        if data.get("contact"):
            contact = data["contact"]
            if contact.get("email"):
                dept.contact.email = contact["email"]
            if contact.get("phone"):
                dept.contact.phone = contact["phone"]
            if contact.get("address"):
                dept.contact.address = contact["address"]

        # Update template suggestion
        if data.get("suggested_template"):
            dept.suggested_template = data["suggested_template"]

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from LLM response."""
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in content
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return {}


def get_llm_discovery_engine(
    llm_router: Any | None = None,
) -> LLMDiscoveryEngine:
    """Get an LLM-enhanced discovery engine."""
    return LLMDiscoveryEngine(llm_router=llm_router)
