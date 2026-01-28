"""Quality scoring implementations for LLM outputs.

Provides multiple scoring dimensions:
- Format validation (JSON, markdown, etc.)
- Completeness (required fields present)
- Accuracy (hallucination detection)
- Tone (professional, appropriate)
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreResult:
    """Result from a quality scorer."""

    dimension: str
    score: float  # 0.0 to 1.0
    passed: bool
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class QualityScorer(ABC):
    """Base class for quality scorers."""

    dimension: str = "base"
    weight: float = 1.0
    threshold: float = 0.7

    @abstractmethod
    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Score the response on this dimension.

        Args:
            response: The LLM response to score
            context: Additional context (expected format, required fields, etc.)

        Returns:
            ScoreResult with score, pass/fail, and issues
        """
        pass


class FormatScorer(QualityScorer):
    """Validates response format (JSON, markdown, etc.)."""

    dimension = "format"
    weight = 1.5  # Format issues are critical

    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Check if response matches expected format."""
        context = context or {}
        expected_format = context.get("output_format", "text")
        issues = []
        score = 1.0

        if expected_format == "json":
            score, issues = self._validate_json(response)
        elif expected_format == "markdown":
            score, issues = self._validate_markdown(response, context)
        elif expected_format == "structured":
            score, issues = self._validate_structured(response, context)

        return ScoreResult(
            dimension=self.dimension,
            score=score,
            passed=score >= self.threshold,
            issues=issues,
            details={"expected_format": expected_format},
        )

    def _validate_json(self, response: str) -> tuple[float, list[str]]:
        """Validate JSON format."""
        issues = []

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
        json_str = json_match.group(1) if json_match else response

        try:
            parsed = json.loads(json_str.strip())
            if isinstance(parsed, dict) or isinstance(parsed, list):
                return 1.0, []
            issues.append("JSON parsed but not an object or array")
            return 0.8, issues
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON: {str(e)[:100]}")

            # Check for common issues
            if response.strip().startswith("{") or response.strip().startswith("["):
                issues.append("Starts like JSON but has syntax errors")
                return 0.3, issues
            else:
                issues.append("Response doesn't appear to be JSON")
                return 0.0, issues

    def _validate_markdown(
        self,
        response: str,
        context: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Validate markdown format."""
        issues = []
        score = 1.0

        # Check for required sections
        required_sections = context.get("required_sections", [])
        for section in required_sections:
            # Look for ## Section or # Section headers
            pattern = rf"^#+\s*{re.escape(section)}"
            if not re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                issues.append(f"Missing section: {section}")
                score -= 0.1

        # Check for basic markdown structure
        if not re.search(r"^#", response, re.MULTILINE):
            issues.append("No markdown headers found")
            score -= 0.2

        return max(0.0, score), issues

    def _validate_structured(
        self,
        response: str,
        context: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Validate structured text format."""
        issues = []
        score = 1.0

        # Check for required patterns
        required_patterns = context.get("required_patterns", [])
        for pattern in required_patterns:
            if not re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Missing required pattern: {pattern}")
                score -= 0.15

        return max(0.0, score), issues


class CompletenessScorer(QualityScorer):
    """Validates that all required fields/sections are present."""

    dimension = "completeness"
    weight = 1.2

    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Check if response has all required content."""
        context = context or {}
        issues = []
        score = 1.0

        # Check required fields for JSON
        output_format = context.get("output_format", "text")
        if output_format == "json":
            required_fields = context.get("required_fields", [])
            if required_fields:
                field_score, field_issues = self._check_json_fields(
                    response, required_fields
                )
                score = min(score, field_score)
                issues.extend(field_issues)

        # Check for placeholder markers
        placeholder_patterns = [
            r"\[TO BE FILLED\]",
            r"\[NEEDS VERIFICATION\]",
            r"\[TBD\]",
            r"\[PLACEHOLDER\]",
            r"TODO:",
            r"FIXME:",
        ]

        placeholder_count = 0
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            placeholder_count += len(matches)

        if placeholder_count > 0:
            # Placeholders reduce score but aren't failures
            penalty = min(0.3, placeholder_count * 0.05)
            score -= penalty
            issues.append(f"Contains {placeholder_count} placeholder(s)")

        # Check minimum length
        min_length = context.get("min_length", 0)
        if min_length and len(response) < min_length:
            issues.append(f"Response too short (got {len(response)}, need {min_length})")
            score -= 0.2

        return ScoreResult(
            dimension=self.dimension,
            score=max(0.0, score),
            passed=score >= self.threshold,
            issues=issues,
            details={"placeholder_count": placeholder_count},
        )

    def _check_json_fields(
        self,
        response: str,
        required_fields: list[str],
    ) -> tuple[float, list[str]]:
        """Check that required JSON fields are present."""
        issues = []

        # Try to parse JSON
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
        json_str = json_match.group(1) if json_match else response

        try:
            parsed = json.loads(json_str.strip())
            if not isinstance(parsed, dict):
                return 0.5, ["JSON is not an object, cannot check fields"]

            missing = []
            empty = []
            for field in required_fields:
                # Handle nested fields with dot notation
                value = self._get_nested_value(parsed, field)
                if value is None:
                    missing.append(field)
                elif value == "" or value == [] or value == {}:
                    empty.append(field)

            score = 1.0
            if missing:
                issues.append(f"Missing fields: {', '.join(missing)}")
                score -= len(missing) * 0.15
            if empty:
                issues.append(f"Empty fields: {', '.join(empty)}")
                score -= len(empty) * 0.05

            return max(0.0, score), issues

        except json.JSONDecodeError:
            return 0.5, ["Cannot parse JSON to check fields"]

    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get a nested value using dot notation."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


class AccuracyScorer(QualityScorer):
    """Detects potential hallucinations and unsupported claims."""

    dimension = "accuracy"
    weight = 1.5  # Hallucinations are serious

    # Phrases that often accompany hallucinations
    HALLUCINATION_INDICATORS = [
        r"as you (mentioned|said|noted|indicated)",
        r"according to (your|the) (previous|earlier)",
        r"you (previously|earlier) (stated|mentioned|said)",
        r"in your (previous|earlier|last)",
        r"as we (discussed|established|agreed)",
    ]

    # Confident claims that should have citations
    UNCITED_CLAIM_PATTERNS = [
        r"studies (show|prove|demonstrate|indicate)",
        r"research (shows|proves|demonstrates|indicates)",
        r"according to experts",
        r"scientists (say|agree|believe)",
        r"statistics show",
        r"\d+%\s+of\s+\w+",  # Percentages without citation
    ]

    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Check for potential hallucinations and unsupported claims."""
        context = context or {}
        issues = []
        score = 1.0
        hallucination_evidence = []

        # Check for self-referential hallucinations
        for pattern in self.HALLUCINATION_INDICATORS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                issues.append(f"Potential hallucination: references non-existent context")
                hallucination_evidence.append(matches[0] if isinstance(matches[0], str) else matches[0][0])
                score -= 0.25

        # Check for uncited claims (only if citations expected)
        if context.get("require_citations", False):
            for pattern in self.UNCITED_CLAIM_PATTERNS:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    # Check if citation follows
                    for match in matches:
                        if not self._has_nearby_citation(response, match):
                            issues.append(f"Uncited claim: '{match}'")
                            score -= 0.1

        # Check for impossible specificity
        if context.get("check_specificity", False):
            specific_issues = self._check_suspicious_specificity(response, context)
            issues.extend(specific_issues)
            score -= len(specific_issues) * 0.1

        return ScoreResult(
            dimension=self.dimension,
            score=max(0.0, score),
            passed=score >= self.threshold,
            issues=issues,
            details={"hallucination_evidence": hallucination_evidence},
        )

    def _has_nearby_citation(self, text: str, claim: str) -> bool:
        """Check if a claim has a nearby citation."""
        # Look for citation patterns near the claim
        citation_patterns = [
            r"\[\d+\]",  # [1]
            r"\(.*?\d{4}\)",  # (Author, 2024)
            r"Source:",
            r"Reference:",
            r"See:",
        ]

        # Find position of claim
        pos = text.lower().find(claim.lower())
        if pos == -1:
            return True  # Can't find it, assume ok

        # Check 200 chars before and after
        context_start = max(0, pos - 200)
        context_end = min(len(text), pos + len(claim) + 200)
        context = text[context_start:context_end]

        for pattern in citation_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True

        return False

    def _check_suspicious_specificity(
        self,
        response: str,
        context: dict[str, Any],
    ) -> list[str]:
        """Check for suspiciously specific numbers/facts that might be hallucinated."""
        issues = []

        # Very specific numbers without context
        specific_numbers = re.findall(
            r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:percent|%|dollars|\$|people|users|employees)\b",
            response,
            re.IGNORECASE,
        )

        # If we find very specific numbers, check if they're in known context
        known_facts = context.get("known_facts", [])
        for num_match in specific_numbers:
            if not any(num_match in fact for fact in known_facts):
                # This specific number wasn't in our known facts
                # Could be hallucinated or could be valid
                pass  # Don't flag automatically, just note

        return issues


class ToneScorer(QualityScorer):
    """Validates professional and appropriate tone."""

    dimension = "tone"
    weight = 0.8

    # Informal/unprofessional language
    INFORMAL_PATTERNS = [
        r"\b(gonna|wanna|gotta|kinda|sorta)\b",
        r"\b(yeah|yep|nope|nah)\b",
        r"\b(awesome|amazing|incredible|insane)\b",  # Hyperbolic
        r"!!+",  # Multiple exclamation marks
        r"\b(lol|lmao|omg|wtf)\b",
        r"😀|😂|🤣|👍|🔥|💯",  # Emojis (unless explicitly allowed)
    ]

    # Potentially inappropriate content
    INAPPROPRIATE_PATTERNS = [
        r"\b(stupid|dumb|idiot|moron)\b",
        r"\b(hate|horrible|terrible|worst)\b",
        r"discriminat|racist|sexist",
    ]

    # Overly confident language for uncertain topics
    OVERCONFIDENT_PATTERNS = [
        r"\bdefinitely\b",
        r"\babsolutely\b",
        r"\bguaranteed\b",
        r"\bno doubt\b",
        r"\bcertainly\b",
    ]

    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Check if response has appropriate tone."""
        context = context or {}
        issues = []
        score = 1.0

        expected_tone = context.get("expected_tone", "professional")
        allow_emojis = context.get("allow_emojis", False)

        # Check for informal language
        if expected_tone == "professional":
            for pattern in self.INFORMAL_PATTERNS:
                if "emoji" in pattern.lower() and allow_emojis:
                    continue
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    issues.append(f"Informal language detected: '{matches[0]}'")
                    score -= 0.1

        # Check for inappropriate content
        for pattern in self.INAPPROPRIATE_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                issues.append(f"Potentially inappropriate: '{matches[0]}'")
                score -= 0.2

        # Check for overconfidence on uncertain topics
        if context.get("topic_uncertain", False):
            for pattern in self.OVERCONFIDENT_PATTERNS:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    issues.append(f"Overconfident language on uncertain topic: '{matches[0]}'")
                    score -= 0.1

        # Check for hedging when confidence expected
        if context.get("confidence_expected", False):
            hedging_patterns = [
                r"\b(maybe|perhaps|might|could be|possibly)\b",
                r"\b(I think|I believe|it seems|it appears)\b",
            ]
            hedge_count = 0
            for pattern in hedging_patterns:
                hedge_count += len(re.findall(pattern, response, re.IGNORECASE))

            if hedge_count > 3:
                issues.append(f"Excessive hedging ({hedge_count} instances)")
                score -= 0.1

        return ScoreResult(
            dimension=self.dimension,
            score=max(0.0, score),
            passed=score >= self.threshold,
            issues=issues,
            details={"expected_tone": expected_tone},
        )


class RelevanceScorer(QualityScorer):
    """Validates that response is relevant to the query."""

    dimension = "relevance"
    weight = 1.0

    def score(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Check if response addresses the query."""
        context = context or {}
        issues = []
        score = 1.0

        query = context.get("query", "")
        if not query:
            return ScoreResult(
                dimension=self.dimension,
                score=1.0,
                passed=True,
                issues=[],
                details={"note": "No query provided for relevance check"},
            )

        # Extract key terms from query
        query_terms = self._extract_key_terms(query)

        # Check how many query terms appear in response
        response_lower = response.lower()
        matched_terms = [
            term for term in query_terms
            if term.lower() in response_lower
        ]

        coverage = len(matched_terms) / len(query_terms) if query_terms else 1.0

        if coverage < 0.3:
            issues.append("Response may not address the query")
            score -= 0.3
        elif coverage < 0.5:
            issues.append("Response partially addresses the query")
            score -= 0.1

        # Check for off-topic indicators
        off_topic_phrases = [
            r"I cannot help with",
            r"I'm not able to",
            r"This is outside my",
            r"I don't have information about",
        ]

        for phrase in off_topic_phrases:
            if re.search(phrase, response, re.IGNORECASE):
                issues.append("Response indicates inability to answer")
                score -= 0.2
                break

        return ScoreResult(
            dimension=self.dimension,
            score=max(0.0, score),
            passed=score >= self.threshold,
            issues=issues,
            details={
                "query_terms": query_terms,
                "matched_terms": matched_terms,
                "coverage": round(coverage, 2),
            },
        )

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms from text for relevance checking."""
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "and", "but", "if", "or", "because",
            "until", "while", "although", "though", "what", "which",
            "who", "whom", "this", "that", "these", "those", "i", "me",
            "my", "myself", "we", "our", "ours", "you", "your", "he",
            "him", "his", "she", "her", "it", "its", "they", "them",
        }

        # Tokenize and filter
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        key_terms = [w for w in words if w not in stop_words]

        # Return unique terms
        return list(dict.fromkeys(key_terms))[:20]  # Max 20 terms
