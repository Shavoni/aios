"""Grounding Engine for AIOS.

Provides source attribution, authority tracking, and response lineage
to ensure every AI response can answer:

    "What authoritative source justifies this output?"

This is the core of enterprise-grade AI governance.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from packages.core.schemas.models import (
    AuthorityLevel,
    DecisionReasoning,
    GroundedClaim,
    PolicyMatch,
    ResponseGrounding,
    ResponseLineage,
    SourceCitation,
    SourceType,
    VerificationStatus,
)


# =============================================================================
# SOURCE CITATION EXTRACTION
# =============================================================================


def extract_source_citations(
    response_text: str,
    sources: list[dict[str, Any]],
    min_relevance: float = 0.3,
) -> list[dict[str, Any]]:
    """Extract structured citations from sources used in response.

    Args:
        response_text: The generated response text
        sources: List of source documents from knowledge base
        min_relevance: Minimum relevance score to include

    Returns:
        List of structured citation dictionaries
    """
    citations = []

    for source in sources:
        # Skip low-relevance sources
        relevance = source.get("relevance", 0)
        if isinstance(relevance, (int, float)) and relevance < 0:
            relevance = 1 + relevance  # Convert distance to similarity

        if relevance < min_relevance:
            continue

        metadata = source.get("metadata", {})
        source_text = source.get("text", "")

        # Determine source type
        source_type = _classify_source_type(metadata)

        # Determine authority level
        authority = _determine_authority_level(metadata, source_type)

        # Extract section reference if present
        section_ref = _extract_section_reference(source_text, metadata)

        # Create citation
        citation = {
            "source_id": metadata.get("document_id", str(uuid.uuid4())[:8]),
            "source_type": source_type,
            "source_name": metadata.get("filename", "Unknown Source"),
            "authority_level": authority,
            "section_reference": section_ref,
            "quote": _extract_relevant_quote(source_text, 200),
            "relevance_score": round(relevance, 3),
            "verification_status": _determine_verification_status(metadata),
            "url": metadata.get("url"),
            "chunk_index": metadata.get("chunk_index"),
        }

        citations.append(citation)

    # Sort by relevance
    citations.sort(key=lambda x: x["relevance_score"], reverse=True)

    return citations


def _classify_source_type(metadata: dict[str, Any]) -> str:
    """Classify the type of source based on metadata."""
    filename = metadata.get("filename", "").lower()
    source_type = metadata.get("source_type", "")

    if "policy" in filename or "procedure" in filename:
        return SourceType.POLICY.value
    elif "ordinance" in filename or "code" in filename:
        return SourceType.ORDINANCE.value
    elif "regulation" in filename or "compliance" in filename:
        return SourceType.REGULATION.value
    elif source_type == "web" or metadata.get("url"):
        return SourceType.WEB_SOURCE.value
    elif source_type == "canon":
        return SourceType.KNOWLEDGE_BASE.value
    else:
        return SourceType.KNOWLEDGE_BASE.value


def _determine_authority_level(
    metadata: dict[str, Any],
    source_type: str
) -> str:
    """Determine the authority level of a source."""
    filename = metadata.get("filename", "").lower()

    # Check for high-authority indicators
    if any(term in filename for term in ["constitution", "charter", "immutable"]):
        return AuthorityLevel.CONSTITUTIONAL.value
    elif any(term in filename for term in ["ordinance", "statute", "law", "code"]):
        return AuthorityLevel.STATUTORY.value
    elif any(term in filename for term in ["regulation", "compliance", "requirement"]):
        return AuthorityLevel.STATUTORY.value
    elif source_type == SourceType.POLICY.value:
        return AuthorityLevel.ORGANIZATIONAL.value
    elif "department" in filename or metadata.get("agent_id"):
        return AuthorityLevel.DEPARTMENTAL.value
    else:
        return AuthorityLevel.OPERATIONAL.value


def _extract_section_reference(text: str, metadata: dict[str, Any]) -> str | None:
    """Extract section/clause reference from text."""
    # Look for common section patterns
    patterns = [
        r"§\s*[\d.]+",  # § 4.2
        r"Section\s+[\d.]+",  # Section 4.2
        r"Article\s+[IVX\d]+",  # Article III
        r"Chapter\s+\d+",  # Chapter 5
        r"Policy\s+[\d.]+",  # Policy 4.2
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group()

    return None


def _extract_relevant_quote(text: str, max_length: int = 200) -> str:
    """Extract a relevant quote from source text."""
    if len(text) <= max_length:
        return text.strip()

    # Find first complete sentence
    sentences = re.split(r'[.!?]+', text)
    if sentences:
        first_sentence = sentences[0].strip()
        if len(first_sentence) <= max_length:
            return first_sentence + "."

    return text[:max_length].strip() + "..."


def _determine_verification_status(metadata: dict[str, Any]) -> str:
    """Determine verification status of a source."""
    if metadata.get("human_verified"):
        return VerificationStatus.VERIFIED.value
    elif metadata.get("source_type") == "canon":
        return VerificationStatus.VERIFIED.value  # Canon is pre-verified
    elif metadata.get("deprecated"):
        return VerificationStatus.DEPRECATED.value
    else:
        return VerificationStatus.UNVERIFIED.value


# =============================================================================
# GROUNDING SCORE CALCULATION
# =============================================================================


def calculate_grounding_score(
    response_text: str,
    citations: list[dict[str, Any]],
    governance_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate comprehensive grounding metrics for a response.

    Returns:
        Dictionary with grounding score and analysis
    """
    if not citations:
        return {
            "grounding_score": 0.0,
            "primary_authority": AuthorityLevel.OPERATIONAL.value,
            "sources_used": 0,
            "verified_sources": 0,
            "analysis": "Response has no source citations - fully AI-generated",
            "requires_human_verification": True,
        }

    # Calculate base score from citation quality
    total_relevance = sum(c.get("relevance_score", 0) for c in citations)
    avg_relevance = total_relevance / len(citations) if citations else 0

    # Boost for verified sources
    verified_count = sum(
        1 for c in citations
        if c.get("verification_status") == VerificationStatus.VERIFIED.value
    )
    verification_bonus = (verified_count / len(citations)) * 0.2 if citations else 0

    # Boost for high-authority sources
    authority_weights = {
        AuthorityLevel.CONSTITUTIONAL.value: 1.0,
        AuthorityLevel.STATUTORY.value: 0.9,
        AuthorityLevel.ORGANIZATIONAL.value: 0.7,
        AuthorityLevel.DEPARTMENTAL.value: 0.5,
        AuthorityLevel.OPERATIONAL.value: 0.3,
    }

    max_authority = max(
        authority_weights.get(c.get("authority_level", ""), 0.3)
        for c in citations
    )
    authority_bonus = max_authority * 0.2

    # Calculate final score
    grounding_score = min(1.0, avg_relevance + verification_bonus + authority_bonus)

    # Determine primary authority
    authority_levels = [c.get("authority_level") for c in citations]
    primary_authority = _get_highest_authority(authority_levels)

    # Determine if human verification needed
    needs_verification = (
        grounding_score < 0.5 or
        verified_count == 0 or
        (governance_decision and governance_decision.get("hitl_mode") != "INFORM")
    )

    # Generate analysis
    if grounding_score >= 0.8:
        analysis = f"Well-grounded response with {len(citations)} citations from {primary_authority} authority"
    elif grounding_score >= 0.5:
        analysis = f"Moderately grounded with {len(citations)} citations - some claims may need verification"
    else:
        analysis = f"Weakly grounded ({len(citations)} citations) - recommend human review"

    return {
        "grounding_score": round(grounding_score, 3),
        "primary_authority": primary_authority,
        "sources_used": len(citations),
        "verified_sources": verified_count,
        "analysis": analysis,
        "requires_human_verification": needs_verification,
    }


