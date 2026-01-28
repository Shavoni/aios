"""Output validation for LLM responses.

Provides comprehensive quality validation including:
- Format validation
- Completeness checking
- Hallucination detection
- Tone analysis
- Relevance scoring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.core.llm.quality.scorers import (
    QualityScorer,
    FormatScorer,
    CompletenessScorer,
    AccuracyScorer,
    ToneScorer,
    RelevanceScorer,
    ScoreResult,
)


@dataclass
class ValidationResult:
    """Complete validation result for an LLM response."""

    valid: bool
    overall_quality: float  # 0.0 to 1.0 weighted average
    scores: dict[str, ScoreResult]  # By dimension
    format_errors: list[str]
    missing_fields: list[str]
    failed_criteria: list[str]
    hallucination_risk: str  # none, low, medium, high
    hallucination_evidence: list[str]
    recommendation: str  # pass, warn, block
    improvement_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "valid": self.valid,
            "overall_quality": round(self.overall_quality, 3),
            "scores": {
                dim: {
                    "score": round(result.score, 3),
                    "passed": result.passed,
                    "issues": result.issues,
                }
                for dim, result in self.scores.items()
            },
            "format_errors": self.format_errors,
            "missing_fields": self.missing_fields,
            "failed_criteria": self.failed_criteria,
            "hallucination_risk": self.hallucination_risk,
            "hallucination_evidence": self.hallucination_evidence,
            "recommendation": self.recommendation,
            "improvement_suggestions": self.improvement_suggestions,
        }


class OutputValidator:
    """Orchestrates multiple quality scorers for comprehensive validation.

    Usage:
        validator = OutputValidator()
        result = await validator.validate(response, task_context)
        if not result.valid:
            # Handle quality issues
    """

    def __init__(
        self,
        scorers: list[QualityScorer] | None = None,
        quality_threshold: float = 0.7,
        require_all_pass: bool = False,
    ):
        """Initialize the validator.

        Args:
            scorers: Custom list of scorers. If None, uses all default scorers.
            quality_threshold: Minimum weighted average score to pass.
            require_all_pass: If True, all individual scorers must pass.
        """
        self._scorers = scorers or [
            FormatScorer(),
            CompletenessScorer(),
            AccuracyScorer(),
            ToneScorer(),
            RelevanceScorer(),
        ]
        self._quality_threshold = quality_threshold
        self._require_all_pass = require_all_pass

    async def validate(
        self,
        response: Any,  # ModelResponse or str
        task: Any | None = None,  # Task object
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate an LLM response.

        Args:
            response: The response to validate (ModelResponse or raw string)
            task: Optional Task object for context
            context: Additional context for validation

        Returns:
            ValidationResult with comprehensive quality assessment
        """
        # Extract response text
        if hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response)

        # Build validation context from task and explicit context
        validation_context = self._build_context(task, context)

        # Run all scorers
        scores: dict[str, ScoreResult] = {}
        for scorer in self._scorers:
            result = scorer.score(response_text, validation_context)
            scores[scorer.dimension] = result

        # Calculate weighted average
        total_weight = sum(s.weight for s in self._scorers)
        weighted_sum = sum(
            scores[s.dimension].score * s.weight
            for s in self._scorers
        )
        overall_quality = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Collect issues
        format_errors = scores.get("format", ScoreResult("format", 1.0, True)).issues
        missing_fields = []
        for issue in scores.get("completeness", ScoreResult("completeness", 1.0, True)).issues:
            if "Missing fields" in issue or "Missing section" in issue:
                missing_fields.append(issue)

        failed_criteria = [
            f"{dim}: {', '.join(result.issues)}"
            for dim, result in scores.items()
            if not result.passed and result.issues
        ]

        # Assess hallucination risk
        accuracy_score = scores.get("accuracy", ScoreResult("accuracy", 1.0, True))
        hallucination_risk = self._assess_hallucination_risk(accuracy_score)
        hallucination_evidence = accuracy_score.details.get("hallucination_evidence", [])

        # Determine if valid
        all_passed = all(result.passed for result in scores.values())
        meets_threshold = overall_quality >= self._quality_threshold

        if self._require_all_pass:
            valid = all_passed and meets_threshold
        else:
            valid = meets_threshold

        # Determine recommendation
        recommendation = self._get_recommendation(
            valid, overall_quality, hallucination_risk, scores
        )

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(scores, validation_context)

        return ValidationResult(
            valid=valid,
            overall_quality=overall_quality,
            scores=scores,
            format_errors=format_errors,
            missing_fields=missing_fields,
            failed_criteria=failed_criteria,
            hallucination_risk=hallucination_risk,
            hallucination_evidence=hallucination_evidence,
            recommendation=recommendation,
            improvement_suggestions=suggestions,
        )

    def _build_context(
        self,
        task: Any | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build validation context from task and explicit context."""
        result: dict[str, Any] = {}

        if task:
            # Extract relevant task properties
            if hasattr(task, "requires_json") and task.requires_json:
                result["output_format"] = "json"
            if hasattr(task, "required_fields"):
                result["required_fields"] = task.required_fields
            if hasattr(task, "quality_criteria"):
                result["quality_criteria"] = task.quality_criteria

        if context:
            result.update(context)

        return result

    def _assess_hallucination_risk(self, accuracy_result: ScoreResult) -> str:
        """Assess hallucination risk level from accuracy score."""
        score = accuracy_result.score
        evidence = accuracy_result.details.get("hallucination_evidence", [])

        if score >= 0.95 and not evidence:
            return "none"
        elif score >= 0.8:
            return "low"
        elif score >= 0.6:
            return "medium"
        else:
            return "high"

    def _get_recommendation(
        self,
        valid: bool,
        overall_quality: float,
        hallucination_risk: str,
        scores: dict[str, ScoreResult],
    ) -> str:
        """Determine recommendation based on validation results."""
        # Block on high hallucination risk
        if hallucination_risk == "high":
            return "block"

        # Block on critical format failures
        format_score = scores.get("format", ScoreResult("format", 1.0, True))
        if format_score.score < 0.3:
            return "block"

        # Warn on medium issues
        if not valid or hallucination_risk == "medium":
            return "warn"

        if overall_quality < 0.8:
            return "warn"

        return "pass"

    def _generate_suggestions(
        self,
        scores: dict[str, ScoreResult],
        context: dict[str, Any],
    ) -> list[str]:
        """Generate improvement suggestions based on failures."""
        suggestions = []

        for dimension, result in scores.items():
            if result.passed:
                continue

            if dimension == "format":
                expected = context.get("output_format", "text")
                suggestions.append(
                    f"Ensure response is valid {expected} format"
                )

            elif dimension == "completeness":
                if "missing fields" in str(result.issues).lower():
                    suggestions.append(
                        "Include all required fields in the response"
                    )
                if "placeholder" in str(result.issues).lower():
                    suggestions.append(
                        "Replace placeholder values with actual content"
                    )

            elif dimension == "accuracy":
                suggestions.append(
                    "Avoid referencing non-existent context or making unsupported claims"
                )

            elif dimension == "tone":
                suggestions.append(
                    "Use professional language appropriate for the context"
                )

            elif dimension == "relevance":
                suggestions.append(
                    "Ensure the response directly addresses the query"
                )

        return suggestions


class ConfigurableValidator(OutputValidator):
    """Validator with configurable scoring weights and thresholds."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
    ):
        """Initialize with configuration.

        Args:
            config: Configuration dict with:
                - scorers: List of scorer configs
                - quality_threshold: Overall threshold
                - require_all_pass: Whether all must pass
        """
        config = config or {}

        # Build scorers from config
        scorer_configs = config.get("scorers", {})
        scorers = []

        # Default scorers with custom weights/thresholds
        scorer_classes = {
            "format": FormatScorer,
            "completeness": CompletenessScorer,
            "accuracy": AccuracyScorer,
            "tone": ToneScorer,
            "relevance": RelevanceScorer,
        }

        for name, cls in scorer_classes.items():
            scorer_config = scorer_configs.get(name, {})
            if scorer_config.get("enabled", True):
                scorer = cls()
                if "weight" in scorer_config:
                    scorer.weight = scorer_config["weight"]
                if "threshold" in scorer_config:
                    scorer.threshold = scorer_config["threshold"]
                scorers.append(scorer)

        super().__init__(
            scorers=scorers,
            quality_threshold=config.get("quality_threshold", 0.7),
            require_all_pass=config.get("require_all_pass", False),
        )


