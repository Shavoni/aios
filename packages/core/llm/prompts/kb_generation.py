"""Prompt templates for knowledge base generation."""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.core.llm.prompts.base import PromptTemplate


@dataclass
class KBGenerationPrompt(PromptTemplate):
    """Prompt for generating knowledge base document content."""

    template_id: str = "kb_generation"
    purpose: str = "Generate knowledge base document content"
    output_format: str = "markdown"
    max_tokens: int = 8000
    temperature: float = 0.5
    required_context: list[str] = field(default_factory=lambda: [
        "org_name", "dept_name", "doc_type", "doc_purpose", "template_structure"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "template_structure_followed",
        "facts_properly_cited",
        "uncertainty_marked",
        "professional_tone",
        "no_hallucinated_specifics",
    ])

    TEMPLATE: str = """Generate knowledge base content for a municipal AI assistant.

CONTEXT:
- Organization: {org_name}
- Department: {dept_name}
- Document Type: {doc_type}
- Document Purpose: {doc_purpose}

TEMPLATE STRUCTURE TO FOLLOW:
{template_structure}

ADDITIONAL RESEARCH/CONTEXT (if available):
{research_data}

GENERATION REQUIREMENTS:
1. Follow the template structure exactly
2. Use researched facts where available
3. Mark uncertain information with [NEEDS VERIFICATION]
4. Mark missing required information with [TO BE FILLED]
5. Include source citations for factual claims
6. Maintain professional, neutral, helpful tone
7. Write for a general employee audience unless specified
8. Include the HAAIS classification footer

PROHIBITED:
- Do NOT invent specific facts (dates, numbers, names, statistics)
- Do NOT make promises on behalf of the organization
- Do NOT include personal opinions
- Do NOT copy verbatim from sources (paraphrase and cite)

REQUIRED FOOTER FORMAT:
---
*HAAIS Classification: Tier 2 - Organizational | Last Updated: [Current Date]*

Generate the knowledge base content now:"""

    def get_system_prompt(self) -> str:
        return """You are a municipal knowledge base content generator.
You create accurate, professional documentation for city employees.
You follow templates exactly and never invent specific facts.
You mark uncertain information clearly for human review.
You maintain HAAIS governance standards in all content."""


@dataclass
class RegulatoryContentPrompt(PromptTemplate):
    """Prompt for synthesizing regulatory compliance content."""

    template_id: str = "regulatory_synthesis"
    purpose: str = "Synthesize regulatory compliance documentation"
    output_format: str = "markdown"
    max_tokens: int = 12000
    temperature: float = 0.3
    required_context: list[str] = field(default_factory=lambda: [
        "org_name", "dept_name", "regulation_name", "regulation_summary"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "regulatory_accuracy",
        "citations_present",
        "actionable_guidance",
        "compliance_requirements_clear",
    ])

    TEMPLATE: str = """Create a regulatory quick reference guide for municipal employees.

CONTEXT:
- Organization: {org_name}
- Department: {dept_name}
- Regulation: {regulation_name}

REGULATION SUMMARY:
{regulation_summary}

DOCUMENT REQUIREMENTS:
1. Executive Summary (2-3 sentences)
2. Key Compliance Requirements (bullet points)
3. Prohibited Actions (what employees must NOT do)
4. Required Procedures (step-by-step when applicable)
5. Reporting Obligations
6. Violation Consequences
7. Resources & Contacts for Questions
8. Last Update Date and Review Schedule

FORMAT GUIDELINES:
- Use clear, plain language (avoid legal jargon where possible)
- Include specific citations to regulation sections
- Provide actionable guidance, not just rules
- Highlight common compliance mistakes to avoid
- Include escalation contacts for complex situations

OUTPUT FORMAT:
# {regulation_name} - Quick Reference Guide

**Version:** 1.0 | **Classification:** INTERNAL | **HAAIS Tier:** Tier 1

## PURPOSE
[Why this regulation matters to this department]

## KEY REQUIREMENTS
[Bullet points of must-do items]

## PROHIBITED ACTIONS
[What employees must NOT do]

## PROCEDURES
[Step-by-step compliance procedures]

## REPORTING
[When and how to report]

## VIOLATIONS
[Consequences of non-compliance]

## CONTACTS
[Who to contact with questions]

---
*HAAIS Classification: Tier 1 - Constitutional | Review: Annually*

Generate the regulatory quick reference now:"""

    def get_system_prompt(self) -> str:
        return """You are a regulatory compliance specialist creating employee-facing documentation.
You translate complex regulations into clear, actionable guidance.
You ensure accuracy while maintaining accessibility.
You always cite specific regulatory sections.
You never provide legal advice but guide employees to proper resources."""


@dataclass
class FAQGenerationPrompt(PromptTemplate):
    """Prompt for generating FAQ content."""

    template_id: str = "faq_generation"
    purpose: str = "Generate frequently asked questions and answers"
    output_format: str = "markdown"
    max_tokens: int = 6000
    temperature: float = 0.5
    required_context: list[str] = field(default_factory=lambda: [
        "org_name", "dept_name", "topic", "source_content"
    ])
    quality_criteria: list[str] = field(default_factory=lambda: [
        "questions_realistic",
        "answers_accurate",
        "coverage_comprehensive",
        "tone_appropriate",
    ])

    TEMPLATE: str = """Generate a comprehensive FAQ document based on the provided source content.

CONTEXT:
- Organization: {org_name}
- Department: {dept_name}
- Topic: {topic}

SOURCE CONTENT:
{source_content}

FAQ REQUIREMENTS:
1. Generate 10-15 realistic questions employees would ask
2. Provide clear, concise answers (2-4 sentences each)
3. Include follow-up questions where natural
4. Reference specific procedures or policies when relevant
5. Include "Who to contact" guidance where appropriate
6. Order questions from most common to most specialized

QUESTION CATEGORIES TO COVER:
- Basic "What is...?" questions
- "How do I...?" procedural questions
- "When should I...?" timing questions
- "Who handles...?" responsibility questions
- "What if...?" edge case questions

OUTPUT FORMAT:
# {topic} - Frequently Asked Questions

**Department:** {dept_name}
**Last Updated:** [Current Date]

## General Questions

### Q: [Question 1]
A: [Answer with specific guidance]

### Q: [Question 2]
A: [Answer with specific guidance]

## Procedures

### Q: [Procedural question]
A: [Step-by-step answer if needed]

## Contact Information

For questions not covered here, contact:
- [Primary contact]
- [Escalation contact]

---
*HAAIS Classification: Tier 2 - Organizational*

Generate the FAQ document now:"""
