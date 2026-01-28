"""Prompt templates for organizational discovery."""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.core.llm.prompts.base import PromptTemplate


@dataclass
class DiscoveryExtractionPrompt(PromptTemplate):
    """Prompt for extracting organizational structure from web content."""

    template_id: str = "discovery_extraction"
    purpose: str = "Extract organizational structure from web content"
    output_format: str = "json"
    max_tokens: int = 8000
    temperature: float = 0.3
    required_context: list[str] = field(default_factory=lambda: [
        "org_name", "org_type", "web_content"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "all_departments_identified",
        "hierarchy_relationships_correct",
        "confidence_scores_appropriate",
        "no_hallucinated_information",
    ])

    TEMPLATE: str = """You are an expert organizational analyst extracting structure from {org_type} websites.

TASK: Extract the organizational hierarchy from the following web content.

ORGANIZATION: {org_name}
ORGANIZATION TYPE: {org_type}

WEB CONTENT:
{web_content}

EXTRACTION REQUIREMENTS:
1. Identify all departments and divisions
2. Determine hierarchical relationships (parent-child)
3. Extract leadership names and titles where visible
4. Note department responsibilities and functions
5. Identify contact information where available
6. Flag any information you're uncertain about with confidence scores

OUTPUT FORMAT (JSON only):
{{
  "org_name": "{org_name}",
  "org_type": "{org_type}",
  "extraction_confidence": 0.0-1.0,
  "departments": [
    {{
      "dept_id": "unique-id",
      "name": "Department Name",
      "description": "Brief description of purpose",
      "level": 0,
      "parent_dept_id": "parent-id or null",
      "leadership": [
        {{"name": "Full Name", "title": "Job Title", "confidence": 0.0-1.0}}
      ],
      "responsibilities": ["responsibility1", "responsibility2"],
      "contact": {{"email": "if found", "phone": "if found", "address": "if found"}},
      "confidence": 0.0-1.0,
      "confidence_notes": "Why this confidence level",
      "source_section": "Where in content this was found"
    }}
  ],
  "org_structure_notes": "Overall notes about the organizational structure",
  "uncertain_items": ["List of items needing human verification"],
  "missing_information": ["Information that would be helpful but wasn't found"]
}}

CRITICAL RULES:
- Only extract information EXPLICITLY present in the content
- Do NOT invent or assume information not stated
- Mark uncertain extractions with lower confidence scores
- If you can't determine something, say so
- Prioritize accuracy over completeness

Extract the organizational structure now:"""

    def get_system_prompt(self) -> str:
        return """You are an expert organizational analyst specializing in government and corporate structures.
Your role is to accurately extract organizational information from web content.
You prioritize accuracy and flag uncertainty rather than making assumptions.
You output valid JSON that exactly matches the requested format."""


@dataclass
class DataSourceDetectionPrompt(PromptTemplate):
    """Prompt for detecting data sources and APIs."""

    template_id: str = "data_source_detection"
    purpose: str = "Detect data sources, APIs, and portals from web content"
    output_format: str = "json"
    max_tokens: int = 4000
    temperature: float = 0.3
    required_context: list[str] = field(default_factory=lambda: [
        "org_name", "web_content"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "data_sources_identified",
        "api_endpoints_valid",
        "sensitivity_levels_appropriate",
    ])

    TEMPLATE: str = """Analyze the following web content to identify data sources, APIs, and data portals.

ORGANIZATION: {org_name}

WEB CONTENT:
{web_content}

DETECTION REQUIREMENTS:
1. Identify public data portals (e.g., data.city.gov)
2. Find API endpoints or documentation references
3. Detect data download links
4. Note data types and formats
5. Assess likely sensitivity levels

OUTPUT FORMAT (JSON only):
{{
  "data_portals": [
    {{
      "name": "Portal Name",
      "url": "https://...",
      "description": "What data it provides",
      "data_types": ["type1", "type2"],
      "confidence": 0.0-1.0
    }}
  ],
  "api_endpoints": [
    {{
      "name": "API Name",
      "endpoint": "https://...",
      "documentation_url": "if found",
      "auth_type": "public/api_key/oauth/unknown",
      "confidence": 0.0-1.0
    }}
  ],
  "data_downloads": [
    {{
      "name": "Dataset Name",
      "url": "https://...",
      "format": "csv/json/xlsx/etc",
      "update_frequency": "if mentioned",
      "sensitivity": "public/internal/confidential"
    }}
  ],
  "integration_opportunities": [
    "Brief descriptions of how these sources could be integrated"
  ],
  "notes": "Overall assessment of data availability"
}}

Detect data sources now:"""

    def get_system_prompt(self) -> str:
        return """You are a data integration specialist analyzing web content for data sources.
You identify public data portals, APIs, and datasets.
You assess data accessibility and integration potential.
You output valid JSON matching the requested format."""


@dataclass
class TemplateMatchingPrompt(PromptTemplate):
    """Prompt for matching discovered departments to templates."""

    template_id: str = "template_matching"
    purpose: str = "Match discovered departments to agent templates"
    output_format: str = "json"
    max_tokens: int = 4000
    temperature: float = 0.2
    required_context: list[str] = field(default_factory=lambda: [
        "department", "available_templates"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "matches_ranked_correctly",
        "reasoning_provided",
        "confidence_appropriate",
    ])

    TEMPLATE: str = """Match the following discovered department to the most appropriate template(s).

DISCOVERED DEPARTMENT:
{department}

AVAILABLE TEMPLATES:
{available_templates}

MATCHING REQUIREMENTS:
1. Rank the top 3 most appropriate template matches
2. Provide confidence score for each match (0.0-1.0)
3. Explain why each template matches or doesn't match
4. Suggest any customizations needed

OUTPUT FORMAT (JSON only):
{{
  "department_name": "Name from input",
  "matches": [
    {{
      "template_id": "template_id",
      "template_name": "Template Name",
      "confidence": 0.0-1.0,
      "match_reasoning": "Why this template matches",
      "matched_keywords": ["keyword1", "keyword2"],
      "gaps": ["What the template doesn't cover"],
      "customizations_needed": ["Suggested customizations"]
    }}
  ],
  "best_match": "template_id of best match",
  "requires_custom_template": true/false,
  "custom_template_notes": "If custom needed, what should it include"
}}

Match templates now:"""