class TaskSpecificValidator(OutputValidator):
    """Validator that adjusts scoring based on task type."""

    # Task type to scorer weight adjustments
    TASK_WEIGHTS = {
        "json_extraction": {
            "format": 2.0,
            "completeness": 1.5,
            "accuracy": 1.0,
            "tone": 0.3,
            "relevance": 0.8,
        },
        "content_generation": {
            "format": 0.8,
            "completeness": 1.2,
            "accuracy": 1.5,
            "tone": 1.2,
            "relevance": 1.0,
        },
        "regulatory": {
            "format": 1.0,
            "completeness": 1.5,
            "accuracy": 2.0,
            "tone": 1.0,
            "relevance": 1.2,
        },
        "conversation": {
            "format": 0.5,
            "completeness": 0.8,
            "accuracy": 1.0,
            "tone": 1.5,
            "relevance": 1.5,
        },
    }

    def __init__(self, task_type: str = "default"):
        """Initialize with task type.

        Args:
            task_type: Type of task for weight adjustment
        """
        super().__init__()
        self._task_type = task_type
        self._apply_task_weights()

    def _apply_task_weights(self) -> None:
        """Apply task-specific weights to scorers."""
        weights = self.TASK_WEIGHTS.get(self._task_type, {})

        for scorer in self._scorers:
            if scorer.dimension in weights:
                scorer.weight = weights[scorer.dimension]