def _get_highest_authority(authority_levels: list[str]) -> str:
    """Get the highest authority level from a list."""
    priority = [
        AuthorityLevel.CONSTITUTIONAL.value,
        AuthorityLevel.STATUTORY.value,
        AuthorityLevel.ORGANIZATIONAL.value,
        AuthorityLevel.DEPARTMENTAL.value,
        AuthorityLevel.OPERATIONAL.value,
    ]

    for level in priority:
        if level in authority_levels:
            return level

    return AuthorityLevel.OPERATIONAL.value


# =============================================================================
# GOVERNANCE REASONING
# =============================================================================


def generate_governance_reasoning(
    governance_decision: dict[str, Any],
    intent: dict[str, Any] | None = None,
    risk_signals: list[str] | None = None,
) -> str:
    """Generate human-readable reasoning for a governance decision.

    Args:
        governance_decision: The governance decision dict
        intent: Classified intent (optional)
        risk_signals: Detected risk signals (optional)

    Returns:
        Human-readable explanation of the decision
    """
    hitl_mode = governance_decision.get("hitl_mode", "INFORM")
    policy_ids = governance_decision.get("policy_trigger_ids", [])
    escalation_reason = governance_decision.get("escalation_reason")

    parts = []

    # Explain the mode
    mode_explanations = {
        "INFORM": "Response delivered immediately - no policy concerns detected.",
        "DRAFT": "Response requires human review before delivery.",
        "EXECUTE": "Response requires manager approval due to policy sensitivity.",
        "ESCALATE": "Request escalated to human handler - AI cannot respond directly.",
    }
    parts.append(mode_explanations.get(hitl_mode, f"Mode: {hitl_mode}"))

    # Explain triggered policies
    if policy_ids:
        parts.append(f"Triggered policies: {', '.join(policy_ids)}")

    # Explain risk signals
    if risk_signals:
        signal_names = {
            "PII": "personal identifiable information",
            "FINANCIAL": "financial data",
            "LEGAL": "legal content",
            "CONFIDENTIAL": "confidential information",
        }
        detected = [signal_names.get(s, s) for s in risk_signals]
        parts.append(f"Detected: {', '.join(detected)}")

    # Add escalation reason
    if escalation_reason:
        parts.append(f"Reason: {escalation_reason}")

    # Add intent context
    if intent:
        domain = intent.get("domain", "General")
        impact = intent.get("impact", "low")
        parts.append(f"Domain: {domain}, Impact: {impact}")

    return " | ".join(parts)


