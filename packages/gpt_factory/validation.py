"""
Agent Validation Framework

Validates agent blueprints against quality standards before deployment.
Ensures instructions, knowledge, and governance are properly configured.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
import re

from .models import (
    AgentBlueprint,
    ValidationReport,
    ValidationStatus,
    ValidationIssue,
    TestScenario,
    TestResult,
)


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, category: str, severity: str = "warning"):
        self.category = category
        self.severity = severity

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        """Run validation and return any issues found."""
        raise NotImplementedError


class InstructionLengthRule(ValidationRule):
    """Validate instruction length and structure."""

    def __init__(self):
        super().__init__("instructions")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []
        instructions = blueprint.instructions

        # Check minimum length
        if len(instructions) < 500:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="Instructions are quite short. Consider adding more detail.",
                field="instructions",
                suggestion="Aim for at least 1000 characters of instructions."
            ))

        # Check for required sections
        required_sections = ["Role", "Boundaries", "Escalation"]
        for section in required_sections:
            if section.lower() not in instructions.lower():
                issues.append(ValidationIssue(
                    severity="warning",
                    category=self.category,
                    message=f"Instructions missing '{section}' section.",
                    field="instructions",
                    suggestion=f"Add a '## {section}' section to clarify agent behavior."
                ))

        return issues


class GuardrailsRule(ValidationRule):
    """Validate guardrails are properly defined."""

    def __init__(self):
        super().__init__("guardrails")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []

        # Check minimum guardrails
        if len(blueprint.guardrails) < 2:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="Agent has fewer than 2 guardrails defined.",
                field="guardrails",
                suggestion="Add guardrails to prevent unwanted agent behaviors."
            ))

        # Check for hard guardrails
        hard_guardrails = [g for g in blueprint.guardrails if g.severity == "hard"]
        if not hard_guardrails:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="No hard guardrails defined. Agent may lack necessary constraints.",
                field="guardrails",
                suggestion="Add at least one hard guardrail for critical boundaries."
            ))

        # Check guardrails have descriptions
        for guardrail in blueprint.guardrails:
            if not guardrail.description or len(guardrail.description) < 10:
                issues.append(ValidationIssue(
                    severity="info",
                    category=self.category,
                    message=f"Guardrail '{guardrail.name}' has a short/missing description.",
                    field="guardrails",
                    suggestion="Add a clear description explaining why this guardrail exists."
                ))

        return issues


class GovernanceRule(ValidationRule):
    """Validate governance configuration."""

    def __init__(self):
        super().__init__("governance")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []
        gov = blueprint.governance

        # Check grounding is enabled for sensitive domains
        sensitive_domains = ["HR", "Finance", "Legal", "PublicSafety", "PublicHealth"]
        if blueprint.domain in sensitive_domains:
            if not gov.require_grounding:
                issues.append(ValidationIssue(
                    severity="warning",
                    category=self.category,
                    message=f"Grounding not required for sensitive domain '{blueprint.domain}'.",
                    field="governance.require_grounding",
                    suggestion="Enable grounding for sensitive domains to ensure source attribution."
                ))

            if gov.min_grounding_score < 0.5:
                issues.append(ValidationIssue(
                    severity="warning",
                    category=self.category,
                    message="Low grounding threshold for sensitive domain.",
                    field="governance.min_grounding_score",
                    suggestion="Consider raising min_grounding_score to 0.5 or higher."
                ))

        # Check for PII escalation
        if "PII" not in gov.risk_escalations:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="No escalation rule for PII risks.",
                field="governance.risk_escalations",
                suggestion="Add 'PII' to risk_escalations to protect personal information."
            ))

        return issues


class CapabilitiesRule(ValidationRule):
    """Validate capabilities are well-defined."""

    def __init__(self):
        super().__init__("capabilities")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []

        # Check minimum capabilities
        if len(blueprint.capabilities) < 2:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="Agent has fewer than 2 capabilities defined.",
                field="capabilities",
                suggestion="Define clear capabilities to set user expectations."
            ))

        # Check capabilities have examples
        for cap in blueprint.capabilities:
            if not cap.examples:
                issues.append(ValidationIssue(
                    severity="info",
                    category=self.category,
                    message=f"Capability '{cap.name}' has no examples.",
                    field="capabilities",
                    suggestion="Add examples to help users understand what this capability means."
                ))

        return issues


class DescriptionRule(ValidationRule):
    """Validate descriptions are appropriate."""

    def __init__(self):
        super().__init__("description")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []

        # Short description checks
        short_desc = blueprint.description_short
        if len(short_desc) < 50:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="Short description is very brief.",
                field="description_short",
                suggestion="Expand description to clearly convey the agent's purpose."
            ))

        if len(short_desc) > 300:
            issues.append(ValidationIssue(
                severity="error",
                category=self.category,
                message="Short description exceeds 300 characters (OpenAI limit).",
                field="description_short",
                suggestion="Shorten description for OpenAI GPT export compatibility."
            ))

        # Check for marketing language
        marketing_words = ["best", "amazing", "revolutionary", "cutting-edge", "world-class"]
        for word in marketing_words:
            if word in short_desc.lower():
                issues.append(ValidationIssue(
                    severity="info",
                    category=self.category,
                    message=f"Description contains marketing language ('{word}').",
                    field="description_short",
                    suggestion="Use factual, professional language in descriptions."
                ))
                break

        return issues


class EscalationRule(ValidationRule):
    """Validate escalation paths are defined."""

    def __init__(self):
        super().__init__("escalation")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []

        # Check escalation target
        if not blueprint.escalates_to:
            issues.append(ValidationIssue(
                severity="warning",
                category=self.category,
                message="No escalation target defined.",
                field="escalates_to",
                suggestion="Define who this agent should escalate to when it can't help."
            ))

        # Check escalation mentioned in instructions
        if blueprint.escalates_to and "escalat" not in blueprint.instructions.lower():
            issues.append(ValidationIssue(
                severity="info",
                category=self.category,
                message="Escalation target defined but not mentioned in instructions.",
                field="instructions",
                suggestion="Add escalation guidance to the agent's instructions."
            ))

        return issues


class ConversationStartersRule(ValidationRule):
    """Validate conversation starters."""

    def __init__(self):
        super().__init__("conversation_starters")

    def validate(self, blueprint: AgentBlueprint) -> list[ValidationIssue]:
        issues = []

        starters = blueprint.conversation_starters

        # Check count
        if len(starters) < 2:
            issues.append(ValidationIssue(
                severity="info",
                category=self.category,
                message="Fewer than 2 conversation starters defined.",
                field="conversation_starters",
                suggestion="Add more conversation starters to guide user interactions."
            ))

        if len(starters) > 4:
            issues.append(ValidationIssue(
                severity="info",
                category=self.category,
                message="More than 4 conversation starters (OpenAI GPT limit).",
                field="conversation_starters",
                suggestion="Reduce to 4 for OpenAI GPT export compatibility."
            ))

        # Check for questions
        for starter in starters:
            if not starter.endswith("?"):
                issues.append(ValidationIssue(
                    severity="info",
                    category=self.category,
                    message=f"Conversation starter doesn't end with '?': '{starter[:30]}...'",
                    field="conversation_starters",
                    suggestion="Phrase conversation starters as questions."
                ))

        return issues


class AgentValidator:
    """
    Validates agent blueprints against enterprise quality standards.

    Runs a suite of validation rules and produces a comprehensive report.
    """

    def __init__(self):
        self.rules: list[ValidationRule] = [
            InstructionLengthRule(),
            GuardrailsRule(),
            GovernanceRule(),
            CapabilitiesRule(),
            DescriptionRule(),
            EscalationRule(),
            ConversationStartersRule(),
        ]
        self.test_scenarios: list[TestScenario] = []

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.rules.append(rule)

    def add_test_scenario(self, scenario: TestScenario) -> None:
        """Add a test scenario for validation."""
        self.test_scenarios.append(scenario)

    def validate(
        self,
        blueprint: AgentBlueprint,
        run_tests: bool = False,
    ) -> ValidationReport:
        """
        Validate an agent blueprint and produce a report.

        Args:
            blueprint: The agent blueprint to validate
            run_tests: Whether to run test scenarios (requires LLM)

        Returns:
            ValidationReport with issues and scores
        """
        issues: list[ValidationIssue] = []
        test_results: list[TestResult] = []

        # Run all validation rules
        for rule in self.rules:
            rule_issues = rule.validate(blueprint)
            issues.extend(rule_issues)

        # Run test scenarios if requested
        if run_tests and self.test_scenarios:
            test_results = self._run_test_scenarios(blueprint)

        # Calculate scores
        instruction_score = self._calculate_instruction_score(blueprint, issues)
        knowledge_score = self._calculate_knowledge_score(blueprint, issues)
        governance_score = self._calculate_governance_score(blueprint, issues)

        overall_score = (
            instruction_score * 0.4 +
            knowledge_score * 0.3 +
            governance_score * 0.3
        )

        # Determine status
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        if error_count > 0:
            status = ValidationStatus.FAILED
        elif warning_count > 3:
            status = ValidationStatus.WARNINGS
        else:
            status = ValidationStatus.PASSED

        return ValidationReport(
            agent_id=blueprint.id,
            status=status,
            issues=issues,
            test_results=test_results,
            overall_score=overall_score,
            instruction_score=instruction_score,
            knowledge_score=knowledge_score,
            governance_score=governance_score,
            validated_at=datetime.utcnow(),
        )

    def _calculate_instruction_score(
        self,
        blueprint: AgentBlueprint,
        issues: list[ValidationIssue],
    ) -> float:
        """Calculate instruction quality score."""
        score = 1.0

        # Deduct for instruction-related issues
        instruction_issues = [i for i in issues if i.category == "instructions"]
        for issue in instruction_issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.1

        # Bonus for well-structured instructions
        instructions = blueprint.instructions
        sections = instructions.count("## ")
        if sections >= 5:
            score += 0.1

        # Check for comprehensive coverage
        good_keywords = ["role", "help", "boundaries", "escalat", "tone"]
        matches = sum(1 for k in good_keywords if k in instructions.lower())
        score += matches * 0.02

        return max(0.0, min(1.0, score))

    def _calculate_knowledge_score(
        self,
        blueprint: AgentBlueprint,
        issues: list[ValidationIssue],
    ) -> float:
        """Calculate knowledge configuration score."""
        score = 0.5  # Base score (knowledge is optional)

        # Add points for having knowledge sources
        knowledge_count = len(blueprint.knowledge_sources)
        if knowledge_count > 0:
            score += min(0.3, knowledge_count * 0.05)

        # Add points for verified sources
        verified = sum(1 for k in blueprint.knowledge_sources if k.verified)
        if knowledge_count > 0:
            verification_rate = verified / knowledge_count
            score += verification_rate * 0.2

        return max(0.0, min(1.0, score))

    def _calculate_governance_score(
        self,
        blueprint: AgentBlueprint,
        issues: list[ValidationIssue],
    ) -> float:
        """Calculate governance configuration score."""
        score = 1.0

        # Deduct for governance-related issues
        gov_issues = [i for i in issues if i.category in ["governance", "guardrails", "escalation"]]
        for issue in gov_issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.1

        # Bonus for comprehensive governance
        gov = blueprint.governance
        if gov.require_grounding:
            score += 0.05
        if len(gov.risk_escalations) >= 3:
            score += 0.05
        if len(blueprint.guardrails) >= 3:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _run_test_scenarios(
        self,
        blueprint: AgentBlueprint,
    ) -> list[TestResult]:
        """Run test scenarios against the agent."""
        # Note: This would require LLM integration to actually test
        # For now, return empty results
        # In production, this would:
        # 1. Spin up the agent with the blueprint
        # 2. Send test queries
        # 3. Evaluate responses against expected behavior
        return []


def quick_validate(blueprint: AgentBlueprint) -> tuple[bool, list[str]]:
    """
    Quick validation that returns pass/fail and error messages.

    Useful for fast checks during development.
    """
    validator = AgentValidator()
    report = validator.validate(blueprint, run_tests=False)

    errors = [i.message for i in report.issues if i.severity == "error"]
    passed = report.status != ValidationStatus.FAILED

    return passed, errors