# =============================================================================
# RESPONSE LINEAGE TRACKING
# =============================================================================


def create_response_lineage(
    request_id: str,
    query: str,
    user_id: str,
    agent_id: str,
    response_text: str,
    sources: list[dict[str, Any]],
    governance_decision: dict[str, Any],
    approval_info: dict[str, Any] | None = None,
    user_role: str = "employee",
    user_department: str = "General",
    agent_version: str = "1.0",
) -> dict[str, Any]:
    """Create a complete lineage record for a response.

    This enables full reconstruction of how a response was generated.
    """
    lineage_id = f"lineage-{uuid.uuid4().hex[:12]}"

    lineage = {
        "lineage_id": lineage_id,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),

        # Query context
        "original_query": query,
        "user_id": user_id,
        "user_role": user_role,
        "user_department": user_department,

        # Agent processing
        "agent_id": agent_id,
        "agent_version": agent_version,

        # Sources
        "sources_retrieved": sources,
        "sources_used_in_response": [
            s.get("metadata", {}).get("document_id")
            for s in sources
            if s.get("relevance", 0) > 0.3 or (1 + s.get("relevance", 0)) > 0.3
        ],

        # Governance
        "governance_decision": governance_decision,
        "guardrails_applied": [],  # TODO: Track which guardrails fired

        # Approval chain
        "approval_required": governance_decision.get("approval_required", False),
        "approval_id": None,
        "approved_by": None,
        "approved_at": None,
        "approval_notes": None,

        # Final response
        "response_text": response_text,
        "response_modified": False,
        "original_response": None,

        # Attribution
        "attribution": "ai_generated",
        "human_verified": False,

        # Integrity
        "response_hash": hashlib.sha256(response_text.encode()).hexdigest()[:16],
    }

    # Add approval info if provided
    if approval_info:
        lineage["approval_id"] = approval_info.get("id")
        lineage["approved_by"] = approval_info.get("resolved_by")
        lineage["approved_at"] = approval_info.get("resolved_at")
        lineage["approval_notes"] = approval_info.get("reviewer_notes")
        if approval_info.get("modified_response"):
            lineage["response_modified"] = True
            lineage["original_response"] = response_text
            lineage["response_text"] = approval_info["modified_response"]
            lineage["attribution"] = "ai_assisted"  # Human modified
        if approval_info.get("status") == "approved":
            lineage["human_verified"] = True
            lineage["attribution"] = "human_verified"

    return lineage


# =============================================================================
# AUTHORITY BASIS EXTRACTION
# =============================================================================


def extract_authority_basis(
    citations: list[dict[str, Any]],
    governance_decision: dict[str, Any] | None = None,
) -> str | None:
    """Extract the primary authority basis for a response.

    Returns a string like "HR Policy 4.2" or "City Ordinance 12.4"
    """
    if not citations:
        return None

    # Find highest-authority citation
    authority_order = [
        AuthorityLevel.CONSTITUTIONAL.value,
        AuthorityLevel.STATUTORY.value,
        AuthorityLevel.ORGANIZATIONAL.value,
        AuthorityLevel.DEPARTMENTAL.value,
        AuthorityLevel.OPERATIONAL.value,
    ]

    best_citation = None
    best_priority = len(authority_order)

    for citation in citations:
        authority = citation.get("authority_level", AuthorityLevel.OPERATIONAL.value)
        try:
            priority = authority_order.index(authority)
            if priority < best_priority:
                best_priority = priority
                best_citation = citation
        except ValueError:
            continue

    if not best_citation:
        return None

    # Build authority string
    source_name = best_citation.get("source_name", "")
    section_ref = best_citation.get("section_reference")

    if section_ref:
        return f"{source_name} {section_ref}"
    else:
        return source_name


# =============================================================================
# GROUNDING SUMMARY FOR RESPONSES
# =============================================================================


def create_grounding_summary(
    response_text: str,
    sources: list[dict[str, Any]],
    governance_decision: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
    risk_signals: list[str] | None = None,
) -> dict[str, Any]:
    """Create a complete grounding summary for an agent response.

    This is the main function to call when processing agent responses.
    """
    # Extract citations
    citations = extract_source_citations(response_text, sources)

    # Calculate grounding score
    grounding_metrics = calculate_grounding_score(
        response_text, citations, governance_decision
    )

    # Extract authority basis
    authority_basis = extract_authority_basis(citations, governance_decision)

    # Generate governance reasoning
    reasoning = None
    if governance_decision:
        reasoning = generate_governance_reasoning(
            governance_decision, intent, risk_signals
        )

    return {
        "source_citations": citations,
        "grounding_score": grounding_metrics["grounding_score"],
        "authority_basis": authority_basis,
        "primary_authority": grounding_metrics["primary_authority"],
        "sources_used": grounding_metrics["sources_used"],
        "verified_sources": grounding_metrics["verified_sources"],
        "requires_human_verification": grounding_metrics["requires_human_verification"],
        "governance_reasoning": reasoning,
        "analysis": grounding_metrics["analysis"],
    }


# =============================================================================
# SINGLETON ACCESS
# =============================================================================


_grounding_engine: "GroundingEngine | None" = None


# =============================================================================
# GROUNDING ENFORCEMENT
# =============================================================================


@dataclass
class GroundingEnforcementConfig:
    """Configuration for grounding enforcement."""

    enabled: bool = True
    min_grounding_score: float = 0.5
    require_verified_sources: bool = False
    fallback_response: str = (
        "I don't have sufficient verified information to answer this question. "
        "Please consult an authoritative source or contact support for assistance."
    )
    warn_threshold: float = 0.7  # Warn but allow below this


class GroundingEnforcer:
    """Enforces grounding requirements on responses.

    Enterprise-grade enforcement that ensures AI responses
    meet minimum source attribution standards.
    """

    def __init__(self, config: GroundingEnforcementConfig | None = None):
        self.config = config or GroundingEnforcementConfig()

    def enforce(
        self,
        response: str,
        grounding: dict[str, Any],
    ) -> tuple[str, bool, str | None]:
        """Enforce grounding requirements.

        Args:
            response: The generated response text
            grounding: Grounding summary from create_grounding_summary()

        Returns:
            tuple: (response_text, was_blocked, warning_message)
            - response_text: Original or fallback response
            - was_blocked: True if response was blocked
            - warning_message: Optional warning for borderline cases
        """
        if not self.config.enabled:
            return response, False, None

        grounding_score = grounding.get("grounding_score", 0.0)
        verified_sources = grounding.get("verified_sources", 0)
        sources_used = grounding.get("sources_used", 0)

        # Check minimum grounding score
        if grounding_score < self.config.min_grounding_score:
            return (
                self.config.fallback_response,
                True,
                f"Response blocked: grounding score {grounding_score:.2f} below minimum {self.config.min_grounding_score}",
            )

        # Check for verified sources if required
        if self.config.require_verified_sources and verified_sources == 0:
            return (
                self.config.fallback_response,
                True,
                "Response blocked: no verified sources available",
            )

        # Check for warning threshold
        warning = None
        if grounding_score < self.config.warn_threshold:
            warning = (
                f"Low grounding score ({grounding_score:.2f}). "
                f"Response based on {sources_used} sources, {verified_sources} verified."
            )

        return response, False, warning


def enforce_grounding(
    response: str,
    grounding: dict[str, Any],
    config: GroundingEnforcementConfig | None = None,
) -> tuple[str, bool, str | None]:
    """Convenience function for grounding enforcement.

    Args:
        response: The generated response text
        grounding: Grounding summary
        config: Optional enforcement configuration

    Returns:
        tuple: (response_text, was_blocked, warning_message)
    """
    enforcer = GroundingEnforcer(config)
    return enforcer.enforce(response, grounding)


class GroundingEngine:
    """Singleton class for grounding operations."""

    def __init__(self, enforcement_config: GroundingEnforcementConfig | None = None):
        self.citation_cache: dict[str, list[dict]] = {}
        self.enforcer = GroundingEnforcer(enforcement_config)

    def ground_response(
        self,
        response_text: str,
        sources: list[dict[str, Any]],
        governance_decision: dict[str, Any] | None = None,
        intent: dict[str, Any] | None = None,
        risk_signals: list[str] | None = None,
        enforce: bool = True,
    ) -> dict[str, Any]:
        """Ground a response with full source attribution.

        Args:
            response_text: The generated response
            sources: Source documents
            governance_decision: Governance decision dict
            intent: Classified intent
            risk_signals: Detected risk signals
            enforce: Whether to apply grounding enforcement

        Returns:
            Grounding summary with optional enforcement results
        """
        grounding = create_grounding_summary(
            response_text, sources, governance_decision, intent, risk_signals
        )

        # Apply enforcement if enabled
        if enforce:
            final_response, was_blocked, warning = self.enforcer.enforce(
                response_text, grounding
            )
            grounding["enforced"] = True
            grounding["was_blocked"] = was_blocked
            grounding["enforcement_warning"] = warning
            if was_blocked:
                grounding["original_response"] = response_text
                grounding["final_response"] = final_response
            else:
                grounding["final_response"] = response_text
        else:
            grounding["enforced"] = False
            grounding["was_blocked"] = False
            grounding["final_response"] = response_text

        return grounding

    def create_lineage(
        self,
        request_id: str,
        query: str,
        user_id: str,
        agent_id: str,
        response_text: str,
        sources: list[dict[str, Any]],
        governance_decision: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """Create response lineage for audit."""
        return create_response_lineage(
            request_id, query, user_id, agent_id,
            response_text, sources, governance_decision, **kwargs
        )


def get_grounding_engine(
    enforcement_config: GroundingEnforcementConfig | None = None
) -> GroundingEngine:
    """Get the grounding engine singleton."""
    global _grounding_engine
    if _grounding_engine is None:
        _grounding_engine = GroundingEngine(enforcement_config)
    return _grounding_engine


def configure_grounding_enforcement(config: GroundingEnforcementConfig) -> None:
    """Configure grounding enforcement globally."""
    engine = get_grounding_engine()
    engine.enforcer = GroundingEnforcer(config)


__all__ = [
    "extract_source_citations",
    "calculate_grounding_score",
    "generate_governance_reasoning",
    "create_response_lineage",
    "extract_authority_basis",
    "create_grounding_summary",
    "get_grounding_engine",
    "configure_grounding_enforcement",
    "GroundingEngine",
    "GroundingEnforcementConfig",
    "GroundingEnforcer",
    "enforce_grounding",
]
